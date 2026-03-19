# agents/pricing_agent.py - Подагент ценообразования
"""
Pricing Agent - автономный подагент для управления ценами
Отвечает только за ценообразование, работает по расписанию
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

# Импорт модулей системы
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from modules.pricing_engine import PricingEngine, PricingStrategy
from modules.ab_testing import ABTestingFramework
from modules.sales_history import SalesHistoryManager

logger = logging.getLogger('pricing_agent')


class PricingAgent:
    """
    🤖 Pricing Agent - автономный подагент
    
    Задачи:
    1. Мониторинг цен конкурентов
    2. Расчет оптимальных цен
    3. Применение стратегий
    4. Отчетность оркестратору
    
    Работает: каждые 10 минут (или по триггеру)
    """
    
    def __init__(self, clients_dir: str = "/opt/clients"):
        self.clients_dir = Path(clients_dir)
        self.agent_dir = self.clients_dir / "agents" / "pricing"
        self.agent_dir.mkdir(parents=True, exist_ok=True)
        
        # Подключаем модули
        self.pricing_engine = PricingEngine(clients_dir)
        self.ab_testing = ABTestingFramework(clients_dir)
        self.sales_history = SalesHistoryManager(clients_dir)
        
        # Статус агента
        self.status_file = self.agent_dir / "status.json"
        self.status = self._load_status()
        
        # Лог действий
        self.log_file = self.agent_dir / "actions.log"
    
    def _load_status(self) -> Dict:
        """Загружает статус агента"""
        if self.status_file.exists():
            with open(self.status_file, 'r') as f:
                return json.load(f)
        return {
            'last_run': None,
            'total_price_changes': 0,
            'active_strategies': {},
            'is_running': False
        }
    
    def _save_status(self):
        """Сохраняет статус"""
        with open(self.status_file, 'w') as f:
            json.dump(self.status, f, indent=2, default=str)
    
    def _log_action(self, action: str, details: Dict):
        """Логирует действие"""
        entry = {
            'timestamp': datetime.now().isoformat(),
            'action': action,
            'details': details
        }
        
        with open(self.log_file, 'a') as f:
            f.write(json.dumps(entry) + '\n')
    
    async def run_cycle(self, client_id: str, platform: str = "wb"):
        """
        Один цикл работы агента
        
        Args:
            client_id: ID клиента
            platform: 'wb' или 'ozon'
        """
        logger.info(f"🔄 Pricing Agent cycle for {client_id}/{platform}")
        
        self.status['is_running'] = True
        self._save_status()
        
        try:
            # 1. Получаем список товаров клиента
            products = await self._get_client_products(client_id, platform)
            
            # 2. Для каждого товара рассчитываем цену
            for product in products:
                await self._process_product(client_id, platform, product)
            
            # 3. Обновляем статус
            self.status['last_run'] = datetime.now().isoformat()
            self._save_status()
            
            logger.info(f"✅ Pricing Agent cycle completed: {len(products)} products processed")
            
        except Exception as e:
            logger.error(f"❌ Pricing Agent error: {e}")
            self._log_action('error', {'error': str(e)})
        
        finally:
            self.status['is_running'] = False
            self._save_status()
    
    async def _get_client_products(self, client_id: str, platform: str) -> List[Dict]:
        """Получает список товаров клиента"""
        # Заглушка - в реальности API запрос
        # Для теста возвращаем mock данные
        return [
            {
                'id': '12345',
                'name': 'Тестовый товар 1',
                'current_price': 1500,
                'cost_price': 800,
                'stock': 45,
                'category': 'electronics'
            },
            {
                'id': '67890',
                'name': 'Тестовый товар 2',
                'current_price': 2300,
                'cost_price': 1200,
                'stock': 12,
                'category': 'home'
            }
        ]
    
    async def _process_product(self, client_id: str, platform: str, product: Dict):
        """Обрабатывает один товар"""
        product_id = product['id']
        
        # 1. Получаем данные для расчета
        velocity_data = self.sales_history.get_product_velocity(
            client_id, platform, product_id
        )
        
        # 2. Получаем конкурентов (mock)
        competitors = await self._get_competitors(product_id)
        
        # 3. Определяем стратегию
        strategy = self.ab_testing.get_recommended_strategy(client_id)
        
        # 4. Рассчитываем оптимальную цену
        recommendation = self.pricing_engine.get_optimal_price(
            product_id=product_id,
            current_price=product['current_price'],
            cost_price=product['cost_price'],
            competitors=competitors,
            sales_velocity=velocity_data['current_velocity'],
            avg_velocity=velocity_data['avg_velocity'],
            stock_days=product['stock'] / max(velocity_data['current_velocity'], 1),
            strategy_name=strategy
        )
        
        # 5. Проверяем, нужно ли менять цену
        price_diff = abs(recommendation.recommended_price - product['current_price'])
        diff_percent = price_diff / product['current_price'] if product['current_price'] > 0 else 0
        
        if diff_percent > 0.02:  # Меняем только если разница > 2%
            await self._apply_price_change(
                client_id, platform, product_id,
                product['current_price'],
                recommendation.recommended_price,
                recommendation.reasoning
            )
        else:
            logger.info(f"⏭️ Price unchanged for {product_id} (diff: {diff_percent:.1%})")
    
    async def _get_competitors(self, product_id: str) -> List[Dict]:
        """Получает цены конкурентов"""
        # Заглушка - в реальности парсинг Mpstats или API
        return [
            {'price': 1450, 'rating': 4.3, 'reviews': 89},
            {'price': 1590, 'rating': 4.7, 'reviews': 120},
        ]
    
    async def _apply_price_change(
        self,
        client_id: str,
        platform: str,
        product_id: str,
        old_price: float,
        new_price: float,
        reasoning: str
    ):
        """Применяет изменение цены"""
        logger.info(f"💰 Price change: {product_id} {old_price} → {new_price}")
        
        # Логируем
        self._log_action('price_change', {
            'client_id': client_id,
            'platform': platform,
            'product_id': product_id,
            'old_price': old_price,
            'new_price': new_price,
            'reasoning': reasoning
        })
        
        # Обновляем счетчик
        self.status['total_price_changes'] = self.status.get('total_price_changes', 0) + 1
        
        # В реальности здесь был бы API вызов к WB/Ozon
        # await update_price_on_marketplace(platform, product_id, new_price)
    
    def get_report(self) -> Dict:
        """Возвращает отчет для оркестратора"""
        return {
            'agent': 'pricing',
            'status': 'running' if self.status['is_running'] else 'idle',
            'last_run': self.status.get('last_run'),
            'total_changes': self.status.get('total_price_changes', 0),
            'active_strategies': self.status.get('active_strategies', {})
        }


# Запуск из командной строки
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python pricing_agent.py <client_id>")
        sys.exit(1)
    
    client_id = sys.argv[1]
    
    agent = PricingAgent()
    asyncio.run(agent.run_cycle(client_id))
