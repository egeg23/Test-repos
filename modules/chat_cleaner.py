# chat_cleaner.py - Система автоочистки чата
"""
Автоматическое удаление старых сообщений для чистого интерфейса.
Логика: при новом действии удаляются предыдущие сообщения бота и пользователя.
"""

import logging
from typing import Optional, List
from dataclasses import dataclass, field
from datetime import datetime

from aiogram import Bot
from aiogram.types import Message, CallbackQuery

logger = logging.getLogger('chat_cleaner')


@dataclass
class ChatSession:
    """Сессия чата с историей сообщений"""
    user_id: int
    bot_messages: List[int] = field(default_factory=list)  # ID сообщений бота
    user_messages: List[int] = field(default_factory=list)  # ID сообщений пользователя
    last_activity: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def add_bot_message(self, message_id: int):
        """Добавляет ID сообщения бота"""
        self.bot_messages.append(message_id)
        self.last_activity = datetime.now().isoformat()
    
    def add_user_message(self, message_id: int):
        """Добавляет ID сообщения пользователя"""
        self.user_messages.append(message_id)
        self.last_activity = datetime.now().isoformat()
    
    def clear_history(self):
        """Очищает историю после удаления"""
        self.bot_messages = []
        self.user_messages = []


class ChatCleaner:
    """Менеджер очистки чата"""
    
    def __init__(self):
        self.sessions: dict[int, ChatSession] = {}
        self.max_history = 10  # Максимум сообщений в истории
    
    def get_session(self, user_id: int) -> ChatSession:
        """Получает или создаёт сессию пользователя"""
        if user_id not in self.sessions:
            self.sessions[user_id] = ChatSession(user_id=user_id)
        return self.sessions[user_id]
    
    async def delete_old_messages(self, bot: Bot, user_id: int, chat_id: int, 
                                   keep_last_bot: bool = True) -> None:
        """
        Удаляет старые сообщения.
        
        Args:
            bot: Экземпляр бота
            user_id: ID пользователя
            chat_id: ID чата
            keep_last_bot: Оставить последнее сообщение бота (для редактирования)
        """
        session = self.get_session(user_id)
        
        # Удаляем сообщения пользователя
        for msg_id in session.user_messages:
            try:
                await bot.delete_message(chat_id=chat_id, message_id=msg_id)
                logger.debug(f"[ChatCleaner] Удалено сообщение пользователя {msg_id}")
            except Exception as e:
                logger.debug(f"[ChatCleaner] Не удалось удалить сообщение {msg_id}: {e}")
        
        # Удаляем старые сообщения бота (кроме последнего если нужно)
        messages_to_delete = session.bot_messages[:-1] if keep_last_bot and session.bot_messages else session.bot_messages
        
        for msg_id in messages_to_delete:
            try:
                await bot.delete_message(chat_id=chat_id, message_id=msg_id)
                logger.debug(f"[ChatCleaner] Удалено сообщение бота {msg_id}")
            except Exception as e:
                logger.debug(f"[ChatCleaner] Не удалось удалить сообщение {msg_id}: {e}")
        
        # Очищаем историю
        if keep_last_bot and session.bot_messages:
            session.bot_messages = [session.bot_messages[-1]]
        else:
            session.bot_messages = []
        session.user_messages = []
    
    async def track_and_clean(self, bot: Bot, message: Optional[Message] = None,
                               callback: Optional[CallbackQuery] = None) -> None:
        """
        Отслеживает сообщение и очищает старые.
        Использовать в начале каждого обработчика.
        """
        if callback:
            user_id = callback.from_user.id
            chat_id = callback.message.chat.id if callback.message else user_id
            
            # Удаляем сообщение с кнопкой, которую нажали
            try:
                if callback.message:
                    await bot.delete_message(chat_id=chat_id, message_id=callback.message.message_id)
            except Exception:
                pass
            
            # Очищаем старую историю
            await self.delete_old_messages(bot, user_id, chat_id, keep_last_bot=False)
            
        elif message:
            user_id = message.from_user.id
            chat_id = message.chat.id
            
            # Добавляем сообщение пользователя в историю
            session = self.get_session(user_id)
            session.add_user_message(message.message_id)
            
            # Очищаем старую историю
            await self.delete_old_messages(bot, user_id, chat_id, keep_last_bot=True)
    
    def add_bot_message(self, user_id: int, message_id: int):
        """Добавляет ID сообщения бота в историю"""
        session = self.get_session(user_id)
        session.add_bot_message(message_id)
        
        # Ограничиваем размер истории
        if len(session.bot_messages) > self.max_history:
            session.bot_messages = session.bot_messages[-self.max_history:]


# Глобальный экземпляр
chat_cleaner = ChatCleaner()


# ============================================================================
# УТИЛИТЫ ДЛЯ ИСПОЛЬЗОВАНИЯ В ОБРАБОТЧИКАХ
# ============================================================================

async def clean_and_respond(bot: Bot, callback: CallbackQuery, text: str, 
                             reply_markup=None, parse_mode=None):
    """
    Очищает чат и отправляет новое сообщение.
    Использовать вместо callback.message.edit_text()
    """
    await chat_cleaner.track_and_clean(bot=bot, callback=callback)
    
    msg = await bot.send_message(
        chat_id=callback.message.chat.id,
        text=text,
        reply_markup=reply_markup,
        parse_mode=parse_mode
    )
    
    chat_cleaner.add_bot_message(callback.from_user.id, msg.message_id)
    return msg


async def clean_on_command(bot: Bot, message: Message):
    """
    Очищает чат при команде.
    Использовать в начале обработчиков команд.
    """
    await chat_cleaner.track_and_clean(bot=bot, message=message)
