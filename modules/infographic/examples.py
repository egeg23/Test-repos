#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Примеры использования модуля infographic_analyzer

Демонстрирует:
1. Анализ категорий
2. Получение паттернов
3. Генерацию инфографики
4. Интеграцию с ботом
"""

import json
from typing import Dict, List

# Импорт модуля
from modules.infographic_analyzer import (
    InfographicAPI,
    analyze_category,
    get_patterns,
    generate_card,
    get_api,
    STYLES,
    CATEGORIES,
    CATEGORY_NAMES
)


def demo_analyze_categories():
    """Демо: Анализ категорий"""
    print("=" * 70)
    print("ДЕМО 1: Анализ категорий")
    print("=" * 70)
    
    api = get_api()
    
    # Анализируем несколько категорий
    for category in ["electronics", "clothing", "cosmetics"]:
        print(f"\n📊 Анализ: {CATEGORY_NAMES[category]}")
        print("-" * 40)
        
        result = api.analyze_category(category)
        
        print(f"   Проанализировано карточек: {result['total_analyzed']}")
        print(f"   Средний success rate: {result['average_success_rate']:.1%}")
        print(f"   Популярные блоки: {', '.join(b['type'] for b in result['popular_blocks'][:4])}")
        print(f"   Топ-триггеры: {', '.join(result['top_triggers'][:3])}")


def demo_get_patterns():
    """Демо: Получение паттернов"""
    print("\n" + "=" * 70)
    print("ДЕМО 2: Получение паттернов")
    print("=" * 70)
    
    api = get_api()
    
    # Все паттерны
    print("\n📋 Все доступные паттерны:")
    all_patterns = api.get_patterns()
    for p in all_patterns[:5]:
        print(f"   • {p['pattern_name']} ({p['category']}, {p['style']}) - {p['success_rate']:.0%}")
    
    # Паттерны по категории
    print("\n📋 Паттерны для 'electronics':")
    electronics_patterns = api.get_patterns(category="electronics")
    for p in electronics_patterns:
        print(f"   • {p['pattern_name']} ({p['style']}) - {p['block_count']} блоков")
    
    # Паттерны по стилю
    print("\n📋 Паттерны стиля 'premium':")
    premium_patterns = api.get_patterns(style="premium")
    for p in premium_patterns[:5]:
        print(f"   • {p['pattern_name']} ({p['category']}) - {p['success_rate']:.0%}")


def demo_generate_simple():
    """Демо: Простая генерация карточки"""
    print("\n" + "=" * 70)
    print("ДЕМО 3: Генерация карточки (простой пример)")
    print("=" * 70)
    
    # Данные товара
    product = {
        "name": "Смартфон Pro Max 256GB",
        "price": 89990,
        "old_price": 109990,
        "rating": 4.8,
        "reviews": 1523,
        "badge": "Топ продаж",
        "delivery": "Доставка завтра",
        "benefits": [
            "Гарантия 2 года",
            "Рассрочка 0%",
            "Оригинал"
        ],
        "image_url": None  # Можно добавить URL изображения
    }
    
    # Генерация в разных стилях
    styles = ["bright", "tech", "premium", "minimal", "lifestyle"]
    
    print(f"\n🎨 Товар: {product['name']}")
    print(f"   Цена: {product['price']:,} ₽ (было {product['old_price']:,} ₽)")
    print(f"   Скидка: {int((1 - product['price']/product['old_price'])*100)}%")
    print()
    
    generated_files = []
    for style in styles:
        try:
            filepath = generate_card(product, style=style, category="electronics")
            generated_files.append((style, filepath))
            print(f"   ✅ Стиль '{style}': {filepath}")
        except Exception as e:
            print(f"   ❌ Стиль '{style}': {e}")
    
    return generated_files


def demo_generate_complex():
    """Демо: Сложная генерация с разными категориями"""
    print("\n" + "=" * 70)
    print("ДЕМО 4: Генерация для разных категорий")
    print("=" * 70)
    
    api = get_api()
    
    # Примеры товаров по категориям
    products = {
        "clothing": {
            "name": "Зимняя куртка Premium",
            "price": 12990,
            "old_price": 18990,
            "rating": 4.7,
            "reviews": 892,
            "badge": "-30%",
            "delivery": "Бесплатная доставка",
            "benefits": [
                "Натуральный пух",
                "Водоотталкивающая ткань",
                "Размеры XS-5XL",
                "Примерка перед покупкой"
            ]
        },
        "cosmetics": {
            "name": "Набор уходовой косметики",
            "price": 4590,
            "old_price": 6990,
            "rating": 4.9,
            "reviews": 3456,
            "badge": "Хит",
            "delivery": "Сегодня",
            "benefits": [
                "100% оригинал",
                "Натуральный состав",
                "Подарок внутри",
                "Сертифицировано"
            ]
        },
        "kids": {
            "name": "Развивающий конструктор",
            "price": 2990,
            "old_price": 4990,
            "rating": 4.8,
            "reviews": 567,
            "badge": "Новинка",
            "delivery": "Завтра",
            "benefits": [
                "Безопасные материалы",
                "С 3 лет",
                "Развивает моторику",
                "Прочная конструкция"
            ]
        }
    }
    
    generated_files = []
    
    for category, product in products.items():
        print(f"\n👕 Категория: {CATEGORY_NAMES[category]}")
        print(f"   Товар: {product['name']}")
        
        for style in ["bright", "lifestyle"]:
            try:
                filepath = api.generate_card(product, style=style, category=category)
                generated_files.append((category, style, filepath))
                print(f"   ✅ {style}: {filepath}")
            except Exception as e:
                print(f"   ❌ {style}: {e}")
    
    return generated_files


def demo_bot_integration():
    """Демо: Пример интеграции с ботом"""
    print("\n" + "=" * 70)
    print("ДЕМО 5: Интеграция с ботом Telegram")
    print("=" * 70)
    
    code = '''
# Пример интеграции в бота (aiogram)

from aiogram import Bot, Dispatcher, types
from modules.infographic_analyzer import (
    InfographicAPI, generate_card, get_patterns
)

bot = Bot(token="YOUR_TOKEN")
dp = Dispatcher()

# Инициализация API
api = InfographicAPI()

@dp.message_handler(commands=['styles'])
async def show_styles(message: types.Message):
    """Показать доступные стили"""
    styles = api.get_styles()
    text = "🎨 Доступные стили инфографики:\n\n"
    for code, info in styles.items():
        text += f"• *{info['name']}* - {info['description']}\n"
    await message.reply(text, parse_mode="Markdown")

@dp.message_handler(commands=['patterns'])
async def show_patterns(message: types.Message):
    """Показать паттерны для категории"""
    args = message.get_args().split()
    category = args[0] if args else "electronics"
    
    patterns = api.get_patterns(category=category)
    text = f"📋 Паттерны для {category}:\n\n"
    for p in patterns[:5]:
        text += f"• {p['pattern_name']} ({p['style']}) - {p['success_rate']:.0%}\\n"
    
    await message.reply(text)

@dp.message_handler(commands=['generate'])
async def generate_infographic(message: types.Message):
    """Генерация инфографики"""
    # Пример: /generate bright electronics
    args = message.get_args().split()
    style = args[0] if len(args) > 0 else "bright"
    category = args[1] if len(args) > 1 else "electronics"
    
    # Данные товара (в реальности из базы или API)
    product = {
        "name": "Смартфон XYZ Pro",
        "price": 49990,
        "old_price": 59990,
        "rating": 4.8,
        "reviews": 1234,
        "benefits": ["Гарантия 2 года", "Оригинал"]
    }
    
    # Генерация
    filepath = generate_card(product, style=style, category=category)
    
    # Отправка
    with open(filepath, 'rb') as f:
        await message.reply_photo(f, caption=f"🎨 Стиль: {style}")

@dp.message_handler(commands=['analyze'])
async def analyze_category_cmd(message: types.Message):
    """Анализ категории"""
    args = message.get_args().split()
    category = args[0] if args else "electronics"
    
    result = api.analyze_category(category)
    
    text = f"📊 Анализ {result['category_name']}:\n\n"
    text += f"Проанализировано: {result['total_analyzed']} карточек\n"
    text += f"Успешность: {result['average_success_rate']:.0%}\n\n"
    text += "Топ триггеры:\n"
    for i, trigger in enumerate(result['top_triggers'][:5], 1):
        text += f"{i}. {trigger}\n"
    
    await message.reply(text)
'''
    print(code)


def demo_json_structure():
    """Демо: Структура паттерна в JSON"""
    print("\n" + "=" * 70)
    print("ДЕМО 6: Структура паттерна (JSON)")
    print("=" * 70)
    
    example_pattern = {
        "category": "electronics",
        "pattern_name": "tech_premium",
        "style": "tech",
        "colors": {
            "primary": "#1565c0",
            "accent": "#00b0ff",
            "background": "#e3f2fd",
            "text": "#0d47a1",
            "text_secondary": "#546e7a",
            "success": "#00c853",
            "warning": "#ffd600",
            "danger": "#dd2c00"
        },
        "blocks": [
            {
                "type": "header",
                "position": [80, 80],
                "size": [1440, 120],
                "font_size": 88,
                "bold": True,
                "color": "#0d47a1",
                "z_index": 0
            },
            {
                "type": "image",
                "position": [100, 280],
                "size": [700, 700],
                "z_index": 1
            },
            {
                "type": "price",
                "position": [900, 1200],
                "size": [600, 200],
                "font_size": 96,
                "bold": True,
                "color": "#1565c0",
                "z_index": 0
            },
            {
                "type": "benefits",
                "position": [900, 350],
                "size": [600, 500],
                "font_size": 44,
                "color": "#0d47a1",
                "z_index": 0
            },
            {
                "type": "badge",
                "position": [1300, 80],
                "size": [200, 80],
                "font_size": 36,
                "color": "#ffffff",
                "z_index": 10
            },
            {
                "type": "rating",
                "position": [80, 1400],
                "size": [400, 80],
                "font_size": 32,
                "color": "#546e7a",
                "z_index": 0
            }
        ],
        "triggers": [
            "Гарантия 2 года",
            "Доставка 1 день",
            "Оригинал",
            "Рассрочка 0%"
        ],
        "success_rate": 0.85,
        "created_at": "2025-03-17T00:00:00"
    }
    
    print("\n" + json.dumps(example_pattern, indent=2, ensure_ascii=False))


def run_all_demos():
    """Запуск всех демо"""
    print("\n" + "🚀" * 35)
    print("  ЗАПУСК ВСЕХ ДЕМОНСТРАЦИЙ МОДУЛЯ INFOGRAPHIC_ANALYZER")
    print("🚀" * 35 + "\n")
    
    try:
        demo_analyze_categories()
    except Exception as e:
        print(f"Ошибка в demo_analyze_categories: {e}")
    
    try:
        demo_get_patterns()
    except Exception as e:
        print(f"Ошибка в demo_get_patterns: {e}")
    
    try:
        generated = demo_generate_simple()
        print(f"\n   📁 Сгенерировано {len(generated)} файлов")
    except Exception as e:
        print(f"Ошибка в demo_generate_simple: {e}")
    
    try:
        generated = demo_generate_complex()
        print(f"\n   📁 Сгенерировано {len(generated)} файлов")
    except Exception as e:
        print(f"Ошибка в demo_generate_complex: {e}")
    
    try:
        demo_bot_integration()
    except Exception as e:
        print(f"Ошибка в demo_bot_integration: {e}")
    
    try:
        demo_json_structure()
    except Exception as e:
        print(f"Ошибка в demo_json_structure: {e}")
    
    print("\n" + "=" * 70)
    print("✅ Все демо завершены!")
    print("=" * 70)
    print("\n📁 Файлы сохранены в:")
    print("   /opt/telegram_bot/modules/infographic/cache/")
    print("   /opt/telegram_bot/modules/infographic/patterns/")
    print("\n💡 Используйте модуль:")
    print("   from modules.infographic_analyzer import generate_card")
    print("   filepath = generate_card(product_data, style='bright')")
    print("=" * 70)


if __name__ == "__main__":
    run_all_demos()
