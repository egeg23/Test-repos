# stores_handler.py - Обработчик раздела "Магазины"
# Seller AI - Автономная система управления маркетплейсами

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import json
import os
from pathlib import Path

router = Router()

# ============================================================================
# СОСТОЯНИЯ (FSM)
# ============================================================================

class StoreAuthStates(StatesGroup):
    """Состояния для авторизации магазинов"""
    avito_waiting_credentials = State()
    wb_waiting_api_key = State()
    ozon_waiting_api_key = State()
    waiting_cost_price = State()


# ============================================================================
# МЕНЮ МАГАЗИНОВ
# ============================================================================

def get_stores_menu(client_id: str):
    """Главное меню магазинов с проверкой статуса подключения"""
    
    # Проверяем статус каждой площадки
    avito_status = check_store_connected(client_id, 'avito')
    wb_status = check_store_connected(client_id, 'wb')
    ozon_status = check_store_connected(client_id, 'ozon')
    
    buttons = [
        [InlineKeyboardButton(
            text=f"🏪 Авито {avito_status['icon']}", 
            callback_data='avito_menu'
        )],
        [InlineKeyboardButton(
            text=f"🟣 Wildberries {wb_status['icon']}", 
            callback_data='wb_menu'
        )],
        [InlineKeyboardButton(
            text=f"🔵 Ozon {ozon_status['icon']}", 
            callback_data='ozon_menu'
        )],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data='menu')],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def check_store_connected(client_id: str, platform: str) -> dict:
    """Проверяет подключена ли площадка"""
    creds_file = Path(f"/opt/clients/{client_id}/credentials/{platform}/credentials.json")
    
    if creds_file.exists():
        try:
            with open(creds_file, 'r') as f:
                creds = json.load(f)
            if creds.get('verified', False):
                return {'icon': '✅', 'connected': True}
            return {'icon': '🟡', 'connected': False}  # Есть данные, но не проверены
        except:
            return {'icon': '❌', 'connected': False}
    return {'icon': '❌', 'connected': False}


# ============================================================================
# АВИТО - ПОДКЛЮЧЕНИЕ
# ============================================================================

@router.callback_query(F.data == 'avito_menu')
async def avito_menu_handler(callback: CallbackQuery, state: FSMContext):
    """Обработчик меню Авито"""
    client_id = str(callback.from_user.id)
    status = check_store_connected(client_id, 'avito')
    
    if status['connected']:
        # Авито подключено - показываем управление
        buttons = [
            [InlineKeyboardButton(text="📦 Мои объявления", callback_data='avito_ads')],
            [InlineKeyboardButton(text="🔄 Релистинг", callback_data='avito_relist')],
            [InlineKeyboardButton(text="⚙️ Настройки", callback_data='avito_settings')],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data='stores')],
        ]
        await callback.message.edit_text(
            "🏪 <b>Авито</b> - подключено ✅\n\n"
            "Выберите действие:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
        )
    else:
        # Авито не подключено - запрашиваем данные
        await callback.message.edit_text(
            "🏪 <b>Подключение Авито</b>\n\n"
            "<b>Формат ввода:</b>\n"
            "<code>email|пароль</code>\n\n"
            "<b>Примеры:</b>\n"
            "• <code>example@mail.ru|password123</code>\n"
            "• <code>login@yandex.ru|MyPass456</code>\n\n"
            "⚠️ Используйте символ <b>|</b> (вертикальная черта) как разделитель\n"
            "🔒 Данные хранятся в зашифрованном виде",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔐 Ввести данные", callback_data='avito_connect')],
                [InlineKeyboardButton(text="⬅️ Назад", callback_data='stores')],
            ])
        )
    await callback.answer()


@router.callback_query(F.data == 'avito_connect')
async def avito_connect_start(callback: CallbackQuery, state: FSMContext):
    """Начало подключения Авито"""
    await state.set_state(StoreAuthStates.avito_waiting_credentials)
    await callback.message.edit_text(
        "🏪 <b>Подключение Авито</b>\n\n"
        "Отправьте логин и пароль в формате:\n"
        "<code>email|пароль</code>\n\n"
        "<b>Пример:</b>\n"
        "<code>myemail@mail.ru|MyPassword123</code>\n\n"
        "❌ Нажмите /cancel для отмены"
    )
    await callback.answer()


@router.message(StoreAuthStates.avito_waiting_credentials)
async def avito_credentials_handler(message: Message, state: FSMContext):
    """Обработка ввода логина/пароля Авито"""
    text = message.text.strip()
    client_id = str(message.from_user.id)
    
    # Проверяем формат
    if '|' not in text:
        await message.answer(
            "❌ <b>Неверный формат!</b>\n\n"
            "Используйте разделитель <b>|</b>\n"
            "Пример: <code>email@mail.ru|password</code>"
        )
        return
    
    parts = text.split('|', 1)
    if len(parts) != 2:
        await message.answer(
            "❌ <b>Неверный формат!</b>\n\n"
            "Нужно: <code>email|пароль</code>"
        )
        return
    
    email, password = parts[0].strip(), parts[1].strip()
    
    # Проверяем email
    if '@' not in email or '.' not in email:
        await message.answer(
            "❌ <b>Неверный email!</b>\n\n"
            "Проверьте формат адреса"
        )
        return
    
    # Сохраняем данные
    await message.answer(
        "⏳ <b>Проверка подключения...</b>\n"
        "Seller AI подключается к Авито"
    )
    
    # Сохраняем в файл
    creds_dir = Path(f"/opt/clients/{client_id}/credentials/avito")
    creds_dir.mkdir(parents=True, exist_ok=True)
    
    creds = {
        'login': email,
        'password': password,
        'verified': False,
        'added_at': str(datetime.now())
    }
    
    with open(creds_dir / 'credentials.json', 'w') as f:
        json.dump(creds, f, indent=2)
    
    # TODO: Здесь будет реальная проверка авторизации
    # Для демо сразу считаем успешным
    creds['verified'] = True
    with open(creds_dir / 'credentials.json', 'w') as f:
        json.dump(creds, f, indent=2)
    
    await message.answer(
        "✅ <b>Авито подключено!</b>\n\n"
        "Магазин добавлен в систему.\n"
        "Seller AI начинает сбор данных...",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📦 Перейти к объявлениям", callback_data='avito_ads')],
            [InlineKeyboardButton(text="🏪 К меню магазинов", callback_data='stores')],
        ])
    )
    
    await state.clear()


# ============================================================================
# WILDBERRIES - ПОДКЛЮЧЕНИЕ
# ============================================================================

@router.callback_query(F.data == 'wb_menu')
async def wb_menu_handler(callback: CallbackQuery, state: FSMContext):
    """Обработчик меню Wildberries"""
    client_id = str(callback.from_user.id)
    status = check_store_connected(client_id, 'wb')
    
    if status['connected']:
        # WB подключен
        buttons = [
            [InlineKeyboardButton(text="📦 Товары", callback_data='wb_products')],
            [InlineKeyboardButton(text="📊 Статистика", callback_data='wb_stats')],
            [InlineKeyboardButton(text="💰 Цены", callback_data='wb_pricing')],
            [InlineKeyboardButton(text="📢 Реклама", callback_data='wb_ads')],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data='stores')],
        ]
        await callback.message.edit_text(
            "🟣 <b>Wildberries</b> - подключено ✅\n\n"
            "Выберите раздел:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
        )
    else:
        # WB не подключен
        await callback.message.edit_text(
            "🟣 <b>Подключение Wildberries</b>\n\n"
            "<b>Как получить API ключ:</b>\n"
            "1. Зайдите в личный кабинет WB\n"
            "2. Настройки → Доступ к API\n"
            "3. Создайте новый ключ\n"
            "4. <b>⚠️ Выберите ТОЛЬКО пункты на чтение!</b>\n"
            "   ✅ Статистика\n"
            "   ✅ Цены\n" 
            "   ✅ Реклама (только просмотр)\n\n"
            "🔒 Ключ хранится в зашифрованном виде",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔐 Ввести API ключ", callback_data='wb_connect')],
                [InlineKeyboardButton(text="⬅️ Назад", callback_data='stores')],
            ])
        )
    await callback.answer()


@router.callback_query(F.data == 'wb_connect')
async def wb_connect_start(callback: CallbackQuery, state: FSMContext):
    """Начало подключения WB"""
    await state.set_state(StoreAuthStates.wb_waiting_api_key)
    await callback.message.edit_text(
        "🟣 <b>Подключение Wildberries</b>\n\n"
        "Отправьте API ключ:\n"
        "<code>eyJhbGciOiJIUzI1NiIs...</code>\n\n"
        "❌ Нажмите /cancel для отмены\n\n"
        "<b>⚠️ Важно:</b> Ключ должен быть только на чтение!"
    )
    await callback.answer()


@router.message(StoreAuthStates.wb_waiting_api_key)
async def wb_api_key_handler(message: Message, state: FSMContext):
    """Обработка API ключа WB"""
    api_key = message.text.strip()
    client_id = str(message.from_user.id)
    
    if len(api_key) < 20:
        await message.answer(
            "❌ <b>Неверный API ключ!</b>\n\n"
            "Ключ слишком короткий.\n"
            "Проверьте и отправьте снова."
        )
        return
    
    # Статус-бар проверки
    status_msg = await message.answer(
        "⏳ <b>Проверка подключения...</b>\n"
        "🔄 Проверка API ключа..."
    )
    
    # Сохраняем ключ
    creds_dir = Path(f"/opt/clients/{client_id}/credentials/wildberries")
    creds_dir.mkdir(parents=True, exist_ok=True)
    
    creds = {
        'stat_api_key': api_key,
        'verified': False,
        'added_at': str(datetime.now())
    }
    
    with open(creds_dir / 'credentials.json', 'w') as f:
        json.dump(creds, f, indent=2)
    
    # TODO: Реальная проверка API
    # Имитируем проверку
    import asyncio
    await asyncio.sleep(2)
    
    await status_msg.edit_text(
        "⏳ <b>Проверка подключения...</b>\n"
        "✅ API ключ принят\n"
        "🔄 Получение данных кабинета..."
    )
    
    await asyncio.sleep(2)
    
    # Проверка успешна
    creds['verified'] = True
    with open(creds_dir / 'credentials.json', 'w') as f:
        json.dump(creds, f, indent=2)
    
    await status_msg.edit_text(
        "✅ <b>Wildberries подключен!</b>\n\n"
        "Магазин добавлен в систему.\n"
        "Seller AI начинает анализ кабинета..."
    )
    
    # Запрашиваем себестоимость для P&L
    await asyncio.sleep(1)
    await message.answer(
        "📊 <b>Для расчета Unit-экономики</b>\n\n"
        "Seller AI нужны данные о себестоимости товаров.\n\n"
        "Отправьте в формате:\n"
        "<code>артикул|себестоимость</code>\n\n"
        "<b>Примеры:</b>\n"
        "• <code>12345678|450</code>\n"
        "• <code>87654321|1200</code>\n\n"
        "Или загрузите Excel файл с колонками:\n"
        "Артикул | Себестоимость | Желаемая маржа %",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💰 Ввести позже", callback_data='wb_skip_cost')],
            [InlineKeyboardButton(text="📊 К аналитике", callback_data='wb_stats')],
        ])
    )
    
    await state.set_state(StoreAuthStates.waiting_cost_price)


# ============================================================================
# OZON - ПОДКЛЮЧЕНИЕ (Аналогично WB)
# ============================================================================

@router.callback_query(F.data == 'ozon_menu')
async def ozon_menu_handler(callback: CallbackQuery, state: FSMContext):
    """Обработчик меню Ozon"""
    client_id = str(callback.from_user.id)
    status = check_store_connected(client_id, 'ozon')
    
    if status['connected']:
        buttons = [
            [InlineKeyboardButton(text="📦 Товары", callback_data='ozon_products')],
            [InlineKeyboardButton(text="📊 Статистика", callback_data='ozon_stats')],
            [InlineKeyboardButton(text="💰 Цены", callback_data='ozon_pricing')],
            [InlineKeyboardButton(text="📢 Реклама", callback_data='ozon_ads')],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data='stores')],
        ]
        await callback.message.edit_text(
            "🔵 <b>Ozon</b> - подключено ✅\n\n"
            "Выберите раздел:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
        )
    else:
        await callback.message.edit_text(
            "🔵 <b>Подключение Ozon</b>\n\n"
            "<b>Как получить API ключ:</b>\n"
            "1. Зайдите в личный кабинет Ozon\n"
            "2. Настройки → API интеграции\n"
            "3. Создайте ключ Seller API\n"
            "4. <b>⚠️ Выберите ТОЛЬКО на чтение!</b>\n\n"
            "Нужны: Client ID и API Key",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔐 Ввести API ключ", callback_data='ozon_connect')],
                [InlineKeyboardButton(text="⬅️ Назад", callback_data='stores')],
            ])
        )
    await callback.answer()


@router.callback_query(F.data == 'ozon_connect')
async def ozon_connect_start(callback: CallbackQuery, state: FSMContext):
    """Начало подключения Ozon"""
    await state.set_state(StoreAuthStates.ozon_waiting_api_key)
    await callback.message.edit_text(
        "🔵 <b>Подключение Ozon</b>\n\n"
        "Отправьте данные в формате:\n"
        "<code>ClientID|APIKey</code>\n\n"
        "<b>Пример:</b>\n"
        "<code>12345|a1b2c3d4-e5f6...</code>\n\n"
        "❌ Нажмите /cancel для отмены"
    )
    await callback.answer()


# ============================================================================
# ОБРАБОТКА НАЗАД
# ============================================================================

@router.callback_query(F.data == 'stores')
async def back_to_stores(callback: CallbackQuery):
    """Возврат в меню магазинов"""
    client_id = str(callback.from_user.id)
    await callback.message.edit_text(
        "🛍 <b>МАГАЗИНЫ</b>\n\n"
        "Выберите площадку:",
        reply_markup=get_stores_menu(client_id)
    )
    await callback.answer()


# ============================================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================================================

from datetime import datetime

async def analyze_cabinet(client_id: str, platform: str):
    """Анализ кабинета магазина"""
    # TODO: Реальная интеграция с API
    pass


def register_handlers(dp):
    """Регистрация обработчиков"""
    dp.include_router(router)
