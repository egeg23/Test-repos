"""
CTR Monitor Handler - Обработчик мониторинга CTR для Telegram бота
"""

import asyncio
from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.enums import ParseMode
from aiogram.filters import Command
import logging

from modules.ctr_monitor import (
    get_monitor, search_campaigns, start_ctr_monitoring,
    stop_ctr_monitoring, get_campaign_metrics, CampaignMetrics
)

logger = logging.getLogger(__name__)
router = Router()

# ============================================================================
# FSM Состояния
# ============================================================================

class CTRMonitorStates(StatesGroup):
    waiting_article = State()
    waiting_campaign_selection = State()
    monitoring_active = State()


# ============================================================================
# КЛАВИАТУРЫ
# ============================================================================

def get_marketplace_selection_menu():
    """Меню выбора маркетплейса"""
    buttons = [
        [InlineKeyboardButton(text="🟣 Wildberries", callback_data='ctr_wb')],
        [InlineKeyboardButton(text="🔵 Ozon", callback_data='ctr_ozon')],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data='content')],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_campaign_selection_menu(campaigns: list):
    """Меню выбора кампании"""
    buttons = []
    
    for camp in campaigns:
        status_icon = "🟢" if camp['status'] in ['active', 'running', 'started'] else "🔴"
        btn_text = f"{status_icon} {camp['name'][:30]}..."
        buttons.append([
            InlineKeyboardButton(
                text=btn_text,
                callback_data=f"ctr_select_{camp['campaign_id']}"
            )
        ])
    
    buttons.append([InlineKeyboardButton(text="⬅️ Назад", callback_data='ctr_start')])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_monitoring_status_menu(campaign_id: str, show_full: bool = False):
    """Меню статуса мониторинга"""
    if show_full:
        buttons = [
            [
                InlineKeyboardButton(text="🔍 Проанализировать конкурентов", callback_data=f'ctr_analyze_{campaign_id}'),
            ],
            [
                InlineKeyboardButton(text="🔄 Обновить", callback_data=f'ctr_refresh_{campaign_id}'),
                InlineKeyboardButton(text="❌ Отмена", callback_data=f'ctr_stop_{campaign_id}'),
            ],
        ]
    else:
        buttons = [
            [
                InlineKeyboardButton(text="🔄 Обновить", callback_data=f'ctr_refresh_{campaign_id}'),
                InlineKeyboardButton(text="❌ Отмена", callback_data=f'ctr_stop_{campaign_id}'),
            ],
        ]
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# ============================================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================================================

def format_ctr_status(campaign: CampaignMetrics, target_impressions: int = 1000) -> str:
    """Форматирование статуса сбора CTR"""
    progress = min(campaign.impressions / target_impressions * 100, 100)
    
    # Создаем прогресс-бар
    filled = int(progress / 10)
    empty = 10 - filled
    progress_bar = "█" * filled + "░" * empty
    
    text = (
        f"📊 <b>Сбор данных</b>\n\n"
        f"🎯 Показы: {campaign.impressions:,}/{target_impressions:,} ({progress:.0f}%)\n"
        f"[{progress_bar}]\n\n"
        f"📈 Текущий CTR: {campaign.current_ctr}%\n"
        f"👆 Клики: {campaign.clicks}\n\n"
    )
    
    if campaign.impressions < target_impressions:
        remaining = target_impressions - campaign.impressions
        text += f"⏳ Ждем еще ~{remaining:,} показов..."
    else:
        text += "✅ Целевое количество показов достигнуто!"
    
    return text


def format_ctr_result(campaign: CampaignMetrics) -> str:
    """Форматирование результата анализа CTR"""
    # Определяем рекомендацию на основе CTR
    ctr = campaign.current_ctr or 0
    
    if ctr >= 5.0:
        recommendation = "Отличный CTR! Выше среднего по категории ✅"
        action = "Продолжайте в том же духе"
    elif ctr >= 3.0:
        recommendation = "Хороший CTR, но есть куда расти 📈"
        action = "Можно протестировать новые баннеры"
    elif ctr >= 1.5:
        recommendation = "CTR ниже среднего по категории (3.2%) ⚠️"
        action = "Рекомендуется обновить главное фото"
    else:
        recommendation = "CTR критически низкий 🚨"
        action = "Срочно меняйте креативы и пересмотрите таргетинг"
    
    text = (
        f"📊 <b>Анализ артикула {campaign.article_id}</b>\n\n"
        f"🎯 <b>Текущий CTR:</b> {campaign.current_ctr}%\n"
        f"📈 Показы: {campaign.impressions:,}\n"
        f"👆 Клики: {campaign.clicks}\n\n"
        f"💡 <b>Рекомендация:</b>\n"
        f"{recommendation}\n"
        f"{action}\n\n"
        f"📁 Кампания: {campaign.name}\n"
        f"🆔 ID: <code>{campaign.campaign_id}</code>"
    )
    
    return text


# ============================================================================
# ОБРАБОТЧИКИ
# ============================================================================

@router.callback_query(F.data == 'content')
async def content_menu_handler(callback: CallbackQuery, state: FSMContext):
    """Обработчик меню Контент"""
    await state.clear()
    
    buttons = [
        [InlineKeyboardButton(text="📊 Мониторинг CTR", callback_data='ctr_start')],
        [InlineKeyboardButton(text="📸 Анализ фото", callback_data='photo_analysis')],
        [InlineKeyboardButton(text="📝 Генерация описаний", callback_data='desc_gen')],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data='menu')],
    ]
    
    await callback.message.edit_text(
        "📢 <b>КОНТЕНТ</b>\n\n"
        "Инструменты для анализа и улучшения контента:\n\n"
        "📊 <b>Мониторинг CTR</b> - отслеживайте эффективность рекламы\n"
        "📸 <b>Анализ фото</b> - сравнение с конкурентами\n"
        "📝 <b>Генерация описаний</b> - AI для создания текстов",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
    )
    await callback.answer()


@router.callback_query(F.data == 'ctr_start')
async def ctr_start_handler(callback: CallbackQuery, state: FSMContext):
    """Начало процесса CTR мониторинга"""
    await state.set_state(CTRMonitorStates.waiting_article)
    
    await callback.message.edit_text(
        "📊 <b>Мониторинг CTR</b>\n\n"
        "Пришлите артикул товара и ID кампании через запятую\n\n"
        "<b>Формат:</b>\n"
        "• <code>артикул, campaign_id</code>\n\n"
        "<b>Примеры:</b>\n"
        "• <code>12345678, 98765</code>\n"
        "• <code>87654321, 123456</code>\n\n"
        "Или выберите маркетплейс для поиска кампаний:",
        reply_markup=get_marketplace_selection_menu()
    )
    await callback.answer()


@router.callback_query(F.data.in_(['ctr_wb', 'ctr_ozon']))
async def ctr_marketplace_handler(callback: CallbackQuery, state: FSMContext):
    """Выбор маркетплейса"""
    marketplace = 'wb' if callback.data == 'ctr_wb' else 'ozon'
    
    await state.update_data(marketplace=marketplace)
    await state.set_state(CTRMonitorStates.waiting_article)
    
    platform_name = "🟣 Wildberries" if marketplace == 'wb' else "🔵 Ozon"
    
    await callback.message.edit_text(
        f"{platform_name}\n\n"
        f"📊 <b>Мониторинг CTR</b>\n\n"
        f"Пришлите <b>только артикул</b> товара\n"
        f"Система найдет все рекламные кампании с этим товаром.\n\n"
        f"<b>Пример:</b> <code>12345678</code>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Назад", callback_data='ctr_start')],
        ])
    )
    await callback.answer()


@router.message(CTRMonitorStates.waiting_article)
async def ctr_article_handler(message: Message, state: FSMContext):
    """Обработка ввода артикула"""
    text = message.text.strip()
    
    # Парсим ввод
    parts = [p.strip() for p in text.split(',')]
    
    article_id = parts[0]
    campaign_id = parts[1] if len(parts) > 1 else None
    
    # Валидация артикула
    if not article_id.isdigit():
        await message.answer(
            "❌ <b>Неверный формат!</b>\n\n"
            "Артикул должен содержать только цифры.\n"
            "Пример: <code>12345678</code>"
        )
        return
    
    data = await state.get_data()
    marketplace = data.get('marketplace', 'wb')  # По умолчанию WB
    
    # Отправляем статус
    status_msg = await message.answer(
        "⏳ <b>Поиск кампаний...</b>\n"
        f"Маркетплейс: {'🟣 WB' if marketplace == 'wb' else '🔵 Ozon'}\n"
        f"Артикул: {article_id}"
    )
    
    try:
        # Если campaign_id не указан, ищем кампании
        if not campaign_id:
            campaigns = await search_campaigns(
                str(message.from_user.id), article_id, marketplace
            )
            
            if not campaigns:
                await status_msg.edit_text(
                    "❌ <b>Кампании не найдены</b>\n\n"
                    f"Не удалось найти рекламные кампании для артикула {article_id}.\n\n"
                    f"Возможные причины:\n"
                    f"• Товар не участвует в рекламе\n"
                    f"• Неверный артикул\n"
                    f"• API временно недоступен\n\n"
                    f"Попробуйте указать ID кампании вручную:\n"
                    f"<code>{article_id}, 12345</code>",
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="🔄 Повторить", callback_data='ctr_start')],
                        [InlineKeyboardButton(text="⬅️ Назад", callback_data='content')],
                    ])
                )
                await state.clear()
                return
            
            # Если найдена одна кампания - сразу запускаем
            if len(campaigns) == 1:
                campaign_id = campaigns[0]['campaign_id']
            else:
                # Несколько кампаний - показываем выбор
                await state.update_data(article_id=article_id, campaigns=campaigns)
                await state.set_state(CTRMonitorStates.waiting_campaign_selection)
                
                await status_msg.edit_text(
                    f"📊 Найдено {len(campaigns)} кампаний\n\n"
                    f"Выберите кампанию для мониторинга:",
                    reply_markup=get_campaign_selection_menu(campaigns)
                )
                return
        
        # Запускаем мониторинг
        await state.clear()
        await _start_monitoring(
            message, status_msg, str(message.from_user.id),
            article_id, campaign_id, marketplace
        )
        
    except Exception as e:
        logger.error(f"Error in ctr_article_handler: {e}")
        await status_msg.edit_text(
            "❌ <b>Ошибка при поиске кампаний</b>\n\n"
            f"Попробуйте позже или проверьте настройки API.\n"
            f"Ошибка: {str(e)[:100]}",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔄 Повторить", callback_data='ctr_start')],
                [InlineKeyboardButton(text="⬅️ Назад", callback_data='content')],
            ])
        )


@router.callback_query(CTRMonitorStates.waiting_campaign_selection, F.data.startswith('ctr_select_'))
async def ctr_campaign_select_handler(callback: CallbackQuery, state: FSMContext):
    """Выбор конкретной кампании"""
    campaign_id = callback.data.replace('ctr_select_', '')
    
    data = await state.get_data()
    article_id = data.get('article_id')
    marketplace = data.get('marketplace', 'wb')
    
    await state.clear()
    
    status_msg = await callback.message.edit_text(
        "⏳ <b>Запуск мониторинга...</b>\n"
        f"Кампания: {campaign_id}"
    )
    
    await _start_monitoring(
        callback.message, status_msg, str(callback.from_user.id),
        article_id, campaign_id, marketplace
    )
    await callback.answer()


async def _start_monitoring(
    message_or_callback, status_msg, user_id: str,
    article_id: str, campaign_id: str, marketplace: str
):
    """Запуск мониторинга кампании"""
    try:
        # Запускаем мониторинг
        campaign = await start_ctr_monitoring(
            user_id, article_id, campaign_id, marketplace
        )
        
        # Проверяем, достигнута ли цель
        if campaign.impressions >= 1000:
            # Показываем финальный результат
            await status_msg.edit_text(
                format_ctr_result(campaign),
                reply_markup=get_monitoring_status_menu(campaign_id, show_full=True)
            )
        else:
            # Показываем статус сбора
            await status_msg.edit_text(
                format_ctr_status(campaign),
                reply_markup=get_monitoring_status_menu(campaign_id)
            )
            
            # Запускаем фоновый мониторинг
            asyncio.create_task(_background_monitor(user_id, campaign_id, message_or_callback))
            
    except ValueError as e:
        await status_msg.edit_text(
            "❌ <b>Ошибка подключения к API</b>\n\n"
            f"{str(e)}\n\n"
            f"Проверьте настройки API в разделе Магазины.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔐 Настройки API", callback_data='stores')],
                [InlineKeyboardButton(text="⬅️ Назад", callback_data='content')],
            ])
        )
    except Exception as e:
        logger.error(f"Error starting monitoring: {e}")
        await status_msg.edit_text(
            "❌ <b>Ошибка при запуске мониторинга</b>\n\n"
            f"{str(e)[:200]}",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔄 Повторить", callback_data='ctr_start')],
                [InlineKeyboardButton(text="⬅️ Назад", callback_data='content')],
            ])
        )


async def _background_monitor(user_id: str, campaign_id: str, message_or_callback):
    """Фоновый мониторинг кампании"""
    from aiogram import Bot
    
    # Получаем экземпляр бота
    # Это хак, но работает в контексте aiogram
    from bot import bot
    
    monitor = get_monitor(user_id)
    check_count = 0
    max_checks = 100  # Максимум ~50 часов мониторинга
    
    while check_count < max_checks:
        await asyncio.sleep(1800)  # 30 минут
        
        campaign = await monitor.update_campaign(campaign_id)
        
        if not campaign:
            # Кампания завершена или удалена
            break
        
        # Обновляем сообщение каждые 2 проверки (1 час)
        if check_count % 2 == 0:
            try:
                if campaign.impressions >= 1000:
                    # Цель достигнута
                    await message_or_callback.edit_text(
                        format_ctr_result(campaign),
                        reply_markup=get_monitoring_status_menu(campaign_id, show_full=True)
                    )
                    
                    # Уведомляем пользователя
                    await bot.send_message(
                        user_id,
                        f"✅ <b>CTR Мониторинг завершен!</b>\n\n"
                        f"Артикул: {campaign.article_id}\n"
                        f"Финальный CTR: {campaign.current_ctr}%\n"
                        f"Показов: {campaign.impressions:,}",
                        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                            [InlineKeyboardButton(text="🔍 Анализ конкурентов", callback_data=f'ctr_analyze_{campaign_id}')],
                        ])
                    )
                    break
                else:
                    await message_or_callback.edit_text(
                        format_ctr_status(campaign),
                        reply_markup=get_monitoring_status_menu(campaign_id)
                    )
            except Exception as e:
                logger.error(f"Error updating message: {e}")
        
        check_count += 1


@router.callback_query(F.data.startswith('ctr_refresh_'))
async def ctr_refresh_handler(callback: CallbackQuery):
    """Обновление статуса мониторинга"""
    campaign_id = callback.data.replace('ctr_refresh_', '')
    user_id = str(callback.from_user.id)
    
    await callback.answer("🔄 Обновление...")
    
    monitor = get_monitor(user_id)
    campaign = await monitor.update_campaign(campaign_id)
    
    if not campaign:
        # Пробуем получить из истории
        await callback.message.edit_text(
            "✅ <b>Мониторинг завершен</b>\n\n"
            "Данные сохранены в истории.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📊 Новый мониторинг", callback_data='ctr_start')],
                [InlineKeyboardButton(text="⬅️ Назад", callback_data='content')],
            ])
        )
        return
    
    if campaign.impressions >= 1000:
        await callback.message.edit_text(
            format_ctr_result(campaign),
            reply_markup=get_monitoring_status_menu(campaign_id, show_full=True)
        )
    else:
        await callback.message.edit_text(
            format_ctr_status(campaign),
            reply_markup=get_monitoring_status_menu(campaign_id)
        )


@router.callback_query(F.data.startswith('ctr_stop_'))
async def ctr_stop_handler(callback: CallbackQuery):
    """Остановка мониторинга"""
    campaign_id = callback.data.replace('ctr_stop_', '')
    user_id = str(callback.from_user.id)
    
    await callback.answer("⏹ Останавливаем...")
    
    success = await stop_ctr_monitoring(user_id, campaign_id)
    
    if success:
        await callback.message.edit_text(
            "⏹ <b>Мониторинг остановлен</b>\n\n"
            "Данные сохранены в истории.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📊 Новый мониторинг", callback_data='ctr_start')],
                [InlineKeyboardButton(text="⬅️ Назад", callback_data='content')],
            ])
        )
    else:
        await callback.answer("Кампания не найдена", show_alert=True)


@router.callback_query(F.data.startswith('ctr_analyze_'))
async def ctr_analyze_handler(callback: CallbackQuery):
    """Анализ конкурентов"""
    campaign_id = callback.data.replace('ctr_analyze_', '')
    user_id = str(callback.from_user.id)
    
    # Получаем данные кампании
    campaign = get_campaign_metrics(user_id, campaign_id)
    
    if not campaign:
        await callback.answer("Кампания не найдена", show_alert=True)
        return
    
    # Вызываем mpstats-analyzer (заглушка для будущей интеграции)
    await callback.message.edit_text(
        f"🔍 <b>Анализ конкурентов</b>\n\n"
        f"Артикул: {campaign.article_id}\n"
        f"CTR: {campaign.current_ctr}%\n\n"
        f"⏳ Запускаем MPStats анализ...",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Назад", callback_data='ctr_start')],
        ])
    )
    
    # TODO: Вызов mpstats-analyzer
    # Здесь будет интеграция с существующим mpstats_content_ai.py
    
    await callback.answer()


# ============================================================================
# РЕГИСТРАЦИЯ
# ============================================================================

def register_handlers(dp):
    """Регистрация обработчиков CTR Monitor"""
    dp.include_router(router)
