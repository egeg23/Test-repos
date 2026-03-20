# ai_recommendations_handler.py - Обработчик AI рекомендаций
"""
AI Recommendations System - Система AI рекомендаций с самообучением

Логика работы:
1. Пользователь подключает API только на чтение (фаза обучения 45 дней)
2. Каждое утро в отчете показывается прогресс обучения
3. AI Рекомендации анализируют данные и предлагают улучшения
4. Пользователь может принять/отклонить рекомендацию
5. При принятии → записывается в self-learning, сравнение через 24/48 часов
6. При отклонении → записывается причина в базу знаний пользователя
"""

import json
import logging
import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict

from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.enums import ParseMode

# Импорт системы очистки чата
from modules.chat_cleaner import chat_cleaner

# States для рекомендаций
class AIRecommendationsStates(StatesGroup):
    waiting_rejection_reason = State()  # Ожидание причины отказа

router = Router()
logger = logging.getLogger('ai_recommendations')


@dataclass
class Recommendation:
    """Структура рекомендации"""
    id: str
    type: str  # price, ad_bid, visual, stock, category
    title: str
    description: str
    articul: Optional[str]
    current_value: Optional[str]
    recommended_value: Optional[str]
    expected_impact: str
    confidence: float  # 0-1
    created_at: str
    status: str = "pending"  # pending, accepted, rejected, completed
    user_feedback: Optional[str] = None
    rejection_reason: Optional[str] = None


@dataclass
class LearningRecord:
    """Запись для самообучения"""
    recommendation_id: str
    user_id: str
    platform: str
    recommendation_type: str
    before_data: Dict
    after_24h: Optional[Dict]
    after_48h: Optional[Dict]
    user_executed: bool
    user_rejection_reason: Optional[str]
    actual_outcome: Optional[str]
    created_at: str
    updated_at: str


class AIRecommendationsEngine:
    """Движок AI рекомендаций"""
    
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.data_dir = Path(f"/opt/clients/{user_id}/ai_recommendations")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.recommendations_file = self.data_dir / "recommendations.json"
        self.learning_file = self.data_dir / "learning_records.json"
        self.user_knowledge_file = self.data_dir / "user_knowledge.json"
        self.recommendations: List[Recommendation] = []
        self.learning_records: List[LearningRecord] = []
        self._load()
    
    def _load(self):
        """Загружает сохраненные данные"""
        if self.recommendations_file.exists():
            try:
                with open(self.recommendations_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.recommendations = [Recommendation(**r) for r in data]
            except Exception as e:
                logger.error(f"[AIRecommendations] Ошибка загрузки: {e}")
        
        if self.learning_file.exists():
            try:
                with open(self.learning_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.learning_records = [LearningRecord(**r) for r in data]
            except Exception as e:
                logger.error(f"[AIRecommendations] Ошибка загрузки learning: {e}")
    
    def _save_recommendations(self):
        """Сохраняет рекомендации"""
        try:
            with open(self.recommendations_file, 'w', encoding='utf-8') as f:
                json.dump([asdict(r) for r in self.recommendations], f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"[AIRecommendations] Ошибка сохранения: {e}")
    
    def _save_learning(self):
        """Сохраняет записи обучения"""
        try:
            with open(self.learning_file, 'w', encoding='utf-8') as f:
                json.dump([asdict(r) for r in self.learning_records], f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"[AIRecommendations] Ошибка сохранения learning: {e}")
    
    def _save_user_knowledge(self, knowledge: Dict):
        """Сохраняет знания о пользователе"""
        try:
            existing = {}
            if self.user_knowledge_file.exists():
                with open(self.user_knowledge_file, 'r', encoding='utf-8') as f:
                    existing = json.load(f)
            
            existing.update(knowledge)
            existing['last_updated'] = datetime.now().isoformat()
            
            with open(self.user_knowledge_file, 'w', encoding='utf-8') as f:
                json.dump(existing, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"[AIRecommendations] Ошибка сохранения knowledge: {e}")
    
    def generate_recommendations(self, platform: str = 'wb') -> List[Recommendation]:
        """Генерирует рекомендации на основе данных"""
        # Здесь будет анализ реальных данных
        # Пока создаем примеры для демонстрации
        
        recommendations = []
        
        # Получаем данные пользователя
        try:
            from modules.cost_price_manager import get_cost_price_manager
            cost_manager = get_cost_price_manager(self.user_id, platform)
            
            # Пример рекомендации по цене
            if cost_manager.has_cost_prices():
                recommendations.append(Recommendation(
                    id=f"price_{datetime.now().strftime('%Y%m%d')}_001",
                    type="price",
                    title="📈 Повысить цену на популярный товар",
                    description="Артикул 12345678 показывает высокий спрос. Рекомендуется повысить цену на 10% для увеличения маржи.",
                    articul="12345678",
                    current_value="450 ₽",
                    recommended_value="495 ₽",
                    expected_impact="+15% к марже, -5% к продажам (нетто +9% прибыли)",
                    confidence=0.85,
                    created_at=datetime.now().isoformat()
                ))
            
            # Пример рекомендации по рекламе
            recommendations.append(Recommendation(
                id=f"ad_{datetime.now().strftime('%Y%m%d')}_001",
                type="ad_bid",
                title="📢 Снизить ставку в РК «Зимняя распродажа»",
                description="ДРР в кампании превышает целевой на 35%. Рекомендуется снизить ставку на 20%.",
                articul=None,
                current_value="ДРР 18%",
                recommended_value="ДРР 12%",
                expected_impact="Экономия 5 000 ₽/день при сохранении позиций",
                confidence=0.78,
                created_at=datetime.now().isoformat()
            ))
            
            # Пример рекомендации по визуалу
            recommendations.append(Recommendation(
                id=f"visual_{datetime.now().strftime('%Y%m%d')}_001",
                type="visual",
                title="🎨 Обновить главное фото артикула 87654321",
                description="CTR ниже среднего по категории на 25%. Рекомендуется добавить инфографику с УТП.",
                articul="87654321",
                current_value="CTR 2.1%",
                recommended_value="CTR 3.5% (целевой)",
                expected_impact="+40% к переходам, +20% к продажам",
                confidence=0.72,
                created_at=datetime.now().isoformat()
            ))
            
            # Пример рекомендации по остаткам
            recommendations.append(Recommendation(
                id=f"stock_{datetime.now().strftime('%Y%m%d')}_001",
                type="stock",
                title="📦 Пополнить запасы артикула 11111111",
                description="Остаток 12 шт при продаже 8 шт/день. До дефицита 1.5 дня.",
                articul="11111111",
                current_value="12 шт",
                recommended_value="100 шт",
                expected_impact="Избежать потери 15 000 ₽ выручки",
                confidence=0.91,
                created_at=datetime.now().isoformat()
            ))
            
        except Exception as e:
            logger.error(f"[AIRecommendations] Ошибка генерации: {e}")
        
        self.recommendations = recommendations
        self._save_recommendations()
        return recommendations
    
    def accept_recommendation(self, rec_id: str) -> bool:
        """Пользователь принял рекомендацию"""
        for rec in self.recommendations:
            if rec.id == rec_id:
                rec.status = "accepted"
                self._save_recommendations()
                
                # Создаем запись для обучения
                record = LearningRecord(
                    recommendation_id=rec_id,
                    user_id=self.user_id,
                    platform='wb',
                    recommendation_type=rec.type,
                    before_data={
                        'articul': rec.articul,
                        'current_value': rec.current_value,
                        'timestamp': datetime.now().isoformat()
                    },
                    after_24h=None,
                    after_48h=None,
                    user_executed=True,
                    user_rejection_reason=None,
                    actual_outcome=None,
                    created_at=datetime.now().isoformat(),
                    updated_at=datetime.now().isoformat()
                )
                self.learning_records.append(record)
                self._save_learning()
                
                # Запускаем отложенную проверку результатов
                asyncio.create_task(self._schedule_outcome_check(rec_id))
                
                return True
        return False
    
    def reject_recommendation(self, rec_id: str, reason: str) -> bool:
        """Пользователь отклонил рекомендацию с причиной"""
        for rec in self.recommendations:
            if rec.id == rec_id:
                rec.status = "rejected"
                rec.rejection_reason = reason
                self._save_recommendations()
                
                # Сохраняем в базу знаний о пользователе
                knowledge = {
                    f"rejection_{rec.type}_{datetime.now().strftime('%Y%m%d')}": {
                        'recommendation_id': rec_id,
                        'type': rec.type,
                        'reason': reason,
                        'context': {
                            'articul': rec.articul,
                            'current_value': rec.current_value,
                            'recommended_value': rec.recommended_value
                        },
                        'timestamp': datetime.now().isoformat()
                    }
                }
                self._save_user_knowledge(knowledge)
                
                # Создаем запись для обучения (отклонено)
                record = LearningRecord(
                    recommendation_id=rec_id,
                    user_id=self.user_id,
                    platform='wb',
                    recommendation_type=rec.type,
                    before_data={'rejection': True},
                    after_24h=None,
                    after_48h=None,
                    user_executed=False,
                    user_rejection_reason=reason,
                    actual_outcome="rejected",
                    created_at=datetime.now().isoformat(),
                    updated_at=datetime.now().isoformat()
                )
                self.learning_records.append(record)
                self._save_learning()
                
                return True
        return False
    
    async def _schedule_outcome_check(self, rec_id: str):
        """Запланировать проверку результата через 24 и 48 часов"""
        await asyncio.sleep(86400)  # 24 часа
        await self._check_outcome(rec_id, "24h")
        
        await asyncio.sleep(86400)  # Еще 24 часа (48 всего)
        await self._check_outcome(rec_id, "48h")
    
    async def _check_outcome(self, rec_id: str, checkpoint: str):
        """Проверяет результат рекомендации"""
        # Здесь будет получение реальных данных
        logger.info(f"[AIRecommendations] Проверка {checkpoint} для {rec_id}")
        
        for record in self.learning_records:
            if record.recommendation_id == rec_id:
                # Собираем данные после
                outcome_data = {
                    'checkpoint': checkpoint,
                    'timestamp': datetime.now().isoformat(),
                    'sales_change': None,  # Будет заполнено реальными данными
                    'margin_change': None,
                    'position_change': None
                }
                
                if checkpoint == "24h":
                    record.after_24h = outcome_data
                else:
                    record.after_48h = outcome_data
                    # Оцениваем общий результат
                    record.actual_outcome = self._evaluate_outcome(record)
                
                record.updated_at = datetime.now().isoformat()
                self._save_learning()
                break
    
    def _evaluate_outcome(self, record: LearningRecord) -> str:
        """Оценивает результат рекомендации"""
        # Простая логика оценки
        # В реальности будет анализ изменений метрик
        return "pending_analysis"
    
    def get_learning_days_remaining(self) -> int:
        """Возвращает оставшиеся дни обучения"""
        # Ищем дату первого подключения
        first_connect_file = Path(f"/opt/clients/{self.user_id}/first_connect.json")
        if first_connect_file.exists():
            try:
                with open(first_connect_file, 'r') as f:
                    data = json.load(f)
                    first_date = datetime.fromisoformat(data.get('date', datetime.now().isoformat()))
                    days_passed = (datetime.now() - first_date).days
                    remaining = max(0, 45 - days_passed)
                    return remaining
            except:
                pass
        return 45  # По умолчанию 45 дней
    
    def get_user_knowledge(self) -> Dict:
        """Возвращает накопленные знания о пользователе"""
        if self.user_knowledge_file.exists():
            try:
                with open(self.user_knowledge_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        return {}


# ============================================================================
# ОБРАБОТЧИКИ
# ============================================================================

@router.callback_query(F.data == 'ai_recommendations')
async def ai_recommendations_handler(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """Главный обработчик AI рекомендаций с очисткой чата"""
    await callback.answer()
    
    user_id = str(callback.from_user.id)
    engine = AIRecommendationsEngine(user_id)
    
    # Очищаем чат
    await chat_cleaner.track_and_clean(bot=bot, callback=callback)
    
    # Получаем оставшиеся дни обучения
    days_remaining = engine.get_learning_days_remaining()
    
    # Генерируем свежие рекомендации
    recommendations = engine.generate_recommendations()
    
    # Показываем статус обучения
    if days_remaining > 0:
        progress_text = f"📚 <b>Фаза обучения: {days_remaining} дней осталось</b>\n\n"
        progress_text += f"<i>Каждое утро я анализирую ваш кабинет и даю рекомендации. "
        progress_text += f"Через {days_remaining} дней активируется кнопка «Автономия» для автоматического управления.</i>\n\n"
    else:
        progress_text = "✅ <b>Обучение завершено!</b>\n\n"
        progress_text += "<i>Теперь вы можете активировать полную автономию в разделе «Автономия».</i>\n\n"
    
    if not recommendations:
        msg = await bot.send_message(
            chat_id=callback.message.chat.id,
            text=progress_text + "🤔 Пока нет рекомендаций. Подключите API и загрузите себестоимость для начала анализа.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🛍 Подключить магазин", callback_data='stores')],
                [InlineKeyboardButton(text="⬅️ Назад", callback_data='menu')],
            ])
        )
        chat_cleaner.add_bot_message(callback.from_user.id, msg.message_id)
        return
    
    # Показываем первую рекомендацию
    await show_recommendation(bot, callback, engine, recommendations[0], 0, len(recommendations), progress_text)


async def show_recommendation(bot: Bot, callback: CallbackQuery, engine: AIRecommendationsEngine, 
                               rec: Recommendation, index: int, total: int, header: str):
    """Показывает конкретную рекомендацию с очисткой"""
    
    # Формируем текст рекомендации
    text = header
    text += f"💡 <b>Рекомендация {index + 1} из {total}</b>\n\n"
    text += f"{rec.title}\n\n"
    text += f"{rec.description}\n\n"
    
    if rec.current_value:
        text += f"📊 <b>Текущее:</b> {rec.current_value}\n"
    if rec.recommended_value:
        text += f"🎯 <b>Рекомендуется:</b> {rec.recommended_value}\n"
    if rec.expected_impact:
        text += f"📈 <b>Ожидаемый эффект:</b> {rec.expected_impact}\n"
    
    text += f"\n🔍 <b>Уверенность:</b> {int(rec.confidence * 100)}%"
    
    # Формируем кнопки
    buttons = []
    
    # Кнопки действий
    action_row = [
        InlineKeyboardButton(text="✅ Делаю", callback_data=f"rec_accept_{rec.id}"),
        InlineKeyboardButton(text="❌ Не делаю", callback_data=f"rec_reject_{rec.id}"),
    ]
    buttons.append(action_row)
    
    # Навигация
    nav_row = []
    if index > 0:
        nav_row.append(InlineKeyboardButton(text="⬅️ Предыдущая", callback_data=f"rec_nav_{index-1}"))
    if index < total - 1:
        nav_row.append(InlineKeyboardButton(text="Следующая ➡️", callback_data=f"rec_nav_{index+1}"))
    if nav_row:
        buttons.append(nav_row)
    
    buttons.append([InlineKeyboardButton(text="📊 История рекомендаций", callback_data='rec_history')])
    buttons.append([InlineKeyboardButton(text="⬅️ В меню", callback_data='menu')])
    
    # Отправляем новое сообщение
    msg = await bot.send_message(
        chat_id=callback.message.chat.id,
        text=text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
    )
    
    # Сохраняем ID
    chat_cleaner.add_bot_message(callback.from_user.id, msg.message_id)


@router.callback_query(F.data.startswith('rec_nav_'))
async def rec_nav_handler(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """Навигация между рекомендациями с очисткой"""
    await callback.answer()
    
    index = int(callback.data.split('_')[2])
    user_id = str(callback.from_user.id)
    engine = AIRecommendationsEngine(user_id)
    
    # Очищаем чат
    await chat_cleaner.track_and_clean(bot=bot, callback=callback)
    
    recommendations = engine.recommendations
    if 0 <= index < len(recommendations):
        days_remaining = engine.get_learning_days_remaining()
        if days_remaining > 0:
            header = f"📚 <b>Фаза обучения: {days_remaining} дней осталось</b>\n\n"
        else:
            header = "✅ <b>Обучение завершено!</b>\n\n"
        
        await show_recommendation(bot, callback, engine, recommendations[index], index, len(recommendations), header)


@router.callback_query(F.data.startswith('rec_accept_'))
async def rec_accept_handler(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """Пользователь принял рекомендацию с очисткой"""
    await callback.answer("✅ Записано! Отслеживаю результат...")
    
    rec_id = callback.data.replace('rec_accept_', '')
    user_id = str(callback.from_user.id)
    engine = AIRecommendationsEngine(user_id)
    
    # Очищаем чат
    await chat_cleaner.track_and_clean(bot=bot, callback=callback)
    
    if engine.accept_recommendation(rec_id):
        # Показываем подтверждение
        text = (
            "✅ <b>Рекомендация принята!</b>\n\n"
            "Я записал все текущие показатели.\n"
            "Через 24 и 48 часов я проверю результат и сообщу о нем.\n\n"
            "<i>Это помогает мне учиться и давать более точные советы.</i>"
        )
        
        msg = await bot.send_message(
            chat_id=callback.message.chat.id,
            text=text,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="💡 Следующая рекомендация", callback_data='ai_recommendations')],
                [InlineKeyboardButton(text="⬅️ В меню", callback_data='menu')],
            ])
        )
        chat_cleaner.add_bot_message(callback.from_user.id, msg.message_id)
    else:
        msg = await bot.send_message(
            chat_id=callback.message.chat.id,
            text="❌ Ошибка. Рекомендация не найдена.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⬅️ Назад", callback_data='ai_recommendations')],
            ])
        )
        chat_cleaner.add_bot_message(callback.from_user.id, msg.message_id)


@router.callback_query(F.data.startswith('rec_reject_'))
async def rec_reject_handler(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """Пользователь отклонил рекомендацию - запрашиваем причину с очисткой"""
    await callback.answer()
    
    rec_id = callback.data.replace('rec_reject_', '')
    await state.update_data(rejecting_rec_id=rec_id)
    
    # Очищаем чат
    await chat_cleaner.track_and_clean(bot=bot, callback=callback)
    
    msg = await bot.send_message(
        chat_id=callback.message.chat.id,
        text="❌ <b>Почему вы отклоняете эту рекомендацию?</b>\n\n"
             "Ваш ответ поможет мне лучше понять ваш бизнес и давать более релевантные советы.\n\n"
             "<i>Напишите коротко, например:</i>\n"
             "• «Уже пробовал, не сработало»\n"
             "• «Сейчас не подходит по сезону»\n"
             "• «Нет бюджета на рекламу»\n"
             "• «Цена и так максимальная»",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Отмена", callback_data='ai_recommendations')],
        ])
    )
    chat_cleaner.add_bot_message(callback.from_user.id, msg.message_id)
    await state.set_state(AIRecommendationsStates.waiting_rejection_reason)


@router.message(AIRecommendationsStates.waiting_rejection_reason)
async def rejection_reason_handler(message: Message, state: FSMContext, bot: Bot):
    """Обработка причины отклонения с очисткой"""
    reason = message.text.strip()
    data = await state.get_data()
    rec_id = data.get('rejecting_rec_id')
    
    if not rec_id:
        await message.answer("❌ Ошибка. Попробуйте снова.")
        await state.clear()
        return
    
    user_id = str(message.from_user.id)
    engine = AIRecommendationsEngine(user_id)
    
    # Очищаем чат (удаляем сообщение пользователя и бота)
    await chat_cleaner.track_and_clean(bot=bot, message=message)
    
    if engine.reject_recommendation(rec_id, reason):
        msg = await bot.send_message(
            chat_id=message.chat.id,
            text=f"📝 <b>Записано!</b>\n\n"
                 f"Причина: <i>{reason}</i>\n\n"
                 "Я запомнил это и буду учитывать в будущих рекомендациях.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="💡 Следующая рекомендация", callback_data='ai_recommendations')],
                [InlineKeyboardButton(text="⬅️ В меню", callback_data='menu')],
            ])
        )
        chat_cleaner.add_bot_message(user_id, msg.message_id)
    else:
        msg = await bot.send_message(
            chat_id=message.chat.id,
            text="❌ Ошибка при сохранении.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⬅️ Назад", callback_data='ai_recommendations')],
            ])
        )
        chat_cleaner.add_bot_message(user_id, msg.message_id)
    
    await state.clear()


@router.callback_query(F.data == 'rec_history')
async def rec_history_handler(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """История рекомендаций с очисткой"""
    await callback.answer()
    
    user_id = str(callback.from_user.id)
    engine = AIRecommendationsEngine(user_id)
    
    # Очищаем чат
    await chat_cleaner.track_and_clean(bot=bot, callback=callback)
    
    # Считаем статистику
    accepted = len([r for r in engine.recommendations if r.status == "accepted"])
    rejected = len([r for r in engine.recommendations if r.status == "rejected"])
    pending = len([r for r in engine.recommendations if r.status == "pending"])
    
    text = (
        "📊 <b>История рекомендаций</b>\n\n"
        f"✅ Принято: {accepted}\n"
        f"❌ Отклонено: {rejected}\n"
        f"⏳ Ожидает: {pending}\n\n"
    )
    
    if engine.learning_records:
        # Показываем последние результаты
        text += "<b>Последние результаты:</b>\n"
        for record in engine.learning_records[-3:]:
            status = "✅" if record.user_executed else "❌"
            text += f"{status} {record.recommendation_type} - {record.actual_outcome or 'в процессе'}\n"
    
    # Получаем знания о пользователе
    knowledge = engine.get_user_knowledge()
    if knowledge:
        rejection_patterns = [k for k in knowledge.keys() if k.startswith('rejection_')]
        if rejection_patterns:
            text += f"\n📚 <b>Что я узнал о вас:</b> {len(rejection_patterns)} паттернов отказа"
    
    msg = await bot.send_message(
        chat_id=callback.message.chat.id,
        text=text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💡 Текущие рекомендации", callback_data='ai_recommendations')],
            [InlineKeyboardButton(text="⬅️ В меню", callback_data='menu')],
        ])
    )
    chat_cleaner.add_bot_message(callback.from_user.id, msg.message_id)


def register_handlers(dp):
    """Регистрация обработчиков"""
    dp.include_router(router)
    logger.info("[AIRecommendations] Обработчики зарегистрированы")
