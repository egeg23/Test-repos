# modules/mpstats_competitors.py - Парсер списка конкурентов
"""
Парсинг списка конкурентов с Mpstats
Шаг 6 чеклиста: Получение списка конкурентов
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

try:
    from playwright.async_api import Page
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

logger = logging.getLogger('mpstats_competitors')


class MpstatsCompetitorParser:
    """
    🏆 Парсер конкурентов Mpstats
    
    Собирает данные о конкурентах:
    - Прямые конкуренты по товару
    - Конкуренты в категории
    - Анализ позиций в поиске
    - Сравнение метрик
    """
    
    def __init__(self, clients_dir: str = "/opt/clients"):
        self.clients_dir = Path(clients_dir)
        self.storage_dir = self.clients_dir / "GLOBAL_AI_LEARNING" / "competitors"
        self.storage_dir.mkdir(parents=True, exist_ok=True)
    
    async def get_product_competitors(
        self,
        product_id: str,
        platform: str = "wb",
        limit: int = 20
    ) -> Optional[Dict]:
        """
        Получает список конкурентов для конкретного товара
        
        Args:
            product_id: nmId или offer_id
            platform: "wb" или "ozon"
            limit: Максимум конкурентов
            
        Returns:
            Dict с данными конкурентов и анализом
        """
        if not PLAYWRIGHT_AVAILABLE:
            return {'error': 'Playwright not available'}
        
        from modules.mpstats_browser import MpstatsBrowserParser
        
        logger.info(f"🏆 Getting competitors for {product_id}")
        
        result = {
            'product_id': product_id,
            'platform': platform,
            'parsed_at': datetime.now().isoformat(),
            'competitors': [],
            'analysis': {}
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
            
            # Ищем секцию конкурентов
            competitors = await self._extract_competitors_from_page(parser.page, limit)
            result['competitors'] = competitors
            
            # Получаем данные нашего товара для сравнения
            our_product = await self._extract_our_product_data(parser.page)
            result['our_product'] = our_product
            
            # Анализируем конкурентов
            result['analysis'] = self._analyze_competitors(competitors, our_product)
        
        # Сохраняем
        await self._save_competitor_data(result)
        
        logger.info(f"✅ Found {len(competitors)} competitors")
        return result
    
    async def get_category_competitors(
        self,
        category_id: str,
        platform: str = "wb",
        top_n: int = 50
    ) -> Optional[Dict]:
        """
        Получает топ конкурентов в категории
        
        Args:
            category_id: ID категории
            platform: "wb" или "ozon"
            top_n: Сколько топовых собрать
        """
        if not PLAYWRIGHT_AVAILABLE:
            return {'error': 'Playwright not available'}
        
        from modules.mpstats_browser import MpstatsBrowserParser
        
        logger.info(f"🏆 Getting top {top_n} in category {category_id}")
        
        result = {
            'category_id': category_id,
            'platform': platform,
            'parsed_at': datetime.now().isoformat(),
            'top_sellers': [],
            'market_share': {}
        }
        
        async with MpstatsBrowserParser(self.clients_dir) as parser:
            session_loaded = await parser.load_session("system_mpstats")
            
            if not session_loaded:
                return {'error': 'Not authenticated'}
            
            # Открываем категорию
            url = f"https://mpstats.io/{platform}/category/{category_id}?sort=sales&order=desc"
            await parser.page.goto(url, timeout=60000)
            await parser.page.wait_for_load_state('networkidle')
            await parser.page.wait_for_timeout(3000)
            
            # Собираем топ товаров
            top_products = await self._extract_top_products(parser.page, top_n)
            result['top_products'] = top_products
            
            # Анализируем долю рынка
            result['market_share'] = self._calculate_market_share(top_products)
        
        await self._save_competitor_data(result, suffix="category")
        
        return result
    
    async def _extract_competitors_from_page(self, page: Page, limit: int) -> List[Dict]:
        """Извлекает конкурентов со страницы товара"""
        competitors = []
        
        try:
            # Ищем секцию "Похожие товары" или "Конкуренты"
            section_selectors = [
                '.competitors-section',
                '.similar-products',
                '[data-section="competitors"]',
                '.related-items'
            ]
            
            section = None
            for selector in section_selectors:
                section = await page.query_selector(selector)
                if section:
                    break
            
            if not section:
                # Пробуем найти таблицу конкурентов
                return await self._extract_from_competitors_table(page, limit)
            
            # Извлекаем карточки конкурентов
            cards = await section.query_selector_all('.product-card, .item-card, .competitor-item')
            
            for card in cards[:limit]:
                try:
                    competitor = await self._parse_competitor_card(card)
                    if competitor:
                        competitors.append(competitor)
                except Exception as e:
                    logger.warning(f"⚠️ Failed to parse competitor card: {e}")
                    continue
            
            return competitors
            
        except Exception as e:
            logger.error(f"❌ Competitor extraction error: {e}")
            return []
    
    async def _extract_from_competitors_table(self, page: Page, limit: int) -> List[Dict]:
        """Извлекает из таблицы конкурентов"""
        competitors = []
        
        try:
            # Ищем таблицу
            table = await page.query_selector('.competitors-table, [data-table="competitors"]')
            
            if not table:
                return []
            
            rows = await table.query_selector_all('tbody tr')
            
            for row in rows[:limit]:
                try:
                    cells = await row.query_selector_all('td')
                    if len(cells) < 3:
                        continue
                    
                    competitor = {
                        'nmId': await self._get_cell_text(cells[0]),
                        'name': await self._get_cell_text(cells[1]),
                        'price': self._parse_price(await self._get_cell_text(cells[2])),
                        'rating': self._parse_rating(await self._get_cell_text(cells[3])) if len(cells) > 3 else None,
                        'seller': await self._get_cell_text(cells[4]) if len(cells) > 4 else None,
                        'position': self._parse_int(await self._get_cell_text(cells[5])) if len(cells) > 5 else None,
                        'source': 'competitors_table'
                    }
                    
                    competitors.append(competitor)
                    
                except Exception as e:
                    logger.warning(f"⚠️ Row parse error: {e}")
                    continue
            
            return competitors
            
        except Exception as e:
            logger.warning(f"⚠️ Table extraction error: {e}")
            return []
    
    async def _parse_competitor_card(self, card) -> Optional[Dict]:
        """Парсит карточку конкурента"""
        try:
            competitor = {
                'nmId': None,
                'name': None,
                'price': None,
                'rating': None,
                'seller': None,
                'source': 'card'
            }
            
            # ID товара
            id_elem = await card.query_selector('.product-id, [data-id]')
            if id_elem:
                competitor['nmId'] = await id_elem.inner_text()
            
            # Название
            name_elem = await card.query_selector('.product-name, .item-name, h3, h4')
            if name_elem:
                competitor['name'] = await name_elem.inner_text()
            
            # Цена
            price_elem = await card.query_selector('.price, .product-price')
            if price_elem:
                price_text = await price_elem.inner_text()
                competitor['price'] = self._parse_price(price_text)
            
            # Рейтинг
            rating_elem = await card.query_selector('.rating, .stars')
            if rating_elem:
                rating_text = await rating_elem.inner_text()
                competitor['rating'] = self._parse_rating(rating_text)
            
            # Продавец
            seller_elem = await card.query_selector('.seller, .store-name')
            if seller_elem:
                competitor['seller'] = await seller_elem.inner_text()
            
            return competitor if competitor['nmId'] else None
            
        except Exception as e:
            logger.warning(f"⚠️ Card parse error: {e}")
            return None
    
    async def _extract_our_product_data(self, page: Page) -> Dict:
        """Извлекает данные нашего товара для сравнения"""
        try:
            data = {
                'price': None,
                'rating': None,
                'reviews': None,
                'sales_30d': None,
                'position': None
            }
            
            # Цена
            price_elem = await page.query_selector('.price-current, .product-price-main')
            if price_elem:
                price_text = await price_elem.inner_text()
                data['price'] = self._parse_price(price_text)
            
            # Рейтинг
            rating_elem = await page.query_selector('.rating-value, .product-rating')
            if rating_elem:
                rating_text = await rating_elem.inner_text()
                data['rating'] = self._parse_rating(rating_text)
            
            return data
            
        except Exception as e:
            logger.warning(f"⚠️ Our product extraction error: {e}")
            return {}
    
    async def _extract_top_products(self, page: Page, top_n: int) -> List[Dict]:
        """Извлекает топ товары из категории"""
        from modules.mpstats_category import MpstatsCategoryParser
        
        category_parser = MpstatsCategoryParser(self.clients_dir)
        products = await category_parser._extract_products_from_page(page)
        
        return products[:top_n]
    
    def _analyze_competitors(self, competitors: List[Dict], our_product: Dict) -> Dict:
        """Анализирует конкурентов"""
        if not competitors:
            return {}
        
        prices = [c['price'] for c in competitors if c.get('price')]
        ratings = [c['rating'] for c in competitors if c.get('rating')]
        
        analysis = {
            'total_competitors': len(competitors),
            'with_price_data': len(prices),
            'with_rating_data': len(ratings),
            'price_analysis': {
                'min': min(prices) if prices else None,
                'max': max(prices) if prices else None,
                'avg': sum(prices) / len(prices) if prices else None,
            },
            'rating_analysis': {
                'min': min(ratings) if ratings else None,
                'max': max(ratings) if ratings else None,
                'avg': sum(ratings) / len(ratings) if ratings else None,
            }
        }
        
        # Сравнение с нашим товаром
        if our_product and our_product.get('price') and prices:
            our_price = our_product['price']
            analysis['our_position'] = {
                'price_vs_avg': our_price - analysis['price_analysis']['avg'],
                'price_vs_min': our_price - analysis['price_analysis']['min'],
                'price_vs_max': our_price - analysis['price_analysis']['max'],
                'is_cheapest': our_price <= analysis['price_analysis']['min'],
                'is_most_expensive': our_price >= analysis['price_analysis']['max']
            }
        
        # Топ конкуренты по цене
        sorted_by_price = sorted(
            [c for c in competitors if c.get('price')],
            key=lambda x: x['price']
        )
        analysis['cheapest_competitors'] = sorted_by_price[:3]
        analysis['most_expensive_competitors'] = sorted_by_price[-3:][::-1]
        
        return analysis
    
    def _calculate_market_share(self, top_products: List[Dict]) -> Dict:
        """Рассчитывает долю рынка по топ товарам"""
        if not top_products:
            return {}
        
        # Группируем по продавцам
        seller_sales = {}
        for product in top_products:
            seller = product.get('seller', 'Unknown')
            sales = product.get('sales_30d', 0) or 0
            
            if seller not in seller_sales:
                seller_sales[seller] = 0
            seller_sales[seller] += sales
        
        total_sales = sum(seller_sales.values())
        
        # Считаем доли
        market_share = {}
        for seller, sales in sorted(seller_sales.items(), key=lambda x: x[1], reverse=True):
            market_share[seller] = {
                'sales_30d': sales,
                'share_percent': (sales / total_sales * 100) if total_sales > 0 else 0
            }
        
        return market_share
    
    async def _get_cell_text(self, cell) -> str:
        """Получает текст из ячейки"""
        try:
            text = await cell.inner_text()
            return text.strip()
        except:
            return ""
    
    def _parse_price(self, text: str) -> Optional[float]:
        """Парсит цену"""
        try:
            cleaned = ''.join(c for c in text if c.isdigit())
            return float(cleaned) if cleaned else None
        except:
            return None
    
    def _parse_rating(self, text: str) -> Optional[float]:
        """Парсит рейтинг"""
        try:
            text = text.replace(',', '.')
            cleaned = ''.join(c for c in text if c.isdigit() or c == '.')
            return float(cleaned) if cleaned else None
        except:
            return None
    
    def _parse_int(self, text: str) -> Optional[int]:
        """Парсит целое число"""
        try:
            cleaned = ''.join(c for c in text if c.isdigit())
            return int(cleaned) if cleaned else None
        except:
            return None
    
    async def _save_competitor_data(self, data: Dict, suffix: str = ""):
        """Сохраняет данные конкурентов"""
        base_name = f"{data.get('platform', 'unknown')}_{data.get('product_id') or data.get('category_id')}"
        filename = f"{base_name}_{suffix}_{datetime.now().strftime('%Y%m%d')}.json" if suffix else f"{base_name}_{datetime.now().strftime('%Y%m%d')}.json"
        
        filepath = self.storage_dir / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"💾 Competitors saved: {filepath}")
    
    def generate_competitor_report(self, data: Dict) -> str:
        """Генерирует текстовый отчет о конкурентах"""
        if not data or 'competitors' not in data:
            return "Нет данных о конкурентах"
        
        report = f"🏆 <b>Анализ конкурентов</b>\n\n"
        report += f"📦 Товар: <code>{data['product_id']}</code>\n"
        report += f"🛒 {data['platform'].upper()}\n"
        report += f"📊 Найдено конкурентов: {len(data['competitors'])}\n\n"
        
        analysis = data.get('analysis', {})
        
        if analysis.get('price_analysis'):
            pa = analysis['price_analysis']
            report += f"<b>Цены конкурентов:</b>\n"
            report += f"• Мин: {pa['min']:,.0f} ₽\n" if pa.get('min') else ""
            report += f"• Средняя: {pa['avg']:,.0f} ₽\n" if pa.get('avg') else ""
            report += f"• Макс: {pa['max']:,.0f} ₽\n" if pa.get('max') else ""
            report += "\n"
        
        if analysis.get('our_position'):
            op = analysis['our_position']
            report += f"<b>Ваша позиция:</b>\n"
            if op.get('price_vs_avg'):
                diff = op['price_vs_avg']
                emoji = "🔺" if diff > 0 else "🔻"
                report += f"{emoji} Отличие от среднего: {diff:+.0f} ₽\n"
            if op.get('is_cheapest'):
                report += "✅ Вы самые дешевые!\n"
            elif op.get('is_most_expensive'):
                report += "⚠️ Вы самые дорогие\n"
        
        # Топ 3 дешевых
        cheap = analysis.get('cheapest_competitors', [])
        if cheap:
            report += f"\n<b>Самые дешевые:</b>\n"
            for i, c in enumerate(cheap[:3], 1):
                price = c.get('price')
                name = c.get('name', 'Unknown')[:30]
                report += f"{i}. {name} — {price:,.0f} ₽\n" if price else ""
        
        return report
