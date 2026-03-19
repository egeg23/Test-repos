# modules/mpstats_auth.py - Авторизация и работа с Mpstats
"""
Mpstats Authenticator - авторизация через логин/пароль
и эмуляция ручных запросов (парсинг HTML)

⚠️ Нет официального API — используем requests + BeautifulSoup
"""

import json
import logging
import pickle
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
import requests
from bs4 import BeautifulSoup

logger = logging.getLogger('mpstats_auth')


class MpstatsAuthenticator:
    """
    🤖 Mpstats Authenticator
    
    Авторизация через логин/пароль с сохранением сессии.
    Для каждого клиента — отдельная сессия.
    """
    
    BASE_URL = "https://mpstats.io"
    LOGIN_URL = "https://mpstats.io/auth/login"
    
    def __init__(self, clients_dir: str = "/opt/clients"):
        self.clients_dir = Path(clients_dir)
        self.mpstats_dir = self.clients_dir / "GLOBAL_AI_LEARNING" / "mpstats"
        self.mpstats_dir.mkdir(parents=True, exist_ok=True)
        
        # User-Agent чтобы выглядеть как браузер
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
        }
    
    def _get_session_file(self, client_id: str) -> Path:
        """Путь к файлу сессии клиента"""
        return self.mpstats_dir / f"{client_id}_session.pkl"
    
    def _get_creds_file(self, client_id: str) -> Path:
        """Путь к файлу с credentials"""
        return self.clients_dir / client_id / "credentials" / "mpstats.json"
    
    def save_credentials(self, client_id: str, login: str, password: str):
        """Сохраняет credentials клиента (зашифрованно в продакшене)"""
        creds_file = self._get_creds_file(client_id)
        creds_file.parent.mkdir(parents=True, exist_ok=True)
        
        creds = {
            'login': login,
            'password': password,  # TODO: encrypt in production
            'saved_at': datetime.now().isoformat()
        }
        
        with open(creds_file, 'w') as f:
            json.dump(creds, f)
        
        logger.info(f"✅ Credentials saved for {client_id}")
    
    def load_credentials(self, client_id: str) -> Optional[Dict]:
        """Загружает credentials клиента"""
        creds_file = self._get_creds_file(client_id)
        
        if not creds_file.exists():
            return None
        
        with open(creds_file) as f:
            return json.load(f)
    
    def login(self, client_id: str, login: str = None, password: str = None) -> bool:
        """
        Авторизуется на Mpstats и сохраняет сессию
        
        Args:
            client_id: ID клиента
            login: Логин (если None — берется из сохраненных)
            password: Пароль (если None — берется из сохраненных)
        
        Returns:
            True если авторизация успешна
        """
        # Если credentials не переданы — загружаем
        if not login or not password:
            creds = self.load_credentials(client_id)
            if not creds:
                logger.error(f"❌ No credentials found for {client_id}")
                return False
            login = creds['login']
            password = creds['password']
        else:
            # Сохраняем credentials
            self.save_credentials(client_id, login, password)
        
        # Создаем сессию
        session = requests.Session()
        session.headers.update(self.headers)
        
        try:
            # 1. Получаем страницу логина (для CSRF токена)
            logger.info(f"🔐 Logging in {client_id} to Mpstats...")
            
            resp = session.get(self.LOGIN_URL, timeout=30)
            resp.raise_for_status()
            
            # 2. Парсим CSRF токен
            soup = BeautifulSoup(resp.text, 'html.parser')
            csrf_token = None
            
            # Ищем токен в meta или form
            csrf_meta = soup.find('meta', {'name': 'csrf-token'})
            if csrf_meta:
                csrf_token = csrf_meta.get('content')
            
            # 3. Отправляем форму логина
            login_data = {
                'email': login,
                'password': password,
            }
            
            if csrf_token:
                login_data['_token'] = csrf_token
            
            resp = session.post(
                self.LOGIN_URL,
                data=login_data,
                headers={'Referer': self.LOGIN_URL},
                timeout=30
            )
            
            # 4. Проверяем успешность
            if 'dashboard' in resp.url or resp.status_code == 200:
                # Сохраняем сессию
                session_file = self._get_session_file(client_id)
                with open(session_file, 'wb') as f:
                    pickle.dump(session.cookies, f)
                
                logger.info(f"✅ Login successful for {client_id}")
                return True
            else:
                logger.error(f"❌ Login failed for {client_id}: {resp.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Login error for {client_id}: {e}")
            return False
    
    def get_session(self, client_id: str) -> Optional[requests.Session]:
        """
        Возвращает активную сессию клиента.
        Если сессия протухла — пытается перелогиниться.
        """
        session_file = self._get_session_file(client_id)
        
        # Загружаем cookies
        if not session_file.exists():
            logger.warning(f"⚠️ No session found for {client_id}, trying to login...")
            # Пробуем залогиниться с сохраненными credentials
            if self.login(client_id):
                return self.get_session(client_id)
            return None
        
        # Создаем сессию с загруженными cookies
        session = requests.Session()
        session.headers.update(self.headers)
        
        with open(session_file, 'rb') as f:
            session.cookies.update(pickle.load(f))
        
        # Проверяем валидность сессии
        if self._check_session_valid(session):
            logger.info(f"✅ Session valid for {client_id}")
            return session
        else:
            logger.warning(f"⚠️ Session expired for {client_id}, re-logging in...")
            # Сессия протухла — перелогиниваемся
            if self.login(client_id):
                return self.get_session(client_id)
            return None
    
    def _check_session_valid(self, session: requests.Session) -> bool:
        """Проверяет валидность сессии"""
        try:
            # Пробуем зайти на дашборд (короткий таймаут)
            resp = session.get(f"{self.BASE_URL}/dashboard", timeout=5)
            # Если редирект на логин — сессия протухла
            return 'login' not in resp.url and resp.status_code == 200
        except Exception as e:
            logger.debug(f"Session check failed: {e}")
            return False
    
    def is_authenticated(self, client_id: str) -> bool:
        """Проверяет авторизован ли клиент"""
        return self.get_session(client_id) is not None


class MpstatsParser:
    """
    🔍 Mpstats Parser - парсинг данных после авторизации
    """
    
    def __init__(self, authenticator: MpstatsAuthenticator):
        self.auth = authenticator
    
    def get_product_data(self, client_id: str, product_id: str, platform: str = "wb") -> Optional[Dict]:
        """
        Получает данные о товаре с Mpstats
        
        Args:
            client_id: ID клиента (для сессии)
            product_id: nmId (WB) или offer_id (Ozon)
            platform: 'wb' или 'ozon'
        """
        session = self.auth.get_session(client_id)
        if not session:
            logger.error(f"❌ Not authenticated for {client_id}")
            return None
        
        try:
            # URL для поиска товара
            search_url = f"https://mpstats.io/{platform}/item/{product_id}"
            
            resp = session.get(search_url, timeout=30)
            resp.raise_for_status()
            
            # Парсим данные
            soup = BeautifulSoup(resp.text, 'html.parser')
            
            # Ищем данные в скриптах (обычно там JSON с данными)
            data = self._extract_data_from_page(soup)
            
            return data
            
        except Exception as e:
            logger.error(f"❌ Error fetching product {product_id}: {e}")
            return None
    
    def get_category_data(self, client_id: str, category_id: str, platform: str = "wb") -> Optional[Dict]:
        """Получает данные по категории"""
        session = self.auth.get_session(client_id)
        if not session:
            return None
        
        try:
            url = f"https://mpstats.io/{platform}/category/{category_id}"
            resp = session.get(url, timeout=30)
            resp.raise_for_status()
            
            soup = BeautifulSoup(resp.text, 'html.parser')
            return self._extract_data_from_page(soup)
            
        except Exception as e:
            logger.error(f"❌ Error fetching category {category_id}: {e}")
            return None
    
    def _extract_data_from_page(self, soup: BeautifulSoup) -> Dict:
        """Извлекает данные из HTML страницы"""
        data = {
            'extracted_at': datetime.now().isoformat(),
            'price': None,
            'sales': None,
            'revenue': None,
            'rating': None,
            'reviews': None,
            'stock': None,
        }
        
        # Ищем цену
        price_elem = soup.find('span', class_=lambda x: x and 'price' in x.lower())
        if price_elem:
            price_text = price_elem.get_text(strip=True)
            # Очищаем от пробелов и ₽
            price_clean = price_text.replace(' ', '').replace('₽', '').replace(',', '')
            try:
                data['price'] = float(price_clean)
            except:
                pass
        
        # Ищем рейтинг
        rating_elem = soup.find('span', class_=lambda x: x and 'rating' in x.lower())
        if rating_elem:
            try:
                data['rating'] = float(rating_elem.get_text(strip=True))
            except:
                pass
        
        # Ищем отзывы
        reviews_elem = soup.find('span', class_=lambda x: x and 'review' in x.lower())
        if reviews_elem:
            reviews_text = reviews_elem.get_text(strip=True)
            try:
                data['reviews'] = int(reviews_text.replace(' ', ''))
            except:
                pass
        
        # Ищем JSON данные в скриптах
        scripts = soup.find_all('script', type='application/json')
        for script in scripts:
            try:
                json_data = json.loads(script.string)
                # Рекурсивно ищем нужные поля
                self._extract_from_json(json_data, data)
            except:
                pass
        
        return data
    
    def _extract_from_json(self, obj, data: Dict):
        """Рекурсивно извлекает данные из JSON"""
        if isinstance(obj, dict):
            # Ищем известные поля
            for key in ['price', 'sales', 'revenue', 'rating', 'reviews', 'stock', 'qty']:
                if key in obj and obj[key] is not None:
                    try:
                        data[key] = float(obj[key]) if key != 'reviews' else int(obj[key])
                    except:
                        pass
            
            # Рекурсивно обходим вложенные объекты
            for value in obj.values():
                self._extract_from_json(value, data)
        elif isinstance(obj, list):
            for item in obj:
                self._extract_from_json(item, data)
