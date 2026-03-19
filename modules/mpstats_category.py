# modules/mpstats_category.py - Парсер категорий Mpstats
"""
Парсинг категорий WB/Ozon через Mpstats
Следующий шаг чеклиста: Парсинг категории
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

try:
    from playwright.async_api import async_playwright, Page, Browser
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

logger = logging.getLogger('mpstats_category')


class MpstatsCategoryParser:
    """
    📁 Парсер категорий Mpstats
    
    Собирает данные по всем товарам в категории:
    - Список товаров с метриками
    - Цены, рейтинги, продажи
    - Динамика изменений
    """
    
    def __init__(self, clients_dir: str = "/opt/clients"):
        self.clients_dir = Path(clients_dir)
        self.storage_dir = self.clients_dir / "GLOBAL_AI_LEARNING" / "category_data"
        self.storage_dir.mkdir(parents=True, exist_ok=True)
    
    async def parse_category(
        self,
        category_id: str,
        platform: str = "wb",
        max_pages: int = 5,
        min_price: Optional[int] = None,
        max_price: Optional[int] = None
    ) -> Optional[Dict]:
        """
        Парсит категорию и возвращает данные
        
        Args:
            category_id: ID категории (например "elektronika" или числовой ID)
            platform: "wb" или "ozon"
            max_pages: Сколько страниц парсить (1 страница ≈ 100 товаров)
            min_price: Минимальная цена для фильтра
            max_price: Максимальная цена для фильтра
        """
        if not PLAYWRIGHT_AVAILABLE:
            logger.error("❌ Playwright not installed")
            return None
        
        from modules.mpstats_browser import MpstatsBrowserParser
        
        logger.info(f"📁 Parsing category {category_id} on {platform}")
        
        async with MpstatsBrowserParser(self.clients_dir) as parser:
            # Загружаем системную сессию
            system_client = "system_mpstats"
            session_loaded = await parser.load_session(system_client)
            
            if not session_loaded:
                logger.warning("⚠️ No session found, need auth first")
                return None
            
            # Формируем URL категории
            url = f"https://mpstats.io/{platform}/category/{category_id}"
            if min_price or max_price:
                url += f"?priceFrom={min_price or ''}&priceTo={max_price or ''}"
            
            logger.info(f"🔍 Loading: {url}")
            
            try:
                await parser.page.goto(url, timeout=60000)
                await parser.page.wait_for_load_state('networkidle')
                await parser.page.wait_for_timeout(3000)  # Ждем загрузку таблицы
                
                # Ждем появления таблицы товаров
                await parser.page.wait_for_selector(
                    '.category-table, [data-table="products"], .products-grid',
                    timeout=10000
                )
                
                # Собираем данные
                products = await self._extract_products_from_page(parser.page)
                
                # Если нужно больше страниц
                all_products = products.copy()
                for page_num in range(2, max_pages + 1):
                    next_page_products = await self._go_to_next_page(parser.page)
                    if not next_page_products:
                        break
                    all_products.extend(next_page_products)
                    logger.info(f"📄 Page {page_num}: +{len(next_page_products)} products")
                
                # Формируем результат
                result = {
                    'category_id': category_id,
                    'platform': platform,
                    'parsed_at': datetime.now().isoformat(),
                    'total_products': len(all_products),
                    'filters': {
                        'min_price': min_price,
                        'max_price': max_price
                    },
                    'products': all_products,
                    'statistics': self._calculate_statistics(all_products)
                }
                
                # Сохраняем
                await self._save_category_data(result)
                
                logger.info(f"✅ Category parsed: {len(all_products)} products")
                return result
                
            except Exception as e:
                logger.error(f"❌ Category parsing error: {e}")
                return None
    
    async def _extract_products_from_page(self, page: Page) -> List[Dict]:
        """Извлекает товары с текущей страницы"""
        products = []
        
        try:
            # Ищем строки таблицы товаров
            rows = await page.query_selector_all(
                '.category-table tbody tr, '
                '[data-table="products"] tr, '
                '.product-row'
            )
            
            for row in rows:
                try:
                    product = await self._parse_product_row(row)
                    if product:
                        products.append(product)
                except Exception as e:
                    logger.warning(f"⚠️ Failed to parse row: {e}")
                    continue
            
            return products
            
        except Exception as e:
            logger.error(f"❌ Extraction error: {e}")
            return []
    
    async def _parse_product_row(self, row) -> Optional[Dict]:
        """Парсит одну строку таблицы"""
        try:
            # Пытаемся извлечь данные разными селекторами
            product = {
                'nmId': None,
                'name': None,
                'price': None,
                'rating': None,
                'reviews': None,
                'sales_30d': None,
                'revenue_30d': None,
                'seller': None,
                'stock': None
            }
            
            # ID товара
            id_elem = await row.query_selector('.product-id, [data-id], td:first-child a')
            if id_elem:
                id_text = await id_elem.inner_text()
                product['nmId'] = id_text.strip()
            
            # Название
            name_elem = await row.query_selector('.product-name, .item-name, td:nth-child(2)')
            if name_elem:
                product['name'] = await name_elem.inner_text()
            
            # Цена
            price_elem = await row.query_selector('.price, .product-price, td:nth-child(3)')
            if price_elem:
                price_text = await price_elem.inner_text()
                product['price'] = self._parse_price(price_text)
            
            # Рейтинг
            rating_elem = await row.query_selector('.rating, .stars, td:nth-child(4)')
            if rating_elem:
                rating_text = await rating_elem.inner_text()
                product['rating'] = self._parse_float(rating_text)
            
            # Продажи за 30 дней
            sales_elem = await row.query_selector('.sales, [data-metric="sales"], td:nth-child(5)')
            if sales_elem:
                sales_text = await sales_elem.inner_text()
                product['sales_30d'] = self._parse_int(sales_text)
            
            # Продавец
            seller_elem = await row.query_selector('.seller, .store-name, td:nth-child(6)')
            if seller_elem:
                product['seller'] = await seller_elem.inner_text()
            
            return product if product['nmId'] else None
            
        except Exception as e:
            logger.warning(f"⚠️ Row parse error: {e}")
            return None
    
    async def _go_to_next_page(self, page: Page) -> List[Dict]:
        """Переходит на следующую страницу и возвращает товары"""
        try:
            # Ищем кнопку "Следующая" или пагинацию
            next_btn = await page.query_selector(
                '.pagination .next, [data-action="next-page"], button:has-text("→")'
            )
            
            if not next_btn:
                return []
            
            # Проверяем, не disabled ли кнопка
            is_disabled = await next_btn.get_attribute('disabled')
            if is_disabled:
                return []
            
            # Кликаем и ждем загрузки
            await next_btn.click()
            await page.wait_for_timeout(2000)
            
            # Ждем обновления таблицы
            await page.wait_for_selector('.category-table tbody tr', timeout=10000)
            
            # Собираем товары
            return await self._extract_products_from_page(page)
            
        except Exception as e:
            logger.warning(f"⚠️ Next page error: {e}")
            return []
    
    def _parse_price(self, text: str) -> Optional[float]:
        """Парсит цену из текста"""
        try:
            # Убираем все кроме цифр
            cleaned = ''.join(c for c in text if c.isdigit())
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
    
    def _parse_float(self, text: str) -> Optional[float]:
        """Парсит float"""
        try:
            # Заменяем запятую на точку
            text = text.replace(',', '.')
            cleaned = ''.join(c for c in text if c.isdigit() or c == '.')
            return float(cleaned) if cleaned else None
        except:
            return None
    
    def _calculate_statistics(self, products: List[Dict]) -> Dict:
        """Считает статистику по категории"""
        if not products:
            return {}
        
        prices = [p['price'] for p in products if p.get('price')]
        ratings = [p['rating'] for p in products if p.get('rating')]
        sales = [p['sales_30d'] for p in products if p.get('sales_30d')]
        
        stats = {
            'avg_price': sum(prices) / len(prices) if prices else 0,
            'min_price': min(prices) if prices else 0,
            'max_price': max(prices) if prices else 0,
            'avg_rating': sum(ratings) / len(ratings) if ratings else 0,
            'total_sales_30d': sum(sales) if sales else 0,
            'active_sellers': len(set(p['seller'] for p in products if p.get('seller')))
        }
        
        return stats
    
    async def _save_category_data(self, data: Dict):
        """Сохраняет данные категории"""
        filename = f"{data['platform']}_{data['category_id']}_{datetime.now().strftime('%Y%m%d')}.json"
        filepath = self.storage_dir / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"💾 Saved to {filepath}")
    
    def get_saved_categories(self) -> List[str]:
        """Возвращает список сохраненных категорий"""
        files = list(self.storage_dir.glob("*.json"))
        return [f.stem for f in files]
    
    def load_category_data(self, filename: str) -> Optional[Dict]:
        """Загружает сохраненные данные"""
        filepath = self.storage_dir / filename
        if not filepath.exists():
            return None
        
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
