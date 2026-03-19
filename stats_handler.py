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
<<<<<<< HEAD
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
=======
        else:
            await callback.message.answer(
                f"📢 <b>Реклама ({platform.upper()})</b>\n\n"
                f"⚠️ Рекламное API для Ozon пока не подключено.\n"
                f"Работаем над этим!"
            )
    except Exception as e:
        logger.error(f"Error showing ads stats: {e}")
        await callback.message.answer(
            f"📢 <b>Реклама ({platform.upper()})</b>\n\n"
            f"⚠️ Не удалось загрузить данные.\n"
            f"Убедитесь, что добавлен кабинет с API ключом."
        )
>>>>>>> main
    
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
            text=f"{'✅ ' if current_strategy == AdsStrategyType.TOP_POSITION_LOW_DRR else ''}🏆 Топ позиция (низкий ДРР)",
            callback_data='strategy_top_position'
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
        'strategy_top_position': AdsStrategyType.TOP_POSITION_LOW_DRR,
    }
    
    strategy = strategy_map.get(callback.data)
    if not strategy:
        await callback.answer("❌ Неизвестная стратегия")
        return
    
    # Устанавливаем стратегию
    ads_strategy_config.set_user_strategy(user_id, strategy)
    config = ads_strategy_config.get_strategy_config(strategy)
    
    text = (
        f"✅ <b>Стратегия изменена!</b>\n\n"
        f"{config.name}\n"
        f"━━━━━━━━━━━━━━\n"
        f"🎯 Целевой ДРР: {config.target_drr}%\n"
        f"📈 Макс. ДРР: {config.max_drr}%\n"
        f"⚡ Агрессивность: {config.bid_aggression}x\n\n"
        f"<i>{config.description}</i>"
    )
    
    await callback.message.edit_text(text)
    await callback.answer()


def register_handlers(dp):
    """Регистрация обработчиков"""
    dp.include_router(router)
    logger.info("✅ Обработчики аналитики зарегистрированы")
