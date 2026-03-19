# competitors_handler.py - Просмотр цен конкурентов через кнопки
"""
Интеграция с кнопками меню:
- Кнопка "🏆 Конкуренты" в аналитике
- Поддержка WB и Ozon
- Автоматически использует системную авторизацию Mpstats
"""

from typing import Optional
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
import logging
import asyncio
import re

logger = logging.getLogger('competitors_handler')
router = Router()

# Системный аккаунт для Mpstats (твои credentials)
SYSTEM_MPSTATS_LOGIN = "tai_yan@mail.ru"
SYSTEM_MPSTATS_PASSWORD = "Elizaweta2003*Mpstat2025"
SYSTEM_CLIENT_ID = "system_mpstats"

# Хранилище временных данных пользователей
user_temp_data = {}


async def ensure_system_auth():
    """Убеждаемся что системная авторизация работает"""
    from modules.mpstats_auth import MpstatsAuthenticator
    from modules.mpstats_browser import MpstatsBrowserParser, PLAYWRIGHT_AVAILABLE
    
    auth = MpstatsAuthenticator("/opt/clients")
    
    # Проверяем есть ли сохраненная системная сессия
    if auth.is_authenticated(SYSTEM_CLIENT_ID):
        return True
    
    # Авторизуемся системным аккаунтом
    logger.info("🔐 Initializing system Mpstats auth...")
    success = auth.login(SYSTEM_CLIENT_ID, SYSTEM_MPSTATS_LOGIN, SYSTEM_MPSTATS_PASSWORD)
    
    if success:
        logger.info("✅ System Mpstats auth successful")
        # Создаем браузерную сессию тоже
        if PLAYWRIGHT_AVAILABLE:
            try:
                async with MpstatsBrowserParser("/opt/clients") as parser:
                    await parser.authenticate(SYSTEM_MPSTATS_LOGIN, SYSTEM_MPSTATS_PASSWORD)
                    await parser.save_session(SYSTEM_CLIENT_ID)
                    logger.info("✅ System browser session saved")
            except Exception as e:
                logger.warning(f"⚠️ Browser auth failed: {e}")
    
    return success


@router.callback_query(F.data == 'analytics_competitors')
async def show_competitors_menu(callback: CallbackQuery):
    """Показывает меню конкурентов (по кнопке)"""
    user_id = str(callback.from_user.id)
    
    # Проверяем/инициализируем системную авторизацию
    await callback.answer("⏳ Подключение к Mpstats...")
    
    is_auth = await ensure_system_auth()
    
    if not is_auth:
        await callback.message.answer(
            "❌ <b>Ошибка подключения к Mpstats</b>\n\n"
            "Системная авторизация недоступна.\n"
            "Обратитесь в поддержку."
        )
        return
    
    # Показываем меню выбора с поддержкой обеих платформ
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔍 По ID товара (WB)", callback_data='comp_search_wb')],
        [InlineKeyboardButton(text="🔍 По ID товара (Ozon)", callback_data='comp_search_ozon')],
        [InlineKeyboardButton(text="📁 Мои товары WB", callback_data='comp_my_products_wb')],
        [InlineKeyboardButton(text="📁 Мои товары Ozon", callback_data='comp_my_products_ozon')],
        [InlineKeyboardButton(text="⭐ Топ WB", callback_data='comp_top_wb'),
         InlineKeyboardButton(text="⭐ Топ Ozon", callback_data='comp_top_ozon')],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data='analytics')],
    ])
    
    await callback.message.answer(
        "🏆 <b>Анализ конкурентов</b>\n\n"
        "Данные из Mpstats в реальном времени:\n"
        "• Цены конкурентов\n"
        "• Рейтинги и отзывы\n"
        "• Динамика продаж\n\n"
        "Выберите маркетплейс:",
        reply_markup=keyboard
    )


@router.callback_query(F.data.startswith('comp_search_'))
async def search_by_platform(callback: CallbackQuery):
    """Поиск по ID с выбором платформы"""
    user_id = str(callback.from_user.id)
    platform = callback.data.replace('comp_search_', '')
    
    # Сохраняем выбранную платформу
    user_temp_data[user_id] = {'platform': platform, 'action': 'search'}
    
    platform_name = "🟣 Wildberries" if platform == "wb" else "🔵 Ozon"
    id_example = "12345678" if platform == "wb" else "123456789"
    
    await callback.message.answer(
        f"🔍 <b>Поиск товара ({platform_name})</b>\n\n"
        f"Введите ID товара:\n"
        f"<code>{id_example}</code>\n\n"
        f"Или отправьте ссылку на товар"
    )
    await callback.answer()


@router.callback_query(F.data.startswith('comp_my_products_'))
async def show_my_products_platform(callback: CallbackQuery):
    """Показывает товары пользователя для выбранной платформы"""
    platform = callback.data.replace('comp_my_products_', '')
    platform_name = "🟣 WB" if platform == "wb" else "🔵 Ozon"
    
    await callback.answer(f"Загрузка товаров {platform_name}...")
    
    # TODO: Загрузить реальные товары из API
    await callback.message.answer(
        f"📋 <b>Ваши товары ({platform_name})</b>\n\n"
        f"Здесь будет список ваших товаров\n"
        f"из подключенного магазина {platform.upper()}.\n\n"
        f"<i>Пока в разработке - используйте поиск по ID</i>"
    )


@router.callback_query(F.data.startswith('comp_top_'))
async def show_top_platform(callback: CallbackQuery):
    """Показывает топ конкурентов для платформы"""
    platform = callback.data.replace('comp_top_', '')
    platform_name = "🟣 WB" if platform == "wb" else "🔵 Ozon"
    
    await callback.answer(f"Анализ топа {platform_name}...")
    
    # TODO: Загрузить реальные топовые товары
    await callback.message.answer(
        f"⭐ <b>Топ конкурентов ({platform_name})</b>\n\n"
        f"Здесь будет анализ топовых\n"
        f"конкурентов на {platform.upper()}.\n\n"
        f"<i>Пока в разработке - используйте поиск по ID</i>"
    )


@router.message(Command("competitors"))
async def cmd_competitors(message: Message):
    """Команда для быстрого поиска с автоопределением платформы"""
    user_id = str(message.from_user.id)
    
    args = message.text.replace('/competitors', '').strip().split()
    
    if not args:
        # Показываем кнопочное меню с выбором платформы
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🟣 WB", callback_data='comp_search_wb'),
             InlineKeyboardButton(text="🔵 Ozon", callback_data='comp_search_ozon')],
        ])
        await message.answer(
            "🏆 <b>Анализ конкурентов</b>\n\n"
            "Выберите маркетплейс:",
            reply_markup=keyboard
        )
        return
    
    # Пробуем определить платформу из аргументов
    product_input = args[0]
    platform = "wb"  # по умолчанию
    
    # Если указан второй аргумент - это платформа
    if len(args) > 1 and args[1].lower() in ['wb', 'ozon']:
        platform = args[1].lower()
    else:
        # Пробуем определить по ссылке
        platform = detect_platform_from_url(product_input)
        # Извлекаем ID из ссылки если нужно
        product_id = extract_product_id(product_input, platform)
    
    product_id = extract_product_id(product_input, platform)
    
    if not product_id:
        await message.answer("❌ Не удалось определить ID товара")
        return
    
    await analyze_product(message, product_id, platform)


def detect_platform_from_url(url: str) -> str:
    """Определяет платформу по URL"""
    url_lower = url.lower()
    if 'ozon' in url_lower or 'ozon.ru' in url_lower:
        return 'ozon'
    elif 'wildberries' in url_lower or 'wb.ru' in url_lower:
        return 'wb'
    return 'wb'  # default


def extract_product_id(text: str, platform: str = 'wb') -> Optional[str]:
    """Извлекает ID товара из текста или ссылки"""
    # Убираем пробелы
    text = text.strip()
    
    # Пробуем найти числа в тексте
    numbers = re.findall(r'\d+', text)
    
    if not numbers:
        return None
    
    # Для WB: nmId обычно 8 цифр
    # Для Ozon: offer_id может быть разной длины
    if platform == 'wb':
        # Ищем 8-значное число
        for num in numbers:
            if len(num) == 8:
                return num
        # Если не нашли 8-значное, берем первое
        return numbers[0]
    else:  # ozon
        # Берем самое длинное число
        return max(numbers, key=len)


async def analyze_product(message_or_callback, product_id: str, platform: str = "wb"):
    """Анализирует товар и показывает отчет"""
    platform_name = "🟣 Wildberries" if platform == "wb" else "🔵 Ozon"
    
    status_msg = await message_or_callback.answer(f"🔍 Анализ {platform_name}:\n<code>{product_id}</code>")
    
    try:
        # Убеждаемся что системная авторизация работает
        is_auth = await ensure_system_auth()
        if not is_auth:
            await status_msg.edit_text("❌ Ошибка авторизации системы")
            return
        
        from modules.mpstats_browser import MpstatsBrowserParser, PLAYWRIGHT_AVAILABLE
        
        if not PLAYWRIGHT_AVAILABLE:
            await status_msg.edit_text("❌ Browser parser not available")
            return
        
        async with MpstatsBrowserParser("/opt/clients") as parser:
            # Загружаем системную сессию
            session_loaded = await parser.load_session(SYSTEM_CLIENT_ID)
            
            if not session_loaded:
                # Переавторизуемся
                await status_msg.edit_text("🔐 Авторизация...")
                auth_success = await parser.authenticate(SYSTEM_MPSTATS_LOGIN, SYSTEM_MPSTATS_PASSWORD)
                if not auth_success:
                    await status_msg.edit_text("❌ Ошибка авторизации")
                    return
            
            await status_msg.edit_text(f"📊 Сбор данных {platform_name}...")
            
            data = await parser.get_product_data(product_id, platform)
            
            if not data:
                await status_msg.edit_text(
                    f"❌ Товар не найден\n\n"
                    f"Платформа: {platform_name}\n"
                    f"ID: <code>{product_id}</code>\n\n"
                    f"Проверьте правильность ID"
                )
                return
            
            # Сохраняем сессию
            await parser.save_session(SYSTEM_CLIENT_ID)
            
            # Формируем отчет
            text = format_competitor_report(product_id, data, platform)
            
            # Кнопки действий
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔄 Обновить", callback_data=f'comp_analyze_{product_id}_{platform}')],
                [InlineKeyboardButton(text="📊 График цен", callback_data=f'comp_chart_{product_id}_{platform}')],
                [InlineKeyboardButton(text="🏆 Конкуренты", callback_data=f'comp_list_{product_id}_{platform}')],
                [InlineKeyboardButton(text="💰 Установить цену", callback_data=f'set_price_{product_id}_{platform}')],
                [InlineKeyboardButton(text="⬅️ Назад", callback_data='analytics_competitors')],
            ])
            
            await status_msg.edit_text(text, reply_markup=keyboard)
            logger.info(f"✅ Competitor analysis shown for {product_id} on {platform}")
            
    except Exception as e:
        logger.error(f"❌ Analysis error: {e}")
        await status_msg.edit_text(f"❌ Ошибка анализа: {str(e)[:100]}")


def format_competitor_report(product_id: str, data: dict, platform: str) -> str:
    """Форматирует отчет о товаре"""
    platform_name = "🟣 Wildberries" if platform == "wb" else "🔵 Ozon"
    platform_emoji = "🟣" if platform == "wb" else "🔵"
    
    text = f"{platform_emoji} <b>Анализ товара</b>\n\n"
    text += f"📦 ID: <code>{product_id}</code>\n"
    text += f"🛒 {platform_name}\n"
    text += f"📊 Mpstats\n\n"
    
    if data.get('name'):
        text += f"📋 <b>{data['name'][:60]}</b>\n\n"
    
    if data.get('price'):
        text += f"💰 <b>Цена: {data['price']:,.0f} ₽</b>\n"
    
    if data.get('rating'):
        stars = "⭐" * int(data['rating'])
        text += f"{stars} {data['rating']:.1f}/5\n"
    
    if data.get('reviews'):
        text += f"💬 {data['reviews']} отзывов\n"
    
    text += f"\n🕐 {data.get('extracted_at', 'только что')[:16]}"
    
    return text


@router.callback_query(F.data.startswith('comp_analyze_'))
async def callback_analyze(callback: CallbackQuery):
    """Обработка кнопки анализа"""
    parts = callback.data.split('_')
    if len(parts) >= 3:
        product_id = parts[2]
        platform = parts[3] if len(parts) > 3 else "wb"
        await analyze_product(callback, product_id, platform)
    await callback.answer()


@router.callback_query(F.data.startswith('comp_chart_'))
async def show_chart(callback: CallbackQuery):
    """Показывает график цен"""
    parts = callback.data.split('_')
    platform = parts[3] if len(parts) > 3 else "wb"
    platform_name = "🟣 WB" if platform == "wb" else "🔵 Ozon"
    await callback.answer(f"📊 График {platform_name} в разработке")


@router.callback_query(F.data.startswith('comp_list_'))
async def show_competitors_list(callback: CallbackQuery):
    """Показывает список конкурентов"""
    parts = callback.data.split('_')
    if len(parts) >= 3:
        product_id = parts[2]
        platform = parts[3] if len(parts) > 3 else "wb"
        platform_name = "🟣 WB" if platform == "wb" else "🔵 Ozon"
        
        await callback.answer(f"🏆 Загрузка конкурентов {platform_name}...")
        
        # TODO: Вызвать парсер конкурентов
        from modules.mpstats_competitors import MpstatsCompetitorParser
        
        parser = MpstatsCompetitorParser("/opt/clients")
        # Здесь можно вызвать async метод
        
        await callback.message.answer(
            f"🏆 <b>Конкуренты ({platform_name})</b>\n\n"
            f"Товар: <code>{product_id}</code>\n\n"
            f"<i>Загрузка списка конкурентов...</i>"
        )


def register_handlers(dp):
    """Регистрация обработчиков"""
    dp.include_router(router)
    logger.info("✅ Обработчики competitors зарегистрированы (WB + Ozon)")
