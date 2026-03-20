# subscription_manager.py - Управление подписками и тарифами
"""
Система тарифов и подписок для Seller AI Bot.
"""

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict

logger = logging.getLogger('subscription_manager')


# ============================================================================
# ТАРИФЫ
# ============================================================================

PLANS = {
    'free': {
        'name': 'Free',
        'price': 0,
        'max_stores': 0,
        'features': [
            'Ознакомительный режим',
            'Без магазинов',
            'Демо данных'
        ],
        'limits': {
            'max_stores': 0,
            'ai_recommendations': False,
            'autonomy': False,
            'priority_support': False
        }
    },
    'basic': {
        'name': 'Базовый',
        'price': 14900,
        'max_stores': 1,
        'features': [
            '1 магазин',
            'AI рекомендации',
            'Ежедневные отчёты',
            'Email поддержка'
        ],
        'limits': {
            'max_stores': 1,
            'ai_recommendations': True,
            'autonomy': False,
            'priority_support': False
        }
    },
    'pro': {
        'name': 'Про',
        'price': 39900,
        'max_stores': 5,
        'features': [
            '5 магазинов',
            'Полная автономия',
            'Fuck Mode',
            'Приоритетная поддержка'
        ],
        'limits': {
            'max_stores': 5,
            'ai_recommendations': True,
            'autonomy': True,
            'priority_support': True
        }
    },
    'enterprise': {
        'name': 'Мега',
        'price': 94500,
        'max_stores': 12,
        'features': [
            '12 магазинов',
            'Все функции Про',
            'Персональный менеджер',
            'API доступ'
        ],
        'limits': {
            'max_stores': 12,
            'ai_recommendations': True,
            'autonomy': True,
            'priority_support': True,
            'api_access': True
        }
    }
}


@dataclass
class Subscription:
    """Модель подписки"""
    user_id: str
    plan: str  # free, basic, pro, enterprise
    activated_at: str
    expires_at: str
    price: int
    status: str  # active, expired, cancelled, trial
    granted_by: Optional[str] = None  # Кто выдал (для админ-выдачи)
    payment_id: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Subscription':
        return cls(**data)


class SubscriptionManager:
    """Менеджер подписок"""
    
    def __init__(self, user_id: str = None):
        self.user_id = user_id
        self.clients_dir = Path("/opt/clients")
    
    def _get_subscription_file(self, user_id: str = None) -> Path:
        """Путь к файлу подписки"""
        uid = user_id or self.user_id
        return self.clients_dir / uid / "subscription.json"
    
    def get_subscription(self, user_id: str = None) -> Optional[Subscription]:
        """Получает подписку пользователя"""
        sub_file = self._get_subscription_file(user_id)
        
        if not sub_file.exists():
            # Создаём бесплатную подписку по умолчанию
            return self._create_default_subscription(user_id)
        
        try:
            with open(sub_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return Subscription.from_dict(data)
        except Exception as e:
            logger.error(f"Error loading subscription: {e}")
            return self._create_default_subscription(user_id)
    
    def _create_default_subscription(self, user_id: str = None) -> Subscription:
        """Создаёт подписку Free по умолчанию"""
        now = datetime.now()
        sub = Subscription(
            user_id=user_id or self.user_id,
            plan='free',
            activated_at=now.isoformat(),
            expires_at=(now + timedelta(days=365*10)).isoformat(),  # Бессрочно
            price=0,
            status='active'
        )
        self.save_subscription(sub)
        return sub
    
    def save_subscription(self, subscription: Subscription) -> bool:
        """Сохраняет подписку"""
        try:
            sub_file = self._get_subscription_file(subscription.user_id)
            sub_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(sub_file, 'w', encoding='utf-8') as f:
                json.dump(subscription.to_dict(), f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            logger.error(f"Error saving subscription: {e}")
            return False
    
    def grant_subscription(self, user_id: str, plan: str, months: int, 
                          granted_by: str = None) -> bool:
        """Выдаёт подписку пользователю (админ-функция)"""
        if plan not in PLANS:
            logger.error(f"Unknown plan: {plan}")
            return False
        
        now = datetime.now()
        plan_info = PLANS[plan]
        
        sub = Subscription(
            user_id=user_id,
            plan=plan,
            activated_at=now.isoformat(),
            expires_at=(now + timedelta(days=30*months)).isoformat(),
            price=plan_info['price'] * months,
            status='active',
            granted_by=granted_by
        )
        
        return self.save_subscription(sub)
    
    def is_active(self, user_id: str = None) -> bool:
        """Проверяет активна ли подписка"""
        sub = self.get_subscription(user_id)
        if not sub:
            return False
        
        if sub.status != 'active':
            return False
        
        expires = datetime.fromisoformat(sub.expires_at)
        return datetime.now() < expires
    
    def get_plan_info(self, plan: str = None, user_id: str = None) -> Dict:
        """Получает информацию о тарифе"""
        if plan:
            return PLANS.get(plan, PLANS['free'])
        
        sub = self.get_subscription(user_id)
        return PLANS.get(sub.plan, PLANS['free'])
    
    def can_add_store(self, user_id: str = None) -> bool:
        """Проверяет можно ли добавить ещё магазин"""
        sub = self.get_subscription(user_id)
        plan_info = PLANS.get(sub.plan, PLANS['free'])
        
        # Считаем текущие магазины
        uid = user_id or self.user_id
        stores_count = 0
        user_dir = self.clients_dir / uid
        
        for platform in ['wb', 'ozon', 'avito']:
            creds_file = user_dir / 'credentials' / platform / 'credentials.json'
            if creds_file.exists():
                stores_count += 1
        
        return stores_count < plan_info['max_stores']


# ============================================================================
# АДМИН-СТАТИСТИКА
# ============================================================================

class AdminStats:
    """Статистика для админ-панели"""
    
    def __init__(self):
        self.clients_dir = Path("/opt/clients")
        self.sub_manager = SubscriptionManager()
    
    def get_full_stats(self) -> Dict:
        """Полная статистика по всем пользователям"""
        users = self._get_all_users()
        
        stats = {
            'total_users': len(users),
            'active_subscriptions': 0,
            'expired_subscriptions': 0,
            'total_revenue': 0,
            'stores': {
                'wb': 0,
                'ozon': 0,
                'avito': 0,
                'total': 0
            },
            'plans': {
                'free': 0,
                'basic': 0,
                'pro': 0,
                'enterprise': 0
            }
        }
        
        for user_id in users:
            # Подписка
            sub = self.sub_manager.get_subscription(user_id)
            if sub:
                stats['plans'][sub.plan] = stats['plans'].get(sub.plan, 0) + 1
                
                # Проверяем активность
                expires = datetime.fromisoformat(sub.expires_at)
                if datetime.now() < expires and sub.status == 'active':
                    stats['active_subscriptions'] += 1
                else:
                    stats['expired_subscriptions'] += 1
                
                # Доход (только платные)
                if sub.price > 0:
                    stats['total_revenue'] += sub.price
            
            # Магазины
            user_stores = self._count_user_stores(user_id)
            stats['stores']['wb'] += user_stores['wb']
            stats['stores']['ozon'] += user_stores['ozon']
            stats['stores']['avito'] += user_stores['avito']
            stats['stores']['total'] += user_stores['total']
        
        return stats
    
    def _get_all_users(self) -> List[str]:
        """Получает список всех пользователей"""
        users = []
        
        if not self.clients_dir.exists():
            return users
        
        for item in self.clients_dir.iterdir():
            if item.is_dir() and not item.name.startswith('.'):
                # Проверяем что это папка пользователя
                if (item / 'credentials').exists() or (item / 'subscription.json').exists():
                    users.append(item.name)
        
        return users
    
    def _count_user_stores(self, user_id: str) -> Dict:
        """Считает магазины пользователя"""
        stores = {'wb': 0, 'ozon': 0, 'avito': 0, 'total': 0}
        user_dir = self.clients_dir / user_id
        
        for platform in ['wb', 'ozon', 'avito']:
            creds_file = user_dir / 'credentials' / platform / 'credentials.json'
            if creds_file.exists():
                try:
                    with open(creds_file, 'r') as f:
                        data = json.load(f)
                    if data.get('verified', False):
                        stores[platform] += 1
                        stores['total'] += 1
                except:
                    pass
        
        return stores
    
    def get_user_details(self, user_id: str) -> Dict:
        """Детальная информация о пользователе"""
        sub = self.sub_manager.get_subscription(user_id)
        stores = self._count_user_stores(user_id)
        
        return {
            'user_id': user_id,
            'subscription': sub.to_dict() if sub else None,
            'stores': stores,
            'plan_info': self.sub_manager.get_plan_info(user_id=user_id)
        }


# ============================================================================
# ГЛОБАЛЬНЫЕ ФУНКЦИИ
# ============================================================================

def get_plan_keyboard() -> List[List[Dict]]:
    """Клавиатура выбора тарифа"""
    from aiogram.types import InlineKeyboardButton
    
    buttons = []
    for plan_id, plan_info in PLANS.items():
        if plan_id == 'free':
            continue  # Пропускаем бесплатный для выдачи
        
        text = f"{plan_info['name']} — {plan_info['price']}₽/мес"
        buttons.append([InlineKeyboardButton(text=text, callback_data=f"grant_plan_{plan_id}")])
    
    return buttons


def get_duration_keyboard() -> List[List[Dict]]:
    """Клавиатура выбора срока"""
    from aiogram.types import InlineKeyboardButton
    
    return [
        [InlineKeyboardButton(text="1 месяц", callback_data="grant_duration_1")],
        [InlineKeyboardButton(text="2 месяца", callback_data="grant_duration_2")],
        [InlineKeyboardButton(text="3 месяца", callback_data="grant_duration_3")],
        [InlineKeyboardButton(text="6 месяцев", callback_data="grant_duration_6")],
    ]
