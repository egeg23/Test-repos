# modules/wb_ads_client.py - Wildberries Advertising API Client
"""
Клиент для работы с рекламным API Wildberries
Документация: https://openapi.wildberries.ru/#tag/Prodvizhenie
"""

import asyncio
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import aiohttp

logger = logging.getLogger('wb_ads_client')


class WBAdsClient:
    """
    Клиент для рекламного API Wildberries
    
    Поддерживает:
    - Получение списка кампаний
    - Управление ставками
    - Получение статистики
    - Автоматический ДРР биддинг
    """
    
    BASE_URL = "https://advert-api.wildberries.ru"
    
    def __init__(self, api_key: str):
        self.api_key = api_key
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
                    'Authorization': self.api_key,
                    'Content-Type': 'application/json',
                    'Accept': 'application/json'
                }
            )
            # Проверяем валидность ключа
            try:
                await self.get_campaigns()
                self._is_valid = True
                logger.info("✅ WB Ads API client connected")
            except Exception as e:
                self._last_error = str(e)
                logger.error(f"❌ Failed to connect to WB Ads API: {e}")
                raise
    
    async def close(self):
        """Закрывает сессию"""
        if self.session and not self.session.closed:
            await self.session.close()
            logger.info("✅ WB Ads API client closed")
    
    # =========================================================================
    # КАМПАНИИ
    # =========================================================================
    
    async def get_campaigns(self, status: Optional[str] = None) -> List[Dict]:
        """
        Получает список рекламных кампаний
        
        Args:
            status: Фильтр по статусу (9 - активна, 11 - пауза, etc.)
        
        Returns:
            Список кампаний с метаданными
        """
        url = f"{self.BASE_URL}/adv/v1/promotion/count"
        
        try:
            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    campaigns = data.get('adverts', [])
                    
                    # Фильтруем по статусу если нужно
                    if status:
                        campaigns = [c for c in campaigns if str(c.get('status')) == str(status)]
                    
                    logger.info(f"📢 Получено {len(campaigns)} кампаний")
                    return campaigns
                elif response.status == 401:
                    raise Exception("Invalid API key for Advertising API")
                elif response.status == 429:
                    raise Exception("Rate limit exceeded")
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
        url = f"{self.BASE_URL}/adv/v1/promotion/adverts"
        
        try:
            async with self.session.post(url, json=[campaign_id]) as response:
                if response.status == 200:
                    data = await response.json()
                    return data[0] if data else {}
                else:
                    error_text = await response.text()
                    raise Exception(f"HTTP {response.status}: {error_text}")
                    
        except Exception as e:
            logger.error(f"Error getting campaign {campaign_id}: {e}")
            raise
    
    async def get_campaigns_by_ids(self, campaign_ids: List[int]) -> List[Dict]:
        """
        Получает информацию о нескольких кампаниях
        
        Args:
            campaign_ids: Список ID кампаний
        
        Returns:
            Список кампаний
        """
        url = f"{self.BASE_URL}/adv/v1/promotion/adverts"
        
        try:
            async with self.session.post(url, json=campaign_ids) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    error_text = await response.text()
                    raise Exception(f"HTTP {response.status}: {error_text}")
                    
        except Exception as e:
            logger.error(f"Error getting campaigns: {e}")
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
        url = f"{self.BASE_URL}/adv/v0/pause"
        
        try:
            async with self.session.get(url, params={'id': campaign_id}) as response:
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
        url = f"{self.BASE_URL}/adv/v0/start"
        
        try:
            async with self.session.get(url, params={'id': campaign_id}) as response:
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
    # СТАВКИ И ДРР
    # =========================================================================
    
    async def set_bid(self, campaign_id: int, bid: float) -> bool:
        """
        Устанавливает ставку для кампании
        
        Args:
            campaign_id: ID кампании
            bid: Новая ставка (в рублях)
        
        Returns:
            True если успешно
        """
        url = f"{self.BASE_URL}/adv/v0/cpm"
        
        try:
            payload = {
                'advertId': campaign_id,
                'cpm': int(bid * 100)  # Конвертируем в копейки
            }
            
            async with self.session.post(url, json=payload) as response:
                if response.status == 200:
                    logger.info(f"💰 Ставка для кампании {campaign_id} изменена на {bid}₽")
                    return True
                else:
                    error_text = await response.text()
                    logger.error(f"Failed to set bid: {error_text}")
                    return False
                    
        except Exception as e:
            logger.error(f"Error setting bid for {campaign_id}: {e}")
            return False
    
    async def calculate_optimal_bid(
        self,
        current_drr: float,
        target_drr: float,
        current_bid: float,
        orders: int,
        min_bid: float = 50.0,
        max_bid: float = 5000.0
    ) -> float:
        """
        Рассчитывает оптимальную ставку на основе ДРР
        
        Args:
            current_drr: Текущий ДРР (%)
            target_drr: Целевой ДРР (%)
            current_bid: Текущая ставка
            orders: Количество заказов
            min_bid: Минимальная ставка
            max_bid: Максимальная ставка
        
        Returns:
            Оптимальная ставка
        """
        # Если ДРР выше целевого - снижаем ставку
        if current_drr > target_drr * 1.2:  # ДРР на 20% выше целевого
            adjustment = 0.85  # Снижаем на 15%
        elif current_drr > target_drr:
            adjustment = 0.92  # Снижаем на 8%
        # Если ДРР ниже целевого - повышаем ставку
        elif current_drr < target_drr * 0.8:  # ДРР на 20% ниже целевого
            adjustment = 1.15  # Повышаем на 15%
        elif current_drr < target_drr:
            adjustment = 1.08  # Повышаем на 8%
        else:
            adjustment = 1.0  # Оставляем как есть
        
        new_bid = current_bid * adjustment
        
        # Ограничиваем границами
        new_bid = max(min_bid, min(new_bid, max_bid))
        
        return round(new_bid, 2)
    
    # =========================================================================
    # СТАТИСТИКА
    # =========================================================================
    
    async def get_statistics(
        self,
        campaign_ids: List[int],
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> List[Dict]:
        """
        Получает статистику по кампаниям
        
        Args:
            campaign_ids: Список ID кампаний
            start_date: Начало периода (YYYY-MM-DD)
            end_date: Конец периода (YYYY-MM-DD)
        
        Returns:
            Статистика по кампаниям
        """
        url = f"{self.BASE_URL}/adv/v2/fullstats"
        
        # Даты по умолчанию - последние 7 дней
        if not end_date:
            end_date = datetime.now().strftime('%Y-%m-%d')
        if not start_date:
            start_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
        
        payload = [
            {
                'id': cid,
                'dates': [start_date, end_date]
            }
            for cid in campaign_ids
        ]
        
        try:
            async with self.session.post(url, json=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    logger.info(f"📊 Получена статистика для {len(data)} кампаний")
                    return data
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
            [campaign_id],
            start_date=start_date.strftime('%Y-%m-%d'),
            end_date=end_date.strftime('%Y-%m-%d')
        )
        
        if stats and len(stats) > 0:
            return stats[0].get('days', [])
        return []
    
    def calculate_drr(self, spent: float, orders_amount: float) -> float:
        """
        Рассчитывает ДРР (Динамическое Рекламное Расходование)
        
        Args:
            spent: Потрачено на рекламу
            orders_amount: Сумма заказов
        
        Returns:
            ДРР в процентах
        """
        if orders_amount == 0:
            return 0.0
        return round((spent / orders_amount) * 100, 2)
    
    # =========================================================================
    # СВОЙСТВА
    # =========================================================================
    
    @property
    def is_valid(self) -> bool:
        """Проверяет валидность подключения"""
        return self._is_valid
    
    @property
    def last_error(self) -> Optional[str]:
        """Возвращает последнюю ошибку"""
        return self._last_error


async def verify_wb_ads_api(api_key: str) -> Tuple[bool, str]:
    """
    Быстрая проверка API ключа рекламы
    
    Args:
        api_key: API ключ
    
    Returns:
        (валиден, сообщение)
    """
    try:
        async with WBAdsClient(api_key) as client:
            campaigns = await client.get_campaigns()
            return True, f"✅ API работает. Найдено {len(campaigns)} кампаний"
    except Exception as e:
        return False, f"❌ Ошибка: {e}"


if __name__ == "__main__":
    # Тестирование
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python wb_ads_client.py <api_key>")
        sys.exit(1)
    
    api_key = sys.argv[1]
    valid, message = asyncio.run(verify_wb_ads_api(api_key))
    print(message)
