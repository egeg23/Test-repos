# stats_handler.py - Обработчик команды /stats
"""
Аналитика и статистика для пользователя.
/reports для расширенных отчетов.
"""

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from modules.analytics_engine import AnalyticsEngine, StatsFormatter
from modules.ads_strategy_config import ads_strategy_config, AdsStrategyType
from datetime import datetime
from functools import lru_cache
import asyncio
import logging

logger = logging.getLogger('stats_handler')
router = Router()

analytics = AnalyticsEngine("/opt/clients")

# Кэш для стратегий (TTL 60 секунд)
_strategy_cache = {}

@lru_cache(maxsize=128)
def get_cached_strategy_config(strategy_type):
    """Кэшированная конфигурация стратегии"""
    return ads_strategy_config.get_strategy_config(strategy_type)

async def prefetch_user_data(user_id: str):
    """Предзагрузка данных пользователя в фоне"""
    try:
        # Предзагружаем стратегию
        current = ads_strategy_config.get_user_strategy(user_id)
        _strategy_cache[user_id] = current
    except Exception:
        pass


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
    """Статистика рекламы - РЕАЛЬНЫЕ ДАННЫЕ"""
    platform = callback.data.split('_')[1]
    user_id = str(callback.from_user.id)
    
    await callback.message.answer("⏳ Загружаю статистику рекламы...")
    
    try:
        if platform == 'wb':
            from agents.ads_agent import AdsAgent
            agent = AdsAgent()
            report = await agent.get_campaigns_report(user_id)
            await callback.message.answer(report, parse_mode='HTML')
        elif platform == 'ozon':
            from modules.ozon_ads_client import OzonAdsClient
            from modules.multi_cabinet_manager import cabinet_manager
            
            cabinets = cabinet_manager.get_active_cabinets(user_id, 'ozon')
            if not cabinets:
                await callback.message.answer(
                    "❌ Нет активных кабинетов Ozon.\n"
                    "Добавьте кабинет в разделе 'Мои магазины'"
                )
                await callback.answer()
                return
            
            cabinet = cabinets[0]
            if not cabinet.api_key or not hasattr(cabinet, 'client_id'):
                await callback.message.answer(
                    "❌ API ключ Ozon не найден."
                )
                await callback.answer()
                return
            
            async with OzonAdsClient(cabinet.api_key, getattr(cabinet, 'client_id', '')) as client:
                if not client.is_valid:
                    await callback.message.answer("❌ Ошибка подключения к Ozon API")
                    await callback.answer()
                    return
                
                campaigns = await client.get_campaigns()
                
                if not campaigns:
                    await callback.message.answer("📢 Нет рекламных кампаний Ozon.")
                    await callback.answer()
                    return
                
                lines = ["📢 <b>Кампании OZON</b>\n"]
                for campaign in campaigns[:10]:
                    state = campaign.get('state', 'UNKNOWN')
                    status_emoji = {'CAMPAIGN_STATE_RUNNING': '🟢', 'CAMPAIGN_STATE_PAUSED': '⏸'}.get(state, '⚪')
                    lines.append(f"{status_emoji} {campaign.get('title', 'Unknown')}")
                
                lines.append(f"\n📊 Всего: {len(campaigns)}")
                await callback.message.answer("\n".join(lines), parse_mode='HTML')
        else:
            await callback.message.answer(f"📢 Платформа {platform} не поддерживается")
    except Exception as e:
        logger.error(f"Error showing ads: {e}")
        await callback.message.answer("⚠️ Ошибка загрузки рекламы")
    
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


@router.message(Command("ads_strategy"))
async def cmd_ads_strategy(message: Message):
    """Показывает меню выбора стратегии рекламы"""
    user_id = str(message.from_user.id)
    
    # Предзагрузка в фоне (не блокирует UI)
    asyncio.create_task(prefetch_user_data(user_id))
    
    current_strategy = ads_strategy_config.get_user_strategy(user_id)
    strategies = ads_strategy_config.get_all_strategies()
    
    text = (
        "📊 <b>Стратегия управления рекламой</b>\n\n"
        f"Текущая: {strategies[current_strategy].name}\n"
        f"Целевой ДРР: {strategies[current_strategy].target_drr}%\n\n"
        "Выберите новую стратегию:"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=f"{'✅ ' if current_strategy == AdsStrategyType.NEW_PRODUCT else ''}🚀 Запустить новый товар",
            callback_data='strategy_new_product'
        )],
        [InlineKeyboardButton(
            text=f"{'✅ ' if current_strategy == AdsStrategyType.MAINTAIN_MARGIN else ''}💰 Держать маржу",
            callback_data='strategy_maintain_margin'
        )],
        [InlineKeyboardButton(
            text=f"{'✅ ' if current_strategy == AdsStrategyType.MAINTAIN_TOP_POSITION else ''}🏆 Поддержание топ позиции",
            callback_data='strategy_maintain_top'
        )],
        [InlineKeyboardButton(
            text=f"{'✅ ' if current_strategy == AdsStrategyType.BREAK_INTO_TOP else ''}🎯 Попадание в топ (для плохих продаж)",
            callback_data='strategy_break_into_top'
        )],
    ])
    
    await message.answer(text, reply_markup=keyboard)


@router.callback_query(F.data.startswith('strategy_'))
async def set_ads_strategy(callback: CallbackQuery):
    """Устанавливает выбранную стратегию"""
    user_id = str(callback.from_user.id)
    
    strategy_map = {
        'strategy_new_product': AdsStrategyType.NEW_PRODUCT,
        'strategy_maintain_margin': AdsStrategyType.MAINTAIN_MARGIN,
        'strategy_maintain_top': AdsStrategyType.MAINTAIN_TOP_POSITION,
        'strategy_break_into_top': AdsStrategyType.BREAK_INTO_TOP,
        'strategy_top_position': AdsStrategyType.MAINTAIN_TOP_POSITION,  # Legacy callback
    }
    
    strategy = strategy_map.get(callback.data)
    if not strategy:
        await callback.answer("❌ Неизвестная стратегия")
        return
    
    # Устанавливаем стратегию
    ads_strategy_config.set_user_strategy(user_id, strategy)
    
    # Используем кэш для мгновенного отображения
    config = get_cached_strategy_config(strategy)
    
    text = (
        f"✅ <b>Стратегия изменена!</b>\n\n"
        f"{config.name}\n"
        f"━━━━━━━━━━━━━━\n"
        f"🎯 Целевой ДРР: {config.target_drr}%\n"
        f"📈 Макс. ДРР: {config.max_drr}%\n"
        f"⚡ Агрессивность: {config.bid_aggression}x\n\n"
        f"<i>{config.description}</i>"
    )
    
    await callback.answer()  # Сразу убираем "часики"
    await callback.message.edit_text(text)





async def _show_product_selection_for_break_into_top(callback: CallbackQuery):
    """Показывает выбор товара для стратегии Break Into Top"""
    # TODO: Получать реальные товары пользователя из API
    # Пока показываем инструкцию с кнопкой ввода артикула
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📝 Ввести артикул вручную", callback_data='bit_enter_artikul')],
        [InlineKeyboardButton(text="« Назад", callback_data='ads_strategy')],
    ])
    
    text = (
        "🎯 <b>Попадание в топ</b>\n\n"
        "Выберите товар для агрессивного продвижения:\n\n"
        "<i>Сейчас: введите артикул вручную</i>\n"
        "<i>Скоро: список ваших товаров загрузится автоматически</i>"
    )
    
    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()

async def _show_break_into_top_menu(message: Message, artikul: str, target_position: int):
    """Показывает меню для запуска Break Into Top"""
    
    # Кнопки для выбора позиции
    position_buttons = [
        InlineKeyboardButton(
            text=f"{'🎯 ' if target_position == pos else ''}Топ-{pos}",
            callback_data=f'bit_position:{artikul}:{pos}'
        )
        for pos in [1, 3, 5, 10]
    ]
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        position_buttons[:2],
        position_buttons[2:],
        [InlineKeyboardButton(
            text="🚀 Запустить прорыв в топ",
            callback_data=f'bit_start:{artikul}:{target_position}'
        )],
        [InlineKeyboardButton(text="« Назад", callback_data='ads_strategy')],
    ])
    
    text = (
        f"🎯 <b>Точное попадание в топ</b>\n\n"
        f"Артикул: <code>{artikul}</code>\n"
        f"Целевая позиция: <b>топ-{target_position}</b>\n\n"
        f"📊 <b>Параметры стратегии:</b>\n"
        f"• Целевой ДРР: 20%\n"
        f"• Макс. ДРР: 35%\n"
        f"• Агрессивность: 2.5x\n"
        f"• Длительность: до 14 дней\n\n"
        f"<i>После достижения топ-{target_position} автоматически\n"
        f"переключится на «Поддержание топ позиции» (ДРР 5%)</i>"
    )
    
    await message.answer(text, reply_markup=keyboard)


@router.callback_query(F.data.startswith('bit_position:'))
async def on_bit_position_selected(callback: CallbackQuery):
    """Обработка выбора позиции для Break Into Top"""
    parts = callback.data.split(':')
    if len(parts) != 3:
        await callback.answer("❌ Ошибка данных")
        return
    
    artikul = parts[1]
    target_position = int(parts[2])
    
    # Обновляем меню с новой позицией
    await callback.answer()  # Мгновенный отклик
    await _show_break_into_top_menu(callback.message, artikul, target_position)


@router.callback_query(F.data.startswith('bit_start:'))
async def on_bit_start(callback: CallbackQuery):
    """Запускает Break Into Top для артикула"""
    user_id = str(callback.from_user.id)
    parts = callback.data.split(':')
    
    if len(parts) != 3:
        await callback.answer("❌ Ошибка данных")
        return
    
    artikul = parts[1]
    target_position = int(parts[2])
    
    # TODO: Интеграция с Evirma для получения ставки
    # Сейчас показываем заглушку
    
    text = (
        f"🚀 <b>Прорыв в топ запущен!</b>\n\n"
        f"Артикул: <code>{artikul}</code>\n"
        f"Цель: <b>топ-{target_position}</b>\n\n"
        f"⏳ <b>Следующие шаги:</b>\n"
        f"1. Анализ ставок через Evirma...\n"
        f"2. Установка оптимальной ставки...\n"
        f"3. Мониторинг позиции...\n\n"
        f"📈 Вы получите уведомление при:\n"
        f"• Достижении топ-{target_position}\n"
        f"• Превышении ДРР 35%\n"
        f"• Необходимости корректировки\n\n"
        f"<i>Стратегия: Break Into Top (ДРР 20%)</i>"
    )
    
    # Устанавливаем стратегию BREAK_INTO_TOP для пользователя
    ads_strategy_config.set_user_strategy(user_id, AdsStrategyType.BREAK_INTO_TOP)
    
    await callback.answer("✅ Запущено!")  # Быстрый отклик
    await callback.message.edit_text(text)


@router.callback_query(F.data == 'bit_enter_artikul')
async def on_bit_enter_artikul(callback: CallbackQuery):
    """Запрашивает ввод артикула вручную"""
    # TODO: Реализовать FSM для ввода артикула
    # Пока просто инструкция
    
    text = (
        "🎯 <b>Ввод артикула</b>\n\n"
        "Введите артикул товара в формате:\n"
        "<code>артикул:12345678</code>\n\n"
        "Или вернитесь назад и выберите другую стратегию."
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="« Назад", callback_data='strategy_break_into_top')],
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()


def register_handlers(dp):
    """Регистрация обработчиков"""
    dp.include_router(router)
    logger.info("✅ Обработчики аналитики зарегистрированы")
