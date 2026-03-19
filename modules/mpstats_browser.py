# modules/mpstats_browser.py - Browser-based Mpstats parser
"""
Playwright-based parser for Mpstats.
Handles JavaScript rendering and dynamic content.
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
    logging.warning("Playwright not installed. Browser parsing unavailable.")

logger = logging.getLogger('mpstats_browser')


class MpstatsBrowserParser:
    """
    🔍 Mpstats Browser Parser
    
    Uses Playwright to render JavaScript and extract data.
    Each client has isolated browser context.
    """
    
    def __init__(self, clients_dir: str = "/opt/clients"):
        self.clients_dir = Path(clients_dir)
        self.browser = None
        self.context = None
        self.page = None
        self.playwright = None
    
    async def __aenter__(self):
        """Async context manager entry"""
        if not PLAYWRIGHT_AVAILABLE:
            raise RuntimeError("Playwright not installed")
        
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-dev-shm-usage']
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
    
    async def authenticate(self, login: str, password: str) -> bool:
        """
        Authenticates on Mpstats using browser
        
        Args:
            login: Email
            password: Password
            
        Returns:
            True if authenticated successfully
        """
        if not self.browser:
            raise RuntimeError("Browser not initialized. Use async context manager.")
        
        # Create new context and page
        self.context = await self.browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        )
        self.page = await self.context.new_page()
        
        try:
            logger.info(f"🔐 Browser auth for {login}")
            
            # Go to login page
            await self.page.goto("https://mpstats.io/auth/login", timeout=30000)
            await self.page.wait_for_load_state('networkidle')
            
            # Fill login form
            await self.page.fill('input[name="email"], input[type="email"]', login)
            await self.page.fill('input[name="password"], input[type="password"]', password)
            
            # Click login button
            await self.page.click('button[type="submit"], .btn-login, button:has-text("Войти")')
            
            # Wait for navigation
            await self.page.wait_for_timeout(3000)
            
            # Check if logged in
            current_url = self.page.url
            if 'dashboard' in current_url or 'login' not in current_url:
                logger.info("✅ Browser auth successful")
                return True
            else:
                logger.error(f"❌ Auth failed. Still on: {current_url}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Browser auth error: {e}")
            return False
    
    async def get_product_data(self, product_id: str, platform: str = "wb") -> Optional[Dict]:
        """
        Gets product data from Mpstats
        
        Args:
            product_id: nmId for WB or offer_id for Ozon
            platform: 'wb' or 'ozon'
            
        Returns:
            Product data dict or None
        """
        if not self.page:
            raise RuntimeError("Not authenticated. Call authenticate() first.")
        
        try:
            url = f"https://mpstats.io/{platform}/item/{product_id}"
            logger.info(f"🔍 Loading product: {url}")
            
            await self.page.goto(url, timeout=60000)
            await self.page.wait_for_load_state('networkidle')
            await self.page.wait_for_timeout(2000)  # Wait for JS render
            
            # Extract data from page
            data = await self._extract_product_data()
            
            return data
            
        except Exception as e:
            logger.error(f"❌ Error loading product {product_id}: {e}")
            return None
    
    async def _extract_product_data(self) -> Dict:
        """Extracts product data from current page"""
        data = {
            'extracted_at': datetime.now().isoformat(),
            'name': None,
            'price': None,
            'rating': None,
            'reviews': None,
            'sales': None,
            'revenue': None,
            'stock': None,
            'seller': None,
            'category': None,
        }
        
        try:
            # Product name
            name_elem = await self.page.query_selector('h1, .product-name, [data-testid="product-name"]')
            if name_elem:
                data['name'] = await name_elem.inner_text()
            
            # Price - try multiple selectors
            price_selectors = [
                '.price-current',
                '[data-testid="price"]',
                '.product-price',
                'span:has-text("₽")',
            ]
            for selector in price_selectors:
                try:
                    elem = await self.page.query_selector(selector)
                    if elem:
                        text = await elem.inner_text()
                        price_clean = text.replace(' ', '').replace('₽', '').replace(',', '')
                        data['price'] = float(price_clean)
                        break
                except:
                    continue
            
            # Rating
            rating_elem = await self.page.query_selector('.rating, [data-testid="rating"], .stars')
            if rating_elem:
                text = await rating_elem.inner_text()
                try:
                    data['rating'] = float(text.replace(',', '.'))
                except:
                    pass
            
            # Reviews count
            reviews_elem = await self.page.query_selector('.reviews-count, [data-testid="reviews"]')
            if reviews_elem:
                text = await reviews_elem.inner_text()
                try:
                    data['reviews'] = int(text.replace(' ', '').replace('отзывов', '').replace('отзыва', ''))
                except:
                    pass
            
            # Try to get data from page scripts (window.__INITIAL_STATE__ etc.)
            page_data = await self.page.evaluate('''() => {
                // Try to find data in common places
                if (window.__INITIAL_STATE__) return window.__INITIAL_STATE__;
                if (window.__DATA__) return window.__DATA__;
                if (window.appData) return window.appData;
                return null;
            }''')
            
            if page_data:
                logger.debug(f"Found page data: {type(page_data)}")
                # Merge with extracted data
                self._merge_page_data(data, page_data)
            
            return data
            
        except Exception as e:
            logger.error(f"❌ Extraction error: {e}")
            return data
    
    def _merge_page_data(self, data: Dict, page_data: dict):
        """Merges data from page scripts"""
        try:
            # Navigate through common structures
            if isinstance(page_data, dict):
                # Try product key
                if 'product' in page_data:
                    product = page_data['product']
                    if 'price' in product and not data['price']:
                        data['price'] = float(product['price'])
                    if 'name' in product and not data['name']:
                        data['name'] = product['name']
                    if 'rating' in product and not data['rating']:
                        data['rating'] = float(product['rating'])
                
                # Try item key
                if 'item' in page_data:
                    item = page_data['item']
                    if isinstance(item, dict):
                        if 'price' in item and not data['price']:
                            data['price'] = float(item['price'])
                        if 'nmId' in item:
                            data['product_id'] = item['nmId']
        except Exception as e:
            logger.debug(f"Could not merge page data: {e}")
    
    async def get_competitor_prices(self, product_id: str, platform: str = "wb") -> List[Dict]:
        """
        Gets competitor prices for a product
        
        Returns:
            List of competitor data: [{seller, price, rating, reviews}, ...]
        """
        competitors = []
        
        try:
            # Navigate to competitors/sellers section if exists
            # This depends on Mpstats UI structure
            
            # Try to find competitor data in page
            comp_data = await self.page.evaluate('''() => {
                const sellers = [];
                // Look for seller elements
                document.querySelectorAll('.seller-item, .competitor-row, [data-seller]').forEach(el => {
                    const priceEl = el.querySelector('.price, [data-price]');
                    const sellerEl = el.querySelector('.seller-name, [data-seller]');
                    if (priceEl && sellerEl) {
                        sellers.push({
                            seller: sellerEl.innerText.trim(),
                            price: priceEl.innerText.trim()
                        });
                    }
                });
                return sellers;
            }''')
            
            if comp_data:
                for item in comp_data:
                    try:
                        price_clean = item['price'].replace(' ', '').replace('₽', '').replace(',', '')
                        competitors.append({
                            'seller': item['seller'],
                            'price': float(price_clean)
                        })
                    except:
                        continue
            
            return competitors
            
        except Exception as e:
            logger.error(f"❌ Error getting competitors: {e}")
            return []
    
    async def save_session(self, client_id: str):
        """Saves browser session for reuse"""
        if not self.context:
            return
        
        session_dir = self.clients_dir / "GLOBAL_AI_LEARNING" / "mpstats_browser"
        session_dir.mkdir(parents=True, exist_ok=True)
        
        # Save storage state (cookies, localStorage)
        storage_state = await self.context.storage_state()
        state_file = session_dir / f"{client_id}_storage.json"
        
        with open(state_file, 'w') as f:
            json.dump(storage_state, f)
        
        logger.info(f"✅ Browser session saved for {client_id}")
    
    async def load_session(self, client_id: str) -> bool:
        """Loads browser session if exists"""
        state_file = self.clients_dir / "GLOBAL_AI_LEARNING" / "mpstats_browser" / f"{client_id}_storage.json"
        
        if not state_file.exists():
            return False
        
        try:
            with open(state_file) as f:
                storage_state = json.load(f)
            
            self.context = await self.browser.new_context(storage_state=storage_state)
            self.page = await self.context.new_page()
            
            logger.info(f"✅ Browser session loaded for {client_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to load session: {e}")
            return False
