# competitors_handler.py - Просмотр цен конкурентов
"""
Команда:
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
    
    status_msg = await message.answer(f"🔍 Ищу данные для товара {product_id}...")
    
    try:
        from modules.mpstats_auth import MpstatsAuthenticator
        auth = MpstatsAuthenticator("/opt/clients")
        
        if not auth.is_authenticated(user_id):
            await status_msg.edit_text(
                "❌ <b>Требуется авторизация</b>\n\n"
                "Для просмотра цен конкурентов нужно авторизоваться в Mpstats:\n"
                "/mpstats_login"
            )
            return
        
        # Используем браузерный парсер
        try:
            from modules.mpstats_browser import MpstatsBrowserParser, PLAYWRIGHT_AVAILABLE
            
            if PLAYWRIGHT_AVAILABLE:
                async with MpstatsBrowserParser("/opt/clients") as parser:
                    creds = auth.load_credentials(user_id)
                    if not creds:
                        await status_msg.edit_text("❌ Credentials not found")
                        return
                    
                    await status_msg.edit_text("🔐 Авторизация в Mpstats...")
                    
                    # Пробуем загрузить сессию или авторизоваться
                    if not await parser.load_session(user_id):
                        auth_success = await parser.authenticate(creds['login'], creds['password'])
                        if not auth_success:
                            await status_msg.edit_text(
                                "❌ <b>Ошибка авторизации</b>\n\n"
                                "Попробуйте заново: /mpstats_login"
                            )
                            return
                    
                    await status_msg.edit_text(f"🔍 Загрузка данных товара {product_id}...")
                    
                    data = await parser.get_product_data(product_id, platform)
                    
                    if not data:
                        await status_msg.edit_text(
                            "❌ <b>Товар не найден</code>\n\n"
                            f"Проверьте правильность nmId: {product_id}"
                        )
                        return
                    
                    # Сохраняем сессию
                    await parser.save_session(user_id)
                    
                    # Формируем отчет
                    text = format_competitor_report(product_id, data, [], platform)
                    
                    keyboard = InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="🔄 Обновить", callback_data=f'comp_refresh_{product_id}_{platform}')],
                    ])
                    
                    await status_msg.edit_text(text, reply_markup=keyboard)
                    return
            
        except Exception as e:
            logger.error(f"Browser parsing failed: {e}")
            await status_msg.edit_text(f"❌ Ошибка: {str(e)[:200]}")
        
    except Exception as e:
        logger.error(f"❌ Competitors command error: {e}")
        await status_msg.edit_text(f"❌ Ошибка: {str(e)[:200]}")


def format_competitor_report(product_id: str, data: dict, competitors: list, platform: str) -> str:
    """Форматирует отчет о конкурентах"""
    
    text = f"🔍 <b>Анализ товара</b>\n\n"
    text += f"📦 ID: <code>{product_id}</code>\n"
    text += f"🛒 Площадка: {platform.upper()}\n\n"
    
    if data.get('name'):
        text += f"📋 <b>{data['name'][:50]}</b>\n"
    
    if data.get('price'):
        text += f"💰 Цена: <b>{data['price']:,.0f} ₽</b>\n"
    
    if data.get('rating'):
        text += f"⭐ Рейтинг: {data['rating']:.1f}\n"
    
    text += f"\n🕐 Обновлено: {data.get('extracted_at', 'только что')[:16]}"
    
    return text


@router.callback_query(F.data.startswith('comp_refresh_'))
async def refresh_competitors(callback: CallbackQuery):
    """Обновить данные"""
    await callback.answer("Обновление...")


def register_handlers(dp):
    """Регистрация обработчиков"""
    dp.include_router(router)
    logger.info("✅ Обработчики competitors зарегистрированы")
