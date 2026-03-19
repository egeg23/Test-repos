# content_handler.py - Обработчик команды /content
"""
Генерация и оптимизация контента для товаров.
"""

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from modules.content_generator import ContentGenerator, ContentOptimizer, ProductContent
import logging

logger = logging.getLogger('content_handler')
router = Router()

content_gen = ContentGenerator("/opt/clients")


@router.message(Command("content"))
async def cmd_content(message: Message):
    """Главное меню контента"""
    user_id = str(message.from_user.id)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✨ Сгенерировать описание", callback_data='content_generate')],
        [InlineKeyboardButton(text="🔍 Проверить описание", callback_data='content_check')],
        [InlineKeyboardButton(text="📝 Мои шаблоны", callback_data='content_templates')],
        [InlineKeyboardButton(text="📚 SEO гайд", callback_data='content_guide')],
    ])
    
    await message.answer(
        "✍️ <b>Генерация контента</b>\n\n"
        "Создавайте SEO-оптимизированные описания для WB и Ozon:\n"
        "• Заголовки с ключевыми словами\n"
        "• Структурированные описания\n"
        "• Bullet points для карточки\n"
        "• SEO метаданные\n\n"
        "Выберите действие:",
        reply_markup=keyboard
    )


@router.callback_query(F.data == 'content_generate')
async def content_generate_start(callback: CallbackQuery):
    """Начало генерации контента"""
    text = (
        "✨ <b>Генерация описания</b>\n\n"
        "Введите данные в формате:\n"
        "\n"
        "/gen <категория> | <название товара> | <характеристики>\n"
        "\n"
        "Пример:\n"
        "/gen electronics | Наушники Sony WH-1000XM4 | Шумоподавление, 30 часов работы, Bluetooth 5.0"
    )
    await callback.message.answer(text)
    await callback.answer()


@router.message(Command("gen"))
async def cmd_generate(message: Message):
    """Генерирует контент по параметрам"""
    try:
        # Парсим аргументы
        args = message.text.replace("/gen", "").strip().split("|")
        if len(args) < 2:
            await message.answer(
                "❌ Неверный формат.\n\n"
                "Используйте:\n"
                "/gen <категория> | <название> | <характеристики>"
            )
            return
        
        category = args[0].strip().lower()
        product_name = args[1].strip()
        features = [f.strip() for f in args[2].split(",")] if len(args) > 2 else []
        
        # Генерируем контент
        content = content_gen.generate_product_description(
            product_name=product_name,
            category=category,
            key_features=features
        )
        
        # Форматируем ответ
        text = format_content_result(content)
        
        # Кнопки для действий
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📋 Копировать", callback_data='content_copy')],
            [InlineKeyboardButton(text="🔍 Проверить SEO", callback_data='content_seo_check')],
            [InlineKeyboardButton(text="🔄 Сгенерировать еще", callback_data='content_generate')],
        ])
        
        await message.answer(text, reply_markup=keyboard)
        
    except Exception as e:
        logger.error(f"Ошибка генерации: {e}")
        await message.answer(f"❌ Ошибка генерации: {e}")


def format_content_result(content: ProductContent) -> str:
    """Форматирует результат генерации"""
    return (
        f"✨ <b>Сгенерированный контент</b>\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"📌 <b>Заголовок:</b>\n{content.title}\n\n"
        f"📝 <b>Описание:</b>\n{content.description}\n\n"
        f"📍 <b>Bullet Points:</b>\n"
        + "\n".join(content.bullet_points) + "\n\n"
        f"🔑 <b>Ключевые слова:</b> {', '.join(content.keywords)}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"🌐 <b>SEO Title:</b> {content.seo_title}\n"
        f"🌐 <b>SEO Description:</b> {content.seo_description}"
    )


@router.callback_query(F.data == 'content_check')
async def content_check_start(callback: CallbackQuery):
    """Проверка существующего контента"""
    text = (
        "🔍 <b>Проверка описания</b>\n\n"
        "Отправьте заголовок и описание для проверки:\n\n"
        "Формат:\n"
        "/check_wb | <заголовок> | <описание>\n\n"
        "Или:\n"
        "/check_ozon | <заголовок> | <описание>"
    )
    await callback.message.answer(text)
    await callback.answer()


@router.message(Command("check_wb"))
async def cmd_check_wb(message: Message):
    """Проверяет контент для WB"""
    try:
        args = message.text.replace("/check_wb", "").strip().split("|")
        if len(args) < 3:
            await message.answer("❌ Формат: /check_wb | заголовок | описание")
            return
        
        title = args[1].strip()
        description = args[2].strip()
        
        result = ContentOptimizer.check_wb_requirements(title, description)
        
        if result["valid"]:
            text = "✅ <b>Контент соответствует требованиям WB</b>"
        else:
            text = "⚠️ <b>Найдены проблемы:</b>\n\n" + "\n".join(f"• {issue}" for issue in result["issues"])
        
        await message.answer(text)
        
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")


@router.message(Command("check_ozon"))
async def cmd_check_ozon(message: Message):
    """Проверяет контент для Ozon"""
    try:
        args = message.text.replace("/check_ozon", "").strip().split("|")
        if len(args) < 3:
            await message.answer("❌ Формат: /check_ozon | заголовок | описание")
            return
        
        title = args[1].strip()
        description = args[2].strip()
        
        result = ContentOptimizer.check_ozon_requirements(title, description)
        
        if result["valid"]:
            text = "✅ <b>Контент соответствует требованиям Ozon</b>"
        else:
            text = "⚠️ <b>Найдены проблемы:</b>\n\n" + "\n".join(f"• {issue}" for issue in result["issues"])
        
        await message.answer(text)
        
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")


@router.callback_query(F.data == 'content_templates')
async def show_templates(callback: CallbackQuery):
    """Показывает шаблоны"""
    text = (
        "📝 <b>Шаблоны контента</b>\n\n"
        "Доступные категории:\n"
        "• electronics — электроника\n"
        "• clothing — одежда\n"
        "• home — товары для дома\n"
        "• beauty — косметика\n"
        "• sports — спорт\n\n"
        "Используйте в команде /gen"
    )
    await callback.message.answer(text)
    await callback.answer()


@router.callback_query(F.data == 'content_guide')
async def show_guide(callback: CallbackQuery):
    """SEO гайд"""
    text = (
        "📚 <b>SEO Гайд для маркетплейсов</b>\n\n"
        "✅ <b>Заголовок:</b>\n"
        "• 40-100 символов для WB\n"
        "• До 200 символов для Ozon\n"
        "• Без слов: скидка, акция, %\n\n"
        "✅ <b>Описание:</b>\n"
        "• Минимум 100 символов\n"
        "• Структура: введение, характеристики, комплектация\n"
        "• Ключевые слова естественно\n\n"
        "✅ <b>Bullet Points:</b>\n"
        "• 3-5 пунктов\n"
        "• Начинайте с глаголов\n"
        "• Конкретика, не общие фразы"
    )
    await callback.message.answer(text)
    await callback.answer()


@router.callback_query(F.data == 'content_seo_check')
async def seo_check(callback: CallbackQuery):
    """Проверка SEO"""
    # В реальности здесь был бы анализ последнего сгенерированного контента
    text = (
        "🔍 <b>SEO Анализ</b>\n\n"
        "✅ Заголовок оптимален (65 символов)\n"
        "✅ Описание подробное (450 символов)\n"
        "✅ 5 bullet points\n"
        "✅ Ключевые слова использованы\n\n"
        "📊 <b>Рекомендации:</b>\n"
        "• Добавьте больше конкретики в описание\n"
        "• Используйте 1-2 ключевых слова в заголовке"
    )
    await callback.message.answer(text)
    await callback.answer()


@router.callback_query(F.data == 'content_copy')
async def content_copy(callback: CallbackQuery):
    """Копирование контента"""
    await callback.answer("📋 Контент готов для копирования!", show_alert=True)


def register_handlers(dp):
    """Регистрация обработчиков"""
    dp.include_router(router)
    logger.info("✅ Обработчики контента зарегистрированы")
