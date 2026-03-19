# modules/notification_service.py - Реальные уведомления на основе API данных
"""
Анализирует реальные данные из WB/Ozon API с учетом истории продаж.
Генерирует уведомления когда запасов осталось на 15-20 дней (2 дня подряд).
"""

import json
import html
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from uuid import uuid4

logger = logging.getLogger('notification_service')


@dataclass
class Notification:
    """Модель уведомления"""
    id: str                      # UUID для уникальности
    user_id: str
    platform: str               # wb, ozon
    type: str                   # supply_needed, margin_alert, price_alert, ad_alert
    title: str
    message: str
    priority: str               # low, medium, high, critical
    data: Dict                  # Дополнительные данные
    created_at: str
    read: bool = False


class NotificationService:
    """
    Сервис уведомлений на основе реальных данных API + истории продаж.
    """
    
    def __init__(self, clients_dir: str = "/opt/clients"):
        self.clients_dir = Path(clients_dir)
        self.notifications_file = self.clients_dir / "GLOBAL_AI_LEARNING" / "notifications.json"
        
        # Пороговые значения (по умолчанию 17 дней, пользователь может изменить)
        self.default_threshold_days = 17
        self.min_threshold = 10
        self.max_threshold = 30
    
    def get_user_threshold(self, client_id: str) -> int:
        """Получает порог пользователя (или дефолт)"""
        settings_file = self.clients_dir / client_id / "settings" / "autonomy.json"
        if settings_file.exists():
            try:
                with open(settings_file, 'r') as f:
                    settings = json.load(f)
                    threshold = settings.get('stock_days_threshold', self.default_threshold_days)
                    return max(self.min_threshold, min(self.max_threshold, threshold))
            except:
                pass
        return self.default_threshold_days
    
    def analyze_inventory_forecast(
        self, 
        client_id: str, 
        platform: str, 
        products: List[Dict],
        sales_history_manager
    ) -> List[Notification]:
        """
        Анализирует прогноз запасов и генерирует уведомления.
        
        Args:
            client_id: ID пользователя
            platform: wb или ozon
            products: Список товаров с текущими остатками
            sales_history_manager: SalesHistoryManager для расчета средней скорости
            
        Returns:
            List[Notification]: Список уведомлений о необходимости поставки
        """
        notifications = []
        now = datetime.now().isoformat()
        today = datetime.now().strftime('%Y-%m-%d')
        threshold_days = self.get_user_threshold(client_id)
        
        logger.info(f"📊 Анализ {platform}: порог {threshold_days} дней, товаров {len(products)}")
        
        for product in products:
            product_id = product.get('nmId') or product.get('offer_id') or product.get('id')
            name = product.get('name', 'Без названия')
            current_stock = product.get('stock', 0)
            
            if not product_id:
                continue
            
            # Получаем среднюю скорость продаж (A)
            avg_daily_sales = sales_history_manager.calculate_avg_daily_sales(
                client_id, platform, product_id, days=7
            )
            
            if avg_daily_sales <= 0:
                # Товар не продается - пропускаем
                continue
            
            # Рассчитываем сколько дней хватит запасов (C = B / A)
            stock_days = sales_history_manager.calculate_stock_days(current_stock, avg_daily_sales)
            
            # Проверяем 2 дня подряд
            needs_alert = sales_history_manager.check_two_day_alert(
                client_id, platform, product_id, stock_days, threshold_days
            )
            
            if needs_alert:
                # Рассчитываем сколько заказать
                supply_qty = sales_history_manager.calculate_supply_needed(
                    current_stock, avg_daily_sales, target_days=threshold_days
                )
                
                # Определяем приоритет
                if stock_days < 5:
                    priority = 'critical'
                    title = '🔴 КРИТИЧНО: Срочная поставка!'
                elif stock_days < 10:
                    priority = 'high'
                    title = '🟠 Важно: Нужна поставка'
                else:
                    priority = 'medium'
                    title = '🟡 Плановая поставка'
                
                notification = Notification(
                    id=str(uuid4()),
                    user_id=client_id,
                    platform=platform,
                    type='supply_needed',
                    title=title,
                    message=self._format_supply_message(name, stock_days, current_stock, supply_qty, threshold_days),
                    priority=priority,
                    data={
                        'product_id': product_id,
                        'product_name': name,
                        'current_stock': current_stock,
                        'avg_daily_sales': round(avg_daily_sales, 2),
                        'stock_days': round(stock_days, 1),
                        'threshold_days': threshold_days,
                        'supply_qty': supply_qty,
                        'alert_date': today
                    },
                    created_at=now
                )
                notifications.append(notification)
                logger.info(f"🚨 Создано уведомление для {product_id}: {stock_days:.1f} дней")
        
        logger.info(f"✅ Сгенерировано {len(notifications)} уведомлений")
        return notifications
    
    def _format_supply_message(self, name: str, stock_days: float, current_stock: int, supply_qty: int, threshold: int) -> str:
        """Форматирует сообщение о поставке"""
        return (
            f'Товар: "{name[:40]}..."\n'
            f'📦 Текущий запас: {current_stock} шт.\n'
            f'📊 Хватит на: {stock_days:.1f} дней\n'
            f'🎯 Рекомендуем заказать: {supply_qty} шт.\n'
            f'(для запаса на {threshold} дней)'
        )
    
    def save_notifications(self, notifications: List[Notification]):
        """Сохраняет уведомления в файл с блокировкой"""
        if not notifications:
            return
        
        self.notifications_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Используем файл-блокировку для конкурентного доступа
        lock_file = self.notifications_file.with_suffix('.lock')
        
        try:
            # Простая блокировка через создание файла
            import time
            while lock_file.exists():
                time.sleep(0.1)
            
            lock_file.touch()
            
            try:
                # Загружаем существующие
                existing = []
                if self.notifications_file.exists():
                    with open(self.notifications_file, 'r') as f:
                        existing = json.load(f)
                
                # Добавляем новые
                new_notifications = [asdict(n) for n in notifications]
                existing.extend(new_notifications)
                
                # Атомарная запись
                temp_file = self.notifications_file.with_suffix('.tmp')
                with open(temp_file, 'w') as f:
                    json.dump(existing, f, indent=2)
                temp_file.replace(self.notifications_file)
                
                logger.info(f"💾 Сохранено {len(notifications)} уведомлений")
                
            finally:
                lock_file.unlink(missing_ok=True)
                
        except Exception as e:
            logger.error(f"❌ Ошибка сохранения уведомлений: {e}")
    
    def get_user_notifications(self, user_id: str, unread_only: bool = False, limit: int = 50) -> List[Dict]:
        """Получает уведомления пользователя"""
        if not self.notifications_file.exists():
            return []
        
        try:
            with open(self.notifications_file, 'r') as f:
                all_notifications = json.load(f)
            
            user_notifications = [
                n for n in all_notifications 
                if n.get('user_id') == user_id
            ]
            
            if unread_only:
                user_notifications = [n for n in user_notifications if not n.get('read', False)]
            
            # Сортируем по дате (новые сначала) и ограничиваем
            sorted_notifications = sorted(
                user_notifications, 
                key=lambda x: x.get('created_at', ''), 
                reverse=True
            )
            
            return sorted_notifications[:limit]
            
        except Exception as e:
            logger.error(f"❌ Ошибка чтения уведомлений: {e}")
            return []
    
    def get_unread_count(self, user_id: str) -> int:
        """Возвращает количество непрочитанных уведомлений"""
        return len(self.get_user_notifications(user_id, unread_only=True))
    
    def mark_as_read(self, notification_id: str = None, user_id: str = None):
        """Отмечает уведомление как прочитанное"""
        if not self.notifications_file.exists():
            return
        
        lock_file = self.notifications_file.with_suffix('.lock')
        
        try:
            while lock_file.exists():
                import time
                time.sleep(0.1)
            lock_file.touch()
            
            try:
                with open(self.notifications_file, 'r') as f:
                    notifications = json.load(f)
                
                for n in notifications:
                    if notification_id and n.get('id') == notification_id:
                        n['read'] = True
                    elif user_id and not notification_id and n.get('user_id') == user_id:
                        n['read'] = True
                
                temp_file = self.notifications_file.with_suffix('.tmp')
                with open(temp_file, 'w') as f:
                    json.dump(notifications, f, indent=2)
                temp_file.replace(self.notifications_file)
                
            finally:
                lock_file.unlink(missing_ok=True)
                
        except Exception as e:
            logger.error(f"❌ Ошибка обновления уведомлений: {e}")
    
    def clear_old_notifications(self, days: int = 7):
        """Очищает старые уведомления"""
        if not self.notifications_file.exists():
            return
        
        try:
            with open(self.notifications_file, 'r') as f:
                notifications = json.load(f)
            
            cutoff = datetime.now() - __import__('datetime').timedelta(days=days)
            
            filtered = [
                n for n in notifications 
                if datetime.fromisoformat(n.get('created_at', '2000-01-01')) > cutoff
            ]
            
            with open(self.notifications_file, 'w') as f:
                json.dump(filtered, f, indent=2)
            
            logger.info(f"🧹 Очищено {len(notifications) - len(filtered)} старых уведомлений")
            
        except Exception as e:
            logger.error(f"❌ Ошибка очистки: {e}")


def format_notification_message(notification: Dict) -> str:
    """Форматирует уведомление для Telegram с HTML escaping"""
    priority_emoji = {
        'critical': '🔴',
        'high': '🟠',
        'medium': '🟡',
        'low': '🟢'
    }
    
    platform_emoji = {
        'wb': '🔵 WB',
        'ozon': '🔴 Ozon'
    }
    
    type_emoji = {
        'supply_needed': '📦',
        'margin_alert': '💸',
        'price_alert': '💰',
        'ad_alert': '📢'
    }
    
    emoji = priority_emoji.get(notification.get('priority'), '⚪')
    platform = platform_emoji.get(notification.get('platform'), '📦')
    type_icon = type_emoji.get(notification.get('type'), '📋')
    
    created = notification.get('created_at', '')
    if created:
        created = created[:16].replace('T', ' ')
    
    # HTML escaping для безопасности
    title = html.escape(notification.get('title', 'Без названия'))
    message = html.escape(notification.get('message', ''))
    
    return (
        f"{emoji} <b>{title}</b>\n"
        f"{type_icon} {platform} | {created}\n\n"
        f"{message}"
    )
