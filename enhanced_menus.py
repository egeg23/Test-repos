# ============================================================================
# УЛУЧШЕННОЕ МЕНЮ ДЛЯ PLANE MODE
# ============================================================================

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def get_main_menu(user_data=None):
    """Главное меню - основная панель управления"""
    buttons = [
        [InlineKeyboardButton(text="🛍 Мои магазины", callback_data='stores'),
         InlineKeyboardButton(text="📊 Дашборд", callback_data='dashboard')],
        [InlineKeyboardButton(text="📈 Аналитика", callback_data='analytics'),
         InlineKeyboardButton(text="💰 Цены", callback_data='pricing')],
        [InlineKeyboardButton(text="🤖 Автономия", callback_data='autonomy'),
         InlineKeyboardButton(text="📢 Реклама", callback_data='advertising')],
        [InlineKeyboardButton(text="🔔 Уведомления", callback_data='notifications'),
         InlineKeyboardButton(text="⚙️ Настройки", callback_data='settings')],
        [InlineKeyboardButton(text="🆘 Поддержка", callback_data='support')],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_stores_menu(user_data=None):
    """Меню управления магазинами"""
    buttons = [
        [InlineKeyboardButton(text="🟣 Wildberries", callback_data='wb_menu')],
        [InlineKeyboardButton(text="🔵 Ozon", callback_data='ozon_menu')],
        [InlineKeyboardButton(text="🟡 Яндекс Маркет", callback_data='yandex_menu')],
        [InlineKeyboardButton(text="🏪 Авито", callback_data='avito_menu')],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data='menu')],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_store_detail_menu(platform, is_connected=False):
    """Меню конкретного магазина"""
    platform_names = {
        'wb': '🟣 Wildberries',
        'ozon': '🔵 Ozon',
        'yandex': '🟡 Яндекс Маркет',
        'avito': '🏪 Авито'
    }
    
    buttons = []
    
    if is_connected:
        buttons.extend([
            [InlineKeyboardButton(text="📦 Товары", callback_data=f'{platform}_products'),
             InlineKeyboardButton(text="📊 Статистика", callback_data=f'{platform}_stats')],
            [InlineKeyboardButton(text="💰 Цены", callback_data=f'{platform}_pricing'),
             InlineKeyboardButton(text="📢 Реклама", callback_data=f'{platform}_ads')],
            [InlineKeyboardButton(text="🔄 API ключи", callback_data=f'{platform}_api')],
            [InlineKeyboardButton(text="⚠️ Отключить", callback_data=f'{platform}_disconnect')],
        ])
    else:
        buttons.append([InlineKeyboardButton(text="🔐 Подключить", callback_data=f'{platform}_connect')])
    
    buttons.append([InlineKeyboardButton(text="⬅️ Назад", callback_data='stores')])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_analytics_menu(user_data=None):
    """Меню аналитики"""
    buttons = [
        [InlineKeyboardButton(text="📊 Общий отчёт", callback_data='analytics_report')],
        [InlineKeyboardButton(text="🏆 Конкуренты", callback_data='analytics_competitors')],
        [InlineKeyboardButton(text="📈 Динамика", callback_data='analytics_trends')],
        [InlineKeyboardButton(text="🔍 Mpstats", callback_data='analytics_mpstats')],
        [InlineKeyboardButton(text="📋 История", callback_data='analytics_history')],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data='menu')],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_autonomy_menu(is_active=False):
    """Меню автономного режима"""
    status = "🟢 Активен" if is_active else "🔴 Остановлен"
    toggle_text = "⏸ Остановить" if is_active else "▶️ Запустить"
    toggle_callback = 'autonomy_stop' if is_active else 'autonomy_start'
    
    buttons = [
        [InlineKeyboardButton(text=f"Статус: {status}", callback_data='autonomy_status')],
        [InlineKeyboardButton(text=toggle_text, callback_data=toggle_callback)],
        [InlineKeyboardButton(text="📋 Лог решений", callback_data='autonomy_logs'),
         InlineKeyboardButton(text="🧠 Стратегии", callback_data='autonomy_strategies')],
        [InlineKeyboardButton(text="✅ Успешные", callback_data='autonomy_success'),
         InlineKeyboardButton(text="❌ Неудачи", callback_data='autonomy_failures')],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data='menu')],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_pricing_menu(user_data=None):
    """Меню ценообразования"""
    buttons = [
        [InlineKeyboardButton(text="💰 Маржинальность", callback_data='pricing_margin')],
        [InlineKeyboardButton(text="🎯 Целевой ДРР", callback_data='pricing_drr')],
        [InlineKeyboardButton(text="📊 Рекомендации", callback_data='pricing_recommend')],
        [InlineKeyboardButton(text="⚡ Авто-цены", callback_data='pricing_auto')],
        [InlineKeyboardButton(text="📈 История цен", callback_data='pricing_history')],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data='menu')],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_advertising_menu(user_data=None):
    """Меню рекламы"""
    buttons = [
        [InlineKeyboardButton(text="📊 Кампании", callback_data='ads_campaigns')],
        [InlineKeyboardButton(text="🔍 Кластеры", callback_data='ads_clusters')],
        [InlineKeyboardButton(text="💸 ДРР/CTR", callback_data='ads_metrics')],
        [InlineKeyboardButton(text="📈 Оптимизация", callback_data='ads_optimize')],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data='menu')],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_dashboard_menu(user_data=None):
    """Меню дашборда"""
    buttons = [
        [InlineKeyboardButton(text="🔄 Обновить", callback_data='dashboard_refresh')],
        [InlineKeyboardButton(text="📊 Подробнее", callback_data='analytics')],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data='menu')],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_settings_menu(user_data=None):
    """Меню настроек"""
    buttons = [
        [InlineKeyboardButton(text="🔐 API Ключи", callback_data='settings_api')],
        [InlineKeyboardButton(text="🔔 Уведомления", callback_data='settings_notifications')],
        [InlineKeyboardButton(text="👤 Профиль", callback_data='settings_profile')],
        [InlineKeyboardButton(text="🤖 Автономия", callback_data='settings_autonomy')],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data='menu')],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_api_keys_menu():
    """Меню управления API ключами"""
    buttons = [
        [InlineKeyboardButton(text="🟣 Wildberries", callback_data='api_wb')],
        [InlineKeyboardButton(text="🔵 Ozon", callback_data='api_ozon')],
        [InlineKeyboardButton(text="🟡 Яндекс", callback_data='api_yandex')],
        [InlineKeyboardButton(text="🏪 Авито", callback_data='api_avito')],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data='settings')],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_margin_setup_menu():
    """Меню настройки маржинальности"""
    buttons = [
        [InlineKeyboardButton(text="📦 По артикулам", callback_data='margin_by_articul')],
        [InlineKeyboardButton(text="📁 По категориям", callback_data='margin_by_category')],
        [InlineKeyboardButton(text="🏪 Общая", callback_data='margin_cabinet')],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data='pricing')],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# ============================================================================
# КНОПКИ ДЕЙСТВИЙ
# ============================================================================

def get_confirm_buttons(yes_callback, no_callback, yes_text="✅ Да", no_text="❌ Нет"):
    """Кнопки подтверждения"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=yes_text, callback_data=yes_callback),
         InlineKeyboardButton(text=no_text, callback_data=no_callback)]
    ])


def get_back_button(callback_data='menu'):
    """Кнопка назад"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Назад", callback_data=callback_data)]
    ])


def get_loading_button():
    """Кнопка загрузки"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⏳ Загрузка...", callback_data='loading')]
    ])


# ============================================================================
# СЛОВАРЬ CALLBACK ДАННЫХ
# ============================================================================

CALLBACK_DESCRIPTIONS = {
    # Главное меню
    'menu': 'Главное меню',
    'stores': 'Мои магазины',
    'dashboard': 'Дашборд',
    'analytics': 'Аналитика',
    'autonomy': 'Автономный режим',
    'pricing': 'Цены и ДРР',
    'advertising': 'Реклама',
    'notifications': 'Уведомления',
    'settings': 'Настройки',
    'support': 'Поддержка',
    
    # Магазины
    'wb_menu': 'Wildberries',
    'ozon_menu': 'Ozon',
    'yandex_menu': 'Яндекс Маркет',
    'avito_menu': 'Авито',
    
    # Автономия
    'autonomy_start': 'Запуск автономии',
    'autonomy_stop': 'Остановка автономии',
    'autonomy_status': 'Статус автономии',
    'autonomy_logs': 'Лог решений',
    'autonomy_strategies': 'Стратегии',
    'autonomy_success': 'Успешные кейсы',
    'autonomy_failures': 'Неудачи',
    
    # Цены
    'pricing_margin': 'Настройка маржинальности',
    'pricing_drr': 'Целевой ДРР',
    'pricing_recommend': 'Рекомендации по ценам',
    'pricing_auto': 'Авто-цены',
    'pricing_history': 'История цен',
    
    # Аналитика
    'analytics_report': 'Отчёт',
    'analytics_competitors': 'Конкуренты',
    'analytics_trends': 'Динамика',
    'analytics_mpstats': 'Mpstats',
    'analytics_history': 'История',
}
