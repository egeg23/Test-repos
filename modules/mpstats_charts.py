# modules/mpstats_charts.py - Парсер графиков Mpstats
"""
Парсинг графиков (цен, продаж, выручки) с Mpstats
Шаг 5 чеклиста: Парсинг графиков
"""

import json
import logging
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

try:
    from playwright.async_api import Page
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

logger = logging.getLogger('mpstats_charts')


class MpstatsChartParser:
    """
    📈 Парсер графиков Mpstats
    
    Извлекает данные графиков:
    - История цен
    - Динамика продаж
    - Выручка по дням
    - Остатки на складах
    """
    
    CHART_TYPES = {
        'price': 'История цен',
        'sales': 'Продажи',
        'revenue': 'Выручка',
        'stock': 'Остатки',
        'rating': 'Рейтинг'
    }
    
    def __init__(self, clients_dir: str = "/opt/clients"):
        self.clients_dir = Path(clients_dir)
        self.storage_dir = self.clients_dir / "GLOBAL_AI_LEARNING" / "charts"
        self.storage_dir.mkdir(parents=True, exist_ok=True)
    
    async def parse_all_charts(
        self,
        product_id: str,
        platform: str = "wb",
        days: int = 30
    ) -> Dict:
        """
        Парсит все доступные графики для товара
        
        Args:
            product_id: nmId или offer_id
            platform: "wb" или "ozon"
            days: Сколько дней истории собирать
            
        Returns:
            Dict со всеми графиками
        """
        if not PLAYWRIGHT_AVAILABLE:
            return {'error': 'Playwright not available'}
        
        from modules.mpstats_browser import MpstatsBrowserParser
        
        logger.info(f"📈 Parsing charts for {product_id}")
        
        result = {
            'product_id': product_id,
            'platform': platform,
            'parsed_at': datetime.now().isoformat(),
            'charts': {}
        }
        
        async with MpstatsBrowserParser(self.clients_dir) as parser:
            # Загружаем системную сессию
            session_loaded = await parser.load_session("system_mpstats")
            
            if not session_loaded:
                logger.error("❌ No system session")
                return {'error': 'Not authenticated'}
            
            # Открываем страницу товара
            url = f"https://mpstats.io/{platform}/item/{product_id}"
            await parser.page.goto(url, timeout=60000)
            await parser.page.wait_for_load_state('networkidle')
            await parser.page.wait_for_timeout(2000)
            
            # Парсим каждый тип графика
            for chart_type in self.CHART_TYPES.keys():
                try:
                    chart_data = await self._parse_chart(parser.page, chart_type, days)
                    if chart_data:
                        result['charts'][chart_type] = chart_data
                        logger.info(f"✅ {chart_type}: {len(chart_data.get('data', []))} points")
                except Exception as e:
                    logger.warning(f"⚠️ Failed to parse {chart_type}: {e}")
                    continue
        
        # Сохраняем
        await self._save_chart_data(result)
        
        return result
    
    async def _parse_chart(
        self,
        page: Page,
        chart_type: str,
        days: int
    ) -> Optional[Dict]:
        """
        Парсит конкретный график
        
        Стратегии:
        1. Пытаемся извлечь из window.__DATA__ или window.__INITIAL_STATE__
        2. Парсим SVG path данные
        3. Парсим canvas если есть
        """
        # Пробуем извлечь из JavaScript переменных
        js_data = await self._extract_from_js(page, chart_type)
        if js_data:
            return {
                'type': chart_type,
                'name': self.CHART_TYPES[chart_type],
                'data': js_data,
                'source': 'javascript'
            }
        
        # Пробуем извлечь из SVG
        svg_data = await self._extract_from_svg(page, chart_type)
        if svg_data:
            return {
                'type': chart_type,
                'name': self.CHART_TYPES[chart_type],
                'data': svg_data,
                'source': 'svg'
            }
        
        # Пробуем извлечь из таблицы данных (data table)
        table_data = await self._extract_from_table(page, chart_type)
        if table_data:
            return {
                'type': chart_type,
                'name': self.CHART_TYPES[chart_type],
                'data': table_data,
                'source': 'table'
            }
        
        return None
    
    async def _extract_from_js(self, page: Page, chart_type: str) -> Optional[List[Dict]]:
        """Извлекает данные графика из JavaScript переменных"""
        try:
            # Пробуем различные варианты именования
            scripts = await page.query_selector_all('script')
            
            for script in scripts:
                content = await script.inner_text()
                
                # Ищем данные графика в различных форматах
                patterns = [
                    rf'"{chart_type}"\s*:\s*(\[[^\]]+\])',
                    rf'{chart_type}Chart\s*[=:]\s*(\{{[^}}]+\}})',
                    rf'"{chart_type}History"\s*:\s*(\[[^\]]+\])',
                ]
                
                for pattern in patterns:
                    matches = re.findall(pattern, content, re.IGNORECASE)
                    for match in matches:
                        try:
                            data = json.loads(match)
                            if isinstance(data, list):
                                return self._normalize_chart_data(data, chart_type)
                        except:
                            continue
            
            # Пробуем извлечь через evaluate
            result = await page.evaluate(f"""
                () => {{
                    const sources = [
                        window.__DATA__?.charts?.{chart_type},
                        window.__INITIAL_STATE__?.charts?.{chart_type},
                        window.{chart_type}Data,
                        window.{chart_type}Chart
                    ];
                    return sources.find(s => s && Array.isArray(s)) || null;
                }}
            """)
            
            if result:
                return self._normalize_chart_data(result, chart_type)
            
            return None
            
        except Exception as e:
            logger.warning(f"⚠️ JS extraction error: {e}")
            return None
    
    async def _extract_from_svg(self, page: Page, chart_type: str) -> Optional[List[Dict]]:
        """Извлекает данные из SVG графика"""
        try:
            # Ищем SVG с данными
            svg_selector = f'.chart-{chart_type} svg, [data-chart="{chart_type}"] svg, .{chart_type}-chart svg'
            svg = await page.query_selector(svg_selector)
            
            if not svg:
                return None
            
            # Извлекаем path или circle элементы
            points = await svg.query_selector_all('circle, path, rect[data-value]')
            
            data = []
            for i, point in enumerate(points):
                try:
                    # Пробуем получить значение из data-атрибутов
                    value_attr = await point.get_attribute('data-value')
                    date_attr = await point.get_attribute('data-date')
                    
                    if value_attr:
                        data.append({
                            'date': date_attr or self._index_to_date(i, len(points)),
                            'value': float(value_attr)
                        })
                except:
                    continue
            
            return data if data else None
            
        except Exception as e:
            logger.warning(f"⚠️ SVG extraction error: {e}")
            return None
    
    async def _extract_from_table(self, page: Page, chart_type: str) -> Optional[List[Dict]]:
        """Извлекает данные из таблицы под графиком"""
        try:
            # Ищем таблицу с историческими данными
            table_selector = f'.chart-{chart_type}-table, [data-table="{chart_type}"], .{chart_type}-data-table'
            table = await page.query_selector(table_selector)
            
            if not table:
                return None
            
            rows = await table.query_selector_all('tbody tr')
            
            data = []
            for row in rows:
                cells = await row.query_selector_all('td')
                if len(cells) >= 2:
                    date_text = await cells[0].inner_text()
                    value_text = await cells[1].inner_text()
                    
                    data.append({
                        'date': date_text.strip(),
                        'value': self._parse_value(value_text)
                    })
            
            return data if data else None
            
        except Exception as e:
            logger.warning(f"⚠️ Table extraction error: {e}")
            return None
    
    def _normalize_chart_data(self, data: List, chart_type: str) -> List[Dict]:
        """Нормализует данные графика к единому формату"""
        normalized = []
        
        for item in data:
            if isinstance(item, dict):
                # Уже в нужном формате или почти
                date = item.get('date') or item.get('x') or item.get('day')
                value = item.get('value') or item.get('y') or item.get('price') or item.get('amount')
                
                if date and value is not None:
                    normalized.append({
                        'date': str(date),
                        'value': float(value)
                    })
            elif isinstance(item, (list, tuple)) and len(item) >= 2:
                # Формат [date, value]
                normalized.append({
                    'date': str(item[0]),
                    'value': float(item[1])
                })
        
        return normalized
    
    def _parse_value(self, text: str) -> float:
        """Парсит числовое значение из текста"""
        # Убираем валюту и пробелы
        cleaned = re.sub(r'[^\d.,]', '', text)
        cleaned = cleaned.replace(',', '.')
        try:
            return float(cleaned)
        except:
            return 0.0
    
    def _index_to_date(self, index: int, total: int, days: int = 30) -> str:
        """Конвертирует индекс точки в дату"""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        if total <= 1:
            return start_date.strftime('%Y-%m-%d')
        
        # Интерполируем дату
        ratio = index / (total - 1)
        delta = timedelta(days=int(ratio * days))
        date = start_date + delta
        
        return date.strftime('%Y-%m-%d')
    
    def calculate_trends(self, chart_data: Dict) -> Dict:
        """Рассчитывает тренды на основе графика"""
        if not chart_data or 'data' not in chart_data:
            return {}
        
        data = chart_data['data']
        if not data:
            return {}
        
        values = [d['value'] for d in data if 'value' in d]
        
        if not values:
            return {}
        
        # Базовые метрики
        trends = {
            'min': min(values),
            'max': max(values),
            'avg': sum(values) / len(values),
            'first': values[0],
            'last': values[-1],
            'change_abs': values[-1] - values[0],
            'change_percent': ((values[-1] - values[0]) / values[0] * 100) if values[0] else 0,
            'data_points': len(values)
        }
        
        # Тренд (растет/падает/стабильно)
        if trends['change_percent'] > 5:
            trends['trend'] = 'up'
        elif trends['change_percent'] < -5:
            trends['trend'] = 'down'
        else:
            trends['trend'] = 'stable'
        
        return trends
    
    async def _save_chart_data(self, data: Dict):
        """Сохраняет данные графиков"""
        filename = f"{data['platform']}_{data['product_id']}_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
        filepath = self.storage_dir / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"💾 Charts saved: {filepath}")
    
    def load_chart_data(self, filename: str) -> Optional[Dict]:
        """Загружает сохраненные данные графиков"""
        filepath = self.storage_dir / filename
        if not filepath.exists():
            return None
        
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def compare_price_history(
        self,
        product_id_1: str,
        product_id_2: str,
        days: int = 30
    ) -> Optional[Dict]:
        """Сравнивает историю цен двух товаров"""
        # Загружаем последние данные для обоих товаров
        files_1 = sorted(self.storage_dir.glob(f"*_{product_id_1}_*.json"))
        files_2 = sorted(self.storage_dir.glob(f"*_{product_id_2}_*.json"))
        
        if not files_1 or not files_2:
            return None
        
        with open(files_1[-1]) as f:
            data_1 = json.load(f)
        with open(files_2[-1]) as f:
            data_2 = json.load(f)
        
        chart_1 = data_1.get('charts', {}).get('price', {})
        chart_2 = data_2.get('charts', {}).get('price', {})
        
        trends_1 = self.calculate_trends(chart_1)
        trends_2 = self.calculate_trends(chart_2)
        
        return {
            'product_1': {'id': product_id_1, 'trends': trends_1},
            'product_2': {'id': product_id_2, 'trends': trends_2},
            'price_difference': trends_1.get('avg', 0) - trends_2.get('avg', 0),
            'comparison_date': datetime.now().isoformat()
        }
