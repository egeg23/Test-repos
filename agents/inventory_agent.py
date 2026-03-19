# agents/inventory_agent.py - Подагент управления запасами
"""
Inventory Agent - мониторинг и прогнозирование запасов
"""

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
from modules.sales_history import SalesHistoryManager
from modules.notification_service import NotificationService

logger = logging.getLogger('inventory_agent')


class InventoryAgent:
    """🤖 Inventory Agent - управление запасами"""
    
    def __init__(self, clients_dir: str = "/opt/clients"):
        self.clients_dir = Path(clients_dir)
        self.agent_dir = self.clients_dir / "agents" / "inventory"
        self.agent_dir.mkdir(parents=True, exist_ok=True)
        
        self.sales_history = SalesHistoryManager(clients_dir)
        self.notifications = NotificationService(clients_dir)
        
        self.status_file = self.agent_dir / "status.json"
        self.status = self._load_status()
    
    def _load_status(self) -> Dict:
        if self.status_file.exists():
            with open(self.status_file) as f:
                return json.load(f)
        return {'last_run': None, 'alerts_sent': 0}
    
    def _save_status(self):
        with open(self.status_file, 'w') as f:
            json.dump(self.status, f, default=str)
    
    async def run_cycle(self, client_id: str, platform: str = "wb"):
        """Цикл работы агента"""
        logger.info(f"📦 Inventory Agent cycle for {client_id}")
        
        products = await self._get_products(client_id, platform)
        
        for product in products:
            await self._check_inventory(client_id, platform, product)
        
        self.status['last_run'] = datetime.now().isoformat()
        self._save_status()
        
        logger.info(f"✅ Inventory Agent: {len(products)} products checked")
    
    async def _get_products(self, client_id: str, platform: str) -> List[Dict]:
        """Получает товары"""
        return [
            {'id': '12345', 'stock': 45, 'name': 'Товар 1'},
            {'id': '67890', 'stock': 8, 'name': 'Товар 2'},
        ]
    
    async def _check_inventory(self, client_id: str, platform: str, product: Dict):
        """Проверяет запасы"""
        product_id = product['id']
        stock = product['stock']
        
        # Получаем скорость продаж
        velocity = self.sales_history.get_product_velocity(client_id, platform, product_id)
        
        # Рассчитываем дней до исчерпания
        stock_days = stock / max(velocity['current_velocity'], 0.1)
        
        # Проверяем двухдневный алерт
        should_alert = self.sales_history.check_two_day_alert(
            client_id, platform, product_id, stock_days, threshold=17
        )
        
        if should_alert:
            # Отправляем уведомление
            self.notifications.send_forecast_notification(
                client_id=client_id,
                product_id=product_id,
                product_name=product['name'],
                days_remaining=stock_days,
                avg_daily_sales=velocity['current_velocity'],
                current_stock=stock
            )
            self.status['alerts_sent'] = self.status.get('alerts_sent', 0) + 1
        
        logger.info(f"📦 {product_id}: {stock} шт, {stock_days:.1f} дней")


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python inventory_agent.py <client_id>")
        sys.exit(1)
    
    agent = InventoryAgent()
    asyncio.run(agent.run_cycle(sys.argv[1]))
