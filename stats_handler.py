# stats_handler.py - Обработчик команды /stats
"""
Аналитика и статистика для пользователя.
/reports для расширенных отчетов.
"""

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from modules.analytics_engine import AnalyticsEngine, StatsFormatter
import logging

logger = logging.getLogger('stats_handler')
router = Router()

analytics = AnalyticsEngine("/opt/clients")


@router.message(Command("stats"))
async def cmd_stats(message: Message):
    """Показывает статистику по магазинам"""
    user_id = str(message.from_user.id)
    
    # Пока заглушка - в реальности определяем подключенные платформы
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔵 Wildberries", callback_data='stats_wb')],
        [InlineKeyboardButton(text="🔴 Ozon", callback_data='stats_ozon')],
        [InlineKeyboardButton(text="📊 Сравнение", callback_data='stats_compare')],
    ])
    
    await message.answer(
        "📊 <b>Аналитика</b>\n\n"
        "Выберите магазин для просмотра статистики:",
        reply_markup=keyboard
    )


@router.callback_query(F.data == 'stats_wb')
async def show_wb_stats(callback: CallbackQuery):
    """Статистика Wildberries"""
    user_id = str(callback.from_user.id)
    
    text = StatsFormatter.format_stats_message(user_id, 'wb', analytics)
    
    # Кнопки для детализации
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📈 Продажи по дням", callback_data='stats_wb_daily')],
        [InlineKeyboardButton(text="🏆 Топ товары", callback_data='stats_wb_top')],
        [InlineKeyboardButton(text="📢 Реклама", callback_data='stats_wb_ads')],
        [InlineKeyboardButton(text="« Назад", callback_data='stats_back')],
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()


@router.callback_query(F.data == 'stats_ozon')
async def show_ozon_stats(callback: CallbackQuery):
    """Статистика Ozon"""
    user_id = str(callback.from_user.id)
    
    text = StatsFormatter.format_stats_message(user_id, 'ozon', analytics)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📈 Продажи по дням", callback_data='stats_ozon_daily')],
        [InlineKeyboardButton(text="🏆 Топ товары", callback_data='stats_ozon_top')],
        [InlineKeyboardButton(text="📢 Реклама", callback_data='stats_ozon_ads')],
        [InlineKeyboardButton(text="« Назад", callback_data='stats_back')],
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()


@router.callback_query(F.data == 'stats_compare')
async def show_comparison(callback: CallbackQuery):
    """Сравнение магазинов"""
    user_id = str(callback.from_user.id)
    
    text = (
        "📊 <b>Сравнение магазинов</b>\n\n"
        "За последние 30 дней:\n\n"
        "┌─────────────┬──────────┬────────┐\n"
        "│    Метрика  │    WB    │  Ozon  │\n"
        "├─────────────┼──────────┼────────┤\n"
        "│ Выручка     │ 350K₽   │ 130K₽  │\n"
        "│ Заказы      │   420    │   160  │\n"
        "│ Средний чек │   833₽   │  812₽  │\n"
        "│ ДРР         │   18%    │   22%  │\n"
        "│ Конверсия   │   3.2%   │  2.8%  │\n"
        "└─────────────┴──────────┴────────┘\n\n"
        "🔵 Wildberries: лидер по выручке\n"
        "🔴 Ozon: хороший потенциал роста"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="« Назад", callback_data='stats_back')],
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()


@router.callback_query(F.data == 'stats_back')
async def stats_back(callback: CallbackQuery):
    """Возврат к выбору магазина"""
    await cmd_stats(callback.message)
    await callback.answer()


@router.callback_query(F.data.endswith('_daily'))
async def show_daily_breakdown(callback: CallbackQuery):
    """Продажи по дням"""
    platform = callback.data.split('_')[1]
    
    trend = analytics.get_sales_trend(str(callback.from_user.id), platform, days=14)
    
    text = (
        f"📈 <b>Продажи по дням ({platform.upper()})</b>\n\n"
        f"{trend['chart']}\n\n"
        f"Всего: {trend['total']} шт.\n"
        f"Тренд: {trend['trend']}"
    )
    
    await callback.message.answer(text)
    await callback.answer()


@router.callback_query(F.data.endswith('_top'))
async def show_top_products(callback: CallbackQuery):
    """Топ товары"""
    platform = callback.data.split('_')[1]
    
    text = (
        f"🏆 <b>Топ товары ({platform.upper()})</b>\n\n"
        f"1. 🥇 Наушники Sony WH-1000XM4\n"
        f"   Продажи: 45 шт. | Выручка: 180K₽\n\n"
        f"2. 🥈 Кофемашина DeLonghi\n"
        f"   Продажи: 28 шт. | Выручка: 168K₽\n\n"
        f"3. 🥉 Робот-пылесос Xiaomi\n"
        f"   Продажи: 22 шт. | Выручка: 110K₽\n\n"
        f"4. Чайник электрический Tefal\n"
        f"   Продажи: 35 шт. | Выручка: 52K₽\n\n"
        f"5. Фен Dyson Supersonic\n"
        f"   Продажи: 12 шт. | Выручка: 96K₽"
    )
    
    await callback.message.answer(text)
    await callback.answer()


@router.callback_query(F.data.endswith('_ads'))
async def show_ads_stats(callback: CallbackQuery):
    """Статистика рекламы"""
    platform = callback.data.split('_')[1]
    
    text = (
        f"📢 <b>Реклама ({platform.upper()})</b>\n\n"
        f"┌─────────────────┬────────┐\n"
        f"│ Показы          │ 45,230 │\n"
        f"│ Клики           │ 1,450  │\n"
        f"│ CTR             │  3.2%  │\n"
        f"│ Заказы из рекл. │   89   │\n"
        f"│ Расходы         │ 22.5K₽ │\n"
        f"│ ДРР             │  18%   │\n"
        f"└─────────────────┴────────┘\n\n"
        f"📊 <b>Кампании:</b>\n"
        f"• Авто-кампания: ДРР 16% ✅\n"
        f"• Поиск: ДРР 21% ⚠️\n"
        f"• Карточка: ДРР 19% ✅"
    )
    
    await callback.message.answer(text)
    await callback.answer()


@router.message(Command("reports"))
async def cmd_reports(message: Message):
    """Расширенные отчеты"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📄 Отчет за неделю", callback_data='report_weekly')],
        [InlineKeyboardButton(text="📄 Отчет за месяц", callback_data='report_monthly')],
        [InlineKeyboardButton(text="📄 Отчет по категориям", callback_data='report_categories')],
        [InlineKeyboardButton(text="📄 Отчет по конкурентам", callback_data='report_competitors')],
    ])
    
    await message.answer(
        "📊 <b>Отчеты</b>\n\n"
        "Выберите тип отчета для генерации:",
        reply_markup=keyboard
    )


def register_handlers(dp):
    """Регистрация обработчиков"""
    dp.include_router(router)
    logger.info("✅ Обработчики аналитики зарегистрированы")
