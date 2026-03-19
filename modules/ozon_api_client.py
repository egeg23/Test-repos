# modules/ozon_api_client.py - Клиент для Ozon Seller API
"""
Реальная интеграция с Ozon Seller API.
Проверка ключей, получение товаров, цен, заказов.
"""

import aiohttp
import asyncio
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import json


@dataclass
class OzonProduct:
    """Модель товара Ozon"""
    id: int  # offer_id
    sku: int  # SKU Ozon
    name: str
    price: float
    old_price: float
    stock: int
    status: str  # selling, not_sold, etc.
    category_id: Optional[int] = None
    rating: Optional[float] = None


@dataclass
class OzonClientInfo:
    """Информация о клиенте"""
    client_id: str
    name: str
    company: Optional[str] = None


class OzonAPIClient:
    """
    Клиент для работы с Ozon Seller API.
    Базовый URL: https://api-seller.ozon.ru
    """
    
    BASE_URL = "https://api-seller.ozon.ru"
    
    def __init__(self, client_id: str, api_key: str):
        self.client_id = client_id
        self.api_key = api_key
        self.session: Optional[aiohttp.ClientSession] = None
        self._is_valid = False
        self._last_error: Optional[str] = None
    
    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession(
            headers={
                "Client-Id": self.client_id,
                "Api-Key": self.api_key,
                "Content-Type": "application/json"
            },
            timeout=aiohttp.ClientTimeout(total=30)
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
    
    async def verify_credentials(self) -> Tuple[bool, str]:
        """
        Проверяет валидность Client ID и API Key.
        
        Returns:
            Tuple[bool, str]: (is_valid, message)
        """
        try:
            # Пробуем получить список товаров (limit=1)
            url = f"{self.BASE_URL}/v3/product/list"
            payload = {
                "filter": {},
                "last_id": "",
                "limit": 1
            }
            
            async with self.session.post(url, json=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    if "items" in data or "products" in data:
                        self._is_valid = True
                        self._last_error = None
                        return True, "✅ Client ID и API Key валидны. Доступ получен."
                    else:
                        self._is_valid = False
                        self._last_error = "Unexpected API response"
                        return False, "⚠️ Неожиданный ответ от API"
                
                elif response.status == 400:
                    data = await response.json()
                    error_msg = data.get("message", "Bad Request")
                    self._is_valid = False
                    self._last_error = error_msg
                    return False, f"❌ Ошибка: {error_msg}"
                    
                elif response.status == 401:
                    self._is_valid = False
                    self._last_error = "Invalid credentials (401)"
                    return False, "❌ Неверный Client ID или API Key (401 Unauthorized)"
                    
                elif response.status == 403:
                    self._is_valid = False
                    self._last_error = "Access forbidden (403)"
                    return False, "❌ Доступ запрещен (403 Forbidden). Проверьте права ключа."
                    
                elif response.status == 429:
                    self._is_valid = False
                    self._last_error = "Rate limit exceeded (429)"
                    return False, "⏳ Слишком много запросов (429 Too Many Requests)"
                    
                else:
                    self._is_valid = False
                    self._last_error = f"HTTP {response.status}"
                    return False, f"❌ Ошибка API: HTTP {response.status}"
                    
        except aiohttp.ClientError as e:
            self._is_valid = False
            self._last_error = str(e)
            return False, f"❌ Ошибка соединения: {str(e)}"
        except asyncio.TimeoutError:
            self._is_valid = False
            self._last_error = "Timeout"
            return False, "⏳ Таймаут соединения с Ozon API"
        except Exception as e:
            self._is_valid = False
            self._last_error = str(e)
            return False, f"❌ Неизвестная ошибка: {str(e)}"
    
    async def get_products(
        self, 
        limit: int = 100,
        offer_id: Optional[str] = None
    ) -> List[OzonProduct]:
        """
        Получает список товаров продавца.
        
        Args:
            limit: Максимум товаров (1-1000)
            offer_id: Фильтр по артикулу
            
        Returns:
            List[OzonProduct]: Список товаров
        """
        url = f"{self.BASE_URL}/v3/product/list"
        
        payload = {
            "filter": {},
            "last_id": "",
            "limit": min(limit, 1000)
        }
        
        if offer_id:
            payload["filter"]["offer_id"] = offer_id
        
        async with self.session.post(url, json=payload) as response:
            if response.status != 200:
                raise Exception(f"Failed to get products: HTTP {response.status}")
            
            data = await response.json()
            products = []
            
            items = data.get("items", [])
            for item in items:
                product = OzonProduct(
                    id=item.get("offer_id", ""),
                    sku=item.get("sku", 0),
                    name=item.get("name", "Без названия"),
                    price=item.get("price", 0),
                    old_price=item.get("old_price", 0),
                    stock=item.get("stock", 0),
                    status=item.get("status", "unknown"),
                    category_id=item.get("category_id"),
                    rating=None
                )
                products.append(product)
            
            return products
    
    async def update_price(
        self, 
        offer_id: str, 
        price: float,
        old_price: Optional[float] = None
    ) -> bool:
        """
        Обновляет цену товара.
        
        Args:
            offer_id: Артикул товара
            price: Новая цена
            old_price: Старая цена (для отображения скидки)
            
        Returns:
            bool: Успешно ли обновление
        """
        url = f"{self.BASE_URL}/v1/product/import/prices"
        
        payload = {
            "prices": [{
                "offer_id": offer_id,
                "price": str(price),
                "old_price": str(old_price) if old_price else str(price)
            }]
        }
        
        async with self.session.post(url, json=payload) as response:
            if response.status == 200:
                data = await response.json()
                # Проверяем результат
                return True
            return False
    
    async def get_stock(self, offer_ids: List[str]) -> Dict[str, int]:
        """
        Получает остатки товаров.
        
        Args:
            offer_ids: Список артикулов
            
        Returns:
            Dict[str, int]: Словарь {offer_id: stock}
        """
        url = f"{self.BASE_URL}/v3/product/info/stocks"
        
        payload = {
            "offer_id": offer_ids
        }
        
        async with self.session.post(url, json=payload) as response:
            if response.status != 200:
                raise Exception(f"Failed to get stock: HTTP {response.status}")
            
            data = await response.json()
            stocks = {}
            
            for item in data.get("items", []):
                offer_id = item.get("offer_id")
                stock = item.get("stocks", [{}])[0].get("present", 0)
                if offer_id:
                    stocks[offer_id] = stock
            
            return stocks
    
    async def get_orders(
        self,
        date_from: datetime,
        date_to: Optional[datetime] = None
    ) -> List[Dict]:
        """
        Получает список заказов.
        
        Args:
            date_from: Начальная дата
            date_to: Конечная дата
            
        Returns:
            List[Dict]: Список заказов
        """
        url = f"{self.BASE_URL}/v3/posting/fbs/list"
        
        if not date_to:
            date_to = datetime.now()
        
        payload = {
            "filter": {
                "since": date_from.isoformat(),
                "to": date_to.isoformat()
            },
            "limit": 100
        }
        
        async with self.session.post(url, json=payload) as response:
            if response.status != 200:
                raise Exception(f"Failed to get orders: HTTP {response.status}")
            
            data = await response.json()
            return data.get("postings", [])
    
    @property
    def is_valid(self) -> bool:
        """Проверяет, были ли учётные данные верифицированы"""
        return self._is_valid
    
    @property
    def last_error(self) -> Optional[str]:
        """Возвращает последнюю ошибку"""
        return self._last_error


# ============================================================================
# УТИЛИТЫ
# ============================================================================

async def verify_ozon_credentials(client_id: str, api_key: str) -> Tuple[bool, str]:
    """
    Быстрая проверка Client ID и API Key без создания клиента.
    
    Args:
        client_id: Client ID из личного кабинета
        api_key: API Key
        
    Returns:
        Tuple[bool, str]: (is_valid, message)
    """
    async with OzonAPIClient(client_id, api_key) as client:
        return await client.verify_credentials()


async def get_ozon_products(client_id: str, api_key: str, limit: int = 10) -> List[OzonProduct]:
    """
    Получает список товаров по учётным данным.
    
    Args:
        client_id: Client ID
        api_key: API Key
        limit: Количество товаров
        
    Returns:
        List[OzonProduct]: Список товаров
    """
    async with OzonAPIClient(client_id, api_key) as client:
        is_valid, msg = await client.verify_credentials()
        if not is_valid:
            raise Exception(msg)
        return await client.get_products(limit=limit)