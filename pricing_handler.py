# pricing_handler.py - Команды для управления ценами
"""
Команды:
/pricing - меню ценообразования
/set_price - установить цену с учетом стратегии
/pricing_analyze - анализ эффективности цен
"""

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from modules.pricing_engine import PricingEngine, PriceRecommendation
import logging

logger = logging.getLogger('pricing_handler')
router = Router()

pricing_engine = PricingEngine("/opt/clients")


@router.message(Command("pricing"))
async def cmd_pricing(message: Message):
    """Меню ценообразования"""
    user_id = str(message.from_user.id)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Анализ цен", callback_data='pricing_analyze')],
        [InlineKeyboardButton(text="🎯 Buy Box стратегия", callback_data='pricing_bb_strategy')],
        [InlineKeyboardButton(text="💰 Profit Optimizer", callback_data='pricing_profit_opt')],
        [InlineKeyboardButton(text="⚡ Velocity pricing", callback_data='pricing_velocity')],
        [InlineKeyboardButton(text="📈 История изменений", callback_data='pricing_history')],
    ])
    
    await message.answer(
        "<b>💰 Ценообразование v2.0</b>\n\n"
        "Стратегии:\n"
        "• <b>Buy Box Targeting</b> — целевая борьба за корзину\n"
        "• <b>Profit Optimizer</b> — повышение цены после победы\n"
        "• <b>Velocity-based</b> — скорость продаж влияет на цену\n\n"
        "Выберите действие:",
        reply_markup=keyboard
    )


@router.callback_query(F.data == 'pricing_analyze')
async def pricing_analyze(callback: CallbackQuery):
    """Анализ цен конкурентов"""
    # Пример анализа
    competitors = [
        {"price": 1450, "rating": 4.3, "reviews": 89},
        {"price": 1590, "rating": 4.7, "reviews": 234},
        {"price": 1380, "rating": 4.1, "reviews": 45},
    ]
    
    bb_prob = pricing_engine.calculate_buy_box_probability(
        our_price=1500,
        competitors=competitors,
        our_rating=4.5,
        our_reviews=120
    )
    
    text = (
        "<b>📊 Анализ цен конкурентов</b>\n\n"
        "Конкуренты:\n"
        "• 1,450₽ (4.3★, 89 отзывов)\n"
        "• 1,590₽ (4.7★, 234 отзыва)\n"
        "• 1,380₽ (4.1★, 45 отзывов)\n\n"
        f"<b>Ваша позиция (1,500₽):</b>\n"
        f"• Вероятность Buy Box: {bb_prob*100:.0f}%\n"
        f"• Рекомендация: снизить до 1,430₽ для захвата BB\n\n"
        f"💡 <b>Profit Optimizer:</b> После 3 дней в BB можно повысить до 1,600₽"
    )
    
    await callback.message.answer(text)
    await callback.answer()


@router.callback_query(F.data == 'pricing_bb_strategy')
async def pricing_bb_strategy(callback: CallbackQuery):
    """Buy Box стратегия"""
    text = (
        "<b>🎯 Buy Box Targeting</b>\n\n"
        "Алгоритм:\n"
        "1️⃣ Анализируем цены конкурентов\n"
        "2️⃣ Рассчитываем вероятность получения BB\n"
        "3️⃣ Ставим цену на 2-5% ниже лидера\n"
        "4️⃣ Побеждаем в BB 🏆\n\n"
        "<b>Факторы BB:</b>\n"
        "• Цена (40% веса)\n"
        "• Рейтинг (30%)\n"
        "• Отзывы (20%)\n"
        "• Доставка FBO/FBS (10%)\n\n"
        "✅ <b>Далее активируется Profit Optimizer</b>"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚀 Применить стратегию", callback_data='apply_bb_strategy')],
    ])
    
    await callback.message.answer(text, reply_markup=keyboard)
    await callback.answer()


@router.callback_query(F.data == 'pricing_profit_opt')
async def pricing_profit_optimizer(callback: CallbackQuery):
    """Profit Optimizer инфо"""
    text = (
        "<b>💰 Profit Optimizer</b>\n\n"
        "Алгоритм повышения цены после победы в Buy Box:\n\n"
        "📅 <b>День 1-3:</b> +5% к цене\n"
        "   Цель: Проверить удержание BB\n\n"
        "📅 <b>День 4-7:</b> +10% к цене\n"
        "   Цель: Максимизация маржи\n\n"
        "📅 <b>День 8+:</b> +15% к цене (макс)\n"
        "   Цель: Оптимальный профит\n\n"
        "⚡ <b>Результат:</b>\n"
        "Выиграли BB по низкой цене → постепенно повышаем → макс. прибыль"
    )
    
    await callback.message.answer(text)
    await callback.answer()


@router.callback_query(F.data == 'pricing_velocity')
async def pricing_velocity(callback: CallbackQuery):
    """Velocity-based pricing"""
    text = (
        "<b>⚡ Velocity-Based Pricing</b>\n\n"
        "Цена корректируется по скорости продаж:\n\n"
        "🚀 <b>Высокая скорость (>2x средней):</b>\n"
        "   → +10% к цене (спрос высокий)\n\n"
        "📈 <b>Выше среднего (1.5-2x):</b>\n"
        "   → +5% к цене\n\n"
        "📉 <b>Ниже среднего (<0.8x):</b>\n"
        "   → -5% к цене (стимулируем продажи)\n\n"
        "🐌 <b>Низкая скорость (<0.5x):</b>\n"
        "   → -10% к цене\n\n"
        "📦 <b>Мало запасов (<10 дней):</b>\n"
        "   → +5% (эффект дефицита)"
    )
    
    await callback.message.answer(text)
    await callback.answer()


@router.callback_query(F.data == 'pricing_history')
async def pricing_history(callback: CallbackQuery):
    """История ценовых изменений"""
    user_id = str(callback.from_user.id)
    
    # Получаем анализ
    performance = pricing_engine.get_price_performance(user_id, "example_product")
    
    if performance.get('status') == 'no_data':
        text = (
            "<b>📈 История изменений цен</b>\n\n"
            "Пока нет данных об изменениях цен.\n"
            "История будет собираться автоматически при работе системы."
        )
    else:
        text = (
            "<b>📈 Эффективность ценообразования</b>\n\n"
            f"Всего изменений: {performance['total_changes']}\n"
            f"Успешных: {performance['successful']} ✅\n"
            f"Неудачных: {performance['failed']} ❌\n"
            f"Успешность: {performance['success_rate']*100:.1f}%\n\n"
            f"💡 Рекомендуемая стратегия: {performance['recommended_strategy']}"
        )
    
    await callback.message.answer(text)
    await callback.answer()


@router.message(Command("set_price"))
async def cmd_set_price(message: Message):
    """Установить цену с учетом стратегии"""
    await message.answer(
        "<b>💰 Установка цены</b>\n\n"
        "Используйте команду с параметрами:\n"
        "/set_price \u003carticul\u003e \u003ccost_price\u003e \u003ccurrent_price\u003e\n\n"
        "Пример:\n"
        "/set_price 12345 800 1200\n\n"
        "Система рассчитает оптимальную цену на основе:\n"
        "• Конкурентов\n"
        "• Buy Box вероятности\n"
        "• Скорости продаж"
    )


def register_handlers(dp):
    """Регистрация обработчиков"""
    dp.include_router(router)
    logger.info("✅ Обработчики ценообразования зарегистрированы")
