# cost_price_manager.py - Управление себестоимостью товаров
"""
Модуль для загрузки и управления себестоимостью товаров.
Поддерживает Excel, CSV, ручной ввод.
"""

import json
import logging
import csv
import io
from typing import Dict, List, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger('cost_price_manager')

@dataclass
class CostPriceEntry:
    """Запись о себестоимости"""
    artikul: str
    cost_price: float
    desired_margin: float = 30.0  # Желаемая маржа по умолчанию 30%
    updated_at: str = ""

class CostPriceManager:
    """Менеджер себестоимости"""
    
    def __init__(self, user_id: str, platform: str):
        self.user_id = user_id
        self.platform = platform
        self.data_dir = Path(f"/opt/clients/{user_id}/data")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.costs_file = self.data_dir / f"{platform}_cost_prices.json"
        self.costs: Dict[str, CostPriceEntry] = {}
        self._load()
    
    def _load(self):
        """Загружает сохраненные себестоимости"""
        if self.costs_file.exists():
            try:
                with open(self.costs_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for artikul, entry in data.items():
                        self.costs[artikul] = CostPriceEntry(**entry)
                logger.info(f"[CostPriceManager] Загружено {len(self.costs)} записей")
            except Exception as e:
                logger.error(f"[CostPriceManager] Ошибка загрузки: {e}")
    
    def _save(self):
        """Сохраняет себестоимости"""
        try:
            data = {
                artikul: {
                    'artikul': artikul,
                    'cost_price': entry.cost_price,
                    'desired_margin': entry.desired_margin,
                    'updated_at': entry.updated_at
                }
                for artikul, entry in self.costs.items()
            }
            with open(self.costs_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"[CostPriceManager] Ошибка сохранения: {e}")
    
    def set_cost_price(self, artikul: str, cost_price: float, desired_margin: float = 30.0):
        """Устанавливает себестоимость для артикула"""
        self.costs[artikul] = CostPriceEntry(
            artikul=artikul,
            cost_price=cost_price,
            desired_margin=desired_margin,
            updated_at=datetime.now().isoformat()
        )
        self._save()
    
    def get_cost_price(self, artikul: str) -> Optional[float]:
        """Возвращает себестоимость артикула"""
        entry = self.costs.get(artikul)
        return entry.cost_price if entry else None
    
    def get_margin(self, artikul: str, current_price: float) -> Optional[float]:
        """Вычисляет текущую маржу"""
        cost = self.get_cost_price(artikul)
        if not cost or cost == 0:
            return None
        return ((current_price - cost) / current_price) * 100
    
    def get_min_price(self, artikul: str) -> Optional[float]:
        """Возвращает минимальную цену с учетом желаемой маржи"""
        entry = self.costs.get(artikul)
        if not entry:
            return None
        # Минимальная цена = себестоимость / (1 - желаемая_маржа)
        # Например: себестоимость 100, маржа 30% → мин цена = 100 / 0.7 = 142.86
        margin_decimal = entry.desired_margin / 100
        if margin_decimal >= 1:
            return entry.cost_price * 2  # Защита от деления на ноль
        return entry.cost_price / (1 - margin_decimal)
    
    def parse_csv(self, csv_content: str) -> Tuple[int, int, List[str]]:
        """Парсит CSV/Excel содержимое
        
        Returns:
            (успешно_загружено, всего_строк, ошибки)
        """
        success_count = 0
        total_count = 0
        errors = []
        
        try:
            # Пробуем разные разделители
            for delimiter in [';', ',', '\t']:
                try:
                    reader = csv.DictReader(io.StringIO(csv_content), delimiter=delimiter)
                    rows = list(reader)
                    if len(rows) > 0:
                        break
                except:
                    continue
            else:
                # Если не удалось распарсить — пробуем как простой CSV
                reader = csv.reader(io.StringIO(csv_content))
                rows = []
                for row in reader:
                    if len(row) >= 2:
                        rows.append({'артикул': row[0], 'себестоимость': row[1]})
            
            for row in rows:
                total_count += 1
                try:
                    # Ищем колонки (разные варианты названий)
                    artikul = (
                        row.get('артикул') or 
                        row.get('Артикул') or 
                        row.get('artikul') or 
                        row.get('nmId') or
                        row.get('offer_id') or
                        ''
                    ).strip()
                    
                    cost_str = (
                        row.get('себестоимость') or 
                        row.get('Себестоимость') or 
                        row.get('cost_price') or 
                        row.get('cost') or
                        row.get('цена') or
                        ''
                    ).strip()
                    
                    margin_str = (
                        row.get('маржа') or 
                        row.get('Маржа') or 
                        row.get('margin') or 
                        row.get('desired_margin') or
                        '30'
                    ).strip()
                    
                    if not artikul or not cost_str:
                        errors.append(f"Строка {total_count}: пропущены артикул или себестоимость")
                        continue
                    
                    # Очищаем от пробелов и валюты
                    cost_str = cost_str.replace(' ', '').replace('₽', '').replace('руб', '')
                    cost_price = float(cost_str)
                    
                    margin = float(margin_str.replace('%', ''))
                    
                    self.set_cost_price(artikul, cost_price, margin)
                    success_count += 1
                    
                except ValueError as e:
                    errors.append(f"Строка {total_count}: неверный формат числа ({e})")
                except Exception as e:
                    errors.append(f"Строка {total_count}: ошибка ({e})")
            
        except Exception as e:
            errors.append(f"Ошибка парсинга файла: {e}")
        
        return success_count, total_count, errors
    
    def get_summary(self) -> Dict:
        """Возвращает сводку по себестоимостям"""
        if not self.costs:
            return {
                'total': 0,
                'avg_cost': 0,
                'avg_margin': 0
            }
        
        costs = [e.cost_price for e in self.costs.values()]
        margins = [e.desired_margin for e in self.costs.values()]
        
        return {
            'total': len(self.costs),
            'avg_cost': sum(costs) / len(costs),
            'avg_margin': sum(margins) / len(margins)
        }
    
    def has_cost_prices(self) -> bool:
        """Проверяет, загружены ли себестоимости"""
        return len(self.costs) > 0
    
    def export_template(self) -> str:
        """Возвращает шаблон CSV для загрузки"""
        return "артикул;себестоимость;маржа\n12345678;450;30\n87654321;1200;25"


# Утилита для быстрого доступа
def get_cost_price_manager(user_id: str, platform: str) -> CostPriceManager:
    """Фабричный метод для получения менеджера"""
    return CostPriceManager(user_id, platform)


__all__ = ['CostPriceManager', 'CostPriceEntry', 'get_cost_price_manager']