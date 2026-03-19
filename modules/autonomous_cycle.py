#!/usr/bin/env python3
# modules/autonomous_cycle.py - Автономный цикл Seller AI
"""
Автономный цикл управления маркетплейсами.
Запускается каждые 10 минут через systemd timer.

Задачи:
1. Проверка всех подключенных магазинов
2. Анализ конкурентов (Mpstats)
3. Мониторинг остатков
4. Оптимизация рекламы (ДРР)
5. Отправка отчетов и рекомендаций
"""

import asyncio
import json
import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/opt/telegram_bot/logs/autonomous_cycle.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('autonomous_cycle')

# Добавляем путь к модулям
sys.path.insert(0, '/opt/telegram_bot')


class AutonomousCycle:
    """Главный класс автономного цикла"""
    
    def __init__(self):
        self.clients_dir = Path('/opt/clients')
        self.results = []
        
    async def run(self):
        """Запускает полный цикл проверки"""
        logger.info("=" * 60)
        logger.info(f"🚀 Автономный цикл запущен: {datetime.now()}")
        logger.info("=" * 60)
        
        # Получаем список всех клиентов
        clients = self._get_active_clients()
        logger.info(f"📊 Найдено клиентов: {len(clients)}")
        
        for client_id in clients:
            try:
                await self._process_client(client_id)
            except Exception as e:
                logger.error(f"❌ Ошибка обработки клиента {client_id}: {e}")
        
        logger.info("=" * 60)
        logger.info(f"✅ Цикл завершен: {datetime.now()}")
        logger.info("=" * 60)
    
    def _get_active_clients(self) -> List[str]:
        """Получает список активных клиентов (только с папкой credentials)"""
        clients = []
        if self.clients_dir.exists():
            for item in self.clients_dir.iterdir():
                if item.is_dir() and not item.name.startswith('.'):
                    # Проверяем, есть ли папка credentials (признак реального клиента)
                    creds_dir = item / 'credentials'
                    if creds_dir.exists():
                        clients.append(item.name)
        return clients
    
    async def _process_client(self, client_id: str):
        """Обрабатывает одного клиента"""
        logger.info(f"\n👤 Клиент: {client_id}")
        
        # Проверяем подключенные магазины
        stores = self._get_connected_stores(client_id)
        
        for platform, creds in stores.items():
            try:
                if platform == 'wb':
                    await self._check_wildberries(client_id, creds)
                elif platform == 'ozon':
                    await self._check_ozon(client_id, creds)
            except Exception as e:
                logger.error(f"  ❌ Ошибка {platform}: {e}")
    
    def _get_connected_stores(self, client_id: str) -> Dict:
        """Получает список подключенных магазинов клиента"""
        stores = {}
        creds_dir = self.clients_dir / client_id / 'credentials'
        
        if not creds_dir.exists():
            return stores
        
        for platform in ['wb', 'ozon', 'avito']:
            creds_file = creds_dir / platform / 'credentials.json'
            if creds_file.exists():
                try:
                    with open(creds_file, 'r') as f:
                        data = json.load(f)
                        if data.get('verified', False):
                            stores[platform] = data
                except Exception as e:
                    logger.warning(f"  ⚠️ Ошибка чтения {platform}: {e}")
        
        return stores
    
    async def _check_wildberries(self, client_id: str, creds: Dict):
        """Проверка магазина Wildberries"""
        logger.info(f"  🔵 Wildberries:")
        
        try:
            from modules.wb_api_client import WildberriesAPIClient
            
            api_key = creds.get('stat_api_key')
            if not api_key:
                logger.warning(f"    ⚠️ Нет API ключа")
                return
            
            async with WildberriesAPIClient(api_key) as client:
                # 1. Получаем товары
                products = await client.get_products(limit=100)
                logger.info(f"    📦 Товаров: {len(products)}")
                
                # 2. Получаем статистику (если доступна)
                try:
                    date_from = datetime.now() - timedelta(days=7)
                    stats = await client.get_sales_stats(date_from)
                    logger.info(f"    📊 Статистика получена")
                except Exception as e:
                    logger.debug(f"    ℹ️ Статистика недоступна: {e}")
                
                # 3. Рекламные кампании (если доступны)
                try:
                    campaigns = await client.get_advertising_campaigns()
                    logger.info(f"    📢 Рекламных кампаний: {len(campaigns)}")
                except Exception as e:
                    logger.debug(f"    ℹ️ Реклама недоступна: {e}")
                
                # 4. Сохраняем результаты
                self._save_analysis(client_id, 'wb', {
                    'products_count': len(products),
                    'checked_at': datetime.now().isoformat()
                })
                
        except Exception as e:
            logger.error(f"    ❌ Ошибка: {e}")
    
    async def _check_ozon(self, client_id: str, creds: Dict):
        """Проверка магазина Ozon"""
        logger.info(f"  🔴 Ozon:")
        
        try:
            from modules.ozon_api_client import OzonAPIClient
            
            client_id_api = creds.get('client_id')
            api_key = creds.get('api_key')
            
            if not client_id_api or not api_key:
                logger.warning(f"    ⚠️ Нет данных API")
                return
            
            async with OzonAPIClient(client_id_api, api_key) as client:
                # 1. Получаем товары
                products = await client.get_products(limit=100)
                logger.info(f"    📦 Товаров: {len(products)}")
                
                # 2. Получаем остатки
                try:
                    offer_ids = [p.id for p in products[:50]]
                    stocks = await client.get_stock(offer_ids)
                    logger.info(f"    📊 Остатки получены: {len(stocks)} SKU")
                except Exception as e:
                    logger.debug(f"    ℹ️ Остатки недоступны: {e}")
                
                # 3. Сохраняем результаты
                self._save_analysis(client_id, 'ozon', {
                    'products_count': len(products),
                    'checked_at': datetime.now().isoformat()
                })
                
        except Exception as e:
            logger.error(f"    ❌ Ошибка: {e}")
    
    def _save_analysis(self, client_id: str, platform: str, data: Dict):
        """Сохраняет результаты анализа"""
        analysis_dir = self.clients_dir / client_id / 'autonomous'
        analysis_dir.mkdir(parents=True, exist_ok=True)
        
        analysis_file = analysis_dir / f'{platform}_analysis.json'
        with open(analysis_file, 'w') as f:
            json.dump(data, f, indent=2)


async def main():
    """Точка входа"""
    cycle = AutonomousCycle()
    await cycle.run()


if __name__ == '__main__':
    asyncio.run(main())