# ab_testing_handler.py - Команды для A/B тестирования
"""
Команды:
/ab_test - создать тест
/ab_status - статус тестов
/ab_results - результаты
"""

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from modules.ab_testing import ABTestingFramework
import logging

logger = logging.getLogger('ab_testing_handler')
router = Router()

ab_framework = ABTestingFramework("/opt/clients")


@router.message(Command("ab_test"))
async def cmd_ab_test(message: Message):
    """Создать A/B тест"""
    await message.answer(
        "<b>🧪 A/B Тестирование</b>\n\n"
        "Создайте тест для сравнения ценовых стратегий:\n\n"
        "Формат:\n"
        "/ab_test_create \u003cназвание\u003e | \u003cтовары\u003e | \u003cстратегия_A\u003e | \u003cстратегия_B\u003e\n\n"
        "Пример:\n"
        "/ab_test_create Test Profit vs BB | 123,456,789,101 | aggressive_buy_box | profit_maximizer\n\n"
        "Стратегии:\n"
        "• aggressive_buy_box — агрессивный захват BB\n"
        "• profit_maximizer — максимизация прибыли\n"
        "• velocity_optimizer — фокус на скорость"
    )


@router.message(Command("ab_status"))
async def cmd_ab_status(message: Message):
    """Статус активных тестов"""
    user_id = str(message.from_user.id)
    
    active_tests = ab_framework.get_active_tests(user_id)
    
    if not active_tests:
        await message.answer(
            "<b>🧪 Нет активных A/B тестов</b>\n\n"
            "Создайте тест командой /ab_test"
        )
        return
    
    text = "<b>🧪 Активные A/B тесты:</b>\n\n"
    
    for test in active_tests:
        text += (
            f"📋 <b>{test.name}</b> (ID: {test.test_id})\n"
            f"   A: {test.variant_a_strategy}\n"
            f"   B: {test.variant_b_strategy}\n"
            f"   Товаров: {len(test.product_ids)}\n\n"
        )
    
    await message.answer(text)


@router.message(Command("ab_results"))
async def cmd_ab_results(message: Message):
    """Результаты тестов"""
    user_id = str(message.from_user.id)
    
    # Получаем рекомендованную стратегию
    recommended = ab_framework.get_recommended_strategy(user_id)
    
    text = (
        "<b>📊 A/B Результаты</b>\n\n"
        f"🎯 <b>Рекомендуемая стратегия:</b> {recommended}\n\n"
        "На основе истории A/B тестов система рекомендует "
        f"использовать стратегию '<b>{recommended}</b>' для новых товаров."
    )
    
    await message.answer(text)


def register_handlers(dp):
    """Регистрация обработчиков"""
    dp.include_router(router)
    logger.info("✅ Обработчики A/B тестирования зарегистрированы")
