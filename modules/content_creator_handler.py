#!/usr/bin/env python3
"""
Content Creator Handler для Telegram Bot
Интеграция генерации контента с ботом
"""

import asyncio
import json
from pathlib import Path
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

# Импортируем ContentCreator
try:
    from modules.content_creator import (
        ContentCreator, ProductData, DesignConfig,
        get_creation_status_keyboard, get_result_keyboard, 
        get_approve_keyboard, format_completion_message
    )
    CONTENT_CREATOR_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ ContentCreator не доступен: {e}")
    CONTENT_CREATOR_AVAILABLE = False

# Router
content_router = Router()

# FSM States
class ContentCreationState(StatesGroup):
    waiting_marketplace = State()
    waiting_product_name = State()
    waiting_price = State()
    creating = State()
    review = State()

# Активные сессии создания контента
active_creations = {}


def get_marketplace_keyboard():
    """Клавиатура выбора маркетплейса"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🟣 Wildberries", callback_data="mp_wb"),
            InlineKeyboardButton(text="🔵 Ozon", callback_data="mp_ozon")
        ],
        [
            InlineKeyboardButton(text="🟡 Авито", callback_data="mp_avito")
        ]
    ])


@content_router.callback_query(F.data == "create_content")
async def start_content_creation(callback: CallbackQuery, state: FSMContext):
    """Начало создания контента"""
    if not CONTENT_CREATOR_AVAILABLE:
        await callback.message.edit_text(
            "❌ Модуль создания контента временно недоступен.\n"
            "Установите playwright: pip install playwright && playwright install chromium"
        )
        return
    
    await callback.message.edit_text(
        "🎨 <b>Создание карточек товара</b>\n\n"
        "Выберите маркетплейс для которого создаём контент:",
        reply_markup=get_marketplace_keyboard()
    )
    await state.set_state(ContentCreationState.waiting_marketplace)


@content_router.callback_query(F.data.startswith("mp_"))
async def select_marketplace(callback: CallbackQuery, state: FSMContext):
    """Выбор маркетплейса"""
    marketplace = callback.data.replace("mp_", "")
    await state.update_data(marketplace=marketplace)
    
    mp_names = {"wb": "Wildberries", "ozon": "Ozon", "avito": "Авито"}
    mp_name = mp_names.get(marketplace, marketplace)
    
    await callback.message.edit_text(
        f"🎨 <b>Создание контента для {mp_name}</b>\n\n"
        f"Введите название товара:\n"
        f"<i>Пример: Беспроводной пылесос Xiaomi Dreame V10</i>"
    )
    await state.set_state(ContentCreationState.waiting_product_name)


@content_router.message(ContentCreationState.waiting_product_name)
async def process_product_name(message: Message, state: FSMContext):
    """Обработка названия товара"""
    product_name = message.text.strip()
    await state.update_data(product_name=product_name)
    
    await message.answer(
        "💰 Введите цену товара:\n"
        "<i>Пример: 12 990₽ или 12990</i>"
    )
    await state.set_state(ContentCreationState.waiting_price)


@content_router.message(ContentCreationState.waiting_price)
async def process_price(message: Message, state: FSMContext, bot: Bot):
    """Обработка цены и запуск создания контента"""
    price = message.text.strip()
    if not any(c.isdigit() for c in price):
        await message.answer("❌ Пожалуйста, введите корректную цену с цифрами")
        return
    
    # Форматируем цену
    price_clean = ''.join(filter(str.isdigit, price))
    if len(price_clean) > 0:
        price = f"{int(price_clean):,}₽".replace(",", " ")
    
    await state.update_data(price=price)
    data = await state.get_data()
    
    marketplace = data.get("marketplace", "wb")
    product_name = data.get("product_name", "Товар")
    
    # Создаём ContentCreator
    user_id = str(message.from_user.id)
    article_id = f"{user_id}_{int(asyncio.get_event_loop().time())}"
    
    creator = ContentCreator(user_id, article_id)
    active_creations[user_id] = creator
    
    # Отправляем начальный статус
    status_msg = await message.answer(
        creator.get_status_bar(),
        reply_markup=get_creation_status_keyboard()
    )
    
    await state.set_state(ContentCreationState.creating)
    
    # Запускаем создание контента в фоне
    asyncio.create_task(
        create_content_task(
            bot, message.chat.id, status_msg.message_id,
            creator, product_name, price, marketplace, user_id
        )
    )


async def create_content_task(bot: Bot, chat_id: int, status_msg_id: int,
                               creator: ContentCreator, product_name: str, 
                               price: str, marketplace: str, user_id: str):
    """Фоновая задача создания контента с обновлением статуса"""
    
    try:
        # Создаём продукт
        product = ProductData(
            name=product_name,
            price=price,
            badges=["ТОП продаж ⭐", "Скидка -25%", "Оригинал ✅"],
            rating=4.8,
            reviews=2340,
            features=["Премиум качество", "Долговечность", "Эргономика", "Гарантия 2 года"]
        )
        
        # Этап 1: Главное фото
        await update_status_message(bot, chat_id, status_msg_id, creator)
        
        # Загружаем рекомендации если есть
        rec_path = Path(f"/opt/clients/{user_id}/recommendations.json")
        rec = await creator.load_recommendations(str(rec_path) if rec_path.exists() else None)
        
        main_photo = await creator.create_main_photo(product, marketplace, rec)
        
        # Показываем результат главного фото
        await show_main_photo_result(bot, chat_id, creator, main_photo, product_name)
        
        # Этап 2: Карточки (если пользователь одобрил)
        # Пока что создаём автоматически для демо
        await update_status_message(bot, chat_id, status_msg_id, creator)
        cards = await creator.create_product_cards(product, marketplace)
        
        # Этап 3: Видео
        await update_status_message(bot, chat_id, status_msg_id, creator)
        video = await creator.create_video(product, marketplace)
        
        # Финальное сообщение
        await send_completion_message(bot, chat_id, creator, article_id=creator.article_id)
        
    except Exception as e:
        await bot.send_message(
            chat_id,
            f"❌ Ошибка при создании контента:\n<code>{str(e)}</code>\n\n"
            f"Попробуйте ещё раз или обратитесь в поддержку."
        )


async def update_status_message(bot: Bot, chat_id: int, message_id: int, creator: ContentCreator):
    """Обновление сообщения со статусом"""
    try:
        await bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=creator.get_status_bar(),
            reply_markup=get_creation_status_keyboard()
        )
    except Exception:
        pass  # Игнорируем ошибки если сообщение не изменилось


async def show_main_photo_result(bot: Bot, chat_id: int, creator: ContentCreator, 
                                  photo_path: str, product_name: str):
    """Показ результата главного фото с кнопками"""
    
    await bot.send_photo(
        chat_id=chat_id,
        photo=FSInputFile(photo_path),
        caption=f"✅ <b>Главное фото готово!</b>\n\n📝 {product_name}",
        reply_markup=get_result_keyboard(creator.version)
    )


async def send_completion_message(bot: Bot, chat_id: int, creator: ContentCreator, article_id: str):
    """Отправка финального сообщения"""
    
    # Отправляем все файлы
    base_dir = Path(creator.base_dir)
    
    # Отправляем главное фото
    main_photo = base_dir / f"main_photo_v{creator.version}.jpg"
    if main_photo.exists():
        await bot.send_photo(
            chat_id=chat_id,
            photo=FSInputFile(main_photo),
            caption="🖼️ <b>Главное фото</b>"
        )
    
    # Отправляем карточки группой
    cards_dir = base_dir / "cards"
    if cards_dir.exists():
        cards = sorted(cards_dir.glob("card_*.jpg"))
        if cards:
            media_group = []
            for i, card in enumerate(cards[:10], 1):  # Максимум 10
                media_group.append({
                    "type": "photo",
                    "media": FSInputFile(card),
                    "caption": f"📸 Карточка {i}" if i == 1 else None
                })
            
            try:
                await bot.send_media_group(chat_id=chat_id, media=media_group)
            except Exception as e:
                print(f"Error sending media group: {e}")
    
    # Отправляем видео
    video_path = base_dir / "video" / "cover_video.mp4"
    if video_path.exists():
        try:
            await bot.send_video(
                chat_id=chat_id,
                video=FSInputFile(video_path),
                caption="🎬 <b>Видео-обложка</b>"
            )
        except Exception as e:
            print(f"Error sending video: {e}")
    
    # Финальное сообщение
    await bot.send_message(
        chat_id=chat_id,
        text=format_completion_message(article_id, creator.version),
        reply_markup=get_approve_keyboard()
    )


@content_router.callback_query(F.data.startswith("content_"))
async def handle_content_actions(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """Обработка действий с контентом"""
    action = callback.data
    user_id = str(callback.from_user.id)
    
    if action == "content_refresh_status":
        # Обновление статуса
        if user_id in active_creations:
            creator = active_creations[user_id]
            await callback.message.edit_text(
                creator.get_status_bar(),
                reply_markup=get_creation_status_keyboard()
            )
        await callback.answer()
    
    elif action.startswith("content_show_v"):
        # Показать фото версии
        version = int(action.replace("content_show_v", ""))
        if user_id in active_creations:
            creator = active_creations[user_id]
            photo_path = creator.base_dir / f"main_photo_v{version}.jpg"
            if photo_path.exists():
                await callback.message.reply_photo(
                    photo=FSInputFile(photo_path),
                    caption=f"🖼️ Главное фото v{version}"
                )
        await callback.answer()
    
    elif action.startswith("content_approve_v"):
        # Одобрить и продолжить
        await callback.message.edit_text(
            callback.message.text + "\n\n👍 Вы одобрили этот вариант!"
        )
        await callback.answer("Создаём остальные материалы...")
    
    elif action.startswith("content_redo_v"):
        # Переделать
        if user_id in active_creations:
            creator = active_creations[user_id]
            creator.increment_version()
            await callback.message.answer(
                "🔄 Создаём новую версию..."
            )
            # Здесь можно запустить пересоздание
        await callback.answer()
    
    elif action == "content_download_all":
        # Скачать все файлы (отправляем как zip)
        if user_id in active_creations:
            creator = active_creations[user_id]
            zip_path = creator.base_dir / "content.zip"
            
            # Создаём zip архив
            import shutil
            shutil.make_archive(
                str(creator.base_dir / "content"),
                'zip',
                creator.base_dir
            )
            
            await callback.message.reply_document(
                document=FSInputFile(zip_path),
                caption="📦 Все файлы контента"
            )
        await callback.answer()
    
    elif action == "content_show_video":
        if user_id in active_creations:
            creator = active_creations[user_id]
            video_path = creator.base_dir / "video" / "cover_video.mp4"
            if video_path.exists():
                await callback.message.reply_video(
                    video=FSInputFile(video_path),
                    caption="🎬 Видео-обложка"
                )
        await callback.answer()
    
    elif action == "content_show_cards":
        if user_id in active_creations:
            creator = active_creations[user_id]
            cards_dir = creator.base_dir / "cards"
            if cards_dir.exists():
                cards = sorted(cards_dir.glob("card_*.jpg"))
                for card in cards:
                    await callback.message.reply_photo(
                        photo=FSInputFile(card),
                        caption=f"📸 {card.stem}"
                    )
        await callback.answer()


# ============================================================================
# Интеграция с mpstats_content_ai
# ============================================================================

async def start_content_from_recommendations(user_id: str, recommendations: dict, bot: Bot, chat_id: int):
    """Запуск создания контента на основе recommendations.json"""
    if not CONTENT_CREATOR_AVAILABLE:
        await bot.send_message(
            chat_id,
            "❌ Модуль создания контента недоступен"
        )
        return
    
    # Создаём ContentCreator
    article_id = f"{user_id}_{int(asyncio.get_event_loop().time())}"
    creator = ContentCreator(user_id, article_id)
    active_creations[user_id] = creator
    
    # Получаем данные из рекомендаций
    product_name = recommendations.get("product_name", "Товар")
    marketplace = recommendations.get("marketplace", "wb")
    
    # Пытаемся получить цену из конкурентов
    competitors = recommendations.get("competitors", [])
    avg_price = 0
    if competitors:
        prices = [c.get("price", 0) for c in competitors if c.get("price")]
        if prices:
            avg_price = sum(prices) / len(prices)
    
    price = f"{int(avg_price):,}₽".replace(",", " ") if avg_price > 0 else "Цена по запросу"
    
    # Запускаем создание
    status_msg = await bot.send_message(
        chat_id,
        creator.get_status_bar(),
        reply_markup=get_creation_status_keyboard()
    )
    
    asyncio.create_task(
        create_content_task(
            bot, chat_id, status_msg.message_id,
            creator, product_name, price, marketplace, user_id
        )
    )


# Экспорт
__all__ = [
    'content_router',
    'ContentCreationState',
    'start_content_from_recommendations',
    'CONTENT_CREATOR_AVAILABLE'
]
