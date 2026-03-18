"""
CTR Monitor Module - Мониторинг CTR рекламных кампаний на WB и Ozon
"""

import asyncio
import json
import logging
import aiohttp
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)

BASE_DIR = Path("/opt/clients")
CTR_DATA_DIR = "ctr_monitor"

# WB Adverts API endpoints
WB_ADVERTS_API = "https://advert-api.wildberries.ru"
WB_STAT_API = "https://statistics-api.wildberries.ru"

# Ozon API endpoints
OZON_API = "https://api-seller.ozon.ru"


@dataclass
class CampaignMetrics:
    """Метрики кампании"""
    article_id: str
    campaign_id: str
    marketplace: str  # 'wb' или 'ozon'
    name: str
    status: str
    impressions: int
    clicks: int
    ctr: float
    start_ctr: Optional[float] = None
    current_ctr: Optional[float] = None
    started_at: str = ""
    completed_at: Optional[str] = None
    status_monitor: str = "collecting"  # collecting, completed, error
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'CampaignMetrics':
        return cls(**data)


class CTRMonitor:
    """Основной класс мониторинга CTR"""
    
    TARGET_IMPRESSIONS = 1000  # Целевое количество показов
    CHECK_INTERVAL = 1800  # 30 минут в секундах
    RETRY_DELAY = 300  # 5 минут при ошибке API
    
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.user_dir = BASE_DIR / user_id
        self.ctr_dir = self.user_dir / CTR_DATA_DIR
        self.ctr_dir.mkdir(parents=True, exist_ok=True)
        
        self.active_campaigns_file = self.ctr_dir / "active_campaigns.json"
        self.history_file = self.ctr_dir / "history.json"
        
        # Кэш активных кампаний
        self._active_campaigns: Dict[str, CampaignMetrics] = {}
        self._load_active_campaigns()
    
    def _load_active_campaigns(self):
        """Загрузка активных кампаний из файла"""
        if self.active_campaigns_file.exists():
            try:
                with open(self.active_campaigns_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for campaign_id, campaign_data in data.items():
                        self._active_campaigns[campaign_id] = CampaignMetrics.from_dict(campaign_data)
            except Exception as e:
                logger.error(f"Error loading active campaigns: {e}")
    
    def _save_active_campaigns(self):
        """Сохранение активных кампаний в файл"""
        try:
            data = {k: v.to_dict() for k, v in self._active_campaigns.items()}
            with open(self.active_campaigns_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Error saving active campaigns: {e}")
    
    def _save_to_history(self, campaign: CampaignMetrics):
        """Сохранение кампании в историю"""
        history = []
        if self.history_file.exists():
            try:
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    history = json.load(f)
            except:
                history = []
        
        history.append(campaign.to_dict())
        
        try:
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(history, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Error saving to history: {e}")
    
    async def get_wb_api_key(self) -> Optional[str]:
        """Получение API ключа WB"""
        creds_file = self.user_dir / "credentials" / "wildberries" / "credentials.json"
        if creds_file.exists():
            try:
                with open(creds_file, 'r', encoding='utf-8') as f:
                    creds = json.load(f)
                    return creds.get('stat_api_key')
            except Exception as e:
                logger.error(f"Error reading WB credentials: {e}")
        return None
    
    async def get_ozon_credentials(self) -> Optional[Dict[str, str]]:
        """Получение credentials Ozon"""
        creds_file = self.user_dir / "credentials" / "ozon" / "credentials.json"
        if creds_file.exists():
            try:
                with open(creds_file, 'r', encoding='utf-8') as f:
                    creds = json.load(f)
                    return {
                        'client_id': creds.get('client_id'),
                        'api_key': creds.get('api_key')
                    }
            except Exception as e:
                logger.error(f"Error reading Ozon credentials: {e}")
        return None
    
    async def search_wb_campaigns(self, article_id: str) -> List[Dict]:
        """Поиск кампаний WB по артикулу товара"""
        api_key = await self.get_wb_api_key()
        if not api_key:
            raise ValueError("WB API key not found")
        
        headers = {
            "Authorization": api_key,
            "Content-Type": "application/json"
        }
        
        campaigns = []
        
        async with aiohttp.ClientSession() as session:
            # Получаем список всех кампаний
            try:
                # Сначала пробуем новое API
                async with session.get(
                    f"{WB_ADVERTS_API}/adv/v1/promotion/adverts",
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        if isinstance(data, list):
                            for camp in data:
                                # Проверяем, содержит ли кампания нужный артикул
                                if self._check_article_in_wb_campaign(camp, article_id):
                                    campaigns.append({
                                        'campaign_id': str(camp.get('advertId', camp.get('id'))),
                                        'name': camp.get('name', 'Без названия'),
                                        'status': camp.get('status', 'unknown'),
                                        'type': camp.get('type', 'unknown'),
                                        'article_id': article_id
                                    })
                    else:
                        logger.warning(f"WB API returned status {resp.status}")
            except Exception as e:
                logger.error(f"Error fetching WB campaigns: {e}")
        
        return campaigns
    
    def _check_article_in_wb_campaign(self, campaign: Dict, article_id: str) -> bool:
        """Проверяет, содержит ли кампания WB нужный артикул"""
        # Проверяем различные поля где может быть артикул
        campaign_name = str(campaign.get('name', ''))
        if article_id in campaign_name:
            return True
        
        # Проверяем параметры кампании
        params = campaign.get('params', [])
        if isinstance(params, list):
            for param in params:
                if isinstance(param, dict):
                    if str(param.get('nm', '')) == article_id:
                        return True
                    if str(param.get('subjectId', '')) == article_id:
                        return True
        
        # Проверяем autoParams
        auto_params = campaign.get('autoParams', {})
        if isinstance(auto_params, dict):
            nm_array = auto_params.get('nm', [])
            if isinstance(nm_array, list):
                if int(article_id) in nm_array or article_id in [str(x) for x in nm_array]:
                    return True
        
        return False
    
    async def search_ozon_campaigns(self, article_id: str) -> List[Dict]:
        """Поиск кампаний Ozon по артикулу/SKU"""
        creds = await self.get_ozon_credentials()
        if not creds:
            raise ValueError("Ozon credentials not found")
        
        headers = {
            "Client-Id": creds['client_id'],
            "Api-Key": creds['api_key'],
            "Content-Type": "application/json"
        }
        
        campaigns = []
        
        async with aiohttp.ClientSession() as session:
            try:
                # Получаем список рекламных кампаний
                async with session.post(
                    f"{OZON_API}/v1/adv/campaign/list",
                    headers=headers,
                    json={},
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        camp_list = data.get('campaigns', [])
                        
                        for camp in camp_list:
                            # Проверяем наличие артикула в кампании
                            if await self._check_article_in_ozon_campaign(
                                session, headers, camp, article_id
                            ):
                                campaigns.append({
                                    'campaign_id': str(camp.get('id')),
                                    'name': camp.get('title', 'Без названия'),
                                    'status': camp.get('state', 'unknown'),
                                    'type': camp.get('advObjectType', 'unknown'),
                                    'article_id': article_id
                                })
                    else:
                        logger.warning(f"Ozon API returned status {resp.status}")
            except Exception as e:
                logger.error(f"Error fetching Ozon campaigns: {e}")
        
        return campaigns
    
    async def _check_article_in_ozon_campaign(
        self, session: aiohttp.ClientSession, headers: Dict, 
        campaign: Dict, article_id: str
    ) -> bool:
        """Проверяет содержит ли кампания Ozon нужный артикул"""
        try:
            # Получаем детали кампании
            campaign_id = campaign.get('id')
            if not campaign_id:
                return False
            
            # Проверяем в названии
            campaign_title = str(campaign.get('title', ''))
            if article_id in campaign_title:
                return True
            
            # Проверяем товары в кампании
            async with session.post(
                f"{OZON_API}/v1/adv/campaign/products",
                headers=headers,
                json={"campaignId": campaign_id},
                timeout=aiohttp.ClientTimeout(total=30)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    products = data.get('products', [])
                    
                    for product in products:
                        if str(product.get('sku', '')) == article_id:
                            return True
                        if str(product.get('offerId', '')) == article_id:
                            return True
        except Exception as e:
            logger.error(f"Error checking Ozon campaign: {e}")
        
        return False
    
    async def get_wb_campaign_stats(self, campaign_id: str) -> Optional[Dict]:
        """Получение статистики кампании WB"""
        api_key = await self.get_wb_api_key()
        if not api_key:
            raise ValueError("WB API key not found")
        
        headers = {
            "Authorization": api_key,
            "Content-Type": "application/json"
        }
        
        # Получаем статистику за последние 7 дней
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)
        
        async with aiohttp.ClientSession() as session:
            try:
                # Метод получения статистики кампании
                async with session.get(
                    f"{WB_ADVERTS_API}/adv/v2/fullstats",
                    headers=headers,
                    params={
                        "id": campaign_id,
                        "from": start_date.strftime("%Y-%m-%d"),
                        "to": end_date.strftime("%Y-%m-%d")
                    },
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return self._parse_wb_stats(data)
                    else:
                        # Пробуем альтернативный метод
                        return await self._get_wb_stats_alternative(session, headers, campaign_id)
            except Exception as e:
                logger.error(f"Error fetching WB campaign stats: {e}")
                return None
    
    async def _get_wb_stats_alternative(
        self, session: aiohttp.ClientSession, headers: Dict, campaign_id: str
    ) -> Optional[Dict]:
        """Альтернативный метод получения статистики WB"""
        try:
            # Получаем данные из деталей кампании
            async with session.get(
                f"{WB_ADVERTS_API}/adv/v1/promotion/adverts",
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if isinstance(data, list):
                        for camp in data:
                            if str(camp.get('advertId', camp.get('id'))) == campaign_id:
                                return self._parse_wb_stats(camp)
        except Exception as e:
            logger.error(f"Error in alternative WB stats: {e}")
        return None
    
    def _parse_wb_stats(self, data: Dict) -> Dict:
        """Парсинг статистики WB"""
        # Различные форматы ответа API
        impressions = 0
        clicks = 0
        
        # Пробуем разные поля
        if 'statistics' in data:
            stats = data['statistics']
            if isinstance(stats, dict):
                impressions = stats.get('views', stats.get('impressions', 0))
                clicks = stats.get('clicks', stats.get('ctr', 0))
        elif 'stats' in data:
            stats_list = data['stats']
            if isinstance(stats_list, list):
                for stat in stats_list:
                    impressions += stat.get('views', 0)
                    clicks += stat.get('clicks', 0)
        else:
            impressions = data.get('views', data.get('impressions', 0))
            clicks = data.get('clicks', 0)
        
        ctr = (clicks / impressions * 100) if impressions > 0 else 0
        
        return {
            'impressions': impressions,
            'clicks': clicks,
            'ctr': round(ctr, 2)
        }
    
    async def get_ozon_campaign_stats(self, campaign_id: str) -> Optional[Dict]:
        """Получение статистики кампании Ozon"""
        creds = await self.get_ozon_credentials()
        if not creds:
            raise ValueError("Ozon credentials not found")
        
        headers = {
            "Client-Id": creds['client_id'],
            "Api-Key": creds['api_key'],
            "Content-Type": "application/json"
        }
        
        async with aiohttp.ClientSession() as session:
            try:
                # Получаем статистику кампании
                async with session.post(
                    f"{OZON_API}/v1/adv/campaign/stats",
                    headers=headers,
                    json={"campaignIds": [int(campaign_id)]},
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        campaigns = data.get('campaigns', [])
                        if campaigns:
                            return self._parse_ozon_stats(campaigns[0])
            except Exception as e:
                logger.error(f"Error fetching Ozon campaign stats: {e}")
        
        return None
    
    def _parse_ozon_stats(self, data: Dict) -> Dict:
        """Парсинг статистики Ozon"""
        stats = data.get('statistics', {})
        
        impressions = stats.get('impressions', 0)
        clicks = stats.get('clicks', 0)
        ctr = stats.get('ctr', 0)
        
        # Если CTR не пришел, считаем сами
        if ctr == 0 and impressions > 0:
            ctr = round(clicks / impressions * 100, 2)
        
        return {
            'impressions': impressions,
            'clicks': clicks,
            'ctr': round(ctr, 2)
        }
    
    async def start_monitoring(
        self, article_id: str, campaign_id: str, marketplace: str
    ) -> CampaignMetrics:
        """Запуск мониторинга кампании"""
        # Получаем начальные метрики
        if marketplace == 'wb':
            stats = await self.get_wb_campaign_stats(campaign_id)
        elif marketplace == 'ozon':
            stats = await self.get_ozon_campaign_stats(campaign_id)
        else:
            raise ValueError(f"Unknown marketplace: {marketplace}")
        
        if not stats:
            raise ValueError("Failed to get campaign stats")
        
        # Ищем информацию о кампании
        if marketplace == 'wb':
            campaigns = await self.search_wb_campaigns(article_id)
        else:
            campaigns = await self.search_ozon_campaigns(article_id)
        
        campaign_name = "Без названия"
        campaign_status = "unknown"
        for camp in campaigns:
            if camp['campaign_id'] == campaign_id:
                campaign_name = camp['name']
                campaign_status = camp['status']
                break
        
        # Создаем объект метрик
        campaign = CampaignMetrics(
            article_id=article_id,
            campaign_id=campaign_id,
            marketplace=marketplace,
            name=campaign_name,
            status=campaign_status,
            impressions=stats['impressions'],
            clicks=stats['clicks'],
            ctr=stats['ctr'],
            start_ctr=stats['ctr'],
            current_ctr=stats['ctr'],
            started_at=datetime.now().isoformat(),
            status_monitor="collecting"
        )
        
        # Сохраняем
        self._active_campaigns[campaign_id] = campaign
        self._save_active_campaigns()
        
        return campaign
    
    async def update_campaign(self, campaign_id: str) -> Optional[CampaignMetrics]:
        """Обновление метрик кампании"""
        if campaign_id not in self._active_campaigns:
            return None
        
        campaign = self._active_campaigns[campaign_id]
        
        try:
            if campaign.marketplace == 'wb':
                stats = await self.get_wb_campaign_stats(campaign_id)
            elif campaign.marketplace == 'ozon':
                stats = await self.get_ozon_campaign_stats(campaign_id)
            else:
                return None
            
            if stats:
                campaign.impressions = stats['impressions']
                campaign.clicks = stats['clicks']
                campaign.current_ctr = stats['ctr']
                
                # Проверяем достижение цели
                if campaign.impressions >= self.TARGET_IMPRESSIONS:
                    campaign.status_monitor = "completed"
                    campaign.completed_at = datetime.now().isoformat()
                    self._save_to_history(campaign)
                    del self._active_campaigns[campaign_id]
                
                self._save_active_campaigns()
                return campaign
                
        except Exception as e:
            logger.error(f"Error updating campaign {campaign_id}: {e}")
            campaign.status_monitor = "error"
            self._save_active_campaigns()
        
        return None
    
    async def monitor_loop(self, callback=None):
        """Основной цикл мониторинга"""
        while True:
            try:
                for campaign_id in list(self._active_campaigns.keys()):
                    campaign = await self.update_campaign(campaign_id)
                    
                    if campaign and callback:
                        await callback(campaign)
                    
                    # Небольшая пауза между запросами
                    await asyncio.sleep(1)
                
                # Если нет активных кампаний, выходим из цикла
                if not self._active_campaigns:
                    logger.info("No active campaigns, stopping monitor loop")
                    break
                
                await asyncio.sleep(self.CHECK_INTERVAL)
                
            except Exception as e:
                logger.error(f"Error in monitor loop: {e}")
                await asyncio.sleep(self.RETRY_DELAY)
    
    def get_active_campaigns(self) -> List[CampaignMetrics]:
        """Получение списка активных кампаний"""
        return list(self._active_campaigns.values())
    
    def get_campaign(self, campaign_id: str) -> Optional[CampaignMetrics]:
        """Получение кампании по ID"""
        return self._active_campaigns.get(campaign_id)
    
    async def stop_monitoring(self, campaign_id: str) -> bool:
        """Остановка мониторинга кампании"""
        if campaign_id in self._active_campaigns:
            campaign = self._active_campaigns[campaign_id]
            campaign.status_monitor = "completed"
            campaign.completed_at = datetime.now().isoformat()
            self._save_to_history(campaign)
            del self._active_campaigns[campaign_id]
            self._save_active_campaigns()
            return True
        return False


# Глобальный реестр мониторов
_monitors: Dict[str, CTRMonitor] = {}


def get_monitor(user_id: str) -> CTRMonitor:
    """Получение или создание монитора для пользователя"""
    if user_id not in _monitors:
        _monitors[user_id] = CTRMonitor(user_id)
    return _monitors[user_id]


async def search_campaigns(user_id: str, article_id: str, marketplace: str) -> List[Dict]:
    """Поиск кампаний по артикулу"""
    monitor = get_monitor(user_id)
    
    if marketplace == 'wb':
        return await monitor.search_wb_campaigns(article_id)
    elif marketplace == 'ozon':
        return await monitor.search_ozon_campaigns(article_id)
    else:
        raise ValueError(f"Unknown marketplace: {marketplace}")


async def start_ctr_monitoring(
    user_id: str, article_id: str, campaign_id: str, marketplace: str
) -> CampaignMetrics:
    """Запуск мониторинга CTR"""
    monitor = get_monitor(user_id)
    return await monitor.start_monitoring(article_id, campaign_id, marketplace)


async def stop_ctr_monitoring(user_id: str, campaign_id: str) -> bool:
    """Остановка мониторинга"""
    monitor = get_monitor(user_id)
    return await monitor.stop_monitoring(campaign_id)


async def get_campaign_metrics(user_id: str, campaign_id: str) -> Optional[CampaignMetrics]:
    """Получение метрик кампании"""
    monitor = get_monitor(user_id)
    return monitor.get_campaign(campaign_id)
