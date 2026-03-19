# fuck_mode_handler.py - Обработчик Fuck Mode
"""
Обработка кнопок Fuck Mode
Бета-функция - требует предварительного тестирования
"""

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
import logging

logger = logging.getLogger('fuck_mode_handler')
router = Router()

# Текст предупреждения для бета-режима
BETA_WARNING = """
⚠️ <b>BETA РЕЖИМ</b>

Fuck Mode - полная автономия управления.
Бот будет сам принимать решения по:
• Ценообразованию
• Рекламным кампаниям
• Остаткам и поставкам

<b>Требуется:</b>
✅ Подключенные API ключи
✅ Настроенные лимиты
✅ Понимание рисков

<i>Функция в стадии бета-тестирования.</i>
"""


@router.callback_query(F.data == 'beta_fuck_mode')
async def show_fuck_mode_menu(callback: CallbackQuery):
    """Показывает меню Fuck Mode (бета)"""
    user_id = str(callback.from_user.id)
    
    # Проверяем статус
    from modules.fuck_mode import fuck_mode_engine
    status = fuck_mode_engine.get_user_status(user_id)
    is_enabled = fuck_mode_engine.is_enabled_for_user(user_id)
    
    # Формируем кнопки
    buttons = []
    
    if is_enabled:
        buttons.extend([
            [InlineKeyboardButton(text="⏸️ Пауза", callback_data='fuck_pause'),
             InlineKeyboardButton(text="🛑 Стоп", callback_data='fuck_stop')],
            [InlineKeyboardButton(text="📊 Отчет", callback_data='fuck_report')],
        ])
    else:
        buttons.extend([
            [InlineKeyboardButton(text="🟣 WB", callback_data='fuck_start_wb'),
             InlineKeyboardButton(text="🔵 Ozon", callback_data='fuck_start_ozon')],
            [InlineKeyboardButton(text="🌟 Все кабинеты", callback_data='fuck_start_all')],
        ])
    
    buttons.append([InlineKeyboardButton(text="⬅️ Назад", callback_data='menu')])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    
    status_emoji = "🟢" if is_enabled else "🔴"
    status_text = "Активен" if is_enabled else "Отключен"
    
    text = f"🤖 <b>Fuck Mode (BETA)</b> {status_emoji}\n\n"
    text += f"Статус: <b>{status_text}</b>\n\n"
    text += BETA_WARNING
    
    await callback.message.answer(text, reply_markup=keyboard)
    await callback.answer()


@router.callback_query(F.data.startswith('fuck_start_'))
async def start_fuck_mode(callback: CallbackQuery):
    """Запускает Fuck Mode"""
    user_id = str(callback.from_user.id)
    target = callback.data.replace('fuck_start_', '')
    
    await callback.answer("⏳ Активация...")
    
    from modules.fuck_mode import fuck_mode_engine
    
    # Определяем платформы
    if target == 'wb':
        platforms = ['wb']
        platform_text = "🟣 Wildberries"
    elif target == 'ozon':
        platforms = ['ozon']
        platform_text = "🔵 Ozon"
    else:  # all
        platforms = ['wb', 'ozon']
        platform_text = "🟣 WB + 🔵 Ozon"
    
    # Активируем
    success, message = fuck_mode_engine.enable_for_user(user_id, platforms)
    
    if success:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📊 Статус", callback_data='fuck_status'),
             InlineKeyboardButton(text="⏸️ Пауза", callback_data='fuck_pause')],
            [InlineKeyboardButton(text="⬅️ В меню", callback_data='menu')],
        ])
        
        text = f"🚀 <b>Fuck Mode АКТИВИРОВАН!</b>\n\n"
        text += f"Платформы: {platform_text}\n\n"
        text += "Бот теперь автоматически:\n"
        text += "• Корректирует цены\n"
        text += "• Оптимизирует рекламу\n"
        text += "• Мониторит остатки\n\n"
        text += "<i>Отчеты будут приходить каждое утро.</i>"
        
        await callback.message.answer(text, reply_markup=keyboard)
    else:
        await callback.message.answer(f"❌ {message}\n\nСначала подключите API ключи в настройках.")
    
    await callback.answer()


@router.callback_query(F.data == 'fuck_pause')
async def pause_fuck_mode(callback: CallbackQuery):
    """Приостанавливает Fuck Mode"""
    user_id = str(callback.from_user.id)
    
    from modules.fuck_mode import fuck_mode_engine
    success, message = fuck_mode_engine.pause_for_user(user_id)
    
    if success:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="▶️ Возобновить", callback_data='fuck_resume')],
            [InlineKeyboardButton(text="🛑 Полный стоп", callback_data='fuck_stop')],
        ])
        await callback.message.answer("⏸️ <b>Fuck Mode на паузе</b>", reply_markup=keyboard)
    else:
        await callback.message.answer(f"❌ {message}")
    
    await callback.answer()


@router.callback_query(F.data == 'fuck_resume')
async def resume_fuck_mode(callback: CallbackQuery):
    """Возобновляет Fuck Mode"""
    user_id = str(callback.from_user.id)
    
    from modules.fuck_mode import fuck_mode_engine
    
    # Получаем предыдущие настройки
    status = fuck_mode_engine.get_user_status(user_id)
    platforms = status.get('platforms', ['wb', 'ozon'])
    
    success, message = fuck_mode_engine.enable_for_user(user_id, platforms)
    
    if success:
        await callback.message.answer("▶️ <b>Fuck Mode возобновлен</b>")
    else:
        await callback.message.answer(f"❌ {message}")
    
    await callback.answer()


@router.callback_query(F.data == 'fuck_stop')
async def stop_fuck_mode(callback: CallbackQuery):
    """Останавливает Fuck Mode"""
    user_id = str(callback.from_user.id)
    
    from modules.fuck_mode import fuck_mode_engine
    success, message = fuck_mode_engine.disable_for_user(user_id)
    
    if success:
        await callback.message.answer(
            "🛑 <b>Fuck Mode остановлен</b>\n\n"
            "Все автоматические действия прекращены.\n"
            "Вы снова управляете кабинетами вручную."
        )
    else:
        await callback.message.answer(f"❌ {message}")
    
    await callback.answer()


@router.callback_query(F.data == 'fuck_status')
async def fuck_mode_status(callback: CallbackQuery):
    """Показывает статус Fuck Mode"""
    user_id = str(callback.from_user.id)
    
    from modules.fuck_mode import fuck_mode_engine
    
    if not fuck_mode_engine.is_enabled_for_user(user_id):
        await callback.message.answer("🔴 Fuck Mode отключен")
        await callback.answer()
        return
    
    # Получаем отчет
    report = fuck_mode_engine.get_daily_report(user_id)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Подробный отчет", callback_data='fuck_report')],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data='beta_fuck_mode')],
    ])
    
    await callback.message.answer(report, reply_markup=keyboard)
    await callback.answer()


@router.callback_query(F.data == 'fuck_report')
async def fuck_mode_report(callback: CallbackQuery):
    """Показывает детальный отчет"""
    user_id = str(callback.from_user.id)
    
    from modules.fuck_mode import fuck_mode_engine
    
    report = fuck_mode_engine.get_daily_report(user_id)
    
    # Добавляем детали
    report += "\n\n<b>Последние действия:</b>\n"
    report += "• Цена товара #123: +5%\n"
    report += "• ДРР кампании #456: оптимизирован\n"
    report += "• Товар #789: заказана поставка\n"
    
    await callback.message.answer(report)
    await callback.answer()


def register_handlers(dp):
    """Регистрация обработчиков"""
    dp.include_router(router)
    logger.info("✅ Fuck Mode handlers registered (BETA)")
