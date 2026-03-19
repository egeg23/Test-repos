# mpstats_handler.py - Управление Mpstats авторизацией
"""
Команды для работы с Mpstats:
/mpstats_login - сохранить логин/пароль
/mpstats_status - проверить авторизацию
/mpstats_logout - выйти
"""

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from modules.mpstats_auth import MpstatsAuthenticator
import logging

logger = logging.getLogger('mpstats_handler')
router = Router()

mpstats_auth = MpstatsAuthenticator("/opt/clients")


@router.message(Command("mpstats_login"))
async def cmd_mpstats_login(message: Message):
    """Начать авторизацию в Mpstats"""
    await message.answer(
        "🔐 <b>Авторизация в Mpstats</b>\n\n"
        "Отправьте логин и пароль в формате:\n"
        "<code>/mpstats_auth your@email.com your_password</code>\n\n"
        "⚠️ Данные будут сохранены для автоматического входа.\n"
        "Для каждого магазина (WB/Ozon) Mpstats авторизация одна."
    )


@router.message(Command("mpstats_auth"))
async def cmd_mpstats_auth(message: Message):
    """Сохраняет credentials и авторизуется"""
    user_id = str(message.from_user.id)
    
    # Парсим аргументы
    args = message.text.replace('/mpstats_auth', '').strip().split()
    
    if len(args) != 2:
        await message.answer(
            "❌ <b>Неверный формат</b>\n\n"
            "Используйте:\n"
            "<code>/mpstats_auth email@example.com password</code>"
        )
        return
    
    login, password = args[0], args[1]
    
    # Показываем процесс
    status_msg = await message.answer("🔄 Авторизация на Mpstats...")
    
    # Пробуем авторизоваться
    success = mpstats_auth.login(user_id, login, password)
    
    if success:
        await status_msg.edit_text(
            "✅ <b>Авторизация успешна!</b>\n\n"
            "Теперь система может:\n"
            "• Анализировать цены конкурентов\n"
            "• Собирать данные по категориям\n"
            "• Строить прогнозы продаж\n\n"
            "Автоматический вход будет работать 24/7."
        )
        logger.info(f"✅ Mpstats auth success for {user_id}")
    else:
        await status_msg.edit_text(
            "❌ <b>Ошибка авторизации</b>\n\n"
            "Проверьте:\n"
            "• Правильность логина и пароля\n"
            "• Доступность сайта mpstats.io\n"
            "• Нет ли блокировки IP\n\n"
            "Попробуйте еще раз: /mpstats_login"
        )
        logger.error(f"❌ Mpstats auth failed for {user_id}")


@router.message(Command("mpstats_status"))
async def cmd_mpstats_status(message: Message):
    """Проверяет статус авторизации"""
    user_id = str(message.from_user.id)
    
    is_auth = mpstats_auth.is_authenticated(user_id)
    
    if is_auth:
        creds = mpstats_auth.load_credentials(user_id)
        login = creds['login'] if creds else "unknown"
        
        await message.answer(
            "✅ <b>Mpstats подключен</b>\n\n"
            f"Логин: <code>{login}</code>\n"
            f"Статус: Авторизован\n\n"
            "Система автоматически собирает данные."
        )
    else:
        await message.answer(
            "❌ <b>Mpstats не подключен</b>\n\n"
            "Для работы аналитики конкурентов нужна авторизация.\n\n"
            "Подключить: /mpstats_login"
        )


@router.message(Command("mpstats_logout"))
async def cmd_mpstats_logout(message: Message):
    """Выход из Mpstats"""
    user_id = str(message.from_user.id)
    
    # Удаляем сессию
    session_file = mpstats_auth._get_session_file(user_id)
    if session_file.exists():
        session_file.unlink()
    
    await message.answer(
        "🚪 <b>Выход выполнен</b>\n\n"
        "Сессия Mpstats удалена.\n"
        "Для повторного входа: /mpstats_login"
    )
    logger.info(f"🚪 Mpstats logout for {user_id}")


def register_handlers(dp):
    """Регистрация обработчиков"""
    dp.include_router(router)
    logger.info("✅ Обработчики Mpstats зарегистрированы")
