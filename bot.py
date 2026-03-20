#!/usr/bin/env python3
"""
Seller AI Bot - Главный файл
Автономная система управления продажами на маркетплейсах
"""

import asyncio
import logging
import sys
from pathlib import Path

from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command, CommandStart
from aiogram.enums import ParseMode

# Добавляем путь к модулям
sys.path.insert(0, str(Path(__file__).parent))

# Импорт системы очистки чата
from modules.chat_cleaner import chat_cleaner

# Database adapter (JSON → PostgreSQL migration)
from modules.db_adapter import db_adapter

# Импорт обработчиков
from notification_handler import register_handlers as register_notification_handlers
from settings_handler import register_handlers as register_settings_handlers
from recommendations_handler import register_handlers as register_recommendations_handlers
from ai_recommendations_handler import register_handlers as register_ai_recommendations_handlers
from stats_handler import register_handlers as register_stats_handlers
from content_handler import register_handlers as register_content_handlers
from pricing_handler import register_handlers as register_pricing_handlers
from ab_testing_handler import register_handlers as register_ab_testing_handlers
from mpstats_handler import register_handlers as register_mpstats_handlers
from competitors_handler import register_handlers as register_competitors_handlers
from fuck_mode_handler import register_handlers as register_fuck_mode_handlers
from cabinet_handler import register_handlers as register_cabinet_handlers
from stores_handler import router as stores_router
from enhanced_menus import get_main_menu

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Токен бота
BOT_TOKEN = "8552259512:AAGKEo5d0ZIKvWGjfv2r9HbndEWtMZNKc-c"

# Инициализация бота и диспетчера с HTML-форматированием по умолчанию
bot = Bot(token=BOT_TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher()

# ============================================================================
# ГЛАВНОЕ МЕНЮ
# ============================================================================

@dp.message(CommandStart())
async def cmd_start(message: Message):
    """Приветствие и главное меню + сохранение пользователя в БД"""
    user_id = message.from_user.id
    username = message.from_user.username or "друг"
    
    # Сохраняем пользователя в БД (JSON + PostgreSQL)
    try:
        user_data = {
            'id': user_id,
            'username': message.from_user.username,
            'first_name': message.from_user.first_name,
            'last_name': message.from_user.last_name,
            'registered_at': message.date.isoformat()
        }
        db_adapter.save_user(user_id, user_data)
        logger.info(f"User {user_id} saved to database")
    except Exception as e:
        logger.error(f"Failed to save user {user_id}: {e}")
        # Не прерываем работу бота если БД недоступна
    
    text = (
        f"👋 Привет, {username}!\n\n"
        f"🤖 <b>Seller AI</b> — ваш автономный помощник для продаж на маркетплейсах.\n\n"
        f"<b>Что умею:</b>\n"
        f"• 📊 Аналитика продаж\n"
        f"• 🧠 AI рекомендации по ценам и ДРР\n"
        f"• 📦 Прогнозирование запасов\n"
        f"• ✍️ Генерация контента для товаров\n"
        f"• 🔔 Уведомления о важных событиях\n\n"
        f"Используйте меню ниже:"
    )
    
    await message.answer(text, reply_markup=get_main_menu(), parse_mode=ParseMode.HTML)


@dp.message(Command("menu"))
async def cmd_menu(message: Message):
    """Показать главное меню"""
    await message.answer("<b>Главное меню</b>", reply_markup=get_main_menu(), parse_mode=ParseMode.HTML)


@dp.callback_query(F.data == 'menu')
async def back_to_menu(callback: CallbackQuery, bot: Bot):
    """Возврат в главное меню с очисткой"""
    # Очищаем чат
    await chat_cleaner.track_and_clean(bot=bot, callback=callback)
    
    # Отправляем новое сообщение
    msg = await bot.send_message(
        chat_id=callback.message.chat.id,
        text="<b>Главное меню</b>",
        reply_markup=get_main_menu()
    )
    chat_cleaner.add_bot_message(callback.from_user.id, msg.message_id)
    await callback.answer()


# ============================================================================
# ОБРАБОТКА КНОПОК МЕНЮ
# ============================================================================

@dp.callback_query(F.data == 'stores')
async def show_stores(callback: CallbackQuery):
    """Мои магазины"""
    from stores_handler import get_stores_menu
    await callback.message.edit_text(
        "<b>🛍 Мои магазины</b>\n\nВыберите площадку:",
        reply_markup=get_stores_menu(str(callback.from_user.id))
    )
    await callback.answer()


@dp.callback_query(F.data == 'dashboard')
async def show_dashboard(callback: CallbackQuery):
    """Дашборд"""
    text = (
        "<b>📊 Дашборд</b>\n\n"
        "Данные по магазинам:\n\n"
        "🟣 <b>Wildberries</b>\n"
        "   Выручка: 350K₽ | Заказы: 420 | ДРР: 18%\n\n"
        "🔵 <b>Ozon</b>\n"
        "   Выручка: 130K₽ | Заказы: 160 | ДРР: 22%\n\n"
        "📈 <b>Тренд:</b> +15% к прошлой неделе"
    )
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📈 Подробнее", callback_data='analytics')],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data='menu')],
    ])
    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()


@dp.callback_query(F.data == 'analytics')
async def show_analytics(callback: CallbackQuery):
    """Аналитика"""
    await callback.message.answer("📊 Используйте команду /stats для подробной аналитики")
    await callback.answer()


@dp.callback_query(F.data == 'autonomy')
async def show_autonomy(callback: CallbackQuery):
    """Автономия"""
    text = (
        "<b>🤖 Автономный режим</b>\n\n"
        "Статус: <b>✅ Активен</b>\n"
        "Периодичность: каждые 10 минут\n\n"
        "<b>Последние действия:</b>\n"
        "• 14:30 — Проверка запасов\n"
        "• 14:20 — Анализ цен конкурентов\n"
        "• 14:10 — Оптимизация ДРР\n\n"
        "Настройки: /settings"
    )
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⚙️ Настройки", callback_data='settings')],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data='menu')],
    ])
    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()


@dp.callback_query(F.data == 'pricing')
async def show_pricing(callback: CallbackQuery):
    """Цены и ДРР"""
    await callback.message.answer("💰 Используйте /recommendations для анализа цен и ДРР")
    await callback.answer()


@dp.callback_query(F.data == 'pricing')
async def show_pricing(callback: CallbackQuery):
    """Ценообразование"""
    await callback.message.answer("💰 Используйте /pricing для управления ценами")
    await callback.answer()


@dp.callback_query(F.data == 'advertising')
async def show_advertising(callback: CallbackQuery):
    """Реклама"""
    text = (
        "<b>📢 Реклама</b>\n\n"
        "Текущие кампании:\n\n"
        "🟣 <b>WB Авто</b>: ДРР 16% ✅\n"
        "🔵 <b>Ozon Поиск</b>: ДРР 21% ⚠️\n\n"
        "Рекомендации: /recommendations"
    )
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🧠 AI рекомендации", callback_data='rec_drr')],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data='menu')],
    ])
    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()


@dp.callback_query(F.data == 'notifications')
async def show_notifications(callback: CallbackQuery):
    """Уведомления"""
    await callback.message.answer("🔔 Используйте /notifications для управления уведомлениями")
    await callback.answer()


@dp.callback_query(F.data == 'settings')
async def show_settings(callback: CallbackQuery):
    """Настройки"""
    await callback.message.answer("⚙️ Используйте /settings для настройки автономности")
    await callback.answer()


@dp.callback_query(F.data == 'support')
async def show_support(callback: CallbackQuery):
    """Поддержка"""
    text = (
        "<b>🆘 Поддержка</b>\n\n"
        "Команды бота:\n"
        "/start — Главное меню\n"
        "/menu — Показать меню\n"
        "/stats — Аналитика\n"
        "/settings — Настройки\n"
        "/recommendations — AI советы\n"
        "/notifications — Уведомления\n"
        "/content — Генерация контента\n\n"
        "По вопросам: @admin"
    )
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Назад", callback_data='menu')],
    ])
    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()


# ============================================================================
# РЕГИСТРАЦИЯ ОБРАБОТЧИКОВ
# ============================================================================

def register_all_handlers():
    """Регистрация всех обработчиков"""
    # Подключаем роутеры
    dp.include_router(stores_router)
    
    # Регистрируем обработчики из модулей
    register_notification_handlers(dp)
    register_settings_handlers(dp)
    register_recommendations_handlers(dp)
    register_ai_recommendations_handlers(dp)
    register_stats_handlers(dp)
    register_content_handlers(dp)
    register_pricing_handlers(dp)
    register_ab_testing_handlers(dp)
    register_mpstats_handlers(dp)
    register_competitors_handlers(dp)
    register_fuck_mode_handlers(dp)
    register_cabinet_handlers(dp)
    
    logger.info("✅ Все обработчики зарегистрированы")


# ============================================================================
# ЗАПУСК
# ============================================================================

async def main():
    """Главная функция запуска"""
    logger.info("🚀 Запуск Seller AI Bot...")
    
    # Регистрируем обработчики
    register_all_handlers()
    
    # Удаляем webhook и запускаем polling
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
