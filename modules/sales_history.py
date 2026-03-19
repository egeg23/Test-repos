# modules/sales_history.py - История продаж для прогнозирования
"""
Локальное хранение истории продаж для расчета средней скорости.
Обновляется каждый цикл автономной системы.
"""

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict

logger = logging.getLogger('sales_history')


@dataclass
class SalesRecord:
    """Запись о продажах за день"""
    date: str                    # YYYY-MM-DD
    product_id: str              # nmId для WB, offer_id для Ozon
    sales_qty: int              # Количество продаж
    revenue: float              # Выручка
    stock_end: int              # Остаток на конец дня
    
    @property
    def avg_daily_sales(self) -> float:
        """Совместимость с полем avg_daily_sales"""
        return float(self.sales_qty)


class SalesHistoryManager:
    """
    Управление историей продаж.
    Хранит данные локально для быстрого доступа.
    """
    
    def __init__(self, clients_dir: str = "/opt/clients"):
        self.clients_dir = Path(clients_dir)
        self.history_dir = self.clients_dir / "GLOBAL_AI_LEARNING" / "sales_history"
        self.history_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_history_file(self, client_id: str, platform: str) -> Path:
        """Путь к файлу истории клиента"""
        return self.history_dir / f"{client_id}_{platform}_sales.json"
    
    def add_daily_record(self, client_id: str, platform: str, record: SalesRecord):
        """Добавляет запись за день (вызывается каждый цикл)"""
        history_file = self._get_history_file(client_id, platform)
        
        # Загружаем существующую историю
        history = self._load_history(history_file)
        
        # Удаляем запись за этот день если есть (избегаем дублей)
        history = [h for h in history if not (
            h.get('date') == record.date and h.get('product_id') == record.product_id
        )]
        
        # Добавляем новую запись
        history.append(asdict(record))
        
        # Оставляем только последние 30 дней
        cutoff_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        history = [h for h in history if h.get('date', '') >= cutoff_date]
        
        # Сохраняем
        with open(history_file, 'w') as f:
            json.dump(history, f, indent=2)
    
    def add_daily_records_batch(self, client_id: str, platform: str, records: List[SalesRecord]):
        """Добавляет несколько записей за день"""
        for record in records:
            self.add_daily_record(client_id, platform, record)
        logger.info(f"💾 Сохранено {len(records)} записей истории для {platform}")
    
    def _load_history(self, history_file: Path) -> List[Dict]:
        """Загружает историю из файла"""
        if not history_file.exists():
            return []
        try:
            with open(history_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"❌ Ошибка загрузки истории: {e}")
            return []
    
    def get_product_history(self, client_id: str, platform: str, product_id: str, days: int = 14) -> List[Dict]:
        """Получает историю продаж товара за N дней"""
        history_file = self._get_history_file(client_id, platform)
        history = self._load_history(history_file)
        
        # Фильтруем по товару и дате
        cutoff_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        product_history = [
            h for h in history 
            if h.get('product_id') == product_id and h.get('date', '') >= cutoff_date
        ]
        
        # Сортируем по дате
        return sorted(product_history, key=lambda x: x.get('date', ''))
    
    def calculate_avg_daily_sales(self, client_id: str, platform: str, product_id: str, days: int = 7) -> float:
        """
        Рассчитывает среднюю скорость продаж за указанный период.
        Возвращает среднее количество продаж в день.
        """
        history = self.get_product_history(client_id, platform, product_id, days)
        
        if not history:
            return 0.0
        
        total_sales = sum(h.get('sales_qty', 0) for h in history)
        actual_days = len(history)
        
        if actual_days == 0:
            return 0.0
        
        avg = total_sales / actual_days
        logger.debug(f"📊 {product_id}: {total_sales} продаж за {actual_days} дней = {avg:.2f}/день")
        return avg
    
    def calculate_stock_days(self, current_stock: int, avg_daily_sales: float) -> float:
        """
        Рассчитывает сколько дней хватит запасов.
        B / A = C (дней)
        """
        if avg_daily_sales <= 0:
            return float('inf')  # Если не продается - запасов хватит "навсегда"
        return current_stock / avg_daily_sales
    
    def calculate_supply_needed(self, current_stock: int, avg_daily_sales: float, target_days: int = 17) -> int:
        """
        Рассчитывает сколько нужно заказать.
        supply_qty = avg_sales × target_days - current_stock
        """
        needed_stock = avg_daily_sales * target_days
        supply_qty = needed_stock - current_stock
        return max(0, int(supply_qty))  # Не меньше 0
    
    def check_two_day_alert(self, client_id: str, platform: str, product_id: str, current_stock_days: float, threshold: float = 17.0) -> bool:
        """
        Проверяет, было ли 2 дня подряд stock_days < threshold.
        Возвращает True если нужен алерт.
        """
        alert_file = self.clients_dir / "GLOBAL_AI_LEARNING" / f"{client_id}_{platform}_alerts.json"
        
        # Загружаем состояние алертов
        alerts = {}
        if alert_file.exists():
            try:
                with open(alert_file, 'r') as f:
                    alerts = json.load(f)
            except:
                pass
        
        product_key = product_id
        today = datetime.now().strftime('%Y-%m-%d')
        yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        
        # Текущее состояние
        is_low = current_stock_days < threshold
        
        # Проверяем историю
        product_alerts = alerts.get(product_key, {})
        was_low_yesterday = product_alerts.get(yesterday, False)
        
        # Сохраняем сегодняшнее состояние
        if product_key not in alerts:
            alerts[product_key] = {}
        alerts[product_key][today] = is_low
        
        # Очищаем старые записи (оставляем 7 дней)
        cutoff = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
        alerts[product_key] = {k: v for k, v in alerts[product_key].items() if k >= cutoff}
        
        # Сохраняем
        with open(alert_file, 'w') as f:
            json.dump(alerts, f, indent=2)
        
        # Алерт если 2 дня подряд
        if is_low and was_low_yesterday:
            logger.info(f"🚨 Двухдневный алерт для {product_id}: {current_stock_days:.1f} дней")
            return True
        
        return False
    
    def get_all_products_stats(self, client_id: str, platform: str) -> Dict[str, Dict]:
        """Возвращает статистику по всем товарам клиента"""
        history_file = self._get_history_file(client_id, platform)
        history = self._load_history(history_file)
        
        stats = {}
        for record in history:
            pid = record.get('product_id')
            if pid not in stats:
                stats[pid] = {'total_sales': 0, 'days_tracked': 0, 'last_stock': 0}
            stats[pid]['total_sales'] += record.get('sales_qty', 0)
            stats[pid]['days_tracked'] += 1
            stats[pid]['last_stock'] = record.get('stock_end', 0)
        
        # Добавляем среднюю скорость
        for pid in stats:
            days = stats[pid]['days_tracked']
            if days > 0:
                stats[pid]['avg_daily_sales'] = stats[pid]['total_sales'] / days
            else:
                stats[pid]['avg_daily_sales'] = 0
        
        return stats
    
    # ============================================================================
    # VELOCITY-BASED ANALYTICS (ЭТАП 2)
    # ============================================================================
    
    def get_product_velocity(self, client_id: str, platform: str, product_id: str, days: int = 7) -> Dict:
        """
        Рассчитывает скорость продаж товара (velocity)
        
        Returns:
            {
                'current_velocity': float,  # продаж в день
                'avg_velocity': float,      # средняя по истории
                'velocity_trend': str,      # 'increasing', 'stable', 'decreasing'
                'velocity_ratio': float,    # текущая / средняя
                'peak_velocity': float,
                'min_velocity': float
            }
        """
        history_file = self._get_history_file(client_id, platform)
        history = self._load_history(history_file)
        
        # Фильтруем по товару
        product_records = [r for r in history if r.get('product_id') == product_id]
        
        if not product_records:
            return {
                'current_velocity': 0,
                'avg_velocity': 0,
                'velocity_trend': 'unknown',
                'velocity_ratio': 1.0,
                'peak_velocity': 0,
                'min_velocity': 0
            }
        
        # Сортируем по дате
        product_records.sort(key=lambda x: x.get('date', ''))
        
        # Берем последние N дней
        recent_records = product_records[-days:] if len(product_records) > days else product_records
        
        # Текущая скорость (последние 3 дня)
        current_window = recent_records[-3:] if len(recent_records) >= 3 else recent_records
        current_velocity = sum(r.get('sales_qty', 0) for r in current_window) / len(current_window) if current_window else 0
        
        # Средняя скорость за весь период
        avg_velocity = sum(r.get('sales_qty', 0) for r in product_records) / len(product_records)
        
        # Пиковая и минимальная скорость
        velocities = [r.get('sales_qty', 0) for r in product_records]
        peak_velocity = max(velocities) if velocities else 0
        min_velocity = min(velocities) if velocities else 0
        
        # Тренд
        if len(recent_records) >= 2:
            first_half = recent_records[:len(recent_records)//2]
            second_half = recent_records[len(recent_records)//2:]
            
            first_avg = sum(r.get('sales_qty', 0) for r in first_half) / len(first_half) if first_half else 0
            second_avg = sum(r.get('sales_qty', 0) for r in second_half) / len(second_half) if second_half else 0
            
            if second_avg > first_avg * 1.2:
                velocity_trend = 'increasing'
            elif second_avg < first_avg * 0.8:
                velocity_trend = 'decreasing'
            else:
                velocity_trend = 'stable'
        else:
            velocity_trend = 'unknown'
        
        # Соотношение текущей к средней
        velocity_ratio = current_velocity / avg_velocity if avg_velocity > 0 else 1.0
        
        return {
            'current_velocity': round(current_velocity, 2),
            'avg_velocity': round(avg_velocity, 2),
            'velocity_trend': velocity_trend,
            'velocity_ratio': round(velocity_ratio, 2),
            'peak_velocity': peak_velocity,
            'min_velocity': min_velocity
        }
    
    def get_category_velocity_benchmark(self, client_id: str, platform: str, category: str) -> Dict:
        """
        Получает среднюю скорость продаж по категории (для сравнения)
        """
        # В реальности здесь был бы анализ всех товаров в категории
        # Пока возвращаем mock данные
        return {
            'category': category,
            'avg_velocity': 5.0,  # Средняя по категории
            'median_velocity': 4.5,
            'top_10_percent': 15.0,  # Верхние 10%
            'bottom_10_percent': 1.0  # Нижние 10%
        }
    
    def calculate_velocity_segments(self, client_id: str, platform: str) -> Dict[str, List[str]]:
        """
        Разбивает товары на сегменты по скорости продаж
        
        Returns:
            {
                'high_velocity': ['product_id_1', 'product_id_2'],  # >2x средней
                'normal_velocity': ['product_id_3'],                # 0.8-2x
                'low_velocity': ['product_id_4', 'product_id_5']    # <0.8x
            }
        """
        stats = self.get_all_products_stats(client_id, platform)
        
        # Рассчитываем среднюю скорость по всем товарам
        all_velocities = [s['avg_daily_sales'] for s in stats.values() if s['avg_daily_sales'] > 0]
        global_avg = sum(all_velocities) / len(all_velocities) if all_velocities else 1
        
        segments = {
            'high_velocity': [],
            'normal_velocity': [],
            'low_velocity': []
        }
        
        for product_id, stat in stats.items():
            velocity = stat['avg_daily_sales']
            ratio = velocity / global_avg if global_avg > 0 else 1
            
            if ratio > 2.0:
                segments['high_velocity'].append(product_id)
            elif ratio < 0.8:
                segments['low_velocity'].append(product_id)
            else:
                segments['normal_velocity'].append(product_id)
        
        return segments
