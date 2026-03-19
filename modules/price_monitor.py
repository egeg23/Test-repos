# modules/price_monitor.py - Автоматический мониторинг цен
"""
Автоматический мониторинг цен конкурентов
Шаг 7 чеклиста (финальный): Автоматический мониторинг цен
"""

import json
import logging
import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Set
import aiofiles

logger = logging.getLogger('price_monitor')


class PriceMonitor:
    """
    📊 Автоматический мониторинг цен
    
    Возможности:
    - Отслеживание цен по списку товаров
    - Оповещения при изменениях
    - История изменений
    - Периодические проверки
    """
    
    def __init__(self, clients_dir: str = "/opt/clients"):
        self.clients_dir = Path(clients_dir)
        self.storage_dir = self.clients_dir / "GLOBAL_AI_LEARNING" / "price_monitor"
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        # Файлы хранения
        self.watchlist_file = self.storage_dir / "watchlist.json"
        self.history_file = self.storage_dir / "price_history.json"
        self.alerts_file = self.storage_dir / "alerts.json"
        
        # Загружаем данные
        self.watchlist = self._load_json(self.watchlist_file, [])
        self.price_history = self._load_json(self.history_file, {})
    
    def _load_json(self, filepath: Path, default) -> dict:
        """Загружает JSON файл"""
        if filepath.exists():
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        return default
    
    async def _save_json(self, filepath: Path, data):
        """Асинхронно сохраняет JSON"""
        async with aiofiles.open(filepath, 'w', encoding='utf-8') as f:
            await f.write(json.dumps(data, ensure_ascii=False, indent=2))
    
    def add_to_watchlist(
        self,
        product_id: str,
        platform: str = "wb",
        user_id: Optional[str] = None,
        alert_threshold_percent: float = 5.0
    ) -> bool:
        """
        Добавляет товар в список отслеживания
        
        Args:
            product_id: nmId или offer_id
            platform: "wb" или "ozon"
            user_id: ID пользователя для уведомлений
            alert_threshold_percent: Порог оповещения (% изменения цены)
        """
        entry = {
            'product_id': product_id,
            'platform': platform,
            'user_id': user_id,
            'alert_threshold_percent': alert_threshold_percent,
            'added_at': datetime.now().isoformat(),
            'last_check': None,
            'active': True
        }
        
        # Проверяем, нет ли уже
        for item in self.watchlist:
            if item['product_id'] == product_id and item['platform'] == platform:
                logger.info(f"⚠️ {product_id} already in watchlist")
                return False
        
        self.watchlist.append(entry)
        
        # Сохраняем
        with open(self.watchlist_file, 'w', encoding='utf-8') as f:
            json.dump(self.watchlist, f, ensure_ascii=False, indent=2)
        
        logger.info(f"✅ Added {product_id} to watchlist")
        return True
    
    def remove_from_watchlist(self, product_id: str, platform: str = "wb") -> bool:
        """Удаляет товар из списка отслеживания"""
        original_len = len(self.watchlist)
        
        self.watchlist = [
            item for item in self.watchlist 
            if not (item['product_id'] == product_id and item['platform'] == platform)
        ]
        
        if len(self.watchlist) < original_len:
            with open(self.watchlist_file, 'w', encoding='utf-8') as f:
                json.dump(self.watchlist, f, ensure_ascii=False, indent=2)
            logger.info(f"✅ Removed {product_id} from watchlist")
            return True
        
        return False
    
    async def run_monitoring_cycle(self):
        """
        Запускает один цикл мониторинга
        Проверяет все товары в watchlist
        """
        logger.info(f"🔄 Starting monitoring cycle for {len(self.watchlist)} products")
        
        alerts = []
        
        for item in self.watchlist:
            if not item.get('active', True):
                continue
            
            try:
                alert = await self._check_product(item)
                if alert:
                    alerts.append(alert)
                
                # Пауза между запросами
                await asyncio.sleep(2)
                
            except Exception as e:
                logger.error(f"❌ Error checking {item['product_id']}: {e}")
                continue
        
        # Сохраняем историю
        await self._save_json(self.history_file, self.price_history)
        
        # Сохраняем алерты
        if alerts:
            existing_alerts = self._load_json(self.alerts_file, [])
            existing_alerts.extend(alerts)
            # Оставляем только последние 100 алертов
            existing_alerts = existing_alerts[-100:]
            await self._save_json(self.alerts_file, existing_alerts)
        
        logger.info(f"✅ Monitoring cycle complete. Alerts: {len(alerts)}")
        return alerts
    
    async def _check_product(self, item: Dict) -> Optional[Dict]:
        """Проверяет один товар"""
        product_id = item['product_id']
        platform = item['platform']
        threshold = item.get('alert_threshold_percent', 5.0)
        
        logger.info(f"🔍 Checking {product_id}")
        
        # Получаем текущие данные
        from modules.mpstats_browser import MpstatsBrowserParser, PLAYWRIGHT_AVAILABLE
        
        if not PLAYWRIGHT_AVAILABLE:
            return None
        
        async with MpstatsBrowserParser(self.clients_dir) as parser:
            # Загружаем сессию
            session_loaded = await parser.load_session("system_mpstats")
            
            if not session_loaded:
                logger.warning("⚠️ No system session")
                return None
            
            # Получаем данные товара
            data = await parser.get_product_data(product_id, platform)
            
            if not data or not data.get('price'):
                logger.warning(f"⚠️ No price data for {product_id}")
                return None
            
            current_price = data['price']
            current_time = datetime.now().isoformat()
            
            # Обновляем last_check
            item['last_check'] = current_time
            
            # Получаем историю этого товара
            history_key = f"{platform}_{product_id}"
            
            if history_key not in self.price_history:
                # Первое измерение
                self.price_history[history_key] = {
                    'product_id': product_id,
                    'platform': platform,
                    'first_seen': current_time,
                    'price_history': [{
                        'timestamp': current_time,
                        'price': current_price
                    }]
                }
                return None
            
            # Получаем предыдущую цену
            history = self.price_history[history_key]['price_history']
            last_entry = history[-1]
            last_price = last_entry['price']
            
            # Добавляем новую точку
            history.append({
                'timestamp': current_time,
                'price': current_price
            })
            
            # Ограничиваем историю (последние 100 точек)
            if len(history) > 100:
                history = history[-100:]
                self.price_history[history_key]['price_history'] = history
            
            # Проверяем изменение
            price_diff = current_price - last_price
            price_diff_percent = (price_diff / last_price * 100) if last_price else 0
            
            # Проверяем порог
            if abs(price_diff_percent) >= threshold:
                # Создаем алерт
                alert = {
                    'type': 'price_change',
                    'product_id': product_id,
                    'platform': platform,
                    'timestamp': current_time,
                    'old_price': last_price,
                    'new_price': current_price,
                    'diff': price_diff,
                    'diff_percent': price_diff_percent,
                    'direction': 'up' if price_diff > 0 else 'down',
                    'user_id': item.get('user_id')
                }
                
                logger.info(f"🚨 Price alert: {product_id} {last_price} -> {current_price}")
                return alert
        
        return None
    
    def get_price_history(self, product_id: str, platform: str = "wb", days: int = 30) -> List[Dict]:
        """Возвращает историю цен товара"""
        history_key = f"{platform}_{product_id}"
        
        if history_key not in self.price_history:
            return []
        
        history = self.price_history[history_key]['price_history']
        
        # Фильтруем по дням
        cutoff = datetime.now() - timedelta(days=days)
        filtered = [
            h for h in history 
            if datetime.fromisoformat(h['timestamp']) > cutoff
        ]
        
        return filtered
    
    def get_statistics(self, product_id: str, platform: str = "wb") -> Dict:
        """Возвращает статистику по ценам товара"""
        history = self.get_price_history(product_id, platform, days=90)
        
        if not history:
            return {}
        
        prices = [h['price'] for h in history]
        
        return {
            'product_id': product_id,
            'platform': platform,
            'data_points': len(prices),
            'min_price': min(prices),
            'max_price': max(prices),
            'avg_price': sum(prices) / len(prices),
            'current_price': prices[-1],
            'first_price': prices[0],
            'total_change': prices[-1] - prices[0],
            'total_change_percent': ((prices[-1] - prices[0]) / prices[0] * 100) if prices[0] else 0,
            'volatility': self._calculate_volatility(prices)
        }
    
    def _calculate_volatility(self, prices: List[float]) -> float:
        """Рассчитывает волатильность цен (стандартное отклонение)"""
        if len(prices) < 2:
            return 0.0
        
        avg = sum(prices) / len(prices)
        variance = sum((p - avg) ** 2 for p in prices) / len(prices)
        return variance ** 0.5
    
    def get_active_alerts(self, user_id: Optional[str] = None, unread_only: bool = True) -> List[Dict]:
        """Возвращает активные алерты"""
        alerts = self._load_json(self.alerts_file, [])
        
        if user_id:
            alerts = [a for a in alerts if a.get('user_id') == user_id]
        
        if unread_only:
            alerts = [a for a in alerts if not a.get('read', False)]
        
        # Сортируем по времени (новые первые)
        alerts.sort(key=lambda x: x['timestamp'], reverse=True)
        
        return alerts
    
    def mark_alerts_read(self, user_id: str):
        """Отмечает алерты как прочитанные"""
        alerts = self._load_json(self.alerts_file, [])
        
        for alert in alerts:
            if alert.get('user_id') == user_id:
                alert['read'] = True
        
        with open(self.alerts_file, 'w', encoding='utf-8') as f:
            json.dump(alerts, f, ensure_ascii=False, indent=2)
    
    def format_alert_message(self, alert: Dict) -> str:
        """Форматирует алерт в сообщение для Telegram"""
        direction_emoji = "🔺" if alert['direction'] == 'up' else "🔻"
        direction_text = "выросла" if alert['direction'] == 'up' else "снизилась"
        
        message = f"{direction_emoji} <b>Изменение цены!</b>\n\n"
        message += f"📦 Товар: <code>{alert['product_id']}</code>\n"
        message += f"🛒 {alert['platform'].upper()}\n\n"
        message += f"Цена {direction_text}:\n"
        message += f"• Было: {alert['old_price']:,.0f} ₽\n"
        message += f"• Стало: {alert['new_price']:,.0f} ₽\n"
        message += f"• Изменение: {alert['diff_percent']:+.1f}%\n\n"
        message += f"🕐 {alert['timestamp'][:16]}"
        
        return message
    
    def get_watchlist_summary(self, user_id: Optional[str] = None) -> Dict:
        """Возвращает сводку по списку отслеживания"""
        items = self.watchlist
        
        if user_id:
            items = [i for i in items if i.get('user_id') == user_id]
        
        active = [i for i in items if i.get('active', True)]
        
        return {
            'total': len(items),
            'active': len(active),
            'by_platform': {
                'wb': len([i for i in items if i['platform'] == 'wb']),
                'ozon': len([i for i in items if i['platform'] == 'ozon'])
            }
        }
