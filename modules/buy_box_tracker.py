# modules/buy_box_tracker.py - Buy Box Tracking Module
"""
Отслеживание статуса Buy Box (корзина) для товаров Wildberries
Хранение истории и анализ трендов
"""

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import asyncio

logger = logging.getLogger('buy_box_tracker')


class BuyBoxTracker:
    """
    📦 Buy Box Tracker - отслеживание корзины WB
    
    Возможности:
    - Проверка текущего статуса Buy Box
    - Хранение истории (30 дней)
    - Расчет процента дней с корзиной
    - Оповещения о потере/возврате корзины
    """
    
    def __init__(self, storage_dir: str = "/opt/clients"):
        self.storage_dir = Path(storage_dir)
        self.bb_dir = self.storage_dir / "GLOBAL_AI_LEARNING" / "buy_box"
        self.bb_dir.mkdir(parents=True, exist_ok=True)
        
        # Файл с текущим статусом
        self.status_file = self.bb_dir / "current_status.json"
        # Файл с историей
        self.history_file = self.bb_dir / "history.jsonl"
    
    def _load_status(self) -> Dict:
        """Загружает текущий статус Buy Box"""
        if self.status_file.exists():
            try:
                with open(self.status_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading BB status: {e}")
        return {}
    
    def _save_status(self, status: Dict):
        """Сохраняет текущий статус"""
        try:
            with open(self.status_file, 'w') as f:
                json.dump(status, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Error saving BB status: {e}")
    
    def _append_history(self, record: Dict):
        """Добавляет запись в историю"""
        try:
            with open(self.history_file, 'a') as f:
                f.write(json.dumps(record, default=str) + '\n')
        except Exception as e:
            logger.error(f"Error appending BB history: {e}")
    
    async def check_buy_box(self, user_id: str, cabinet_id: str, product_id: str, api_key: str) -> Optional[bool]:
        """
        Проверяет статус Buy Box через API
        
        Returns:
            True - есть корзина
            False - нет корзины
            None - ошибка проверки
        """
        try:
            # Используем WB API для проверки
            from .wb_api_client import WBAPIClient
            
            async with WBAPIClient(api_key) as client:
                product_info = await client.get_product_info(product_id)
                
                # Проверяем наличие корзины
                # В WB корзина = товар продается по нашей цене (мы в выкупе)
                has_bb = product_info.get('has_buy_box', False)
                
                # Логируем результат
                record = {
                    'timestamp': datetime.now().isoformat(),
                    'user_id': user_id,
                    'cabinet_id': cabinet_id,
                    'product_id': product_id,
                    'has_buy_box': has_bb,
                    'price': product_info.get('price', 0),
                    'stock': product_info.get('stock', 0)
                }
                
                self._append_history(record)
                
                # Обновляем текущий статус
                status = self._load_status()
                key = f"{user_id}:{cabinet_id}:{product_id}"
                
                # Проверяем изменение
                old_status = status.get(key, {}).get('has_buy_box')
                if old_status is not None and old_status != has_bb:
                    if has_bb:
                        logger.info(f"🎉 Buy Box ВОЗВРАЩЁН: {product_id}")
                    else:
                        logger.warning(f"⚠️ Buy Box ПОТЕРЯН: {product_id}")
                
                status[key] = {
                    'has_buy_box': has_bb,
                    'last_check': datetime.now().isoformat(),
                    'price': product_info.get('price', 0)
                }
                
                self._save_status(status)
                
                return has_bb
                
        except Exception as e:
            logger.error(f"Error checking Buy Box for {product_id}: {e}")
            return None
    
    def get_buy_box_status(self, user_id: str, cabinet_id: str, product_id: str) -> Optional[Dict]:
        """
        Получает текущий статус Buy Box из кэша
        
        Returns:
            Dict с has_buy_box, last_check, price
            или None если нет данных
        """
        status = self._load_status()
        key = f"{user_id}:{cabinet_id}:{product_id}"
        return status.get(key)
    
    def get_buy_box_history(
        self,
        user_id: str,
        cabinet_id: str,
        product_id: str,
        days: int = 30
    ) -> List[Dict]:
        """
        Получает историю Buy Box за указанный период
        
        Returns:
            Список записей с timestamp и has_buy_box
        """
        history = []
        cutoff_date = datetime.now() - timedelta(days=days)
        
        if not self.history_file.exists():
            return history
        
        try:
            with open(self.history_file, 'r') as f:
                for line in f:
                    try:
                        record = json.loads(line.strip())
                        if (record.get('user_id') == user_id and
                            record.get('cabinet_id') == cabinet_id and
                            record.get('product_id') == product_id):
                            
                            record_date = datetime.fromisoformat(record['timestamp'])
                            if record_date >= cutoff_date:
                                history.append(record)
                    except json.JSONDecodeError:
                        continue
        except Exception as e:
            logger.error(f"Error reading BB history: {e}")
        
        return history
    
    def calculate_buy_box_stats(
        self,
        user_id: str,
        cabinet_id: str,
        product_id: str,
        days: int = 30
    ) -> Dict:
        """
        Рассчитывает статистику Buy Box
        
        Returns:
            {
                'days_with_bb': int,
                'days_without_bb': int,
                'days_total': int,
                'bb_percentage': float,
                'trend': 'improving' | 'declining' | 'stable'
            }
        """
        history = self.get_buy_box_history(user_id, cabinet_id, product_id, days)
        
        if not history:
            return {
                'days_with_bb': 0,
                'days_without_bb': 0,
                'days_total': 0,
                'bb_percentage': 0.0,
                'trend': 'unknown'
            }
        
        # Группируем по дням (берём последнее значение дня)
        daily_status = {}
        for record in history:
            date = record['timestamp'][:10]  # YYYY-MM-DD
            daily_status[date] = record['has_buy_box']
        
        days_with = sum(1 for v in daily_status.values() if v)
        days_total = len(daily_status)
        days_without = days_total - days_with
        
        percentage = (days_with / days_total * 100) if days_total > 0 else 0
        
        # Определяем тренд
        trend = 'stable'
        if days_total >= 7:
            dates = sorted(daily_status.keys())
            first_week = sum(1 for d in dates[:7] if daily_status[d]) / min(7, len(dates))
            last_week = sum(1 for d in dates[-7:] if daily_status[d]) / min(7, len(dates))
            
            if last_week > first_week * 1.1:
                trend = 'improving'
            elif last_week < first_week * 0.9:
                trend = 'declining'
        
        return {
            'days_with_bb': days_with,
            'days_without_bb': days_without,
            'days_total': days_total,
            'bb_percentage': round(percentage, 1),
            'trend': trend
        }
    
    async def batch_check_buy_box(
        self,
        user_id: str,
        cabinet_id: str,
        product_ids: List[str],
        api_key: str
    ) -> Dict[str, bool]:
        """
        Проверяет Buy Box для нескольких товаров
        
        Returns:
            Словарь {product_id: has_buy_box}
        """
        results = {}
        
        for product_id in product_ids:
            try:
                has_bb = await self.check_buy_box(user_id, cabinet_id, product_id, api_key)
                if has_bb is not None:
                    results[product_id] = has_bb
                await asyncio.sleep(0.5)  # Rate limiting
            except Exception as e:
                logger.error(f"Error in batch check for {product_id}: {e}")
                continue
        
        return results


# Глобальный экземпляр
buy_box_tracker = BuyBoxTracker()


if __name__ == "__main__":
    # Тестирование
    import sys
    
    if len(sys.argv) < 4:
        print("Usage: python buy_box_tracker.py <user_id> <cabinet_id> <product_id>")
        sys.exit(1)
    
    async def test():
        tracker = BuyBoxTracker()
        stats = tracker.calculate_buy_box_stats(sys.argv[1], sys.argv[2], sys.argv[3])
        print(f"Buy Box Stats: {stats}")
    
    asyncio.run(test())
