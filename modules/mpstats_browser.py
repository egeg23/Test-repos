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
        """
        if not self.browser:
            raise RuntimeError("Browser not initialized")
        
        self.context = await self.browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        )
        self.page = await self.context.new_page()
        
        try:
            logger.info(f"🔐 Browser auth for {login}")
            
            await self.page.goto("https://mpstats.io/auth/login", timeout=30000)
            await self.page.wait_for_load_state('networkidle')
            
            await self.page.fill('input[name="email"], input[type="email"]', login)
            await self.page.fill('input[name="password"], input[type="password"]', password)
            
            await self.page.click('button[type="submit"], .btn-login, button:has-text("Войти")')
            await self.page.wait_for_timeout(3000)
            
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
        """Gets product data from Mpstats"""
        if not self.page:
            raise RuntimeError("Not authenticated")
        
        try:
            url = f"https://mpstats.io/{platform}/item/{product_id}"
            logger.info(f"🔍 Loading product: {url}")
            
            await self.page.goto(url, timeout=60000)
            await self.page.wait_for_load_state('networkidle')
            await self.page.wait_for_timeout(2000)
            
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
        }
        
        try:
            name_elem = await self.page.query_selector('h1, .product-name')
            if name_elem:
                data['name'] = await name_elem.inner_text()
            
            price_selectors = ['.price-current', '[data-testid="price"]', '.product-price']
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
            
            rating_elem = await self.page.query_selector('.rating, [data-testid="rating"]')
            if rating_elem:
                text = await rating_elem.inner_text()
                try:
                    data['rating'] = float(text.replace(',', '.'))
                except:
                    pass
            
            return data
            
        except Exception as e:
            logger.error(f"❌ Extraction error: {e}")
            return data
    
    async def save_session(self, client_id: str):
        """Saves browser session for reuse"""
        if not self.context:
            return
        
        session_dir = self.clients_dir / "GLOBAL_AI_LEARNING" / "mpstats_browser"
        session_dir.mkdir(parents=True, exist_ok=True)
        
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
