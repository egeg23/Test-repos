# modules/ai_learning_engine.py - Глобальный AI Learning Engine
"""
Система обучения на гипотезах и результатах.
Сохраняет паттерны в GLOBAL_AI_LEARNING для всех клиентов.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict

logger = logging.getLogger('ai_learning_engine')


@dataclass
class PriceHypothesis:
    """Гипотеза о цене"""
    id: str
    product_id: str
    category: str
    hypothesis_type: str  # 'price_increase', 'price_decrease'
    old_price: float
    suggested_price: float
    reasoning: str
    created_at: str
    tested: bool = False
    result: Optional[Dict] = None
    confidence: float = 0.0  # 0-1


@dataclass
class DRRAnalysis:
    """Анализ ДРР"""
    campaign_id: str
    product_id: str
    current_drr: float
    target_drr: float
    orders_count: int
    ctr: float
    recommendation: str  # 'increase', 'decrease', 'maintain_high'
    reasoning: str
    created_at: str


class AILearningEngine:
    """
    Движок обучения на гипотезах.
    Сохраняет успешные стратегии в глобальную базу.
    """
    
    def __init__(self, clients_dir: str = "/opt/clients"):
        self.clients_dir = Path(clients_dir)
        self.learning_dir = self.clients_dir / "GLOBAL_AI_LEARNING"
        self.learning_dir.mkdir(parents=True, exist_ok=True)
        
        # Файлы базы знаний
        self.price_patterns_file = self.learning_dir / "price_patterns.json"
        self.drr_patterns_file = self.learning_dir / "drr_patterns.json"
        self.hypotheses_file = self.learning_dir / "active_hypotheses.json"
    
    def analyze_price_vs_competitors(
        self,
        client_id: str,
        product_id: str,
        category: str,
        current_price: float,
        our_sales_velocity: float,  # наши продажи в день
        competitors: List[Dict]  # [{price, sales_velocity, position}]
    ) -> Dict:
        """
        Анализ цены относительно конкурентов через Mpstats.
        
        Логика:
        - Если цена ниже рынка И мы продаем лучше конкурента с низкой ценой → можно поднять
        - Если цена ниже рынка И продажи хуже → анализировать дальше
        - Если при высокой цене продаем лучше → не спускаться
        """
        if not competitors:
            return {"recommendation": "no_data", "confidence": 0}
        
        # Находим среднюю цену рынка
        avg_market_price = sum(c['price'] for c in competitors) / len(competitors)
        
        # Находим конкурентов с ценой ниже и выше нас
        lower_priced = [c for c in competitors if c['price'] < current_price]
        higher_priced = [c for c in competitors if c['price'] > current_price]
        
        # Анализируем продажи конкурентов с более низкой ценой
        best_lower_sales = max([c['sales_velocity'] for c in lower_priced], default=0) if lower_priced else 0
        
        # Анализируем продажи конкурентов с более высокой ценой
        best_higher_sales = max([c['sales_velocity'] for c in higher_priced], default=0) if higher_priced else 0
        
        recommendation = {}
        
        # Сценарий 1: Наша цена ниже рынка
        if current_price < avg_market_price * 0.95:  # На 5%+
            if our_sales_velocity > best_lower_sales * 1.2:  # Продаем на 20% лучше дешевых
                recommendation = {
                    "recommendation": "price_increase",
                    "suggested_price": round(avg_market_price * 0.98, 2),
                    "reasoning": f"При цене ниже рынка продаем лучше конкурентов с низкой ценой ({our_sales_velocity:.1f} vs {best_lower_sales:.1f}/день). Можно поднять цену к среднерыночной.",
                    "confidence": 0.75,
                    "market_avg": avg_market_price
                }
            else:
                recommendation = {
                    "recommendation": "analyze_deeper",
                    "reasoning": f"Цена ниже рынка, но продажи не выделяются. Нужен анализ карточки/контента.",
                    "confidence": 0.4
                }
        
        # Сценарий 2: Наша цена выше рынка
        elif current_price > avg_market_price * 1.05:
            if our_sales_velocity > best_higher_sales * 0.8:  # Продаем не хуже дорогих
                recommendation = {
                    "recommendation": "maintain_price",
                    "reasoning": f"При высокой цене продаем на уровне дорогих конкурентов. Не снижать.",
                    "confidence": 0.8
                }
            else:
                recommendation = {
                    "recommendation": "consider_decrease",
                    "suggested_price": round(avg_market_price * 1.02, 2),
                    "reasoning": f"Цена выше рынка, продажи ниже дорогих конкурентов. Возможно снижение.",
                    "confidence": 0.5
                }
        
        # Сценарий 3: Цена на уровне рынка
        else:
            recommendation = {
                "recommendation": "maintain_price",
                "reasoning": "Цена на уровне рынка. Мониторить конкурентов.",
                "confidence": 0.6
            }
        
        # Сохраняем паттерн
        self._save_price_pattern(category, current_price, avg_market_price, recommendation)
        
        return recommendation
    
    def _save_price_pattern(self, category: str, our_price: float, market_avg: float, result: Dict):
        """Сохраняет паттерн ценообразования"""
        patterns = []
        if self.price_patterns_file.exists():
            try:
                with open(self.price_patterns_file, 'r') as f:
                    patterns = json.load(f)
            except:
                pass
        
        pattern = {
            "category": category,
            "our_price_ratio": our_price / market_avg if market_avg > 0 else 1,
            "recommendation": result.get("recommendation"),
            "confidence": result.get("confidence"),
            "timestamp": datetime.now().isoformat()
        }
        
        patterns.append(pattern)
        
        # Оставляем последние 1000 паттернов
        patterns = patterns[-1000:]
        
        with open(self.price_patterns_file, 'w') as f:
            json.dump(patterns, f, indent=2)
    
    def analyze_drr_situation(
        self,
        campaign_id: str,
        product_id: str,
        current_drr: float,
        target_drr: float,
        orders_count: int,
        total_views: int,
        ctr: float,
        days_since_start: int,
        category_competition: str = "medium"  # low, medium, high
    ) -> Dict:
        """
        Анализирует ситуацию с ДРР и дает рекомендации.
        
        Логика:
        - Высокий ДРР оправдан при: бусте нового товара, борьбе за топ-50, низком CTR
        - Нужно получить заказы для поднятия в листинге
        - Чем выше в листинге = дешевле реклама
        """
        recommendation = {}
        
        # Рассчитываем CTR
        calculated_ctr = (total_views / orders_count * 100) if orders_count > 0 else 0
        
        # Сценарий 1: Мало заказов, новый товар (буст)
        if orders_count < 10 and days_since_start < 14:
            recommendation = {
                "recommendation": "maintain_high_drr",
                "reasoning": "Новый товар, нужно набрать заказы для поднятия в листинге. Высокий ДРР оправдан для буста.",
                "action": "Продолжить с текущим ДРР еще 7-10 дней для набора истории заказов",
                "confidence": 0.85
            }
        
        # Сценарий 2: Борьба за топ-50 (высокая конкуренция)
        elif category_competition == "high" and orders_count < 50:
            recommendation = {
                "recommendation": "strategic_high_drr",
                "reasoning": "Высокая конкуренция в категории. Нужно закрепиться в топ-50 для снижения стоимости рекламы в будущем.",
                "action": "Поддерживать высокий ДРР до выхода в топ-50, затем постепенно снижать",
                "confidence": 0.7
            }
        
        # Сценарий 3: Низкий CTR
        elif ctr < 3.0:  # CTR меньше 3%
            recommendation = {
                "recommendation": "check_content",
                "reasoning": f"Низкий CTR ({ctr:.1f}%). Проблема не в ставках, а в карточке товара (фото, заголовок, цена).",
                "action": "Проверить: главное фото, заголовок, цена. Реклама не поможет при плохом CTR.",
                "confidence": 0.8
            }
        
        # Сценарий 4: Достаточно заказов, ДРР высокий
        elif orders_count >= 20 and current_drr > target_drr * 1.3:
            recommendation = {
                "recommendation": "decrease_drr",
                "reasoning": f"Достаточно заказов ({orders_count}) для позиции в листинге. Можно снижать ДРР к целевому {target_drr}%",
                "action": f"Снизить ДРР на 10% каждые 3 дня до достижения {target_drr}%",
                "confidence": 0.75
            }
        
        # Сценарий 5: Нормальная ситуация
        else:
            recommendation = {
                "recommendation": "maintain",
                "reasoning": f"ДРР в пределах нормы. Заказов: {orders_count}, CTR: {ctr:.1f}%",
                "action": "Продолжать мониторинг",
                "confidence": 0.6
            }
        
        # Сохраняем анализ
        self._save_drr_pattern(product_id, current_drr, orders_count, recommendation)
        
        return recommendation
    
    def _save_drr_pattern(self, product_id: str, drr: float, orders: int, result: Dict):
        """Сохраняет паттерн ДРР"""
        patterns = []
        if self.drr_patterns_file.exists():
            try:
                with open(self.drr_patterns_file, 'r') as f:
                    patterns = json.load(f)
            except:
                pass
        
        pattern = {
            "product_id": product_id,
            "drr": drr,
            "orders": orders,
            "recommendation": result.get("recommendation"),
            "timestamp": datetime.now().isoformat()
        }
        
        patterns.append(pattern)
        patterns = patterns[-500:]  # Последние 500
        
        with open(self.drr_patterns_file, 'w') as f:
            json.dump(patterns, f, indent=2)
    
    def get_category_insights(self, category: str) -> Dict:
        """Получает инсайты по категории из глобальной базы"""
        insights = {
            "price_patterns": [],
            "drr_patterns": [],
            "recommendations": []
        }
        
        # Загружаем паттерны цен
        if self.price_patterns_file.exists():
            try:
                with open(self.price_patterns_file, 'r') as f:
                    all_patterns = json.load(f)
                    insights["price_patterns"] = [
                        p for p in all_patterns if p.get("category") == category
                    ][-20:]  # Последние 20
            except:
                pass
        
        # Формируем рекомендации на основе паттернов
        if insights["price_patterns"]:
            successful_increases = sum(1 for p in insights["price_patterns"] 
                                     if p.get("recommendation") == "price_increase" and p.get("confidence", 0) > 0.6)
            total = len(insights["price_patterns"])
            if total > 0:
                success_rate = successful_increases / total
                if success_rate > 0.6:
                    insights["recommendations"].append(
                        f"В категории '{category}' повышение цены часто успешно ({success_rate:.0%} случаев)"
                    )
        
        return insights
    
    def create_price_hypothesis(self, client_id: str, product_id: str, category: str,
                               old_price: float, new_price: float, reasoning: str) -> str:
        """Создает гипотезу о цене для тестирования"""
        import uuid
        
        hypothesis = PriceHypothesis(
            id=str(uuid.uuid4()),
            product_id=product_id,
            category=category,
            hypothesis_type="price_increase" if new_price > old_price else "price_decrease",
            old_price=old_price,
            suggested_price=new_price,
            reasoning=reasoning,
            created_at=datetime.now().isoformat()
        )
        
        # Сохраняем
        hypotheses = []
        if self.hypotheses_file.exists():
            try:
                with open(self.hypotheses_file, 'r') as f:
                    hypotheses = json.load(f)
            except:
                pass
        
        hypotheses.append(asdict(hypothesis))
        
        with open(self.hypotheses_file, 'w') as f:
            json.dump(hypotheses, f, indent=2)
        
        logger.info(f"🧠 Создана гипотеза {hypothesis.id} для {product_id}")
        return hypothesis.id
    
    def record_hypothesis_result(self, hypothesis_id: str, result_data: Dict):
        """Записывает результат тестирования гипотезы"""
        if not self.hypotheses_file.exists():
            return
        
        try:
            with open(self.hypotheses_file, 'r') as f:
                hypotheses = json.load(f)
            
            for h in hypotheses:
                if h.get("id") == hypothesis_id:
                    h["tested"] = True
                    h["result"] = result_data
                    h["tested_at"] = datetime.now().isoformat()
                    
                    # Обновляем confidence на основе результата
                    success = result_data.get("success", False)
                    h["confidence"] = 0.9 if success else 0.1
                    
                    logger.info(f"✅ Гипотеза {hypothesis_id} протестирована: {'успех' if success else 'неудача'}")
                    break
            
            with open(self.hypotheses_file, 'w') as f:
                json.dump(hypotheses, f, indent=2)
                
        except Exception as e:
            logger.error(f"❌ Ошибка записи результата гипотезы: {e}")
