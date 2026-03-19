# cabinet_handler.py - Управление множественными кабинетами
"""
Обработчик для управления до 5 WB + 5 Ozon кабинетов
Этап 3: Cabinet Management UI
"""

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import logging

logger = logging.getLogger('cabinet_handler')
router = Router()

# FSM для добавления кабинета
class AddCabinetForm(StatesGroup):
    waiting_for_platform = State()
    waiting_for_name = State()
    waiting_for_api_key = State()
    waiting_for_client_id = State()  # Только для Ozon


@router.callback_query(F.data == 'settings_cabinets')
async def show_cabinets_menu(callback: CallbackQuery):
    """Показывает меню управления кабинетами"""
    user_id = str(callback.from_user.id)
    
    from modules.multi_cabinet_manager import cabinet_manager
    
    # Получаем список кабинетов
    cabinets = cabinet_manager.get_user_cabinets(user_id)
    counts = cabinet_manager.get_cabinet_count(user_id)
    
    # Формируем текст
    text = "🏪 <b>Управление кабинетами</b>\n\n"
    text += f"🟣 Wildberries: {counts['wb']}/{counts['wb_limit']}\n"
    text += f"🔵 Ozon: {counts['ozon']}/{counts['ozon_limit']}\n\n"
    
    if cabinets:
        text += "<b>Ваши кабинеты:</b>\n"
        for cab in cabinets:
            status = "🟢" if cab.is_active else "🔴"
            platform = "🟣" if cab.platform == "wb" else "🔵"
            text += f"{status} {platform} {cab.name}\n"
    else:
        text += "📭 Пока нет подключенных кабинетов\n"
    
    # Кнопки
    buttons = []
    
    # Показываем кнопку добавления если есть место
    if counts['wb'] < counts['wb_limit'] or counts['ozon'] < counts['ozon_limit']:
        buttons.append([InlineKeyboardButton(text="➕ Добавить кабинет", callback_data='cabinet_add')])
    
    if cabinets:
        buttons.append([InlineKeyboardButton(text="🗑 Удалить кабинет", callback_data='cabinet_remove_menu')])
        buttons.append([InlineKeyboardButton(text="✏️ Редактировать", callback_data='cabinet_edit_menu')])
    
    buttons.append([InlineKeyboardButton(text="⬅️ Назад", callback_data='settings')])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    
    await callback.message.answer(text, reply_markup=keyboard)
    await callback.answer()


@router.callback_query(F.data == 'cabinet_add')
async def start_add_cabinet(callback: CallbackQuery, state: FSMContext):
    """Начинает процесс добавления кабинета"""
    user_id = str(callback.from_user.id)
    
    from modules.multi_cabinet_manager import cabinet_manager
    counts = cabinet_manager.get_cabinet_count(user_id)
    
    # Проверяем доступные платформы
    available = []
    if counts['wb'] < counts['wb_limit']:
        available.append(('wb', '🟣 Wildberries'))
    if counts['ozon'] < counts['ozon_limit']:
        available.append(('ozon', '🔵 Ozon'))
    
    if not available:
        await callback.message.answer("❌ Достигнут лимит кабинетов")
        await callback.answer()
        return
    
    # Кнопки выбора платформы
    buttons = [
        [InlineKeyboardButton(text=name, callback_data=f'cabinet_platform_{platform}')]
        for platform, name in available
    ]
    buttons.append([InlineKeyboardButton(text="❌ Отмена", callback_data='settings_cabinets')])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    
    await callback.message.answer(
        "🏪 <b>Добавление кабинета</b>\n\n"
        "Выберите платформу:",
        reply_markup=keyboard
    )
    await callback.answer()


@router.callback_query(F.data.startswith('cabinet_platform_'))
async def select_platform(callback: CallbackQuery, state: FSMContext):
    """Обрабатывает выбор платформы"""
    platform = callback.data.replace('cabinet_platform_', '')
    
    await state.update_data(platform=platform)
    await state.set_state(AddCabinetForm.waiting_for_name)
    
    platform_name = "🟣 Wildberries" if platform == "wb" else "🔵 Ozon"
    
    await callback.message.answer(
        f"{platform_name}\n\n"
        f"Введите <b>название</b> кабинета:\n"
        f"(например: 'Основной', 'Запасной', 'Тестовый')"
    )
    await callback.answer()


@router.message(AddCabinetForm.waiting_for_name)
async def process_name(message: Message, state: FSMContext):
    """Обрабатывает название"""
    name = message.text.strip()
    
    if len(name) < 2 or len(name) > 30:
        await message.answer("❌ Название должно быть от 2 до 30 символов")
        return
    
    await state.update_data(name=name)
    await state.set_state(AddCabinetForm.waiting_for_api_key)
    
    data = await state.get_data()
    platform = data['platform']
    
    platform_name = "🟣 Wildberries" if platform == "wb" else "🔵 Ozon"
    
    await message.answer(
        f"{platform_name} - {name}\n\n"
        f"Введите <b>API ключ</b>:\n"
        f"(стандартный токен авторизации)"
    )


@router.message(AddCabinetForm.waiting_for_api_key)
async def process_api_key(message: Message, state: FSMContext):
    """Обрабатывает API ключ"""
    api_key = message.text.strip()
    
    if len(api_key) < 10:
        await message.answer("❌ API ключ слишком короткий")
        return
    
    await state.update_data(api_key=api_key)
    
    data = await state.get_data()
    platform = data['platform']
    
    if platform == 'ozon':
        # Для Ozon нужен еще Client ID
        await state.set_state(AddCabinetForm.waiting_for_client_id)
        await message.answer(
            "🔵 Ozon требует дополнительный параметр\n\n"
            "Введите <b>Client ID</b>:\n"
            "(можно найти в личном кабинете Ozon)"
        )
    else:
        # Для WB - сохраняем
        await save_cabinet(message, state)


@router.message(AddCabinetForm.waiting_for_client_id)
async def process_client_id(message: Message, state: FSMContext):
    """Обрабатывает Client ID для Ozon"""
    client_id = message.text.strip()
    
    if not client_id.isdigit():
        await message.answer("❌ Client ID должен содержать только цифры")
        return
    
    await state.update_data(client_id=client_id)
    await save_cabinet(message, state)


async def save_cabinet(message: Message, state: FSMContext):
    """Сохраняет кабинет"""
    user_id = str(message.from_user.id)
    data = await state.get_data()
    
    from modules.multi_cabinet_manager import cabinet_manager
    
    success, result_msg = cabinet_manager.add_cabinet(
        user_id=user_id,
        name=data['name'],
        platform=data['platform'],
        api_key=data['api_key'],
        client_id=data.get('client_id')
    )
    
    await state.clear()
    
    if success:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🏪 К списку кабинетов", callback_data='settings_cabinets')],
        ])
        await message.answer(result_msg, reply_markup=keyboard)
    else:
        await message.answer(f"❌ {result_msg}")


@router.callback_query(F.data == 'cabinet_remove_menu')
async def show_remove_menu(callback: CallbackQuery):
    """Показывает меню удаления"""
    user_id = str(callback.from_user.id)
    
    from modules.multi_cabinet_manager import cabinet_manager
    cabinets = cabinet_manager.get_user_cabinets(user_id)
    
    buttons = []
    for cab in cabinets:
        platform = "🟣" if cab.platform == "wb" else "🔵"
        buttons.append([
            InlineKeyboardButton(
                text=f"🗑 {platform} {cab.name}",
                callback_data=f'cabinet_delete_{cab.id}'
            )
        ])
    
    buttons.append([InlineKeyboardButton(text="❌ Отмена", callback_data='settings_cabinets')])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    
    await callback.message.answer(
        "🗑 <b>Удаление кабинета</b>\n\n"
        "Выберите кабинет для удаления:\n"
        "<i>(это действие нельзя отменить)</i>",
        reply_markup=keyboard
    )
    await callback.answer()


@router.callback_query(F.data.startswith('cabinet_delete_'))
async def delete_cabinet(callback: CallbackQuery):
    """Удаляет кабинет"""
    user_id = str(callback.from_user.id)
    cabinet_id = callback.data.replace('cabinet_delete_', '')
    
    from modules.multi_cabinet_manager import cabinet_manager
    
    success, msg = cabinet_manager.remove_cabinet(user_id, cabinet_id)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏪 К списку", callback_data='settings_cabinets')],
    ])
    
    await callback.message.answer(msg, reply_markup=keyboard)
    await callback.answer()


def register_handlers(dp):
    """Регистрация обработчиков"""
    dp.include_router(router)
    logger.info("✅ Cabinet management handlers registered (5 WB + 5 Ozon)")
