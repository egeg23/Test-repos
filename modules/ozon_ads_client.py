# modules/ozon_ads_client.py - Ozon Advertising API Client
"""
Клиент для работы с рекламным API Ozon (Performance)
Документация: https://api-seller.ozon.ru/#tag/Finance
"""

import asyncio
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import aiohttp

logger = logging.getLogger('ozon_ads_client')


class OzonAdsClient:
    """
    Клиент для рекламного API Ozon
    
    Поддерживает:
    - Получение списка кампаний
    - Управление ставками
    - Получение статистики
    - Автоматический ДРР биддинг
    """
    
    BASE_URL = "https://api-seller.ozon.ru"
    
    def __init__(self, api_key: str, client_id: str):
        self.api_key = api_key
        self.client_id = client_id
        self.session: Optional[aiohttp.ClientSession] = None
        self._is_valid = False
        self._last_error: Optional[str] = None
    
    async def __aenter__(self):
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
    
    async def connect(self):
        """Создает HTTP сессию"""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(
                headers={
                    'Client-Id': self.client_id,
                    'Api-Key': self.api_key,
                    'Content-Type': 'application/json'
                }
            )
            # Проверяем валидность
            try:
                await self.get_campaigns()
                self._is_valid = True
                logger.info("✅ Ozon Ads API client connected")
            except Exception as e:
                self._last_error = str(e)
                logger.error(f"❌ Failed to connect to Ozon Ads API: {e}")
                raise
    
    async def close(self):
        """Закрывает сессию"""
        if self.session and not self.session.closed:
            await self.session.close()
            logger.info("✅ Ozon Ads API client closed")
    
    # =========================================================================
    # КАМПАНИИ
    # =========================================================================
    
    async def get_campaigns(self, state: str = "CAMPAIGN_STATE_RUNNING") -> List[Dict]:
        """
        Получает список рекламных кампаний
        
        Args:
            state: Фильтр по состоянию (CAMPAIGN_STATE_RUNNING, etc.)
        
        Returns:
            Список кампаний
        """
        url = f"{self.BASE_URL}/v1/campaign"
        
        payload = {
            "campaigns": [],
            "states": [state] if state else []
        }
        
        try:
            async with self.session.post(url, json=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    campaigns = data.get('campaigns', [])
                    logger.info(f"📢 Получено {len(campaigns)} кампаний Ozon")
                    return campaigns
                elif response.status == 401:
                    raise Exception("Invalid API credentials for Ozon Ads API")
                else:
                    error_text = await response.text()
                    raise Exception(f"HTTP {response.status}: {error_text}")
                    
        except aiohttp.ClientError as e:
            logger.error(f"Network error getting campaigns: {e}")
            raise
    
    async def get_campaign_info(self, campaign_id: int) -> Dict:
        """
        Получает детальную информацию о кампании
        
        Args:
            campaign_id: ID кампании
        
        Returns:
            Информация о кампании
        """
        url = f"{self.BASE_URL}/v1/campaign/{campaign_id}"
        
        try:
            async with self.session.get(url) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    error_text = await response.text()
                    raise Exception(f"HTTP {response.status}: {error_text}")
                    
        except Exception as e:
            logger.error(f"Error getting campaign {campaign_id}: {e}")
            raise
    
    # =========================================================================
    # УПРАВЛЕНИЕ КАМПАНИЯМИ
    # =========================================================================
    
    async def pause_campaign(self, campaign_id: int) -> bool:
        """
        Ставит кампанию на паузу
        
        Args:
            campaign_id: ID кампании
        
        Returns:
            True если успешно
        """
        url = f"{self.BASE_URL}/v1/campaign/pause"
        
        try:
            payload = {"campaign_id": campaign_id}
            
            async with self.session.post(url, json=payload) as response:
                if response.status == 200:
                    logger.info(f"⏸ Кампания {campaign_id} на паузе")
                    return True
                else:
                    error_text = await response.text()
                    logger.error(f"Failed to pause campaign: {error_text}")
                    return False
                    
        except Exception as e:
            logger.error(f"Error pausing campaign {campaign_id}: {e}")
            return False
    
    async def resume_campaign(self, campaign_id: int) -> bool:
        """
        Возобновляет кампанию
        
        Args:
            campaign_id: ID кампании
        
        Returns:
            True если успешно
        """
        url = f"{self.BASE_URL}/v1/campaign/resume"
        
        try:
            payload = {"campaign_id": campaign_id}
            
            async with self.session.post(url, json=payload) as response:
                if response.status == 200:
                    logger.info(f"▶️ Кампания {campaign_id} возобновлена")
                    return True
                else:
                    error_text = await response.text()
                    logger.error(f"Failed to resume campaign: {error_text}")
                    return False
                    
        except Exception as e:
            logger.error(f"Error resuming campaign {campaign_id}: {e}")
            return False
    
    # =========================================================================
    # СТАВКИ И БЮДЖЕТ
    # =========================================================================
    
    async def set_daily_budget(self, campaign_id: int, budget: float) -> bool:
        """
        Устанавливает дневной бюджет кампании
        
        Args:
            campaign_id: ID кампании
            budget: Бюджет в рублях
        
        Returns:
            True если успешно
        """
        url = f"{self.BASE_URL}/v1/campaign/budget"
        
        try:
            payload = {
                "campaign_id": campaign_id,
                "daily_budget": str(int(budget))
            }
            
            async with self.session.post(url, json=payload) as response:
                if response.status == 200:
                    logger.info(f"💰 Бюджет кампании {campaign_id} изменен на {budget}₽")
                    return True
                else:
                    error_text = await response.text()
                    logger.error(f"Failed to set budget: {error_text}")
                    return False
                    
        except Exception as e:
            logger.error(f"Error setting budget for {campaign_id}: {e}")
            return False
    
    async def calculate_optimal_budget(
        self,
        current_drr: float,
        target_drr: float,
        current_budget: float,
        orders: int,
        min_budget: float = 500.0,
        max_budget: float = 50000.0
    ) -> float:
        """
        Рассчитывает оптимальный бюджет на основе ДРР
        
        Args:
            current_drr: Текущий ДРР (%)
            target_drr: Целевой ДРР (%)
            current_budget: Текущий бюджет
            orders: Количество заказов
            min_budget: Минимальный бюджет
            max_budget: Максимальный бюджет
        
        Returns:
            Оптимальный бюджет
        """
        # Логика аналогична WB
        if current_drr > target_drr * 1.2:
            adjustment = 0.85
        elif current_drr > target_drr:
            adjustment = 0.92
        elif current_drr < target_drr * 0.8:
            adjustment = 1.15
        elif current_drr < target_drr:
            adjustment = 1.08
        else:
            adjustment = 1.0
        
        new_budget = current_budget * adjustment
        new_budget = max(min_budget, min(new_budget, max_budget))
        
        return round(new_budget, 2)
    
    # =========================================================================
    # СТАТИСТИКА
    # =========================================================================
    
    async def get_statistics(
        self,
        date_from: str,
        date_to: str,
        campaigns: Optional[List[int]] = None
    ) -> List[Dict]:
        """
        Получает статистику по кампаниям
        
        Args:
            date_from: Начало периода (YYYY-MM-DD)
            date_to: Конец периода (YYYY-MM-DD)
            campaigns: Список ID кампаний (если None - все)
        
        Returns:
            Статистика по кампаниям
        """
        url = f"{self.BASE_URL}/v1/campaign/statistic"
        
        payload = {
            "date_from": date_from,
            "date_to": date_to,
            "campaigns": campaigns or []
        }
        
        try:
            async with self.session.post(url, json=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    rows = data.get('rows', [])
                    logger.info(f"📊 Получена статистика для {len(rows)} кампаний Ozon")
                    return rows
                else:
                    error_text = await response.text()
                    raise Exception(f"HTTP {response.status}: {error_text}")
                    
        except Exception as e:
            logger.error(f"Error getting statistics: {e}")
            raise
    
    async def get_daily_statistics(
        self,
        campaign_id: int,
        days: int = 7
    ) -> List[Dict]:
        """
        Получает ежедневную статистику кампании
        
        Args:
            campaign_id: ID кампании
            days: Количество дней
        
        Returns:
            Статистика по дням
        """
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        stats = await self.get_statistics(
            date_from=start_date.strftime('%Y-%m-%d'),
            date_to=end_date.strftime('%Y-%m-%d'),
            campaigns=[campaign_id]
        )
        
        return stats
    
    def calculate_drr(self, spent: float, orders_amount: float) -> float:
        """
        Рассчитывает ДРР
        
        Args:
            spent: Потрачено на рекламу
            orders_amount: Сумма заказов
        
        Returns:
            ДРР в процентах
        """
        if orders_amount == 0:
            return 0.0
        return round((spent / orders_amount) * 100, 2)
    
    @property
    def is_valid(self) -> bool:
        """Проверяет валидность подключения"""
        return self._is_valid
    
    @property
    def last_error(self) -> Optional[str]:
        """Возвращает последнюю ошибку"""
        return self._last_error


async def verify_ozon_ads_api(api_key: str, client_id: str) -> Tuple[bool, str]:
    """
    Быстрая проверка API ключа Ozon
    
    Args:
        api_key: API ключ
        client_id: Client ID
    
    Returns:
        (валиден, сообщение)
    """
    try:
        async with OzonAdsClient(api_key, client_id) as client:
            campaigns = await client.get_campaigns()
            return True, f"✅ Ozon API работает. Найдено {len(campaigns)} кампаний"
    except Exception as e:
        return False, f"❌ Ошибка: {e}"


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 3:
        print("Usage: python ozon_ads_client.py <client_id> <api_key>")
        sys.exit(1)
    
    client_id = sys.argv[1]
    api_key = sys.argv[2]
    valid, message = asyncio.run(verify_ozon_ads_api(api_key, client_id))
    print(message)
