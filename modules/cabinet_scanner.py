# cabinet_scanner.py - Полное сканирование кабинета продавца
"""
Модуль для глубокого анализа кабинета после подключения.
Собирает: товары, цены, остатки, РК, конкурентов, нишу.
Интегрируется с self_learning_engine.
"""

import json
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
import asyncio

logger = logging.getLogger('cabinet_scanner')

@dataclass
class ProductData:
    """Данные о товаре"""
    artikul: str
    name: str
    price: float
    cost_price: Optional[float] = None
    stock: int = 0
    category: str = ""
    subcategory: str = ""
    brand: str = ""
    description: str = ""
    rating: float = 0.0
    reviews_count: int = 0
    sales_count: int = 0
    images_count: int = 0
    created_at: str = ""
    
@dataclass
class AdCampaign:
    """Рекламная кампания"""
    campaign_id: str
    name: str
    status: str  # ACTIVE, PAUSED, etc.
    budget: float
    spent: float
    drr: float  # ДРР
    views: int
    clicks: int
    ctr: float
    orders: int
    target_place: Optional[int] = None  # Целевая позиция

@dataclass
class CabinetProfile:
    """Профиль кабинета"""
    platform: str  # wb, ozon
    cabinet_id: str
    user_id: str
    scanned_at: str
    
    # Общая статистика
    total_products: int = 0
    active_products: int = 0
    out_of_stock: int = 0
    
    # Финансы
    total_revenue_30d: float = 0.0
    total_orders_30d: int = 0
    avg_order_value: float = 0.0
    
    # Категории
    main_categories: List[str] = None
    niche_tags: List[str] = None
    
    # Реклама
    active_campaigns: int = 0
    total_ad_spent_30d: float = 0.0
    avg_drr: float = 0.0
    
    # Риски
    risk_flags: List[str] = None
    opportunities: List[str] = None


class CabinetScanner:
    """Сканер кабинета продавца"""
    
    def __init__(self, user_id: str, platform: str, api_key: str, client_id: Optional[str] = None):
        self.user_id = user_id
        self.platform = platform  # wb, ozon
        self.api_key = api_key
        self.client_id = client_id or user_id
        self.profile = None
        self.products: List[ProductData] = []
        self.campaigns: List[AdCampaign] = []
        self.learning_entries = []
        
    async def scan_full_cabinet(self) -> Dict[str, Any]:
        """Полное сканирование кабинета"""
        logger.info(f"[CabinetScanner] Начинаю сканирование {self.platform} для {self.user_id}")
        
        self.profile = CabinetProfile(
            platform=self.platform,
            cabinet_id=self.user_id,
            user_id=self.user_id,
            scanned_at=datetime.now().isoformat(),
            main_categories=[],
            niche_tags=[],
            risk_flags=[],
            opportunities=[]
        )
        
        try:
            # 1. Сканируем товары
            await self._scan_products()
            
            # 2. Сканируем рекламу
            await self._scan_ad_campaigns()
            
            # 3. Анализируем нишу
            await self._analyze_niche()
            
            # 4. Оцениваем риски и возможности
            await self._evaluate_risks_and_opportunities()
            
            # 5. Сохраняем в self-learning
            await self._save_to_learning_engine()
            
            logger.info(f"[CabinetScanner] Сканирование завершено: {len(self.products)} товаров, {len(self.campaigns)} РК")
            
            return {
                'success': True,
                'profile': asdict(self.profile),
                'products_count': len(self.products),
                'campaigns_count': len(self.campaigns),
                'summary': self._generate_summary()
            }
            
        except Exception as e:
            logger.error(f"[CabinetScanner] Ошибка сканирования: {e}")
            await self._record_failure('scan_error', str(e))
            return {
                'success': False,
                'error': str(e)
            }
    
    async def _scan_products(self):
        """Сканирование товаров"""
        try:
            if self.platform == 'wb':
                from modules.wb_api_client import WildberriesAPIClient
                async with WildberriesAPIClient(self.api_key) as client:
                    raw_products = await client.get_products(limit=1000)
                    
                    for p in raw_products:
                        product = ProductData(
                            artikul=str(p.get('nmId', '')),
                            name=p.get('productName', ''),
                            price=p.get('price', 0),
                            cost_price=None,  # Будет заполнено позже
                            stock=p.get('quantity', 0),
                            category=p.get('subjectName', ''),
                            subcategory=p.get('parent', ''),
                            brand=p.get('brand', ''),
                            rating=p.get('rating', 0),
                            reviews_count=p.get('feedbacks', 0),
                            sales_count=p.get('ordersCount', 0),
                            images_count=len(p.get('photos', [])),
                            created_at=p.get('createAt', '')
                        )
                        self.products.append(product)
                        
            elif self.platform == 'ozon':
                from modules.ozon_api_client import OzonAPIClient
                async with OzonAPIClient(self.client_id, self.api_key) as client:
                    raw_products = await client.get_products(limit=1000)
                    
                    for p in raw_products:
                        product = ProductData(
                            artikul=str(p.get('offer_id', '')),
                            name=p.get('name', ''),
                            price=p.get('price', 0),
                            cost_price=None,
                            stock=p.get('stock', 0),
                            category=p.get('category', ''),
                            brand=p.get('brand', ''),
                            rating=p.get('rating', 0),
                            reviews_count=p.get('reviews_count', 0)
                        )
                        self.products.append(product)
            
            # Обновляем профиль
            self.profile.total_products = len(self.products)
            self.profile.active_products = len([p for p in self.products if p.stock > 0])
            self.profile.out_of_stock = len([p for p in self.products if p.stock == 0])
            
            # Извлекаем категории
            categories = set(p.category for p in self.products if p.category)
            self.profile.main_categories = list(categories)[:5]  # Топ-5 категорий
            
            logger.info(f"[CabinetScanner] Найдено товаров: {len(self.products)}")
            
        except Exception as e:
            logger.error(f"[CabinetScanner] Ошибка сканирования товаров: {e}")
            await self._record_failure('products_scan', str(e))
    
    async def _scan_ad_campaigns(self):
        """Сканирование рекламных кампаний"""
        try:
            if self.platform == 'wb':
                from modules.wb_ads_client import WildberriesAdsClient
                async with WildberriesAdsClient(self.api_key) as client:
                    campaigns = await client.get_campaigns()
                    
                    for c in campaigns:
                        campaign = AdCampaign(
                            campaign_id=str(c.get('advertId', '')),
                            name=c.get('name', ''),
                            status=c.get('status', 'UNKNOWN'),
                            budget=c.get('dailyBudget', 0),
                            spent=c.get('spend', 0),
                            drr=c.get('drr', 0),
                            views=c.get('views', 0),
                            clicks=c.get('clicks', 0),
                            ctr=c.get('ctr', 0),
                            orders=c.get('orders', 0)
                        )
                        self.campaigns.append(campaign)
                        
            elif self.platform == 'ozon':
                from modules.ozon_ads_client import OzonAdsClient
                async with OzonAdsClient(self.client_id, self.api_key) as client:
                    campaigns = await client.get_campaigns()
                    
                    for c in campaigns:
                        campaign = AdCampaign(
                            campaign_id=str(c.get('id', '')),
                            name=c.get('title', ''),
                            status=c.get('state', 'UNKNOWN'),
                            budget=c.get('daily_budget', 0),
                            spent=c.get('money_spent', 0),
                            drr=c.get('drr', 0),
                            views=c.get('views', 0),
                            clicks=c.get('clicks', 0),
                            ctr=c.get('ctr', 0),
                            orders=c.get('orders_count', 0)
                        )
                        self.campaigns.append(campaign)
            
            # Обновляем профиль
            self.profile.active_campaigns = len([c for c in self.campaigns if c.status == 'ACTIVE'])
            self.profile.total_ad_spent_30d = sum(c.spent for c in self.campaigns)
            
            if self.campaigns:
                self.profile.avg_drr = sum(c.drr for c in self.campaigns) / len(self.campaigns)
            
            logger.info(f"[CabinetScanner] Найдено РК: {len(self.campaigns)}")
            
        except Exception as e:
            logger.error(f"[CabinetScanner] Ошибка сканирования РК: {e}")
            await self._record_failure('ads_scan', str(e))
    
    async def _analyze_niche(self):
        """Анализ ниши на основе товаров"""
        if not self.products:
            return
        
        # Анализируем ценовые сегменты
        prices = [p.price for p in self.products if p.price > 0]
        if prices:
            avg_price = sum(prices) / len(prices)
            max_price = max(prices)
            min_price = min(prices)
            
            # Определяем нишу по ценам
            if avg_price < 500:
                self.profile.niche_tags.append('budget_segment')
            elif avg_price < 2000:
                self.profile.niche_tags.append('mid_segment')
            else:
                self.profile.niche_tags.append('premium_segment')
        
        # Анализ по категориям
        category_counts = {}
        for p in self.products:
            cat = p.category or 'unknown'
            category_counts[cat] = category_counts.get(cat, 0) + 1
        
        # Топ категории
        sorted_cats = sorted(category_counts.items(), key=lambda x: x[1], reverse=True)
        self.profile.main_categories = [cat for cat, _ in sorted_cats[:3]]
    
    async def _evaluate_risks_and_opportunities(self):
        """Оценка рисков и возможностей"""
        # Риски
        if self.profile.out_of_stock > self.profile.total_products * 0.3:
            self.profile.risk_flags.append('high_out_of_stock')
        
        if self.profile.avg_drr > 25:
            self.profile.risk_flags.append('high_drr')
        
        if len(self.campaigns) == 0 and self.profile.total_products > 0:
            self.profile.opportunities.append('no_ads_running')
        
        # Возможности
        if self.profile.avg_drr < 15 and len(self.campaigns) > 0:
            self.profile.opportunities.append('good_drr_can_scale')
        
        if self.profile.active_products > 50:
            self.profile.opportunities.append('large_catalog_optimize')
    
    async def _save_to_learning_engine(self):
        """Сохраняем данные в self-learning engine"""
        try:
            from modules.self_learning_engine import SelfLearningEngine
            
            engine = SelfLearningEngine()
            
            # Записываем успешное подключение
            await engine.record_event(
                user_id=self.user_id,
                platform=self.platform,
                event_type='cabinet_connected',
                data={
                    'products_count': len(self.products),
                    'campaigns_count': len(self.campaigns),
                    'categories': self.profile.main_categories
                },
                outcome='success'
            )
            
            # Записываем паттерны категорий
            if self.profile.main_categories:
                await engine.record_pattern(
                    pattern_type='category_niche',
                    pattern_data={
                        'categories': self.profile.main_categories,
                        'avg_price_range': self._get_price_range(),
                        'avg_drr': self.profile.avg_drr
                    },
                    source_user=self.user_id
                )
            
            logger.info(f"[CabinetScanner] Данные сохранены в self-learning")
            
        except Exception as e:
            logger.error(f"[CabinetScanner] Ошибка сохранения в learning engine: {e}")
    
    async def _record_failure(self, failure_type: str, details: str):
        """Записываем неудачу для предотвращения в будущем"""
        try:
            from modules.self_learning_engine import SelfLearningEngine
            
            engine = SelfLearningEngine()
            await engine.record_event(
                user_id=self.user_id,
                platform=self.platform,
                event_type=f'failure_{failure_type}',
                data={'details': details},
                outcome='failure'
            )
            
            logger.warning(f"[CabinetScanner] Записана неудача: {failure_type}")
            
        except Exception as e:
            logger.error(f"[CabinetScanner] Ошибка записи неудачи: {e}")
    
    def _get_price_range(self) -> str:
        """Возвращает ценовой диапазон"""
        prices = [p.price for p in self.products if p.price > 0]
        if not prices:
            return 'unknown'
        avg = sum(prices) / len(prices)
        if avg < 500:
            return 'budget'
        elif avg < 2000:
            return 'mid'
        return 'premium'
    
    def _generate_summary(self) -> str:
        """Генерирует текстовое summary для пользователя"""
        lines = [
            f"📦 Товаров: {self.profile.total_products} (активных: {self.profile.active_products})",
            f"📢 Рекламных кампаний: {len(self.campaigns)} (активных: {self.profile.active_campaigns})",
            f"💰 Средний ДРР: {self.profile.avg_drr:.1f}%",
        ]
        
        if self.profile.main_categories:
            lines.append(f"🏷 Категории: {', '.join(self.profile.main_categories[:3])}")
        
        if self.profile.opportunities:
            lines.append(f"✅ Возможности: {len(self.profile.opportunities)}")
        
        if self.profile.risk_flags:
            lines.append(f"⚠️ Риски: {len(self.profile.risk_flags)}")
        
        return '\n'.join(lines)


# Экспортируем для использования
__all__ = ['CabinetScanner', 'ProductData', 'AdCampaign', 'CabinetProfile']