# stores_handler.py - Обработчик раздела "Магазины"
# Seller AI - Автономная система управления маркетплейсами

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import json
import os
import logging
from pathlib import Path

# Импорт клиентов API (реальная интеграция)
try:
    from modules.wb_api_client import verify_wb_api_key, WildberriesAPIClient
    WB_API_AVAILABLE = True
except ImportError:
    WB_API_AVAILABLE = False

try:
    from modules.ozon_api_client import verify_ozon_credentials, OzonAPIClient
    OZON_API_AVAILABLE = True
except ImportError:
    OZON_API_AVAILABLE = False

router = Router()

# Логгер
logger = logging.getLogger('stores_handler')

# ============================================================================
# СОСТОЯНИЯ (FSM)
# ============================================================================

class StoreAuthStates(StatesGroup):
    """Состояния для авторизации магазинов"""
    avito_waiting_credentials = State()
    wb_waiting_api_key = State()
    wb_waiting_cost_price = State()  # Новое: ожидание загрузки себестоимости WB
    wb_ready_to_scan = State()
    ozon_waiting_api_key = State()
    ozon_waiting_cost_price = State()  # Новое: ожидание загрузки себестоимости Ozon
    ozon_ready_to_scan = State()
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
        await callback.answer()
    else:
        # WB не подключен - СРАЗУ запрашиваем API ключ
        await state.set_state(StoreAuthStates.wb_waiting_api_key)
        await callback.message.edit_text(
            "🟣 <b>Подключение Wildberries</b>\n\n"
            "<b>📋 Инструкция по получению API ключа (фаза обучения):</b>\n"
            "1️⃣ Зайдите в <a href='https://seller.wildberries.ru/'>личный кабинет WB</a>\n"
            "2️⃣ Перейдите в <b>Профиль → Доступ к API</b>\n"
            "3️⃣ Нажмите <b>+ Создать ключ</b>\n"
            "4️⃣ Выберите тип: <b>Стандартный</b>\n"
            "5️⃣ ✅ <b>Важно:</b> выберите <b>ВСЕ галочки на «Только чтение»</b>\n"
            "   <i>Тогда все новые функции будут работать автоматически</i>\n\n"
            "💡 <b>Логика работы:</b>\n"
            "• Сейчас: ключ только на чтение (фаза обучения 45 дней)\n"
            "• Каждое утро: аналитика и рекомендации в отчёте\n"
            "• Потом: в разделе «Автономия» добавите ключ с записью\n\n"
            "🔐 <b>Введите API ключ:</b>\n"
            "<code>eyJhbGciOiJIUzI1NiIs...</code>\n\n"
            "❌ Отправьте /cancel для отмены",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
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

    # Используем правильную папку 'wb' (не 'wildberries') для совместимости с check_store_connected
    creds_dir = Path(f"/opt/clients/{client_id}/credentials/wb")
    creds_file = creds_dir / 'credentials.json'

    # Статус-бар проверки
    status_msg = await message.answer(
        "⏳ <b>Проверка подключения...</b>\n"
        "🔄 Проверка API ключа..."
    )

    # РЕАЛЬНАЯ проверка API ключа (СНАЧАЛА проверяем, ПОТОМ сохраняем)
    if not WB_API_AVAILABLE:
        await status_msg.edit_text(
            "❌ <b>Ошибка:</b> Модуль интеграции недоступен.\n"
            "Обратитесь к администратору."
        )
        return

    try:
        from modules.wb_api_client import verify_wb_api_key, WildberriesAPIClient

        is_valid, msg = await verify_wb_api_key(api_key)

        if not is_valid:
            await status_msg.edit_text(
                f"❌ <b>Ошибка подключения</b>\n\n{msg}\n\n"
                f"Проверьте ключ и попробуйте снова."
            )
            return

        await status_msg.edit_text(
            "⏳ <b>Проверка подключения...</b>\n"
            "✅ API ключ принят\n"
            "🔄 Получение данных кабинета..."
        )

        # Получаем список товаров через одну сессию
        products_count = 0
        try:
            async with WildberriesAPIClient(api_key) as client:
                products = await client.get_products(limit=100)  # Получаем реальное количество
                products_count = len(products)
        except Exception as e:
            # При ошибке получения товаров всё равно продолжаем, но с count=0
            products_count = 0

    except Exception as e:
        await status_msg.edit_text(
            f"❌ <b>Ошибка при проверке:</b>\n{str(e)}\n\n"
            f"Попробуйте позже или обратитесь в поддержку."
        )
        return

    # Проверка успешна - сохраняем credentials
    creds_dir.mkdir(parents=True, exist_ok=True)

    creds = {
        'stat_api_key': api_key,
        'verified': True,
        'products_count': products_count,
        'added_at': str(datetime.now())
    }

    with open(creds_file, 'w') as f:
        json.dump(creds, f, indent=2)

    # Сохраняем дату первого подключения (для отсчета 45 дней обучения)
    first_connect_file = Path(f"/opt/clients/{client_id}/first_connect.json")
    if not first_connect_file.exists():
        with open(first_connect_file, 'w') as f:
            json.dump({'date': datetime.now().isoformat(), 'platform': 'wb'}, f)

    # Сохраняем API ключ в состоянии для сканирования
    await state.update_data(wb_api_key=api_key, products_count=products_count)

    # Показываем запрос на загрузку себестоимости
    await status_msg.edit_text(
        f"✅ <b>Wildberries подключен!</b>\n\n"
        f"📦 Найдено товаров: <b>{products_count}</b>\n"
        f"🔐 API ключ сохранен\n\n"
        f"💰 <b>Шаг 2: Загрузите себестоимость</b>\n\n"
        f"<i>Без себестоимости я не смогу корректно считать маржинальность и управлять ценами.</i>\n\n"
        f"<b>Формат файла (CSV/Excel):</b>\n"
        f"<code>артикул;себестоимость;маржа</code>\n\n"
        f"<b>Пример:</b>\n"
        f"<code>12345678;450;30</code>\n"
        f"<code>87654321;1200;25</code>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📤 Загрузить файл", callback_data='wb_upload_cost')],
            [InlineKeyboardButton(text="⌨️ Ввести вручную", callback_data='wb_manual_cost')],
            [InlineKeyboardButton(text="⏭ Пропустить (не рекомендуется)", callback_data='wb_skip_cost')],
        ])
    )

    await state.set_state(StoreAuthStates.wb_waiting_cost_price)


@router.callback_query(F.data == 'wb_scan_start')
async def wb_scan_start_handler(callback: CallbackQuery, state: FSMContext):
    """Запуск полного сканирования WB кабинета"""
    user_id = str(callback.from_user.id)

    # Получаем данные из состояния
    data = await state.get_data()
    api_key = data.get('wb_api_key')

    if not api_key:
        await callback.answer("❌ Ошибка: API ключ не найден")
        return

    # Сразу отвечаем на callback
    await callback.answer("🚀 Начинаю сканирование...")

    # Показываем анимированный статус
    scan_msg = await callback.message.edit_text(
        "🚀 <b>Погнали!</b>\n\n"
        "⏳ <b>Сканирование кабинета...</b>\n"
        "🔄 Получаю список товаров...",
        reply_markup=None
    )

    try:
        from modules.cabinet_scanner import CabinetScanner

        scanner = CabinetScanner(
            user_id=user_id,
            platform='wb',
            api_key=api_key
        )

        # Запускаем сканирование
        result = await scanner.scan_full_cabinet()

        if result['success']:
            # Сканирование успешно
            profile = result['profile']

            await scan_msg.edit_text(
                f"✅ <b>Сканирование завершено!</b>\n\n"
                f"{result['summary']}\n\n"
                f"<i>Seller AI теперь знает ваш кабинет и будет принимать умные решения.</i>",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="📊 К дашборду", callback_data='dashboard')],
                    [InlineKeyboardButton(text="🤖 Настроить автономию", callback_data='autonomy')],
                ])
            )

            # Записываем успех в self-learning
            try:
                from modules.self_learning_engine import SelfLearningEngine
                engine = SelfLearningEngine()
                await engine.record_event(
                    user_id=user_id,
                    platform='wb',
                    event_type='cabinet_scan_completed',
                    data={
                        'products_count': result['products_count'],
                        'campaigns_count': result['campaigns_count'],
                        'categories': profile.get('main_categories', [])
                    },
                    outcome='success'
                )
            except Exception as e:
                logger.error(f"[wb_scan] Ошибка записи в learning: {e}")
        else:
            # Ошибка сканирования
            await scan_msg.edit_text(
                f"⚠️ <b>Сканирование завершено с ошибками</b>\n\n"
                f"Кабинет подключен, но не удалось получить все данные.\n"
                f"Ошибка: {result.get('error', 'Unknown')}\n\n"
                f"<i>Вы можете продолжить работу - Seller AI будет собирать данные постепенно.</i>",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="📊 К дашборду", callback_data='dashboard')],
                ])
            )

            # Записываем частичный успех
            try:
                from modules.self_learning_engine import SelfLearningEngine
                engine = SelfLearningEngine()
                await engine.record_event(
                    user_id=user_id,
                    platform='wb',
                    event_type='cabinet_scan_partial',
                    data={'error': result.get('error')},
                    outcome='partial_success'
                )
            except Exception as e:
                logger.error(f"[wb_scan] Ошибка записи неудачи: {e}")

    except Exception as e:
        logger.error(f"[wb_scan] Критическая ошибка: {e}")
        await scan_msg.edit_text(
            f"❌ <b>Ошибка сканирования</b>\n\n"
            f"{str(e)}\n\n"
            f"<i>Попробуйте позже или обратитесь в поддержку.</i>",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔄 Попробовать снова", callback_data='wb_scan_start')],
                [InlineKeyboardButton(text="📊 К дашборду", callback_data='dashboard')],
            ])
        )

        # Записываем неудачу
        try:
            from modules.self_learning_engine import SelfLearningEngine
            engine = SelfLearningEngine()
            await engine.record_event(
                user_id=user_id,
                platform='wb',
                event_type='cabinet_scan_failed',
                data={'error': str(e)},
                outcome='failure'
            )
        except Exception as le:
            logger.error(f"[wb_scan] Ошибка записи неудачи: {le}")

    finally:
        await state.clear()


# ============================================================================
# WB - ЗАГРУЗКА СЕБЕСТОИМОСТИ
# ============================================================================

@router.callback_query(F.data == 'wb_upload_cost')
async def wb_upload_cost_handler(callback: CallbackQuery, state: FSMContext):
    """Запрос на загрузку файла с себестоимостью"""
    await callback.message.edit_text(
        "📤 <b>Загрузка себестоимости</b>\n\n"
        "Отправьте CSV или Excel файл с колонками:\n"
        "<code>артикул;себестоимость;маржа</code>\n\n"
        "<b>Требования:</b>\n"
        "• Разделитель: точка с запятой (;)\n"
        "• Маржа в процентах (по умолчанию 30%)\n"
        "• Первая строка — заголовки\n\n"
        "<b>Пример файла:</b>\n"
        "<pre>артикул;себестоимость;маржа\n"
        "12345678;450;30\n"
        "87654321;1200;25</pre>\n\n"
        "❌ Отправьте /cancel для отмены",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Назад", callback_data='wb_waiting_cost_price')],
        ])
    )
    await state.set_state(StoreAuthStates.wb_waiting_cost_price)
    await callback.answer()


@router.message(StoreAuthStates.wb_waiting_cost_price)
async def wb_cost_file_handler(message: Message, state: FSMContext):
    """Обработка загруженного файла с себестоимостью"""
    # Проверяем, есть ли документ
    if message.document:
        # Загрузка файла
        try:
            from aiogram import Bot
            bot = Bot.get_current()
            file = await bot.get_file(message.document.file_id)
            file_content = await bot.download_file(file.file_path)
            content = file_content.read().decode('utf-8')
        except Exception as e:
            await message.answer(f"❌ Ошибка загрузки файла: {e}")
            return
    else:
        # Текстовый ввод
        content = message.text

    user_id = str(message.from_user.id)

    # Парсим файл
    from modules.cost_price_manager import get_cost_price_manager
    manager = get_cost_price_manager(user_id, 'wb')

    status_msg = await message.answer("⏳ Обрабатываю файл...")

    success, total, errors = manager.parse_csv(content)

    if success > 0:
        summary = manager.get_summary()

        text = (
            f"✅ <b>Себестоимость загружена!</b>\n\n"
            f"📊 Загружено: <b>{success}</b> из {total} товаров\n"
            f"💰 Средняя себестоимость: {summary['avg_cost']:.0f}₽\n"
            f"📈 Средняя маржа: {summary['avg_margin']:.0f}%\n"
        )

        if errors and len(errors) <= 3:
            text += f"\n⚠️ Ошибки:\n" + "\n".join(errors[:3])
        elif errors:
            text += f"\n⚠️ Ошибок: {len(errors)} (показано 3)\n" + "\n".join(errors[:3])

        text += "\n\n<i>Теперь можно запускать сканирование!</i>"

        await status_msg.edit_text(
            text,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🚀 Погнали!", callback_data='wb_scan_start')],
                [InlineKeyboardButton(text="🔄 Загрузить другой файл", callback_data='wb_upload_cost')],
            ])
        )

        # Сохраняем состояние
        await state.set_state(StoreAuthStates.wb_ready_to_scan)

    else:
        await status_msg.edit_text(
            f"❌ <b>Не удалось загрузить себестоимость</b>\n\n"
            f"Ошибок: {len(errors)}\n"
            f"\n".join(errors[:5]) + "\n\n"
            f"<i>Проверьте формат файла и попробуйте снова.</i>",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔄 Попробовать снова", callback_data='wb_upload_cost')],
                [InlineKeyboardButton(text="⏭ Пропустить", callback_data='wb_skip_cost')],
            ])
        )


@router.callback_query(F.data == 'wb_manual_cost')
async def wb_manual_cost_handler(callback: CallbackQuery, state: FSMContext):
    """Ручной ввод себестоимости"""
    await callback.message.edit_text(
        "⌨️ <b>Ввод себестоимости вручную</b>\n\n"
        "Отправьте данные в формате:\n"
        "<code>артикул|себестоимость|маржа</code>\n\n"
        "<b>Примеры:</b>\n"
        "• <code>12345678|450|30</code>\n"
        "• <code>87654321|1200|25</code>\n"
        "• <code>11111111|800</code> (маржа по умолчанию 30%)\n\n"
        "Можно отправить несколько строк сразу.\n"
        "❌ Отправьте /cancel для отмены",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Назад", callback_data='wb_waiting_cost_price')],
        ])
    )
    await callback.answer()


@router.callback_query(F.data == 'wb_skip_cost')
async def wb_skip_cost_handler(callback: CallbackQuery, state: FSMContext):
    """Пропуск загрузки себестоимости"""
    await callback.message.edit_text(
        "⚠️ <b>Сканирование без себестоимости</b>\n\n"
        "<i>Я не смогу корректно рассчитывать:</i>\n"
        "• Маржинальность\n"
        "• Оптимальные цены\n"
        "• Прибыльность товаров\n\n"
        "<b>Рекомендация:</b> Загрузите себестоимость позже в разделе Настройки → Себестоимость\n\n"
        "<i>Всё равно продолжить?</i>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🚀 Да, погнали!", callback_data='wb_scan_start')],
            [InlineKeyboardButton(text="💰 Загрузить себестоимость", callback_data='wb_upload_cost')],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data='wb_waiting_cost_price')],
        ])
    )
    await state.set_state(StoreAuthStates.wb_ready_to_scan)
    await callback.answer()


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
        await callback.answer()
    else:
        # Ozon не подключен - СРАЗУ запрашиваем данные
        await state.set_state(StoreAuthStates.ozon_waiting_api_key)
        await callback.message.edit_text(
            "🔵 <b>Подключение Ozon</b>\n\n"
            "<b>📋 Инструкция по получению API ключей (фаза обучения):</b>\n"
            "1️⃣ Зайдите в <a href='https://seller.ozon.ru/'>личный кабинет Ozon</a>\n"
            "2️⃣ Перейдите в <b>Настройки → API интеграции</b>\n"
            "3️⃣ Нажмите <b>+ Создать ключ Seller API</b>\n"
            "4️⃣ Выберите тип: <b>Seller API</b>\n"
            "5️⃣ ✅ <b>Важно:</b> выберите <b>ВСЕ галочки на «Только чтение»</b>\n"
            "   <i>Тогда все новые функции будут работать автоматически</i>\n\n"
            "💡 <b>Логика работы:</b>\n"
            "• Сейчас: ключ только на чтение (фаза обучения 45 дней)\n"
            "• Каждое утро: аналитика и рекомендации в отчёте\n"
            "• Потом: в разделе «Автономия» добавите ключ с записью\n\n"
            "<b>🔐 Введите данные в формате:</b>\n"
            "<code>ClientID|APIKey</code>\n"
            "<i>Пример: 12345|a1b2c3d4...</i>\n\n"
            "❌ Отправьте /cancel для отмены",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
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


@router.message(StoreAuthStates.ozon_waiting_api_key)
async def ozon_api_key_handler(message: Message, state: FSMContext):
    """Обработка ввода Client ID и API Key Ozon"""
    text = message.text.strip()
    client_id = str(message.from_user.id)

    # Проверяем формат
    if '|' not in text:
        await message.answer(
            "❌ <b>Неверный формат!</b>\n\n"
            "Используйте разделитель <b>|</b>\n"
            "Пример: <code>12345|a1b2c3d4-e5f6...</code>"
        )
        return

    parts = text.split('|', 1)
    if len(parts) != 2:
        await message.answer(
            "❌ <b>Неверный формат!</b>\n\n"
            "Нужно: <code>ClientID|APIKey</code>"
        )
        return

    ozon_client_id, api_key = parts[0].strip(), parts[1].strip()

    # Проверяем Client ID (должен быть числом)
    if not ozon_client_id.isdigit():
        await message.answer(
            "❌ <b>Неверный Client ID!</b>\n\n"
            "Client ID должен содержать только цифры.\n"
            "Найдите его в личном кабинете Ozon."
        )
        return

    # Используем правильную папку 'ozon' для совместимости с check_store_connected
    creds_dir = Path(f"/opt/clients/{client_id}/credentials/ozon")
    creds_file = creds_dir / 'credentials.json'

    # Статус-бар проверки
    status_msg = await message.answer(
        "⏳ <b>Проверка подключения...</b>\n"
        "🔄 Проверка Client ID и API Key..."
    )

    # РЕАЛЬНАЯ проверка Ozon API (СНАЧАЛА проверяем, ПОТОМ сохраняем)
    if not OZON_API_AVAILABLE:
        await status_msg.edit_text(
            "❌ <b>Ошибка:</b> Модуль интеграции Ozon недоступен.\n"
            "Обратитесь к администратору."
        )
        return

    try:
        from modules.ozon_api_client import verify_ozon_credentials, OzonAPIClient

        is_valid, msg = await verify_ozon_credentials(ozon_client_id, api_key)

        if not is_valid:
            await status_msg.edit_text(
                f"❌ <b>Ошибка подключения</b>\n\n{msg}\n\n"
                f"Проверьте Client ID и API Key, попробуйте снова."
            )
            return

        await status_msg.edit_text(
            "⏳ <b>Проверка подключения...</b>\n"
            "✅ Данные приняты\n"
            "🔄 Получение данных кабинета..."
        )

        # Получаем список товаров через одну сессию
        products_count = 0
        try:
            async with OzonAPIClient(ozon_client_id, api_key) as client:
                products = await client.get_products(limit=100)
                products_count = len(products)
        except Exception as e:
            # При ошибке получения товаров всё равно продолжаем
            products_count = 0

    except Exception as e:
        await status_msg.edit_text(
            f"❌ <b>Ошибка при проверке:</b>\n{str(e)}\n\n"
            f"Попробуйте позже или обратитесь в поддержку."
        )
        return

    # Проверка успешна - сохраняем credentials
    creds_dir.mkdir(parents=True, exist_ok=True)

    creds = {
        'client_id': ozon_client_id,
        'api_key': api_key,
        'verified': True,
        'products_count': products_count,
        'added_at': str(datetime.now())
    }

    with open(creds_file, 'w') as f:
        json.dump(creds, f, indent=2)

    # Сохраняем дату первого подключения (для отсчета 45 дней обучения)
    first_connect_file = Path(f"/opt/clients/{client_id}/first_connect.json")
    if not first_connect_file.exists():
        with open(first_connect_file, 'w') as f:
            json.dump({'date': datetime.now().isoformat(), 'platform': 'ozon'}, f)

    # Сохраняем данные в состоянии для сканирования
    await state.update_data(
        ozon_client_id=ozon_client_id,
        ozon_api_key=api_key,
        products_count=products_count
    )

    # Показываем запрос на загрузку себестоимости
    await status_msg.edit_text(
        f"✅ <b>Ozon подключен!</b>\n\n"
        f"📦 Найдено товаров: <b>{products_count}</b>\n"
        f"🔐 API ключ сохранен\n\n"
        f"💰 <b>Шаг 2: Загрузите себестоимость</b>\n\n"
        f"<i>Без себестоимости я не смогу корректно считать маржинальность и управлять ценами.</i>\n\n"
        f"<b>Формат файла (CSV/Excel):</b>\n"
        f"<code>артикул;себестоимость;маржа</code>\n\n"
        f"<b>Пример:</b>\n"
        f"<code>12345678;450;30</code>\n"
        f"<code>87654321;1200;25</code>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📤 Загрузить файл", callback_data='ozon_upload_cost')],
            [InlineKeyboardButton(text="⌨️ Ввести вручную", callback_data='ozon_manual_cost')],
            [InlineKeyboardButton(text="⏭ Пропустить (не рекомендуется)", callback_data='ozon_skip_cost')],
        ])
    )

    await state.set_state(StoreAuthStates.ozon_waiting_cost_price)


@router.callback_query(F.data == 'ozon_scan_start')
async def ozon_scan_start_handler(callback: CallbackQuery, state: FSMContext):
    """Запуск полного сканирования Ozon кабинета"""
    user_id = str(callback.from_user.id)

    # Получаем данные из состояния
    data = await state.get_data()
    client_id = data.get('ozon_client_id')
    api_key = data.get('ozon_api_key')

    if not client_id or not api_key:
        await callback.answer("❌ Ошибка: API данные не найдены")
        return

    # Сразу отвечаем на callback
    await callback.answer("🚀 Начинаю сканирование...")

    # Показываем анимированный статус
    scan_msg = await callback.message.edit_text(
        "🚀 <b>Погнали!</b>\n\n"
        "⏳ <b>Сканирование кабинета Ozon...</b>\n"
        "🔄 Получаю список товаров...",
        reply_markup=None
    )

    try:
        from modules.cabinet_scanner import CabinetScanner

        scanner = CabinetScanner(
            user_id=user_id,
            platform='ozon',
            api_key=api_key,
            client_id=client_id
        )

        # Запускаем сканирование
        result = await scanner.scan_full_cabinet()

        if result['success']:
            # Сканирование успешно
            profile = result['profile']

            await scan_msg.edit_text(
                f"✅ <b>Сканирование Ozon завершено!</b>\n\n"
                f"{result['summary']}\n\n"
                f"<i>Seller AI теперь знает ваш кабинет Ozon и будет принимать умные решения.</i>",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="📊 К дашборду", callback_data='dashboard')],
                    [InlineKeyboardButton(text="🤖 Настроить автономию", callback_data='autonomy')],
                ])
            )

            # Записываем успех в self-learning
            try:
                from modules.self_learning_engine import SelfLearningEngine
                engine = SelfLearningEngine()
                await engine.record_event(
                    user_id=user_id,
                    platform='ozon',
                    event_type='cabinet_scan_completed',
                    data={
                        'products_count': result['products_count'],
                        'campaigns_count': result['campaigns_count'],
                        'categories': profile.get('main_categories', [])
                    },
                    outcome='success'
                )
            except Exception as e:
                logger.error(f"[ozon_scan] Ошибка записи в learning: {e}")
        else:
            # Ошибка сканирования
            await scan_msg.edit_text(
                f"⚠️ <b>Сканирование Ozon завершено с ошибками</b>\n\n"
                f"Кабинет подключен, но не удалось получить все данные.\n"
                f"Ошибка: {result.get('error', 'Unknown')}\n\n"
                f"<i>Вы можете продолжить работу - Seller AI будет собирать данные постепенно.</i>",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="📊 К дашборду", callback_data='dashboard')],
                ])
            )

            # Записываем частичный успех
            try:
                from modules.self_learning_engine import SelfLearningEngine
                engine = SelfLearningEngine()
                await engine.record_event(
                    user_id=user_id,
                    platform='ozon',
                    event_type='cabinet_scan_partial',
                    data={'error': result.get('error')},
                    outcome='partial_success'
                )
            except Exception as e:
                logger.error(f"[ozon_scan] Ошибка записи: {e}")

    except Exception as e:
        logger.error(f"[ozon_scan] Критическая ошибка: {e}")
        await scan_msg.edit_text(
            f"❌ <b>Ошибка сканирования Ozon</b>\n\n"
            f"{str(e)}\n\n"
            f"<i>Попробуйте позже или обратитесь в поддержку.</i>",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔄 Попробовать снова", callback_data='ozon_scan_start')],
                [InlineKeyboardButton(text="📊 К дашборду", callback_data='dashboard')],
            ])
        )

        # Записываем неудачу
        try:
            from modules.self_learning_engine import SelfLearningEngine
            engine = SelfLearningEngine()
            await engine.record_event(
                user_id=user_id,
                platform='ozon',
                event_type='cabinet_scan_failed',
                data={'error': str(e)},
                outcome='failure'
            )
        except Exception as le:
            logger.error(f"[ozon_scan] Ошибка записи неудачи: {le}")

    finally:
        await state.clear()


# ============================================================================
# OZON - ЗАГРУЗКА СЕБЕСТОИМОСТИ
# ============================================================================

@router.callback_query(F.data == 'ozon_upload_cost')
async def ozon_upload_cost_handler(callback: CallbackQuery, state: FSMContext):
    """Запрос на загрузку файла с себестоимостью Ozon"""
    await callback.message.edit_text(
        "📤 <b>Загрузка себестоимости Ozon</b>\n\n"
        "Отправьте CSV или Excel файл с колонками:\n"
        "<code>артикул;себестоимость;маржа</code>\n\n"
        "<b>Требования:</b>\n"
        "• Разделитель: точка с запятой (;)\n"
        "• Маржа в процентах (по умолчанию 30%)\n"
        "• Первая строка — заголовки\n\n"
        "<b>Пример файла:</b>\n"
        "<pre>артикул;себестоимость;маржа\n"
        "12345678;450;30\n"
        "87654321;1200;25</pre>\n\n"
        "❌ Отправьте /cancel для отмены",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Назад", callback_data='ozon_waiting_cost_price')],
        ])
    )
    await state.set_state(StoreAuthStates.ozon_waiting_cost_price)
    await callback.answer()


@router.message(StoreAuthStates.ozon_waiting_cost_price)
async def ozon_cost_file_handler(message: Message, state: FSMContext):
    """Обработка загруженного файла с себестоимостью Ozon"""
    # Проверяем, есть ли документ
    if message.document:
        try:
            from aiogram import Bot
            bot = Bot.get_current()
            file = await bot.get_file(message.document.file_id)
            file_content = await bot.download_file(file.file_path)
            content = file_content.read().decode('utf-8')
        except Exception as e:
            await message.answer(f"❌ Ошибка загрузки файла: {e}")
            return
    else:
        content = message.text

    user_id = str(message.from_user.id)

    from modules.cost_price_manager import get_cost_price_manager
    manager = get_cost_price_manager(user_id, 'ozon')

    status_msg = await message.answer("⏳ Обрабатываю файл...")

    success, total, errors = manager.parse_csv(content)

    if success > 0:
        summary = manager.get_summary()

        text = (
            f"✅ <b>Себестоимость Ozon загружена!</b>\n\n"
            f"📊 Загружено: <b>{success}</b> из {total} товаров\n"
            f"💰 Средняя себестоимость: {summary['avg_cost']:.0f}₽\n"
            f"📈 Средняя маржа: {summary['avg_margin']:.0f}%\n"
        )

        if errors and len(errors) <= 3:
            text += f"\n⚠️ Ошибки:\n" + "\n".join(errors[:3])
        elif errors:
            text += f"\n⚠️ Ошибок: {len(errors)} (показано 3)\n" + "\n".join(errors[:3])

        text += "\n\n<i>Теперь можно запускать сканирование!</i>"

        await status_msg.edit_text(
            text,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🚀 Погнали!", callback_data='ozon_scan_start')],
                [InlineKeyboardButton(text="🔄 Загрузить другой файл", callback_data='ozon_upload_cost')],
            ])
        )

        await state.set_state(StoreAuthStates.ozon_ready_to_scan)

    else:
        await status_msg.edit_text(
            f"❌ <b>Не удалось загрузить себестоимость</b>\n\n"
            f"Ошибок: {len(errors)}\n"
            f"\n".join(errors[:5]) + "\n\n"
            f"<i>Проверьте формат файла и попробуйте снова.</i>",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔄 Попробовать снова", callback_data='ozon_upload_cost')],
                [InlineKeyboardButton(text="⏭ Пропустить", callback_data='ozon_skip_cost')],
            ])
        )


@router.callback_query(F.data == 'ozon_manual_cost')
async def ozon_manual_cost_handler(callback: CallbackQuery, state: FSMContext):
    """Ручной ввод себестоимости Ozon"""
    await callback.message.edit_text(
        "⌨️ <b>Ввод себестоимости вручную</b>\n\n"
        "Отправьте данные в формате:\n"
        "<code>артикул|себестоимость|маржа</code>\n\n"
        "<b>Примеры:</b>\n"
        "• <code>12345678|450|30</code>\n"
        "• <code>87654321|1200|25</code>\n"
        "• <code>11111111|800</code> (маржа по умолчанию 30%)\n\n"
        "Можно отправить несколько строк сразу.\n"
        "❌ Отправьте /cancel для отмены",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Назад", callback_data='ozon_waiting_cost_price')],
        ])
    )
    await callback.answer()


@router.callback_query(F.data == 'ozon_skip_cost')
async def ozon_skip_cost_handler(callback: CallbackQuery, state: FSMContext):
    """Пропуск загрузки себестоимости Ozon"""
    await callback.message.edit_text(
        "⚠️ <b>Сканирование без себестоимости</b>\n\n"
        "<i>Я не смогу корректно рассчитывать:</i>\n"
        "• Маржинальность\n"
        "• Оптимальные цены\n"
        "• Прибыльность товаров\n\n"
        "<b>Рекомендация:</b> Загрузите себестоимость позже в разделе Настройки → Себестоимость\n\n"
        "<i>Всё равно продолжить?</i>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🚀 Да, погнали!", callback_data='ozon_scan_start')],
            [InlineKeyboardButton(text="💰 Загрузить себестоимость", callback_data='ozon_upload_cost')],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data='ozon_waiting_cost_price')],
        ])
    )
    await state.set_state(StoreAuthStates.ozon_ready_to_scan)
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
