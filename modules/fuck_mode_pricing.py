# modules/fuck_mode_pricing.py
"""
Реальная логика ценообразования для Fuck Mode

Интегрирует Pricing Engine v2.0 с API данными
"""

import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

from .api_client_factory import api_client_factory, CabinetNotFoundError
from .pricing_engine import PricingEngine, PricingRecommendation
from .mpstats_browser import mpstats_browser

logger = logging.getLogger('fuck_mode_pricing')


@dataclass
class PricingDecision:
    """Решение по ценообразованию"""
    action: str  # 'increase', 'decrease', 'maintain'
    current_price: float
    recommended_price: float
    reason: str
    confidence: float  # 0-1
    factors: Dict  # Факторы принятия решения


class FuckModePricing:
    """
    Модуль ценообразования для Fuck Mode
    
    Использует:
    1. WB/Ozon API для получения данных о товаре
    2. Mpstats для анализа конкурентов
    3. Pricing Engine v2.0 для расчета цены
    """
    
    def __init__(self):
        self.pricing_engine = PricingEngine()
    
    async def analyze_product_price(
        self,
        user_id: str,
        cabinet,
        product: Dict
    ) -> Optional[PricingDecision]:
        """
        Анализирует цену товара и принимает решение
        
        Args:
            user_id: ID пользователя
            cabinet: Объект кабинета
            product: Данные о товаре
            
        Returns:
            PricingDecision или None если изменение не требуется
        """
        try:
            # 1. Получаем данные о конкурентах через Mpstats
            competitor_data = await self._get_competitor_data(product)
            
            # 2. Получаем историю цен товара
            price_history = await self._get_price_history(user_id, cabinet, product)
            
            # 3. Получаем данные о продажах (velocity)
            velocity_data = await self._get_velocity_data(user_id, cabinet, product)
            
            # 4. Используем Pricing Engine для расчета
            recommendation = self.pricing_engine.calculate_price(
                current_price=product.get('price', 0),
                cost_price=product.get('cost_price', 0),
                competitor_prices=competitor_data.get('prices', []),
                price_history=price_history,
                velocity=velocity_data.get('current', 1.0),
                rating=product.get('rating', 0),
                reviews_count=product.get('reviews', 0)
            )
            
            # 5. Формируем решение
            if recommendation.recommended_price != product.get('price'):
                return PricingDecision(
                    action='increase' if recommendation.recommended_price > product.get('price') else 'decrease',
                    current_price=product.get('price'),
                    recommended_price=recommendation.recommended_price,
                    reason=recommendation.reason,
                    confidence=recommendation.confidence,
                    factors=recommendation.factors
                )
            
            return None  # Цена оптимальна
            
        except Exception as e:
            logger.error(f"Error analyzing price for {product.get('id')}: {e}")
            return None
    
    async def _get_competitor_data(self, product: Dict) -> Dict:
        """
        Получает данные о ценах конкурентов через Mpstats
        
        Returns:
            {'prices': [100, 110, 95], 'avg': 101.6, 'min': 95, 'max': 110}
        """
        try:
            # Пробуем получить через Mpstats browser
            nm_id = product.get('nm_id') or product.get('id')
            if not nm_id:
                return {'prices': [], 'avg': 0, 'min': 0, 'max': 0}
            
            # Получаем цены конкурентов
            competitors = await mpstats_browser.get_competitor_prices(str(nm_id))
            
            if competitors and 'prices' in competitors:
                prices = competitors['prices']
                return {
                    'prices': prices,
                    'avg': sum(prices) / len(prices) if prices else 0,
                    'min': min(prices) if prices else 0,
                    'max': max(prices) if prices else 0
                }
            
            return {'prices': [], 'avg': 0, 'min': 0, 'max': 0}
            
        except Exception as e:
            logger.warning(f"Failed to get competitor data: {e}")
            return {'prices': [], 'avg': 0, 'min': 0, 'max': 0}
    
    async def _get_price_history(
        self,
        user_id: str,
        cabinet,
        product: Dict
    ) -> List[Dict]:
        """
        Получает историю изменения цены товара
        
        Returns:
            [{'date': '2026-03-01', 'price': 100}, ...]
        """
        try:
            # Пока возвращаем пустую историю
            # TODO: Реализовать хранение истории цен в БД
            return []
        except Exception as e:
            logger.warning(f"Failed to get price history: {e}")
            return []
    
    async def _get_velocity_data(
        self,
        user_id: str,
        cabinet,
        product: Dict
    ) -> Dict:
        """
        Получает данные о скорости продаж (velocity)
        
        Returns:
            {'current': 1.5, 'average': 1.2, 'trend': 'up'}
        """
        try:
            # Пока возвращаем дефолт
            # TODO: Интеграция с sales_history.py
            return {'current': 1.0, 'average': 1.0, 'trend': 'stable'}
        except Exception as e:
            logger.warning(f"Failed to get velocity data: {e}")
            return {'current': 1.0, 'average': 1.0, 'trend': 'stable'}
    
    async def get_products_from_api(
        self,
        user_id: str,
        cabinet,
        limit: int = 100
    ) -> List[Dict]:
        """
        Получает список товаров из API кабинета
        
        Args:
            user_id: ID пользователя
            cabinet: Объект кабинета
            limit: Максимум товаров
            
        Returns:
            Список товаров с полями: id, name, price, stock, rating...
        """
        try:
            if cabinet.platform == 'wb':
                client = api_client_factory.get_wb_client(user_id, cabinet.id)
                products = await client.get_products(limit=limit)
                
                # Нормализуем формат
                return [
                    {
                        'id': str(p.get('nmId') or p.get('id')),
                        'name': p.get('name', 'Unknown'),
                        'price': float(p.get('price', 0)),
                        'cost_price': float(p.get('cost_price', 0)),
                        'stock': int(p.get('stock', 0)),
                        'rating': float(p.get('rating', 0)),
                        'reviews': int(p.get('reviews', 0)),
                        'category': p.get('category', 'unknown')
                    }
                    for p in products
                ]
            
            elif cabinet.platform == 'ozon':
                client = api_client_factory.get_ozon_client(user_id, cabinet.id)
                products = await client.get_products(limit=limit)
                
                # Нормализуем формат
                return [
                    {
                        'id': str(p.get('offer_id') or p.get('id')),
                        'name': p.get('name', 'Unknown'),
                        'price': float(p.get('price', 0)),
                        'cost_price': float(p.get('cost_price', 0)),
                        'stock': int(p.get('stock', 0)),
                        'rating': float(p.get('rating', 0)),
                        'reviews': int(p.get('reviews', 0)),
                        'category': p.get('category', 'unknown')
                    }
                    for p in products
                ]
            
            else:
                logger.error(f"Unknown platform: {cabinet.platform}")
                return []
                
        except CabinetNotFoundError:
            logger.error(f"Cabinet not found: {cabinet.id}")
            return []
        except Exception as e:
            logger.error(f"Failed to get products from API: {e}")
            return []


# Глобальный экземпляр
fuck_mode_pricing = FuckModePricing()
