# settings_handler.py - Обработчик настроек автономности
"""
Команды для управления настройками автономного цикла.
/settings - показать текущие настройки
"""

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from modules.settings_manager import SettingsManager
import logging

logger = logging.getLogger('settings_handler')
router = Router()

settings_manager = SettingsManager("/opt/clients")


@router.message(Command("settings"))
async def cmd_settings(message: Message):
    """Показывает текущие настройки"""
    user_id = str(message.from_user.id)
    
    text = settings_manager.format_settings_message(user_id)
    
    # Кнопки для изменения
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📦 Изменить порог запасов", callback_data='set_stock_threshold')],
        [InlineKeyboardButton(text="💰 Изменить макс. цену", callback_data='set_price_change')],
        [InlineKeyboardButton(text="📢 Изменить целевой ДРР", callback_data='set_target_drr')],
        [InlineKeyboardButton(text="💸 Изменить мин. маржу", callback_data='set_min_margin')],
        [InlineKeyboardButton(text="🔄 Сбросить к дефолтным", callback_data='reset_settings')],
    ])
    
    await message.answer(text, reply_markup=keyboard)


@router.callback_query(F.data == 'set_stock_threshold')
async def set_stock_threshold(callback: CallbackQuery):
    """Запрашивает новый порог запасов"""
    text = (
        "📦 <b>Изменение порога запасов</b>\n\n"
        "Текущий порог: уведомление когда запасов хватает на менее чем X дней.\n\n"
        "Введите число от 10 до 30:\n"
        "Пример: /set_stock 20"
    )
    await callback.message.answer(text)
    await callback.answer()


@router.message(Command("set_stock"))
async def cmd_set_stock(message: Message):
    """Устанавливает порог запасов"""
    user_id = str(message.from_user.id)
    
    try:
        args = message.text.split()
        if len(args) < 2:
            await message.answer("❌ Укажите значение: /set_stock 20")
            return
        
        value = int(args[1])
        if settings_manager.update_setting(user_id, 'stock_days_threshold', value):
            await message.answer(f"✅ Порог запасов установлен: {value} дней")
        else:
            await message.answer(f"❌ Ошибка: значение должно быть от 10 до 30")
            
    except ValueError:
        await message.answer("❌ Некорректное число. Пример: /set_stock 20")


@router.callback_query(F.data == 'set_price_change')
async def set_price_change(callback: CallbackQuery):
    """Запрашивает макс. изменение цены"""
    text = (
        "💰 <b>Максимальное изменение цены</b>\n\n"
        "Автономный режим не будет менять цену больше чем на этот процент за раз.\n\n"
        "Введите число от 5 до 50:\n"
        "Пример: /set_price_change 15"
    )
    await callback.message.answer(text)
    await callback.answer()


@router.message(Command("set_price_change"))
async def cmd_set_price_change(message: Message):
    """Устанавливает макс. изменение цены"""
    user_id = str(message.from_user.id)
    
    try:
        args = message.text.split()
        if len(args) < 2:
            await message.answer("❌ Укажите значение: /set_price_change 20")
            return
        
        value = int(args[1])
        if settings_manager.update_setting(user_id, 'max_price_change_percent', value):
            await message.answer(f"✅ Макс. изменение цены: ±{value}%")
        else:
            await message.answer(f"❌ Ошибка: значение должно быть от 5 до 50")
            
    except ValueError:
        await message.answer("❌ Некорректное число. Пример: /set_price_change 20")


@router.callback_query(F.data == 'set_target_drr')
async def set_target_drr(callback: CallbackQuery):
    """Запрашивает целевой ДРР"""
    text = (
        "📢 <b>Целевой ДРР</b>\n\n"
        "Доля рекламных расходов в выручке.\n"
        "Оптимально: 10-20%\n\n"
        "Введите число от 5 до 30:\n"
        "Пример: /set_drr 15"
    )
    await callback.message.answer(text)
    await callback.answer()


@router.message(Command("set_drr"))
async def cmd_set_drr(message: Message):
    """Устанавливает целевой ДРР"""
    user_id = str(message.from_user.id)
    
    try:
        args = message.text.split()
        if len(args) < 2:
            await message.answer("❌ Укажите значение: /set_drr 15")
            return
        
        value = int(args[1])
        if settings_manager.update_setting(user_id, 'target_drr_percent', value):
            await message.answer(f"✅ Целевой ДРР установлен: {value}%")
        else:
            await message.answer(f"❌ Ошибка: значение должно быть от 5 до 30")
            
    except ValueError:
        await message.answer("❌ Некорректное число. Пример: /set_drr 15")


@router.callback_query(F.data == 'set_min_margin')
async def set_min_margin(callback: CallbackQuery):
    """Запрашивает мин. маржу"""
    text = (
        "💸 <b>Минимальная маржа</b>\n\n"
        "Алерт если маржа товара ниже этого значения.\n\n"
        "Введите число от 5 до 30:\n"
        "Пример: /set_margin 15"
    )
    await callback.message.answer(text)
    await callback.answer()


@router.message(Command("set_margin"))
async def cmd_set_margin(message: Message):
    """Устанавливает мин. маржу"""
    user_id = str(message.from_user.id)
    
    try:
        args = message.text.split()
        if len(args) < 2:
            await message.answer("❌ Укажите значение: /set_margin 15")
            return
        
        value = int(args[1])
        if settings_manager.update_setting(user_id, 'min_margin_percent', value):
            await message.answer(f"✅ Минимальная маржа установлена: {value}%")
        else:
            await message.answer(f"❌ Ошибка: значение должно быть от 5 до 30")
            
    except ValueError:
        await message.answer("❌ Некорректное число. Пример: /set_margin 15")


@router.callback_query(F.data == 'reset_settings')
async def reset_settings(callback: CallbackQuery):
    """Сбрасывает настройки к дефолтным"""
    user_id = str(callback.from_user.id)
    
    if settings_manager.reset_to_defaults(user_id):
        await callback.message.answer("✅ Настройки сброшены к дефолтным")
    else:
        await callback.message.answer("❌ Ошибка сброса настроек")
    
    await callback.answer()


def register_handlers(dp):
    """Регистрация обработчиков"""
    dp.include_router(router)
    logger.info("✅ Обработчики настроек зарегистрированы")
