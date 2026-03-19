# modules/ab_testing.py - A/B тестирование ценовых стратегий
"""
A/B Testing Framework для Seller AI
Тестирование ценовых стратегий на подвыборках товаров
"""

import json
import logging
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum

logger = logging.getLogger('ab_testing')


class TestStatus(Enum):
    """Статусы теста"""
    PENDING = "pending"      # Ожидает запуска
    RUNNING = "running"      # Активен
    COMPLETED = "completed"  # Завершен
    CANCELLED = "cancelled"  # Отменен


class TestResult(Enum):
    """Результаты теста"""
    VARIANT_A_WINS = "variant_a_wins"
    VARIANT_B_WINS = "variant_b_wins"
    NO_DIFFERENCE = "no_difference"
    INCONCLUSIVE = "inconclusive"


@dataclass
class ABTest:
    """A/B тест ценовой стратегии"""
    test_id: str
    name: str
    client_id: str
    product_ids: List[str]  # Товары в тесте
    
    # Варианты
    variant_a_strategy: str  # Стратегия A
    variant_b_strategy: str  # Стратегия B
    
    # Статус
    status: str
    start_date: str
    end_date: Optional[str] = None
    
    # Результаты
    variant_a_revenue: float = 0
    variant_b_revenue: float = 0
    variant_a_profit: float = 0
    variant_b_profit: float = 0
    
    # Метрики
    variant_a_sales: int = 0
    variant_b_sales: int = 0
    variant_a_bb_wins: int = 0
    variant_b_bb_wins: int = 0
    
    winner: Optional[str] = None
    confidence: float = 0.0


class ABTestingFramework:
    """
    Фреймворк A/B тестирования для ценовых стратегий
    
    Позволяет тестировать:
    - Разные стратегии ценообразования
    - Buy Box подходы
    - Velocity-based корректировки
    """
    
    def __init__(self, clients_dir: str = "/opt/clients"):
        self.clients_dir = Path(clients_dir)
        self.tests_dir = self.clients_dir / "GLOBAL_AI_LEARNING" / "ab_tests"
        self.tests_dir.mkdir(parents=True, exist_ok=True)
        
        self.tests_file = self.tests_dir / "active_tests.json"
        self.tests = self._load_tests()
    
    def _load_tests(self) -> Dict[str, ABTest]:
        """Загружает тесты"""
        if not self.tests_file.exists():
            return {}
        
        with open(self.tests_file, 'r') as f:
            data = json.load(f)
        
        tests = {}
        for test_id, test_data in data.items():
            tests[test_id] = ABTest(**test_data)
        
        return tests
    
    def _save_tests(self):
        """Сохраняет тесты"""
        data = {tid: asdict(t) for tid, t in self.tests.items()}
        with open(self.tests_file, 'w') as f:
            json.dump(data, f, indent=2, default=str)
    
    def create_test(
        self,
        client_id: str,
        name: str,
        product_ids: List[str],
        variant_a_strategy: str,
        variant_b_strategy: str,
        duration_days: int = 14
    ) -> str:
        """
        Создает новый A/B тест
        
        Args:
            product_ids: список товаров (четное количество, половина в A, половина в B)
            variant_a_strategy: стратегия для группы A
            variant_b_strategy: стратегия для группы B
            duration_days: длительность теста
        """
        test_id = str(uuid.uuid4())[:8]
        
        # Разбиваем товары на две группы
        mid = len(product_ids) // 2
        group_a = product_ids[:mid]
        group_b = product_ids[mid:]
        
        test = ABTest(
            test_id=test_id,
            name=name,
            client_id=client_id,
            product_ids=product_ids,
            variant_a_strategy=variant_a_strategy,
            variant_b_strategy=variant_b_strategy,
            status=TestStatus.PENDING.value,
            start_date=datetime.now().isoformat(),
        )
        
        self.tests[test_id] = test
        self._save_tests()
        
        logger.info(f"🧪 Создан A/B тест {test_id}: {name}")
        logger.info(f"   Группа A ({len(group_a)} товаров): {variant_a_strategy}")
        logger.info(f"   Группа B ({len(group_b)} товаров): {variant_b_strategy}")
        
        return test_id
    
    def start_test(self, test_id: str) -> bool:
        """Запускает тест"""
        if test_id not in self.tests:
            logger.error(f"Тест {test_id} не найден")
            return False
        
        test = self.tests[test_id]
        test.status = TestStatus.RUNNING.value
        test.start_date = datetime.now().isoformat()
        
        self._save_tests()
        logger.info(f"▶️ Тест {test_id} запущен")
        
        return True
    
    def record_sale(
        self,
        test_id: str,
        variant: str,  # 'A' или 'B'
        revenue: float,
        profit: float,
        won_buy_box: bool = False
    ):
        """Записывает продажу в тест"""
        if test_id not in self.tests:
            return
        
        test = self.tests[test_id]
        
        if variant == 'A':
            test.variant_a_revenue += revenue
            test.variant_a_profit += profit
            test.variant_a_sales += 1
            if won_buy_box:
                test.variant_a_bb_wins += 1
        else:
            test.variant_b_revenue += revenue
            test.variant_b_profit += profit
            test.variant_b_sales += 1
            if won_buy_box:
                test.variant_b_bb_wins += 1
        
        self._save_tests()
    
    def complete_test(self, test_id: str) -> Optional[Dict]:
        """
        Завершает тест и определяет победителя
        
        Returns:
            Результаты теста или None
        """
        if test_id not in self.tests:
            return None
        
        test = self.tests[test_id]
        test.status = TestStatus.COMPLETED.value
        test.end_date = datetime.now().isoformat()
        
        # Анализируем результаты
        # Критерии:
        # 1. Прибыль (вес 50%)
        # 2. Выручка (вес 30%)
        # 3. Buy Box win rate (вес 20%)
        
        profit_a = test.variant_a_profit
        profit_b = test.variant_b_profit
        
        revenue_a = test.variant_a_revenue
        revenue_b = test.variant_b_revenue
        
        bb_rate_a = test.variant_a_bb_wins / max(test.variant_a_sales, 1)
        bb_rate_b = test.variant_b_bb_wins / max(test.variant_b_sales, 1)
        
        # Нормализуем метрики
        total_profit = profit_a + profit_b
        total_revenue = revenue_a + revenue_b
        
        if total_profit > 0:
            profit_score_a = profit_a / total_profit
            profit_score_b = profit_b / total_profit
        else:
            profit_score_a = profit_score_b = 0.5
        
        if total_revenue > 0:
            revenue_score_a = revenue_a / total_revenue
            revenue_score_b = revenue_b / total_revenue
        else:
            revenue_score_a = revenue_score_b = 0.5
        
        # Итоговые скоры
        score_a = profit_score_a * 0.5 + revenue_score_a * 0.3 + bb_rate_a * 0.2
        score_b = profit_score_b * 0.5 + revenue_score_b * 0.3 + bb_rate_b * 0.2
        
        # Определяем победителя
        diff = abs(score_a - score_b)
        
        if diff < 0.05:
            test.winner = TestResult.NO_DIFFERENCE.value
            test.confidence = 1 - diff
        elif score_a > score_b:
            test.winner = TestResult.VARIANT_A_WINS.value
            test.confidence = min(diff * 2, 0.95)
        else:
            test.winner = TestResult.VARIANT_B_WINS.value
            test.confidence = min(diff * 2, 0.95)
        
        self._save_tests()
        
        logger.info(f"✅ Тест {test_id} завершен")
        logger.info(f"   Победитель: {test.winner} (уверенность: {test.confidence:.0%})")
        
        return {
            'test_id': test_id,
            'winner': test.winner,
            'confidence': test.confidence,
            'variant_a': {
                'revenue': test.variant_a_revenue,
                'profit': test.variant_a_profit,
                'sales': test.variant_a_sales,
                'bb_wins': test.variant_a_bb_wins
            },
            'variant_b': {
                'revenue': test.variant_b_revenue,
                'profit': test.variant_b_profit,
                'sales': test.variant_b_sales,
                'bb_wins': test.variant_b_bb_wins
            }
        }
    
    def get_active_tests(self, client_id: Optional[str] = None) -> List[ABTest]:
        """Возвращает активные тесты"""
        active = [t for t in self.tests.values() if t.status == TestStatus.RUNNING.value]
        
        if client_id:
            active = [t for t in active if t.client_id == client_id]
        
        return active
    
    def get_test_results(self, test_id: str) -> Optional[Dict]:
        """Возвращает результаты теста"""
        if test_id not in self.tests:
            return None
        
        test = self.tests[test_id]
        
        return {
            'test_id': test.test_id,
            'name': test.name,
            'status': test.status,
            'winner': test.winner,
            'confidence': test.confidence,
            'variant_a_strategy': test.variant_a_strategy,
            'variant_b_strategy': test.variant_b_strategy,
            'variant_a_profit': test.variant_a_profit,
            'variant_b_profit': test.variant_b_profit,
            'duration': test.end_date if test.end_date else "ongoing"
        }
    
    def get_recommended_strategy(self, client_id: str, category: str = "default") -> str:
        """
        Рекомендует стратегию на основе истории A/B тестов
        """
        # Фильтруем завершенные тесты клиента
        completed = [
            t for t in self.tests.values()
            if t.client_id == client_id and t.status == TestStatus.COMPLETED.value
        ]
        
        if not completed:
            return "aggressive_buy_box"  # Стратегия по умолчанию
        
        # Считаем победы каждой стратегии
        strategy_wins = {}
        
        for test in completed:
            if test.confidence < 0.7:  # Игнорируем ненадежные результаты
                continue
            
            if test.winner == TestResult.VARIANT_A_WINS.value:
                winner_strategy = test.variant_a_strategy
            elif test.winner == TestResult.VARIANT_B_WINS.value:
                winner_strategy = test.variant_b_strategy
            else:
                continue
            
            strategy_wins[winner_strategy] = strategy_wins.get(winner_strategy, 0) + 1
        
        # Возвращаем стратегию с наибольшим количеством побед
        if strategy_wins:
            best_strategy = max(strategy_wins.items(), key=lambda x: x[1])[0]
            logger.info(f"🎯 Рекомендуемая стратегия для {client_id}: {best_strategy}")
            return best_strategy
        
        return "aggressive_buy_box"
