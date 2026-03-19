# modules/wb_api_client.py - Клиент для Wildberries API
"""
Реальная интеграция с Wildberries API.
Проверка ключей, получение товаров, цен, статистики.
"""

import aiohttp
import asyncio
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
import json


@dataclass
class WBProduct:
    """Модель товара Wildberries"""
    nm_id: int  # Номенклатурный номер
    vendor_code: str  # Артикул продавца
    name: str
    price: float
    discount: int
    final_price: float
    stock: int  # Остаток
    rating: Optional[float] = None
    reviews: int = 0
    category: Optional[str] = None


@dataclass
class WBCabinetInfo:
    """Информация о кабинете"""
    id: int
    name: str
    email: str
    created_at: datetime


class WildberriesAPIClient:
    """
    Клиент для работы с Wildberries API.
    Поддерживает API версии 1 и 2.
    """
    
    BASE_URL_V1 = "https://suppliers-api.wildberries.ru"
    BASE_URL_V2 = "https://suppliers-api.wildberries.ru/api/v2"
    BASE_URL_V3 = "https://suppliers-api.wildberries.ru/api/v3"
    BASE_URL_STAT = "https://statistics-api.wildberries.ru"
    BASE_URL_ADS = "https://advert-api.wb.ru"
    
    def __init__(self, api_key: str, client_id: Optional[str] = None):
        self.api_key = api_key
        self.client_id = client_id
        self.session: Optional[aiohttp.ClientSession] = None
        self._is_valid = False
        self._last_error: Optional[str] = None
    
    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession(
            headers={
                "Authorization": self.api_key,
                "Content-Type": "application/json",
                "Accept": "application/json"
            },
            timeout=aiohttp.ClientTimeout(total=30)
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
    
    async def verify_key(self) -> Tuple[bool, str]:
        """
        Проверяет валидность API ключа.
        
        Returns:
            Tuple[bool, str]: (is_valid, message)
        """
        try:
            # Пробуем получить список товаров (самый простой endpoint)
            # Используем limit=1 чтобы не нагружать API
            url = f"{self.BASE_URL_V2}/stock"
            params = {"skip": 0, "take": 1}
            
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    if isinstance(data, dict) or isinstance(data, list):
                        self._is_valid = True
                        self._last_error = None
                        return True, "✅ API ключ валиден. Доступ получен."
                    else:
                        self._is_valid = False
                        self._last_error = "Unexpected API response"
                        return False, "⚠️ Неожиданный ответ от API"
                        
                elif response.status == 401:
                    self._is_valid = False
                    self._last_error = "Invalid API key (401)"
                    return False, "❌ Неверный API ключ (401 Unauthorized)"
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
            return False, "⏳ Таймаут соединения с WB API"
        except Exception as e:
            self._is_valid = False
            self._last_error = str(e)
            return False, f"❌ Неизвестная ошибка: {str(e)}"
    
    async def get_cabinet_info(self) -> Optional[WBCabinetInfo]:
        """
        Получает информацию о кабинете продавца.
        WB API не даёт прямого метода, поэтому извлекаем из контекста.
        """
        # WB API v3/users не существует, используем workaround
        # Получаем информацию из первого товара
        try:
            products = await self.get_products(limit=1)
            if products:
                # Возвращаем минимальную информацию
                return WBCabinetInfo(
                    id=0,  # WB не отдаёт ID кабинета напрямую
                    name="Wildberries Seller",
                    email="",
                    created_at=datetime.now()
                )
            return None
        except Exception as e:
            return None
    
    async def get_products(
        self, 
        limit: int = 100, 
        offset: int = 0
    ) -> List[WBProduct]:
        """
        Получает список товаров продавца.
        
        Args:
            limit: Максимум товаров (1-1000)
            offset: Смещение для пагинации
            
        Returns:
            List[WBProduct]: Список товаров
        """
        url = f"{self.BASE_URL_V2}/stock"
        params = {"skip": offset, "take": min(limit, 1000)}
        
        async with self.session.get(url, params=params) as response:
            if response.status != 200:
                raise Exception(f"Failed to get products: HTTP {response.status}")
            
            data = await response.json()
            products = []
            
            # WB API возвращает список или dict с ключом stocks
            items = data.get('stocks', []) if isinstance(data, dict) else data
            
            for item in items:
                product = WBProduct(
                    nm_id=item.get('nmId', 0),
                    vendor_code=item.get('vendorCode', ''),
                    name=item.get('productName', 'Без названия'),
                    price=item.get('price', 0),
                    discount=item.get('discount', 0),
                    final_price=item.get('finalPrice', item.get('price', 0)),
                    stock=item.get('stock', 0),
                    rating=None,  # Нужен отдельный запрос
                    reviews=0,     # Нужен отдельный запрос
                    category=item.get('category', 'Не указана')
                )
                products.append(product)
            
            return products
    
    async def update_price(
        self, 
        nm_id: int, 
        price: float, 
        discount: int = 0
    ) -> bool:
        """
        Обновляет цену товара.
        
        Args:
            nm_id: Номенклатурный номер
            price: Новая цена
            discount: Скидка в процентах (0-95)
            
        Returns:
            bool: Успешно ли обновление
        """
        url = "https://discounts-prices-api.wildberries.ru/api/v2/upload/task"
        
        payload = {
            "data": [{
                "nmID": nm_id,
                "price": price,
                "discount": discount
            }]
        }
        
        async with self.session.post(url, json=payload) as response:
            return response.status == 200
    
    async def get_sales_stats(
        self, 
        date_from: datetime, 
        date_to: Optional[datetime] = None
    ) -> Dict:
        """
        Получает статистику продаж.
        Требует Statistics API (отдельный ключ!).
        """
        # Statistics API использует другой base URL и может требовать другой ключ
        if not date_to:
            date_to = datetime.now()
        
        url = f"{self.BASE_URL_STAT}/api/v1/supplier/sales"
        params = {
            "dateFrom": date_from.strftime("%Y-%m-%d"),
            "dateTo": date_to.strftime("%Y-%m-%d")
        }
        
        async with self.session.get(url, params=params) as response:
            if response.status == 200:
                return await response.json()
            elif response.status == 401:
                raise Exception("Statistics API требует отдельный ключ!")
            else:
                raise Exception(f"HTTP {response.status}")
    
    async def get_advertising_campaigns(self) -> List[Dict]:
        """
        Получает список рекламных кампаний.
        Требует Advertising API.
        """
        url = f"{self.BASE_URL_ADS}/adv/v0/adverts"
        
        async with self.session.get(url) as response:
            if response.status == 200:
                return await response.json()
            elif response.status == 401:
                raise Exception("Advertising API требует отдельный API ключ (401 Unauthorized)")
            elif response.status == 403:
                raise Exception("Доступ к Advertising API запрещен (403 Forbidden)")
            else:
                raise Exception(f"HTTP {response.status}")
    
    @property
    def is_valid(self) -> bool:
        """Проверяет, был ли ключ верифицирован"""
        return self._is_valid
    
    @property
    def last_error(self) -> Optional[str]:
        """Возвращает последнюю ошибку"""
        return self._last_error


# ============================================================================
# УТИЛИТЫ
# ============================================================================

async def verify_wb_api_key(api_key: str) -> Tuple[bool, str]:
    """
    Быстрая проверка API ключа без создания клиента.
    
    Args:
        api_key: API ключ Wildberries
        
    Returns:
        Tuple[bool, str]: (is_valid, message)
    """
    async with WildberriesAPIClient(api_key) as client:
        return await client.verify_key()


async def get_wb_products(api_key: str, limit: int = 10) -> List[WBProduct]:
    """
    Получает список товаров по API ключу.
    
    Args:
        api_key: API ключ
        limit: Количество товаров
        
    Returns:
        List[WBProduct]: Список товаров
    """
    async with WildberriesAPIClient(api_key) as client:
        is_valid, msg = await client.verify_key()
        if not is_valid:
            raise Exception(msg)
        return await client.get_products(limit=limit)