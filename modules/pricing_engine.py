# modules/pricing_engine.py - Улучшенный движок ценообразования
"""
Pricing Engine v2.0 - Buy Box Targeting + Profit Optimizer
Стратегии:
1. Buy Box Targeting - целевая борьба за корзину
2. Profit Optimizer - повышение цены после победы
3. Velocity-based pricing - скорость продаж влияет на цену
"""

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict

logger = logging.getLogger('pricing_engine')


@dataclass
class PricingStrategy:
    """Стратегия ценообразования"""
    name: str
    min_price: float
    max_price: float
    target_margin: float
    competitor_strategy: str  # 'match', 'undercut', 'ignore'
    buy_box_target: bool = True
    profit_boost: bool = True
    velocity_factor: bool = True


@dataclass
class PriceRecommendation:
    """Рекомендация по цене"""
    current_price: float
    recommended_price: float
    strategy_used: str
    confidence: float
    reasoning: str
    expected_margin: float
    buy_box_probability: float


class PricingEngine:
    """
    Улучшенный движок ценообразования
    
    Алгоритмы:
    1. Buy Box Targeting - анализ конкурентов, цель = корзина
    2. Profit Optimizer - после победы в BB цена +5-15%
    3. Velocity-based - высокая скорость = можно дороже
    """
    
    def __init__(self, clients_dir: str = "/opt/clients"):
        self.clients_dir = Path(clients_dir)
        self.pricing_dir = self.clients_dir / "GLOBAL_AI_LEARNING" / "pricing"
        self.pricing_dir.mkdir(parents=True, exist_ok=True)
        
        # Загружаем историю цен
        self.price_history_file = self.pricing_dir / "price_history.json"
        self.price_history = self._load_price_history()
        
        # Стратегии по умолчанию
        self.default_strategies = {
            "aggressive_buy_box": PricingStrategy(
                name="aggressive_buy_box",
                min_price=0.85,  # -15% от себестоимости
                max_price=1.5,   # +50% от себестоимости
                target_margin=0.20,
                competitor_strategy='undercut',
                buy_box_target=True,
                profit_boost=True,
                velocity_factor=True
            ),
            "profit_maximizer": PricingStrategy(
                name="profit_maximizer",
                min_price=0.90,
                max_price=2.0,
                target_margin=0.35,
                competitor_strategy='match',
                buy_box_target=True,
                profit_boost=True,
                velocity_factor=True
            ),
            "velocity_optimizer": PricingStrategy(
                name="velocity_optimizer",
                min_price=0.80,
                max_price=1.3,
                target_margin=0.15,
                competitor_strategy='undercut',
                buy_box_target=False,
                profit_boost=False,
                velocity_factor=True
            )
        }
    
    def _load_price_history(self) -> Dict:
        """Загружает историю цен"""
        if self.price_history_file.exists():
            with open(self.price_history_file, 'r') as f:
                return json.load(f)
        return {}
    
    def _save_price_history(self):
        """Сохраняет историю цен"""
        with open(self.price_history_file, 'w') as f:
            json.dump(self.price_history, f, indent=2, default=str)
    
    def calculate_buy_box_probability(
        self,
        our_price: float,
        competitors: List[Dict],
        our_rating: float = 4.5,
        our_reviews: int = 100
    ) -> float:
        """
        Рассчитывает вероятность получения Buy Box
        
        Факторы:
        - Цена (вес 40%)
        - Рейтинг (вес 30%)
        - Количество отзывов (вес 20%)
        - Доставка FBS/FBO (вес 10%)
        """
        if not competitors:
            return 0.8  # Нет конкурентов = высокая вероятность
        
        # Находим лучшую цену
        best_price = min(c['price'] for c in competitors)
        
        # Ценовой фактор (40%)
        price_ratio = best_price / our_price if our_price > 0 else 1
        price_score = min(price_ratio * 0.4, 0.4)
        
        # Рейтинг (30%)
        avg_competitor_rating = sum(c.get('rating', 4.0) for c in competitors) / len(competitors)
        rating_score = min((our_rating / avg_competitor_rating) * 0.3, 0.3)
        
        # Отзывы (20%)
        avg_competitor_reviews = sum(c.get('reviews', 50) for c in competitors) / len(competitors)
        review_score = min((our_reviews / avg_competitor_reviews) * 0.2, 0.2)
        
        # Доставка (10%) - предполагаем FBO = лучше
        delivery_score = 0.1
        
        total_probability = price_score + rating_score + review_score + delivery_score
        return min(total_probability, 0.95)
    
    def apply_profit_optimizer(
        self,
        current_price: float,
        cost_price: float,
        has_buy_box: bool,
        days_with_bb: int = 0
    ) -> float:
        """
        Profit Optimizer - повышает цену после победы в Buy Box
        
        Логика:
        - День 1-3 с BB: цена +5%
        - День 4-7: цена +10%
        - День 8+: цена +15% (макс)
        """
        if not has_buy_box:
            return current_price
        
        base_margin = (current_price - cost_price) / current_price
        
        # Если маржа уже высокая - не повышаем
        if base_margin > 0.40:
            return current_price
        
        # Повышение в зависимости от дней с BB
        if days_with_bb >= 8:
            boost = 0.15
        elif days_with_bb >= 4:
            boost = 0.10
        elif days_with_bb >= 1:
            boost = 0.05
        else:
            boost = 0
        
        new_price = current_price * (1 + boost)
        
        # Проверяем, что новая цена не выше max
        max_allowed = cost_price * 2.0  # Макс +100% от себестоимости
        return min(new_price, max_allowed)
    
    def apply_velocity_factor(
        self,
        base_price: float,
        sales_velocity: float,  # продаж в день
        avg_velocity: float,    # средняя по категории
        stock_days: float
    ) -> float:
        """
        Velocity-based pricing
        
        Логика:
        - Высокая скорость (>2x средней) → можно +10% цены
        - Низкая скорость (<0.5x средней) → -10% цены
        - Мало запасов (<10 дней) → +5% (дефицит)
        """
        velocity_ratio = sales_velocity / avg_velocity if avg_velocity > 0 else 1
        
        adjustment = 0
        
        # Корректировка по скорости продаж
        if velocity_ratio > 2.0:
            adjustment = 0.10
        elif velocity_ratio > 1.5:
            adjustment = 0.05
        elif velocity_ratio < 0.5:
            adjustment = -0.10
        elif velocity_ratio < 0.8:
            adjustment = -0.05
        
        # Дефицит товара
        if stock_days < 10:
            adjustment += 0.05
        
        return base_price * (1 + adjustment)
    
    def get_optimal_price(
        self,
        product_id: str,
        current_price: float,
        cost_price: float,
        competitors: List[Dict],
        sales_velocity: float = 0,
        avg_velocity: float = 0,
        stock_days: float = 30,
        has_buy_box: bool = False,
        days_with_bb: int = 0,
        strategy_name: str = "aggressive_buy_box"
    ) -> PriceRecommendation:
        """
        Главный метод - рассчитывает оптимальную цену
        """
        strategy = self.default_strategies.get(strategy_name, self.default_strategies["aggressive_buy_box"])
        
        # 1. Рассчитываем базовую цену для Buy Box
        if competitors and strategy.buy_box_target:
            best_competitor = min(competitors, key=lambda x: x['price'])
            competitor_price = best_competitor['price']
            
            if strategy.competitor_strategy == 'undercut':
                base_price = competitor_price * 0.98  # На 2% ниже
            elif strategy.competitor_strategy == 'match':
                base_price = competitor_price
            else:
                base_price = current_price
        else:
            base_price = current_price
        
        # 2. Применяем Profit Optimizer (если есть BB)
        if strategy.profit_boost:
            base_price = self.apply_profit_optimizer(
                base_price, cost_price, has_buy_box, days_with_bb
            )
        
        # 3. Применяем Velocity Factor
        if strategy.velocity_factor and avg_velocity > 0:
            base_price = self.apply_velocity_factor(
                base_price, sales_velocity, avg_velocity, stock_days
            )
        
        # 4. Проверяем границы
        min_allowed = cost_price * strategy.min_price
        max_allowed = cost_price * strategy.max_price
        
        recommended_price = max(min(base_price, max_allowed), min_allowed)
        
        # 5. Рассчитываем метрики
        bb_probability = self.calculate_buy_box_probability(
            recommended_price, competitors
        )
        
        expected_margin = (recommended_price - cost_price) / recommended_price
        
        # 6. Формируем reasoning
        reasons = []
        if has_buy_box and days_with_bb > 0:
            reasons.append(f"Profit Optimizer: +{min(days_with_bb * 5, 15)}% к цене (дней с BB: {days_with_bb})")
        if sales_velocity > avg_velocity * 1.5:
            reasons.append(f"Velocity boost: высокая скорость продаж ({sales_velocity:.1f}/день)")
        if stock_days < 10:
            reasons.append(f"Scarcity factor: мало запасов ({stock_days:.0f} дней)")
        
        reasoning = "; ".join(reasons) if reasons else "Standard pricing"
        
        return PriceRecommendation(
            current_price=current_price,
            recommended_price=round(recommended_price, 2),
            strategy_used=strategy_name,
            confidence=bb_probability,
            reasoning=reasoning,
            expected_margin=expected_margin,
            buy_box_probability=bb_probability
        )
    
    def record_price_change(
        self,
        client_id: str,
        product_id: str,
        old_price: float,
        new_price: str,
        strategy: str,
        result: str  # 'success', 'failed', 'no_change'
    ):
        """Записывает изменение цены для обучения"""
        key = f"{client_id}:{product_id}"
        
        if key not in self.price_history:
            self.price_history[key] = []
        
        self.price_history[key].append({
            'timestamp': datetime.now().isoformat(),
            'old_price': old_price,
            'new_price': new_price,
            'strategy': strategy,
            'result': result
        })
        
        # Храним только последние 50 записей
        self.price_history[key] = self.price_history[key][-50:]
        self._save_price_history()
    
    def get_price_performance(
        self,
        client_id: str,
        product_id: str,
        days: int = 30
    ) -> Dict:
        """Анализ эффективности ценовых изменений"""
        key = f"{client_id}:{product_id}"
        history = self.price_history.get(key, [])
        
        if not history:
            return {'status': 'no_data'}
        
        # Анализируем результаты
        successful = sum(1 for h in history if h.get('result') == 'success')
        failed = sum(1 for h in history if h.get('result') == 'failed')
        total = len(history)
        
        return {
            'status': 'ok',
            'total_changes': total,
            'successful': successful,
            'failed': failed,
            'success_rate': successful / total if total > 0 else 0,
            'recommended_strategy': self._recommend_strategy(history)
        }
    
    def _recommend_strategy(self, history: List[Dict]) -> str:
        """Рекомендует стратегию на основе истории"""
        strategy_performance = {}
        
        for record in history:
            strategy = record.get('strategy', 'unknown')
            result = record.get('result', 'failed')
            
            if strategy not in strategy_performance:
                strategy_performance[strategy] = {'success': 0, 'total': 0}
            
            strategy_performance[strategy]['total'] += 1
            if result == 'success':
                strategy_performance[strategy]['success'] += 1
        
        # Находим лучшую стратегию
        best_strategy = 'aggressive_buy_box'
        best_rate = 0
        
        for strategy, stats in strategy_performance.items():
            rate = stats['success'] / stats['total']
            if rate > best_rate:
                best_rate = rate
                best_strategy = strategy
        
        return best_strategy
