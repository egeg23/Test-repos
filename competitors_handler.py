# competitors_handler.py - Просмотр цен конкурентов
"""
Команды:
/competitors [nmId] - показать цены конкурентов с Mpstats
"""

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
import logging
import asyncio

logger = logging.getLogger('competitors_handler')
router = Router()


@router.message(Command("competitors"))
async def cmd_competitors(message: Message):
    """Показывает цены конкурентов"""
    user_id = str(message.from_user.id)
    
    # Парсим аргументы
    args = message.text.replace('/competitors', '').strip().split()
    
    if not args:
        await message.answer(
            "🔍 <b>Цены конкурентов</b>\n\n"
            "Использование:\n"
            "<code>/competitors 12345678</code>\n\n"
            "Где 12345678 — nmId товара на Wildberries\n\n"
            "Требуется авторизация в Mpstats:\n"
            "/mpstats_login"
        )
        return
    
    product_id = args[0]
    platform = args[1] if len(args) > 1 else "wb"
    
    # Показываем процесс
    status_msg = await message.answer(f"🔍 Ищу данные для товара {product_id}...")
    
    try:
        # Проверяем авторизацию
        from modules.mpstats_auth import MpstatsAuthenticator
        auth = MpstatsAuthenticator("/opt/clients")
        
        if not auth.is_authenticated(user_id):
            await status_msg.edit_text(
                "❌ <b>Требуется авторизация</b>\n\n"
                "Для просмотра цен конкурентов нужно авторизоваться в Mpstats:\n"
                "/mpstats_login"
            )
            return
        
        # Пробуем получить данные через браузер
        try:
            from modules.mpstats_browser import MpstatsBrowserParser, PLAYWRIGHT_AVAILABLE
            
            if PLAYWRIGHT_AVAILABLE:
                async with MpstatsBrowserParser("/opt/clients") as parser:
                    # Пробуем загрузить сохраненную сессию
                    session_loaded = await parser.load_session(user_id)
                    
                    if not session_loaded:
                        # Нужна новая авторизация
                        creds = auth.load_credentials(user_id)
                        if creds:
                            await status_msg.edit_text("🔐 Авторизация в Mpstats...")
                            auth_success = await parser.authenticate(creds['login'], creds['password'])
                            if not auth_success:
                                await status_msg.edit_text(
                                    "❌ <b>Ошибка авторизации</b>\n\n"
                                    "Попробуйте заново: /mpstats_login"
                                )
                                return
                    
                    await status_msg.edit_text(f"🔍 Загрузка данных товара {product_id}...")
                    
                    # Получаем данные
                    data = await parser.get_product_data(product_id, platform)
                    
                    if not data:
                        await status_msg.edit_text(
                            "❌ <b>Товар не найден</code>\n\n"
                            f"Проверьте правильность nmId: {product_id}"
                        )
                        return
                    
                    # Получаем цены конкурентов
                    competitors = await parser.get_competitor_prices(product_id, platform)
                    
                    # Сохраняем сессию
                    await parser.save_session(user_id)
                    
                    # Формируем ответ
                    text = format_competitor_report(product_id, data, competitors, platform)
                    
                    # Кнопки действий
                    keyboard = InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="🔄 Обновить", callback_data=f'comp_refresh_{product_id}_{platform}')],
                        [InlineKeyboardButton(text="💰 Установить цену", callback_data=f'set_price_{product_id}')],
                    ])
                    
                    await status_msg.edit_text(text, reply_markup=keyboard)
                    logger.info(f"✅ Competitor data shown for {product_id} to {user_id}")
                    return
            
        except Exception as e:
            logger.error(f"Browser parsing failed: {e}")
        
        # Fallback на простой парсинг
        await status_msg.edit_text(
            "⚠️ <b>Браузерный парсинг недоступен</b>\n\n"
            "Проверьте установку Playwright:\n"
            "<code>pip install playwright && playwright install chromium</code>"
        )
        
    except Exception as e:
        logger.error(f"❌ Competitors command error: {e}")
        await status_msg.edit_text(
            "❌ <b>Ошибка при получении данных</b>\n\n"
            f"<code>{str(e)[:200]}</code>"
        )


def format_competitor_report(product_id: str, data: dict, competitors: list, platform: str) -> str:
    """Форматирует отчет о конкурентах"""
    
    text = f"🔍 <b>Анализ конкурентов</b>\n\n"
    text += f"📦 Товар: <code>{product_id}</code>\n"
    text += f"🛒 Площадка: {platform.upper()}\n\n"
    
    # Данные о товаре
    if data.get('name'):
        text += f"📋 <b>{data['name'][:50]}</b>\n"
    
    if data.get('price'):
        text += f"💰 Цена: <b>{data['price']:,.0f} ₽</b>\n"
    
    if data.get('rating'):
        text += f"⭐ Рейтинг: {data['rating']:.1f}"
        if data.get('reviews'):
            text += f" ({data['reviews']} отзывов)"
        text += "\n"
    
    text += "\n"
    
    # Конкуренты
    if competitors:
        text += "🏆 <b>Конкуренты:</b>\n"
        
        # Сортируем по цене
        sorted_comp = sorted(competitors, key=lambda x: x.get('price', float('inf')))
        
        for i, comp in enumerate(sorted_comp[:5], 1):  # Топ 5
            price = comp.get('price', 0)
            seller = comp.get('seller', f'Продавец {i}')
            rating = comp.get('rating', '-')
            
            text += f"{i}. {price:,.0f} ₽ — {seller[:20]}"
            if rating != '-':
                text += f" ({rating}★)"
            text += "\n"
        
        # Статистика
        prices = [c.get('price', 0) for c in competitors if c.get('price')]
        if prices:
            text += f"\n📊 <b>Статистика цен:</b>\n"
            text += f"Мин: {min(prices):,.0f} ₽\n"
            text += f"Макс: {max(prices):,.0f} ₽\n"
            text += f"Средняя: {sum(prices)/len(prices):,.0f} ₽\n"
    else:
        text += "⚠️ Конкуренты не найдены\n"
    
    text += f"\n🕐 Обновлено: {data.get('extracted_at', 'только что')[:16]}"
    
    return text


@router.callback_query(F.data.startswith('comp_refresh_'))
async def refresh_competitors(callback: CallbackQuery):
    """Обновить данные"""
    # Парсим callback_data
    parts = callback.data.split('_')
    if len(parts) >= 4:
        product_id = parts[2]
        platform = parts[3] if len(parts) > 3 else "wb"
        
        await callback.message.edit_text(f"🔄 Обновление данных для {product_id}...")
        
        # Вызываем команду заново
        from aiogram.types import Message
        msg = callback.message
        msg.text = f"/competitors {product_id} {platform}"
        await cmd_competitors(msg)
    
    await callback.answer()


def register_handlers(dp):
    """Регистрация обработчиков"""
    dp.include_router(router)
    logger.info("✅ Обработчики competitors зарегистрированы")
