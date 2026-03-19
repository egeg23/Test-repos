# notification_handler.py - Обработчик уведомлений для Telegram бота
"""
Команды и обработчики для работы с уведомлениями.
Показывает реальные алерты из autonomous_cycle.
"""

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from modules.notification_service import NotificationService, format_notification_message
import logging

logger = logging.getLogger('notification_handler')
router = Router()

# Инициализация сервиса
notification_service = NotificationService("/opt/clients")


@router.message(Command("notifications"))
async def cmd_notifications(message: Message):
    """Показывает список уведомлений"""
    user_id = str(message.from_user.id)
    
    # Получаем уведомления
    notifications = notification_service.get_user_notifications(user_id, limit=10)
    unread_count = notification_service.get_unread_count(user_id)
    
    if not notifications:
        await message.answer(
            "🔔 <b>Уведомления</b>\n\n"
            "У вас пока нет уведомлений.\n\n"
            "Автономный цикл проверяет магазины каждые 10 минут. "
            "Если будут найдены проблемы (низкие остатки, маржа), "
            "вы получите уведомление здесь."
        )
        return
    
    # Формируем сообщение
    text = f"🔔 <b>Уведомления ({unread_count} новых)</b>\n\n"
    
    for i, notif in enumerate(notifications[:5], 1):
        status = "🔴" if not notif.get('read') else "⚪"
        text += f"{status} {notif.get('title', 'Без названия')}\n"
    
    if len(notifications) > 5:
        text += f"\n... и ещё {len(notifications) - 5}"
    
    # Кнопки
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📖 Показать все", callback_data='show_notifications')],
        [InlineKeyboardButton(text="✅ Отметить прочитанными", callback_data='mark_read_all')],
        [InlineKeyboardButton(text="🔄 Обновить", callback_data='refresh_notifications')]
    ])
    
    await message.answer(text, reply_markup=keyboard)


@router.callback_query(F.data == 'show_notifications')
async def show_all_notifications(callback: CallbackQuery):
    """Показывает все уведомления подробно"""
    user_id = str(callback.from_user.id)
    notifications = notification_service.get_user_notifications(user_id, limit=10)
    
    if not notifications:
        await callback.message.edit_text("У вас нет уведомлений.")
        await callback.answer()
        return
    
    # Отправляем каждое уведомление отдельным сообщением
    for notif in notifications[:3]:  # Показываем первые 3
        text = format_notification_message(notif)
        
        # Кнопка "Прочитано" для каждого
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text="✅ Отметить прочитанным", 
                callback_data=f"mark_read:{notif.get('created_at')}"
            )]
        ])
        
        await callback.message.answer(text, reply_markup=keyboard)
    
    if len(notifications) > 3:
        await callback.message.answer(f"... и ещё {len(notifications) - 3} уведомлений. Используйте /notifications")
    
    await callback.answer()


@router.callback_query(F.data == 'mark_read_all')
async def mark_all_read(callback: CallbackQuery):
    """Отмечает все уведомления прочитанными"""
    user_id = str(callback.from_user.id)
    notification_service.mark_as_read(user_id=user_id)
    
    await callback.message.edit_text(
        "✅ <b>Все уведомления отмечены прочитанными</b>"
    )
    await callback.answer("Готово!")


@router.callback_query(F.data.startswith('mark_read:'))
async def mark_one_read(callback: CallbackQuery):
    """Отмечает одно уведомление прочитанным"""
    created_at = callback.data.split(':')[1]
    notification_service.mark_as_read(notification_ids=[created_at])
    
    await callback.message.edit_text(
        callback.message.text + "\n\n✅ Прочитано"
    )
    await callback.answer("Отмечено")


@router.callback_query(F.data == 'refresh_notifications')
async def refresh_notifications(callback: CallbackQuery):
    """Обновляет список уведомлений"""
    await cmd_notifications(callback.message)
    await callback.answer("Обновлено")


@router.message(Command("alerts"))
async def cmd_alerts(message: Message):
    """Показывает только важные алерты (high priority)"""
    user_id = str(message.from_user.id)
    notifications = notification_service.get_user_notifications(user_id, unread_only=True)
    
    # Фильтруем только high priority
    alerts = [n for n in notifications if n.get('priority') == 'high']
    
    if not alerts:
        await message.answer(
            "🟢 <b>Важных алертов нет</b>\n\n"
            "Все показатели в норме. Автономный цикл работает."
        )
        return
    
    text = f"🔴 <b>Важные алерты ({len(alerts)})</b>\n\n"
    
    for alert in alerts[:5]:
        text += format_notification_message(alert) + "\n---\n"
    
    await message.answer(text)


def register_handlers(dp):
    """Регистрация обработчиков"""
    dp.include_router(router)
    logger.info("✅ Обработчики уведомлений зарегистрированы")