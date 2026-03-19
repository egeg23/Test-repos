# modules/notification_service.py - Реальные уведомления на основе API данных
"""
Анализирует реальные данные из WB/Ozon API и генерирует уведомления
при выходе за пороговые значения.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict

logger = logging.getLogger('notification_service')


@dataclass
class Notification:
    """Модель уведомления"""
    user_id: str
    platform: str  # wb, ozon
    type: str      # price_alert, stock_alert, ad_alert, margin_alert
    title: str
    message: str
    priority: str  # low, medium, high
    data: Dict     # Дополнительные данные (артикул, цена, остаток и т.д.)
    created_at: str
    read: bool = False


class NotificationService:
    """
    Сервис уведомлений на основе реальных данных API.
    Анализирует данные и генерирует алерты при выходе за пороги.
    """
    
    def __init__(self, clients_dir: str = "/opt/clients"):
        self.clients_dir = Path(clients_dir)
        self.notifications_file = self.clients_dir / "GLOBAL_AI_LEARNING" / "notifications.json"
        
        # Пороговые значения (можно вынести в настройки пользователя)
        self.thresholds = {
            'stock_min': 10,          # Минимальный остаток
            'margin_min': 0.15,       # Минимальная маржа 15%
            'drr_max': 0.25,          # Макс. ДРР 25%
            'price_change_max': 0.20  # Макс. изменение цены 20%
        }
    
    def analyze_wb_data(self, client_id: str, products: List[Dict], stats: Optional[Dict] = None) -> List[Notification]:
        """
        Анализирует данные WB и генерирует уведомления.
        
        Args:
            client_id: ID пользователя
            products: Список товаров из WB API
            stats: Статистика продаж (опционально)
            
        Returns:
            List[Notification]: Список уведомлений
        """
        notifications = []
        now = datetime.now().isoformat()
        
        for product in products:
            nm_id = product.get('nmId') or product.get('sku')
            name = product.get('name', 'Без названия')
            price = product.get('price', 0)
            stock = product.get('stock', 0)
            
            # 1. Проверка остатков
            if stock < self.thresholds['stock_min']:
                notifications.append(Notification(
                    user_id=client_id,
                    platform='wb',
                    type='stock_alert',
                    title=f'⚠️ Заканчивается товар',
                    message=f'"{name[:30]}..." (Арт. {nm_id}): остаток {stock} шт.',
                    priority='high' if stock < 5 else 'medium',
                    data={'nm_id': nm_id, 'stock': stock, 'threshold': self.thresholds['stock_min']},
                    created_at=now
                ))
            
            # 2. Проверка цены (если есть себестоимость в данных)
            cost_price = product.get('cost_price')
            if cost_price and price > 0:
                margin = (price - cost_price) / price
                if margin < self.thresholds['margin_min']:
                    notifications.append(Notification(
                        user_id=client_id,
                        platform='wb',
                        type='margin_alert',
                        title=f'💸 Низкая маржа',
                        message=f'"{name[:30]}..." (Арт. {nm_id}): маржа {margin:.1%} (ниже {self.thresholds["margin_min"]:.0%})',
                        priority='high',
                        data={'nm_id': nm_id, 'price': price, 'cost': cost_price, 'margin': margin},
                        created_at=now
                    ))
        
        logger.info(f"🔔 Сгенерировано {len(notifications)} уведомлений для WB")
        return notifications
    
    def analyze_ozon_data(self, client_id: str, products: List[Dict], stocks: Optional[Dict] = None) -> List[Notification]:
        """
        Анализирует данные Ozon и генерирует уведомления.
        
        Args:
            client_id: ID пользователя
            products: Список товаров из Ozon API
            stocks: Остатки по SKU (опционально)
            
        Returns:
            List[Notification]: Список уведомлений
        """
        notifications = []
        now = datetime.now().isoformat()
        
        for product in products:
            offer_id = product.get('offer_id') or product.get('id')
            name = product.get('name', 'Без названия')
            price = product.get('price', 0)
            
            # Получаем остаток из stocks если есть
            stock = stocks.get(offer_id, 0) if stocks else product.get('stock', 0)
            
            # 1. Проверка остатков
            if stock < self.thresholds['stock_min']:
                notifications.append(Notification(
                    user_id=client_id,
                    platform='ozon',
                    type='stock_alert',
                    title=f'⚠️ Заканчивается товар',
                    message=f'"{name[:30]}..." (Арт. {offer_id}): остаток {stock} шт.',
                    priority='high' if stock < 5 else 'medium',
                    data={'offer_id': offer_id, 'stock': stock, 'threshold': self.thresholds['stock_min']},
                    created_at=now
                ))
            
            # 2. Проверка маржи
            cost_price = product.get('cost_price')
            if cost_price and price > 0:
                margin = (price - cost_price) / price
                if margin < self.thresholds['margin_min']:
                    notifications.append(Notification(
                        user_id=client_id,
                        platform='ozon',
                        type='margin_alert',
                        title=f'💸 Низкая маржа',
                        message=f'"{name[:30]}..." (Арт. {offer_id}): маржа {margin:.1%}',
                        priority='high',
                        data={'offer_id': offer_id, 'price': price, 'cost': cost_price, 'margin': margin},
                        created_at=now
                    ))
        
        logger.info(f"🔔 Сгенерировано {len(notifications)} уведомлений для Ozon")
        return notifications
    
    def save_notifications(self, notifications: List[Notification]):
        """Сохраняет уведомления в файл"""
        if not notifications:
            return
            
        self.notifications_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Загружаем существующие
        existing = []
        if self.notifications_file.exists():
            try:
                with open(self.notifications_file, 'r') as f:
                    existing = json.load(f)
            except:
                pass
        
        # Добавляем новые
        new_notifications = [asdict(n) for n in notifications]
        existing.extend(new_notifications)
        
        # Сохраняем
        with open(self.notifications_file, 'w') as f:
            json.dump(existing, f, indent=2)
        
        logger.info(f"💾 Сохранено {len(notifications)} уведомлений")
    
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
    
    def mark_as_read(self, notification_ids: List[str] = None, user_id: str = None):
        """Отмечает уведомления как прочитанные"""
        if not self.notifications_file.exists():
            return
        
        try:
            with open(self.notifications_file, 'r') as f:
                notifications = json.load(f)
            
            for n in notifications:
                if notification_ids and n.get('created_at') in notification_ids:
                    n['read'] = True
                elif user_id and n.get('user_id') == user_id and not notification_ids:
                    n['read'] = True
            
            with open(self.notifications_file, 'w') as f:
                json.dump(notifications, f, indent=2)
                
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
    """Форматирует уведомление для Telegram"""
    priority_emoji = {
        'high': '🔴',
        'medium': '🟡',
        'low': '🟢'
    }
    
    platform_emoji = {
        'wb': '🔵 WB',
        'ozon': '🔴 Ozon'
    }
    
    type_emoji = {
        'stock_alert': '📦',
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
    
    return (
        f"{emoji} <b>{notification.get('title')}</b>\n"
        f"{type_icon} {platform} | {created}\n\n"
        f"{notification.get('message')}\n"
    )
