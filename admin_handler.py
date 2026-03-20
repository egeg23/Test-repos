# admin_handler.py - Админ-панель (только для админа)
"""
Административные функции бота.
Доступ только для ADMIN_USER_ID (216929582)
"""

import json
import logging
import os
import subprocess
from datetime import datetime
from pathlib import Path

from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from enhanced_menus import is_admin, get_admin_menu
from modules.chat_cleaner import chat_cleaner
from modules.subscription_manager import (
    SubscriptionManager, AdminStats, PLANS,
    get_plan_keyboard, get_duration_keyboard
)

router = Router()
logger = logging.getLogger('admin_handler')


# ============================================================================
# СОСТОЯНИЯ ДЛЯ АДМИНА
# ============================================================================

class AdminStates(StatesGroup):
    waiting_broadcast_message = State()  # Ожидание текста рассылки
    waiting_test_user_id = State()  # Ожидание ID для теста
    # NEW: Состояния для выдачи доступа
    waiting_grant_username = State()  # Ожидание ника Telegram
    waiting_grant_plan = State()  # Выбор тарифа
    waiting_grant_duration = State()  # Выбор срока
    confirm_grant = State()  # Подтверждение выдачи


# ============================================================================
# ГЛАВНЫЙ ОБРАБОТЧИК АДМИН-ПАНЕЛИ
# ============================================================================

@router.callback_query(F.data == 'admin_panel')
async def admin_panel_handler(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """Админ-панель (только для админа)"""
    user_id = callback.from_user.id
    
    # Проверка админа
    if not is_admin(user_id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    await callback.answer()
    
    # Очищаем чат
    await chat_cleaner.track_and_clean(bot=bot, callback=callback)
    
    # Получаем статистику
    stats = await get_system_stats()
    
    text = (
        "🔐 <b>АДМИН-ПАНЕЛЬ</b>\n\n"
        f"👥 Пользователей: <b>{stats['users']}</b>\n"
        f"🏪 Подключено магазинов: <b>{stats['stores']}</b>\n"
        f"💾 Размер данных: <b>{stats['data_size']}</b>\n"
        f"🤖 Бот работает: <b>{stats['uptime']}</b>\n\n"
        "Выберите действие:"
    )
    
    msg = await bot.send_message(
        chat_id=callback.message.chat.id,
        text=text,
        reply_markup=get_admin_menu(user_id)
    )
    chat_cleaner.add_bot_message(user_id, msg.message_id)


# ============================================================================
# ПОЛЬЗОВАТЕЛИ
# ============================================================================

@router.callback_query(F.data == 'admin_users')
async def admin_users_handler(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """Список пользователей"""
    user_id = callback.from_user.id
    
    if not is_admin(user_id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    await callback.answer()
    await chat_cleaner.track_and_clean(bot=bot, callback=callback)
    
    # Считаем пользователей
    users = await get_users_list()
    
    text = f"👥 <b>ПОЛЬЗОВАТЕЛИ ({len(users)})</b>\n\n"
    
    for user in users[:10]:  # Показываем первые 10
        text += f"• {user['name']} (@{user['username']}) - {user['stores']} магазинов\n"
    
    if len(users) > 10:
        text += f"\n... и ещё {len(users) - 10}\n"
    
    msg = await bot.send_message(
        chat_id=callback.message.chat.id,
        text=text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Обновить", callback_data='admin_users')],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data='admin_panel')],
        ])
    )
    chat_cleaner.add_bot_message(user_id, msg.message_id)


# ============================================================================
# СТАТИСТИКА
# ============================================================================

@router.callback_query(F.data == 'admin_stats')
async def admin_stats_handler(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """Обновлённая статистика с тарифами и доходами"""
    user_id = callback.from_user.id
    
    if not is_admin(user_id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    await callback.answer()
    await chat_cleaner.track_and_clean(bot=bot, callback=callback)
    
    # Получаем полную статистику
    stats = AdminStats().get_full_stats()
    basic = await get_detailed_stats()
    
    text = (
        "📊 <b>СТАТИСТИКА</b>\n\n"
        "<b>👥 Пользователи:</b>\n"
        f"• Всего: {stats['total_users']}\n"
        f"• Активные подписки: {stats['active_subscriptions']}\n"
        f"• Просроченные: {stats['expired_subscriptions']}\n\n"
        "<b>💰 Финансы:</b>\n"
        f"• Общая выручка: {stats['total_revenue']:,}₽\n"
        f"• Средний чек: {stats['total_revenue'] // max(stats['active_subscriptions'], 1):,}₽\n\n"
        "<b>📦 Магазины:</b>\n"
        f"• Всего: {stats['stores']['total']}\n"
        f"• Wildberries: {stats['stores']['wb']}\n"
        f"• Ozon: {stats['stores']['ozon']}\n"
        f"• Авито: {stats['stores']['avito']}\n\n"
        "<b>📋 Тарифы:</b>\n"
        f"• Free: {stats['plans'].get('free', 0)}\n"
        f"• Basic (490₽): {stats['plans'].get('basic', 0)}\n"
        f"• Pro (990₽): {stats['plans'].get('pro', 0)}\n"
        f"• Enterprise (2990₽): {stats['plans'].get('enterprise', 0)}\n\n"
        f"<b>🤖 Бот:</b> {basic['uptime']}"
    )
    
    msg = await bot.send_message(
        chat_id=callback.message.chat.id,
        text=text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Обновить", callback_data='admin_stats')],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data='admin_panel')],
        ])
    )
    chat_cleaner.add_bot_message(user_id, msg.message_id)


# ============================================================================
# AI ОБУЧЕНИЕ
# ============================================================================

@router.callback_query(F.data == 'admin_ai_learning')
async def admin_ai_learning_handler(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """Управление AI обучением"""
    user_id = callback.from_user.id
    
    if not is_admin(user_id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    await callback.answer()
    await chat_cleaner.track_and_clean(bot=bot, callback=callback)
    
    # Получаем статистику обучения
    learning_stats = await get_ai_learning_stats()
    
    text = (
        "🤖 <b>AI ОБУЧЕНИЕ</b>\n\n"
        f"📊 Всего паттернов: {learning_stats['patterns']}\n"
        f"✅ Успешных рекомендаций: {learning_stats['success']}\n"
        f"❌ Отклонённых: {learning_stats['rejected']}\n"
        f"📈 Точность: {learning_stats['accuracy']}%\n\n"
        "Глобальные знания:\n"
        f"• Ценообразование: {learning_stats['pricing_rules']} правил\n"
        f"• Реклама: {learning_stats['ad_rules']} правил\n"
        f"• Категории: {learning_stats['categories']} шт\n"
    )
    
    msg = await bot.send_message(
        chat_id=callback.message.chat.id,
        text=text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Синхронизировать", callback_data='admin_ai_sync')],
            [InlineKeyboardButton(text="🧹 Очистить кэш", callback_data='admin_ai_clear_cache')],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data='admin_panel')],
        ])
    )
    chat_cleaner.add_bot_message(user_id, msg.message_id)


# ============================================================================
# БЭКАПЫ
# ============================================================================

@router.callback_query(F.data == 'admin_backups')
async def admin_backups_handler(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """Управление бэкапами"""
    user_id = callback.from_user.id
    
    if not is_admin(user_id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    await callback.answer()
    await chat_cleaner.track_and_clean(bot=bot, callback=callback)
    
    backups = await get_backups_list()
    
    text = (
        "💾 <b>БЭКАПЫ</b>\n\n"
        f"Последний бэкап: {backups['last_backup']}\n"
        f"Всего бэкапов: {backups['total']}\n"
        f"Занято места: {backups['size']}\n\n"
    )
    
    if backups['files']:
        text += "Последние:\n"
        for f in backups['files'][:5]:
            text += f"• {f['name']} ({f['size']})\n"
    
    msg = await bot.send_message(
        chat_id=callback.message.chat.id,
        text=text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Создать бэкап", callback_data='admin_backup_create')],
            [InlineKeyboardButton(text="📋 Список", callback_data='admin_backups_list')],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data='admin_panel')],
        ])
    )
    chat_cleaner.add_bot_message(user_id, msg.message_id)


# ============================================================================
# ТЕСТ РЕЖИМ
# ============================================================================

@router.callback_query(F.data == 'admin_test_mode')
async def admin_test_mode_handler(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """Тестовый режим"""
    user_id = callback.from_user.id
    
    if not is_admin(user_id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    await callback.answer()
    await chat_cleaner.track_and_clean(bot=bot, callback=callback)
    
    text = (
        "🧪 <b>ТЕСТОВЫЙ РЕЖИМ</b>\n\n"
        "Проверка компонентов:\n"
        "✅ Telegram API\n"
        "✅ База данных\n"
        "✅ AI модуль\n"
        "🟡 WB API (mock)\n"
        "🟡 Ozon API (mock)\n\n"
        "Выберите тест:"
    )
    
    msg = await bot.send_message(
        chat_id=callback.message.chat.id,
        text=text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🧪 Тест API", callback_data='admin_test_api')],
            [InlineKeyboardButton(text="📊 Тест БД", callback_data='admin_test_db')],
            [InlineKeyboardButton(text="🤖 Тест AI", callback_data='admin_test_ai')],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data='admin_panel')],
        ])
    )
    chat_cleaner.add_bot_message(user_id, msg.message_id)


# ============================================================================
# РАССЫЛКА
# ============================================================================

@router.callback_query(F.data == 'admin_broadcast')
async def admin_broadcast_handler(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """Рассылка всем пользователям"""
    user_id = callback.from_user.id
    
    if not is_admin(user_id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    await callback.answer()
    await chat_cleaner.track_and_clean(bot=bot, callback=callback)
    
    msg = await bot.send_message(
        chat_id=callback.message.chat.id,
        text=(
            "📢 <b>РАССЫЛКА</b>\n\n"
            "Отправьте сообщение для рассылки ВСЕМ пользователям.\n\n"
            "Поддерживается HTML:\n"
            "• <b>жирный</b>\n"
            "• <i>курсив</i>\n"
            "• <code>код</code>\n\n"
            "Для отмены: /cancel"
        ),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Отмена", callback_data='admin_panel')],
        ])
    )
    chat_cleaner.add_bot_message(user_id, msg.message_id)
    await state.set_state(AdminStates.waiting_broadcast_message)


@router.message(AdminStates.waiting_broadcast_message)
async def broadcast_message_handler(message: Message, state: FSMContext, bot: Bot):
    """Обработка сообщения для рассылки"""
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        return
    
    if message.text == '/cancel':
        await state.clear()
        await message.answer("❌ Рассылка отменена")
        return
    
    # Получаем список пользователей
    users = await get_users_list()
    
    # Отправляем
    sent = 0
    failed = 0
    
    for user in users:
        try:
            await bot.send_message(
                chat_id=user['id'],
                text=f"📢 <b>Сообщение от админа:</b>\n\n{message.text}"
            )
            sent += 1
        except Exception as e:
            logger.error(f"Failed to send to {user['id']}: {e}")
            failed += 1
    
    await message.answer(
        f"✅ Рассылка завершена\n"
        f"📤 Отправлено: {sent}\n"
        f"❌ Ошибок: {failed}",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Назад", callback_data='admin_panel')],
        ])
    )
    await state.clear()


# ============================================================================
# ОЧИСТКА
# ============================================================================

@router.callback_query(F.data == 'admin_cleanup')
async def admin_cleanup_handler(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """Очистка системы"""
    user_id = callback.from_user.id
    
    if not is_admin(user_id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    await callback.answer()
    await chat_cleaner.track_and_clean(bot=bot, callback=callback)
    
    text = (
        "🧹 <b>ОЧИСТКА СИСТЕМЫ</b>\n\n"
        "Что очистить?"
    )
    
    msg = await bot.send_message(
        chat_id=callback.message.chat.id,
        text=text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🗑 Логи (>30 дней)", callback_data='admin_cleanup_logs')],
            [InlineKeyboardButton(text="🗑 Кэш", callback_data='admin_cleanup_cache')],
            [InlineKeyboardButton(text="🗑 Временные файлы", callback_data='admin_cleanup_temp')],
            [InlineKeyboardButton(text="⚠️ Полная очистка", callback_data='admin_cleanup_all')],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data='admin_panel')],
        ])
    )
    chat_cleaner.add_bot_message(user_id, msg.message_id)


# ============================================================================
# РЕСТАРТ
# ============================================================================

@router.callback_query(F.data == 'admin_restart')
async def admin_restart_handler(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """Рестарт бота"""
    user_id = callback.from_user.id
    
    if not is_admin(user_id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    await callback.answer()
    await chat_cleaner.track_and_clean(bot=bot, callback=callback)
    
    msg = await bot.send_message(
        chat_id=callback.message.chat.id,
        text=(
            "🔄 <b>РЕСТАРТ БОТА</b>\n\n"
            "Вы уверены? Бот перезапустится через 5 секунд."
        ),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Да, рестарт", callback_data='admin_restart_confirm')],
            [InlineKeyboardButton(text="❌ Отмена", callback_data='admin_panel')],
        ])
    )
    chat_cleaner.add_bot_message(user_id, msg.message_id)


@router.callback_query(F.data == 'admin_restart_confirm')
async def admin_restart_confirm_handler(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """Подтверждение рестарта"""
    user_id = callback.from_user.id
    
    if not is_admin(user_id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    await callback.answer("🔄 Рестарт...", show_alert=True)
    
    await bot.send_message(
        chat_id=callback.message.chat.id,
        text="🔄 Бот перезапускается..."
    )
    
    # Выполняем рестарт
    import sys
    import os
    os.execv(sys.executable, [sys.executable] + sys.argv)


# ============================================================================
# ВЫДАЧА ДОСТУПА (Многоступенчатый процесс)
# ============================================================================

@router.callback_query(F.data == 'admin_grant_access')
async def admin_grant_access_handler(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """Начало выдачи доступа - запрос ника Telegram"""
    user_id = callback.from_user.id
    
    if not is_admin(user_id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    await callback.answer()
    await chat_cleaner.track_and_clean(bot=bot, callback=callback)
    
    msg = await bot.send_message(
        chat_id=callback.message.chat.id,
        text=(
            "🎁 <b>ВЫДАЧА ДОСТУПА</b>\n\n"
            "Шаг 1/4: Введите <b>ник в Telegram</b> пользователя\n"
            "(без @, например: username)\n\n"
            "Для отмены: /cancel"
        ),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data='admin_panel')],
        ])
    )
    chat_cleaner.add_bot_message(user_id, msg.message_id)
    await state.set_state(AdminStates.waiting_grant_username)


@router.message(AdminStates.waiting_grant_username)
async def grant_username_handler(message: Message, state: FSMContext, bot: Bot):
    """Получение ника и запрос тарифа"""
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        return
    
    if message.text == '/cancel':
        await state.clear()
        await message.answer("❌ Отменено")
        return
    
    username = message.text.strip().replace('@', '')
    
    # Сохраняем ник
    await state.update_data(grant_username=username)
    
    # Удаляем сообщение пользователя
    await chat_cleaner.track_and_clean(bot=bot, message=message)
    
    # Показываем тарифы
    msg = await bot.send_message(
        chat_id=message.chat.id,
        text=(
            f"🎁 <b>ВЫДАЧА ДОСТУПА</b>\n\n"
            f"Пользователь: @{username}\n\n"
            f"Шаг 2/4: Выберите <b>тариф</b>:"
        ),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=get_plan_keyboard() + [
            [InlineKeyboardButton(text="❌ Отмена", callback_data='admin_panel')],
        ])
    )
    chat_cleaner.add_bot_message(user_id, msg.message_id)
    await state.set_state(AdminStates.waiting_grant_plan)


@router.callback_query(F.data.startswith('grant_plan_'))
async def grant_plan_handler(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """Выбор тарифа и запрос срока"""
    user_id = callback.from_user.id
    
    if not is_admin(user_id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    plan = callback.data.replace('grant_plan_', '')
    
    # Сохраняем тариф
    await state.update_data(grant_plan=plan)
    
    # Получаем данные
    data = await state.get_data()
    username = data.get('grant_username', 'unknown')
    plan_info = PLANS.get(plan, {})
    
    await callback.answer()
    await chat_cleaner.track_and_clean(bot=bot, callback=callback)
    
    # Показываем сроки
    msg = await bot.send_message(
        chat_id=callback.message.chat.id,
        text=(
            f"🎁 <b>ВЫДАЧА ДОСТУПА</b>\n\n"
            f"Пользователь: @{username}\n"
            f"Тариф: <b>{plan_info.get('name', plan)}</b> ({plan_info.get('price', 0)}₽/мес)\n\n"
            f"Шаг 3/4: Выберите <b>срок</b>:"
        ),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=get_duration_keyboard() + [
            [InlineKeyboardButton(text="❌ Отмена", callback_data='admin_panel')],
        ])
    )
    chat_cleaner.add_bot_message(user_id, msg.message_id)
    await state.set_state(AdminStates.waiting_grant_duration)


@router.callback_query(F.data.startswith('grant_duration_'))
async def grant_duration_handler(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """Выбор срока и подтверждение"""
    user_id = callback.from_user.id
    
    if not is_admin(user_id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    duration = int(callback.data.replace('grant_duration_', ''))
    
    # Сохраняем срок
    await state.update_data(grant_duration=duration)
    
    # Получаем все данные
    data = await state.get_data()
    username = data.get('grant_username', 'unknown')
    plan = data.get('grant_plan', 'basic')
    plan_info = PLANS.get(plan, {})
    
    total_price = plan_info.get('price', 0) * duration
    
    await callback.answer()
    await chat_cleaner.track_and_clean(bot=bot, callback=callback)
    
    # Показываем подтверждение
    msg = await bot.send_message(
        chat_id=callback.message.chat.id,
        text=(
            f"🎁 <b>ПОДТВЕРЖДЕНИЕ</b>\n\n"
            f"Пользователь: <b>@{username}</b>\n"
            f"Тариф: <b>{plan_info.get('name', plan)}</b>\n"
            f"Срок: <b>{duration} мес.</b>\n"
            f"Стоимость: <b>{total_price:,}₽</b>\n\n"
            f"✅ Всё верно?"
        ),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Подтвердить", callback_data='grant_confirm')],
            [InlineKeyboardButton(text="❌ Отмена", callback_data='admin_panel')],
        ])
    )
    chat_cleaner.add_bot_message(user_id, msg.message_id)
    await state.set_state(AdminStates.confirm_grant)


@router.callback_query(F.data == 'grant_confirm')
async def grant_confirm_handler(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """Финальное подтверждение и выдача доступа"""
    user_id = callback.from_user.id
    
    if not is_admin(user_id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    # Получаем все данные
    data = await state.get_data()
    username = data.get('grant_username', 'unknown')
    plan = data.get('grant_plan', 'basic')
    duration = data.get('grant_duration', 1)
    
    await callback.answer()
    await chat_cleaner.track_and_clean(bot=bot, callback=callback)
    
    # Находим пользователя по нику
    target_user_id = await find_user_by_username(username)
    
    if not target_user_id:
        msg = await bot.send_message(
            chat_id=callback.message.chat.id,
            text=f"❌ Пользователь @{username} не найден в базе",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔄 Попробовать снова", callback_data='admin_grant_access')],
                [InlineKeyboardButton(text="⬅️ Назад", callback_data='admin_panel')],
            ])
        )
        chat_cleaner.add_bot_message(user_id, msg.message_id)
        await state.clear()
        return
    
    # Выдаём подписку
    sub_manager = SubscriptionManager()
    success = sub_manager.grant_subscription(
        user_id=target_user_id,
        plan=plan,
        months=duration,
        granted_by=str(user_id)
    )
    
    if success:
        plan_info = PLANS.get(plan, {})
        msg = await bot.send_message(
            chat_id=callback.message.chat.id,
            text=(
                f"✅ <b>ДОСТУП ВЫДАН!</b>\n\n"
                f"Пользователь: @{username}\n"
                f"Тариф: {plan_info.get('name', plan)}\n"
                f"Срок: {duration} мес.\n"
                f"Действует до: {(datetime.now() + __import__('datetime').timedelta(days=30*duration)).strftime('%d.%m.%Y')}\n\n"
                f"Пользователь получит уведомление."
            ),
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🎁 Выдать ещё", callback_data='admin_grant_access')],
                [InlineKeyboardButton(text="⬅️ В админ-панель", callback_data='admin_panel')],
            ])
        )
        
        # Отправляем уведомление пользователю
        try:
            await bot.send_message(
                chat_id=int(target_user_id),
                text=(
                    f"🎉 <b>Вам выдан доступ!</b>\n\n"
                    f"Тариф: <b>{plan_info.get('name', plan)}</b>\n"
                    f"Срок: {duration} мес.\n"
                    f"Действует до: {(datetime.now() + __import__('datetime').timedelta(days=30*duration)).strftime('%d.%m.%Y')}\n\n"
                    f"Нажмите /start для обновления меню."
                )
            )
        except Exception as e:
            logger.error(f"Failed to notify user {target_user_id}: {e}")
    else:
        msg = await bot.send_message(
            chat_id=callback.message.chat.id,
            text=f"❌ Ошибка при выдаче доступа. Попробуйте снова.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⬅️ Назад", callback_data='admin_panel')],
            ])
        )
    
    chat_cleaner.add_bot_message(user_id, msg.message_id)
    await state.clear()


async def find_user_by_username(username: str) -> str:
    """Находит user_id по username"""
    try:
        clients_dir = Path("/opt/clients")
        registry_file = clients_dir / 'USER_REGISTRY.json'
        
        if registry_file.exists():
            with open(registry_file, 'r') as f:
                registry = json.load(f)
            
            for user_id, data in registry.items():
                if data.get('username', '').lower() == username.lower():
                    return user_id.replace('user_', '')
    except Exception as e:
        logger.error(f"Error finding user: {e}")
    
    return None


# ============================================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================================================

async def get_system_stats():
    """Получает системную статистику"""
    try:
        clients_dir = Path("/opt/clients")
        users = [d for d in clients_dir.iterdir() if d.is_dir() and not d.name.startswith('.')]
        
        # Считаем магазины
        stores = 0
        for user_dir in users:
            for platform in ['wb', 'ozon', 'avito']:
                creds_file = user_dir / 'credentials' / platform / 'credentials.json'
                if creds_file.exists():
                    stores += 1
        
        # Размер данных
        total_size = sum(
            f.stat().st_size 
            for user_dir in users 
            for f in user_dir.rglob('*') 
            if f.is_file()
        )
        
        return {
            'users': len(users),
            'stores': stores,
            'data_size': f"{total_size / (1024*1024):.1f} MB",
            'uptime': "N/A"  # TODO: track uptime
        }
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        return {'users': 0, 'stores': 0, 'data_size': 'N/A', 'uptime': 'N/A'}


async def get_detailed_stats():
    """Детальная статистика"""
    basic = await get_system_stats()
    
    return {
        'version': '2.0.0',
        'uptime': basic['uptime'],
        'total_users': basic['users'],
        'wb_cabinets': basic['stores'],  # Simplified
        'ozon_cabinets': 0,
        'recommendations': 0,
        'db_size': basic['data_size'],
        'errors_24h': 0
    }


async def get_users_list():
    """Получает список пользователей"""
    try:
        clients_dir = Path("/opt/clients")
        users = []
        
        registry_file = clients_dir / 'USER_REGISTRY.json'
        if registry_file.exists():
            with open(registry_file, 'r') as f:
                registry = json.load(f)
                for user_id, data in registry.items():
                    if user_id.startswith('user_') or user_id.isdigit():
                        users.append({
                            'id': int(user_id.replace('user_', '')),
                            'name': data.get('first_name', 'Unknown'),
                            'username': data.get('username', 'N/A'),
                            'stores': len(data.get('stores', []))
                        })
        
        return users
    except Exception as e:
        logger.error(f"Error getting users: {e}")
        return []


async def get_ai_learning_stats():
    """Статистика AI обучения"""
    try:
        learning_file = Path("/opt/clients/GLOBAL_AI_LEARNING/learning_log.json")
        if learning_file.exists():
            with open(learning_file, 'r') as f:
                data = json.load(f)
                return {
                    'patterns': len(data.get('patterns', [])),
                    'success': len([p for p in data.get('patterns', []) if p.get('success')]),
                    'rejected': len([p for p in data.get('patterns', []) if not p.get('success')]),
                    'accuracy': 85,  # Placeholder
                    'pricing_rules': 12,
                    'ad_rules': 8,
                    'categories': 6
                }
    except Exception as e:
        logger.error(f"Error getting AI stats: {e}")
    
    return {
        'patterns': 0, 'success': 0, 'rejected': 0,
        'accuracy': 0, 'pricing_rules': 0, 'ad_rules': 0, 'categories': 0
    }


async def get_backups_list():
    """Список бэкапов"""
    try:
        backup_dir = Path("/root/.openclaw/workspace/marketplace_bot/backups")
        if not backup_dir.exists():
            return {'last_backup': 'Нет', 'total': 0, 'size': '0 MB', 'files': []}
        
        backups = sorted(backup_dir.glob('backup_*.tar.gz'), reverse=True)
        total_size = sum(f.stat().st_size for f in backups)
        
        files = [{'name': f.name, 'size': f"{f.stat().st_size/(1024*1024):.1f} MB"} for f in backups[:10]]
        
        return {
            'last_backup': backups[0].name if backups else 'Нет',
            'total': len(backups),
            'size': f"{total_size/(1024*1024):.1f} MB",
            'files': files
        }
    except Exception as e:
        logger.error(f"Error getting backups: {e}")
        return {'last_backup': 'Error', 'total': 0, 'size': '0 MB', 'files': []}


# ============================================================================
# РЕГИСТРАЦИЯ
# ============================================================================

def register_handlers(dp):
    """Регистрация обработчиков"""
    dp.include_router(router)
    logger.info("[Admin] Обработчики зарегистрированы")
