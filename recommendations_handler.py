# recommendations_handler.py - AI рекомендации для пользователя
"""
Команда /recommendations - умные рекомендации на основе:
- Анализа цен через Mpstats
- Анализа ДРР
- Глобальной базы знаний
"""

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from modules.ai_learning_engine import AILearningEngine
from modules.sales_history import SalesHistoryManager
import logging

logger = logging.getLogger('recommendations_handler')
router = Router()

ai_engine = AILearningEngine("/opt/clients")
sales_manager = SalesHistoryManager("/opt/clients")


@router.message(Command("recommendations"))
async def cmd_recommendations(message: Message):
    """Показывает AI рекомендации"""
    user_id = str(message.from_user.id)
    
    # Заглушка - в реальности здесь будет интеграция с API WB/Ozon
    text = (
        "🧠 <b>AI Рекомендации</b>\n\n"
        "Анализирую ваши магазины...\n\n"
        "<i>Для получения реальных рекомендаций подключите API ключи:</i>\n"
        "/settings → Магазины → Добавить WB/Ozon"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💰 Анализ цен", callback_data='rec_prices')],
        [InlineKeyboardButton(text="📢 Анализ ДРР", callback_data='rec_drr')],
        [InlineKeyboardButton(text="📦 Анализ запасов", callback_data='rec_stock')],
        [InlineKeyboardButton(text="🧠 Глобальные инсайты", callback_data='rec_insights')],
    ])
    
    await message.answer(text, reply_markup=keyboard)


@router.callback_query(F.data == 'rec_prices')
async def recommend_prices(callback: CallbackQuery):
    """Рекомендации по ценам"""
    user_id = str(callback.from_user.id)
    
    # Пример анализа (в реальности - данные из API)
    example_analysis = ai_engine.analyze_price_vs_competitors(
        client_id=user_id,
        product_id="12345",
        category="electronics",
        current_price=1500,
        our_sales_velocity=5.2,
        competitors=[
            {"price": 1400, "sales_velocity": 4.0, "position": 12},
            {"price": 1600, "sales_velocity": 3.5, "position": 8},
            {"price": 1550, "sales_velocity": 5.0, "position": 10},
        ]
    )
    
    rec = example_analysis.get("recommendation")
    
    if rec == "price_increase":
        text = (
            "💰 <b>Рекомендация: ПОВЫСИТЬ ЦЕНУ</b>\n\n"
            f"Текущая цена: 1,500₽\n"
            f"Рекомендуемая: {example_analysis.get('suggested_price', 1600)}₽\n\n"
            f"<b>Обоснование:</b>\n"
            f"{example_analysis.get('reasoning')}\n\n"
            f"Уверенность: {example_analysis.get('confidence', 0) * 100:.0f}%"
        )
    elif rec == "maintain_price":
        text = (
            "✅ <b>Рекомендация: ЦЕНУ НЕ МЕНЯТЬ</b>\n\n"
            f"<b>Обоснование:</b>\n"
            f"{example_analysis.get('reasoning')}\n\n"
            f"Уверенность: {example_analysis.get('confidence', 0) * 100:.0f}%"
        )
    else:
        text = (
            "🤔 <b>Требуется дополнительный анализ</b>\n\n"
            f"{example_analysis.get('reasoning')}"
        )
    
    await callback.message.answer(text)
    await callback.answer()


@router.callback_query(F.data == 'rec_drr')
async def recommend_drr(callback: CallbackQuery):
    """Рекомендации по ДРР"""
    user_id = str(callback.from_user.id)
    
    # Пример анализа ДРР
    example_drr = ai_engine.analyze_drr_situation(
        campaign_id="camp_123",
        product_id="12345",
        current_drr=25.0,
        target_drr=15.0,
        orders_count=8,
        total_views=500,
        ctr=4.2,
        days_since_start=5,
        category_competition="high"
    )
    
    rec = example_drr.get("recommendation")
    
    if rec == "maintain_high_drr":
        text = (
            "📢 <b>ДРР: ПОДДЕРЖИВАТЬ ВЫСОКИЙ</b>\n\n"
            "Текущий ДРР: 25%\n"
            "Целевой ДРР: 15%\n\n"
            f"<b>Обоснование:</b>\n"
            f"{example_drr.get('reasoning')}\n\n"
            f"<b>Действие:</b>\n"
            f"{example_drr.get('action')}\n\n"
            f"Уверенность: {example_drr.get('confidence', 0) * 100:.0f}%"
        )
    elif rec == "decrease_drr":
        text = (
            "📉 <b>ДРР: СНИЖАТЬ</b>\n\n"
            "Текущий ДРР: 25%\n"
            "Целевой ДРР: 15%\n\n"
            f"<b>Обоснование:</b>\n"
            f"{example_drr.get('reasoning')}\n\n"
            f"<b>Действие:</b>\n"
            f"{example_drr.get('action')}"
        )
    elif rec == "check_content":
        text = (
            "⚠️ <b>ПРОБЛЕМА: Низкий CTR</b>\n\n"
            f"<b>Обоснование:</b>\n"
            f"{example_drr.get('reasoning')}\n\n"
            f"<b>Действие:</b>\n"
            f"{example_drr.get('action')}"
        )
    else:
        text = (
            "✅ <b>ДРР: НОРМА</b>\n\n"
            f"{example_drr.get('reasoning')}"
        )
    
    await callback.message.answer(text)
    await callback.answer()


@router.callback_query(F.data == 'rec_stock')
async def recommend_stock(callback: CallbackQuery):
    """Рекомендации по запасам"""
    user_id = str(callback.from_user.id)
    
    # Пример данных
    current_stock = 45
    avg_daily_sales = 3.5
    
    stock_days = sales_manager.calculate_stock_days(current_stock, avg_daily_sales)
    supply_needed = sales_manager.calculate_supply_needed(
        current_stock, avg_daily_sales, target_days=17
    )
    
    if stock_days < 10:
        priority = "🔴 КРИТИЧНО"
    elif stock_days < 17:
        priority = "🟠 ВАЖНО"
    else:
        priority = "🟢 НОРМА"
    
    text = (
        f"📦 <b>Анализ запасов {priority}</b>\n\n"
        f"Текущий остаток: {current_stock} шт.\n"
        f"Средние продажи: {avg_daily_sales:.1f} шт/день\n"
        f"Хватит на: {stock_days:.1f} дней\n\n"
    )
    
    if supply_needed > 0:
        text += f"<b>Рекомендуется заказать:</b> {supply_needed} шт.\n"
        text += "(для запаса на 17 дней)"
    else:
        text += "✅ Запасы в норме"
    
    await callback.message.answer(text)
    await callback.answer()


@router.callback_query(F.data == 'rec_insights')
async def show_insights(callback: CallbackQuery):
    """Глобальные инсайты из базы знаний"""
    user_id = str(callback.from_user.id)
    
    # Получаем инсайты по категории
    insights = ai_engine.get_category_insights("electronics")
    
    text = "🧠 <b>Глобальные инсайты</b>\n\n"
    
    if insights.get("recommendations"):
        for rec in insights["recommendations"]:
            text += f"• {rec}\n\n"
    else:
        text += "Пока недостаточно данных для глобальных инсайтов.\n"
        text += "Гипотезы собираются при работе с товарами."
    
    text += f"\n📊 Собрано паттернов: {len(insights.get('price_patterns', []))}"
    
    await callback.message.answer(text)
    await callback.answer()


def register_handlers(dp):
    """Регистрация обработчиков"""
    dp.include_router(router)
    logger.info("✅ Обработчики рекомендаций зарегистрированы")
