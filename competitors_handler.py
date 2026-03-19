# competitors_handler.py - Просмотр цен конкурентов через кнопки
"""
Интеграция с кнопками меню:
- Кнопка "🏆 Конкуренты" в аналитике
- Автоматически использует системную авторизацию Mpstats
"""

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
import logging
import asyncio

logger = logging.getLogger('competitors_handler')
router = Router()

# Системный аккаунт для Mpstats (твои credentials)
SYSTEM_MPSTATS_LOGIN = "tai_yan@mail.ru"
SYSTEM_MPSTATS_PASSWORD = "Elizaweta2003*Mpstat2025"
SYSTEM_CLIENT_ID = "system_mpstats"


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
    
    # Показываем меню выбора
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔍 По nmId товара", callback_data='comp_search_by_id')],
        [InlineKeyboardButton(text="📁 Мои товары", callback_data='comp_my_products')],
        [InlineKeyboardButton(text="⭐ Топ конкурентов", callback_data='comp_top_competitors')],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data='analytics')],
    ])
    
    await callback.message.answer(
        "🏆 <b>Анализ конкурентов</b>\n\n"
        "Данные из Mpstats в реальном времени:\n"
        "• Цены конкурентов\n"
        "• Рейтинги и отзывы\n"
        "• Динамика продаж\n\n"
        "Выберите действие:",
        reply_markup=keyboard
    )


@router.callback_query(F.data == 'comp_search_by_id')
async def search_by_id(callback: CallbackQuery):
    """Поиск по nmId"""
    await callback.message.answer(
        "🔍 <b>Поиск товара по ID</b>\n\n"
        "Введите nmId (артикул WB):\n"
        "<code>12345678</code>\n\n"
        "Или отправьте ссылку на товар"
    )
    await callback.answer()


@router.message(Command("competitors"))
async def cmd_competitors(message: Message):
    """Команда для быстрого поиска (можно через кнопку тоже)"""
    user_id = str(message.from_user.id)
    
    args = message.text.replace('/competitors', '').strip().split()
    
    if not args:
        # Показываем кнопочное меню
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔍 Ввести nmId", callback_data='comp_search_by_id')],
            [InlineKeyboardButton(text="📋 Мои товары", callback_data='comp_my_products')],
        ])
        await message.answer(
            "🏆 <b>Анализ конкурентов</b>\n\n"
            "Данные предоставлены Mpstats",
            reply_markup=keyboard
        )
        return
    
    product_id = args[0]
    platform = args[1] if len(args) > 1 else "wb"
    
    await analyze_product(message, product_id, platform)


async def analyze_product(message_or_callback, product_id: str, platform: str = "wb"):
    """Анализирует товар и показывает отчет"""
    
    status_msg = await message_or_callback.answer(f"🔍 Анализ товара {product_id}...")
    
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
            
            await status_msg.edit_text(f"📊 Сбор данных {product_id}...")
            
            data = await parser.get_product_data(product_id, platform)
            
            if not data:
                await status_msg.edit_text(
                    f"❌ Товар <code>{product_id}</code> не найден\n\n"
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
                [InlineKeyboardButton(text="📊 График цен", callback_data=f'comp_chart_{product_id}')],
                [InlineKeyboardButton(text="💰 Установить цену", callback_data=f'set_price_{product_id}')],
                [InlineKeyboardButton(text="⬅️ Назад", callback_data='analytics_competitors')],
            ])
            
            await status_msg.edit_text(text, reply_markup=keyboard)
            logger.info(f"✅ Competitor analysis shown for {product_id}")
            
    except Exception as e:
        logger.error(f"❌ Analysis error: {e}")
        await status_msg.edit_text(f"❌ Ошибка анализа: {str(e)[:100]}")


def format_competitor_report(product_id: str, data: dict, platform: str) -> str:
    """Форматирует отчет о товаре"""
    
    text = f"🔍 <b>Анализ товара</b>\n\n"
    text += f"📦 ID: <code>{product_id}</code>\n"
    text += f"🛒 {platform.upper()}\n"
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
    await callback.answer("📊 График в разработке")


@router.callback_query(F.data == 'comp_my_products')
async def show_my_products(callback: CallbackQuery):
    """Показывает список товаров пользователя"""
    await callback.answer("📁 Загрузка товаров...")
    # TODO: Получить список товаров из API WB/Ozon
    await callback.message.answer(
        "📋 <b>Ваши товары</b>\n\n"
        "Здесь будет список ваших товаров\n"
        "из подключенных магазинов."
    )


@router.callback_query(F.data == 'comp_top_competitors')
async def show_top_competitors(callback: CallbackQuery):
    """Показывает топ конкурентов"""
    await callback.answer("⭐ Анализ топ конкурентов...")
    await callback.message.answer(
        "⭐ <b>Топ конкурентов</b>\n\n"
        "Здесь будет анализ ваших основных\n"
        "конкурентов по категориям."
    )


def register_handlers(dp):
    """Регистрация обработчиков"""
    dp.include_router(router)
    logger.info("✅ Обработчики competitors зарегистрированы")
