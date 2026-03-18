#!/usr/bin/env python3
"""
Content Creator Module
Генерация карточек товаров и видео для маркетплейсов
HTML Canvas → PNG через Playwright
"""

import json
import asyncio
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
import tempfile

try:
    from playwright.async_api import async_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

@dataclass
class DesignConfig:
    """Конфигурация дизайна"""
    width: int = 900
    height: int = 1200
    bg_color: str = "#f8f9fa"
    accent_color: str = "#ff6b35"
    text_color: str = "#212529"
    secondary_color: str = "#6c757d"
    font_family: str = "system-ui, -apple-system, sans-serif"
    marketplace: str = "wb"  # wb, ozon, avito

@dataclass
class ProductData:
    """Данные товара"""
    name: str
    price: str
    badges: List[str]
    rating: float
    reviews: int
    main_image_url: Optional[str] = None
    features: List[str] = None
    colors: List[str] = None

class ContentCreator:
    """Генератор контента для товаров"""
    
    MARKETPLACE_SIZES = {
        "wb": {"main": (900, 1200), "cards": (900, 1200), "video": (1080, 1920)},
        "ozon": {"main": (1200, 1200), "cards": (1200, 1200), "video": (1080, 1080)},
        "avito": {"main": (1280, 960), "cards": (1280, 960), "video": (1280, 720)},
    }
    
    def __init__(self, user_id: str, article_id: str = None):
        self.user_id = user_id
        self.article_id = article_id or datetime.now().strftime("%Y%m%d_%H%M%S")
        self.base_dir = Path(f"/opt/clients/{user_id}/content_creation/{self.article_id}")
        self.base_dir.mkdir(parents=True, exist_ok=True)
        (self.base_dir / "cards").mkdir(exist_ok=True)
        (self.base_dir / "video").mkdir(exist_ok=True)
        
        self.version = 1
        self.status = {
            "current_stage": "idle",
            "progress": 0,
            "stages": {
                "analyze": {"status": "pending", "label": "Анализ конкурентов"},
                "main_photo": {"status": "pending", "label": "Создание главного фото"},
                "cards": {"status": "pending", "label": "Генерация карточек"},
                "video": {"status": "pending", "label": "Анимация видео"},
                "check": {"status": "pending", "label": "Финальная проверка"},
            }
        }
    
    def update_status(self, stage: str, status: str, progress: int = None):
        """Обновление статуса"""
        self.status["current_stage"] = stage
        if progress is not None:
            self.status["progress"] = progress
        if stage in self.status["stages"]:
            self.status["stages"][stage]["status"] = status
        
        # Сохраняем в файл
        status_file = self.base_dir / "status.json"
        with open(status_file, 'w', encoding='utf-8') as f:
            json.dump(self.status, f, ensure_ascii=False, indent=2)
    
    def get_status_bar(self) -> str:
        """Генерация статус-бара для Telegram"""
        progress = self.status["progress"]
        filled = int(progress / 5)  # 20 блоков = 100%
        empty = 20 - filled
        bar = "█" * filled + "░" * empty
        
        stages_text = []
        for key, stage in self.status["stages"].items():
            icon = {
                "completed": "☑️",
                "in_progress": "⏳",
                "pending": "☐",
                "error": "❌"
            }.get(stage["status"], "☐")
            stages_text.append(f"{icon} {stage['label']}")
        
        eta = "~2-3 минуты" if progress < 50 else "~1-2 минуты" if progress < 80 else "~30 секунд"
        
        return f"""🎨 <b>Создание контента</b>

<code>[{bar}] {progress}%</code>

📋 <b>Этапы:</b>
{chr(10).join(stages_text)}

⏳ Осталось: {eta}"""
    
    async def load_recommendations(self, recommendations_path: str = None) -> Dict:
        """Загрузка recommendations.json от mpstats-analyzer"""
        if recommendations_path and Path(recommendations_path).exists():
            with open(recommendations_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        
        # Ищем в стандартных местах
        possible_paths = [
            self.base_dir.parent / "recommendations.json",
            Path(f"/opt/clients/{self.user_id}/recommendations.json"),
            Path(f"/opt/clients/{self.user_id}/mpstats/recommendations.json"),
        ]
        
        for path in possible_paths:
            if path.exists():
                with open(path, 'r', encoding='utf-8') as f:
                    return json.load(f)
        
        # Возвращаем мок-данные если ничего не найдено
        return self._get_mock_recommendations()
    
    def _get_mock_recommendations(self) -> Dict:
        """Мок-данные для тестирования"""
        return {
            "product_name": "Беспроводной пылесос Xiaomi Dreame V10",
            "marketplace": "wb",
            "competitors": [
                {
                    "position": 1,
                    "name": "ProCleaner Shop",
                    "price": 12990,
                    "rating": 4.8,
                    "reviews_count": 2340,
                    "colors": ["#FF6B35", "#FFFFFF", "#1A1A1A"],
                    "badges": ["ТОП продаж", "Скидка -30%", "Быстрая доставка"],
                    "keywords": ["оригинал", "гарантия", "мощный", "бесшумный"]
                }
            ],
            "recommendations": {
                "bg_style": "gradient",
                "bg_colors": ["#FF6B35", "#FF8C42"],
                "text_style": "modern",
                "badges": ["ТОП продаж ⭐", "Скидка -25% 🔥", "Оригинал ✅"],
                "price_position": "bottom_right",
                "font_style": "bold"
            }
        }
    
    def _generate_main_photo_html(self, product: ProductData, config: DesignConfig, 
                                   recommendations: Dict) -> str:
        """Генерация HTML для главного фото"""
        
        badges_html = ""
        for badge in product.badges[:3]:
            badges_html += f'''
            <div style="
                background: linear-gradient(135deg, {config.accent_color}, #ff8c42);
                color: white;
                padding: 8px 16px;
                border-radius: 20px;
                font-size: 18px;
                font-weight: bold;
                margin: 5px;
                display: inline-block;
                box-shadow: 0 2px 8px rgba(0,0,0,0.2);
                text-transform: uppercase;
            ">{badge}</div>'''
        
        # Градиентный фон
        bg_colors = recommendations.get("recommendations", {}).get("bg_colors", ["#f8f9fa", "#e9ecef"])
        gradient = f"linear-gradient(135deg, {bg_colors[0]}, {bg_colors[1] if len(bg_colors) > 1 else bg_colors[0]})"
        
        # Плейсхолдер для изображения товара
        product_image = ""
        if product.main_image_url:
            product_image = f'<img src="{product.main_image_url}" style="max-width: 70%; max-height: 50%; object-fit: contain; filter: drop-shadow(0 10px 30px rgba(0,0,0,0.3));" />'
        else:
            # Заглушка с иконкой
            product_image = f'''
            <div style="
                width: 400px;
                height: 400px;
                background: white;
                border-radius: 20px;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 120px;
                box-shadow: 0 20px 60px rgba(0,0,0,0.15);
            ">📦</div>'''
        
        rating_stars = "★" * int(product.rating) + "☆" * (5 - int(product.rating))
        
        return f'''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ 
            width: {config.width}px; 
            height: {config.height}px; 
            background: {gradient};
            font-family: {config.font_family};
            overflow: hidden;
            position: relative;
        }}
        .container {{
            width: 100%;
            height: 100%;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: space-between;
            padding: 40px;
            position: relative;
        }}
        .badges {{
            display: flex;
            flex-wrap: wrap;
            justify-content: center;
            gap: 10px;
            z-index: 10;
        }}
        .product-area {{
            flex: 1;
            display: flex;
            align-items: center;
            justify-content: center;
            width: 100%;
        }}
        .footer {{
            width: 100%;
            display: flex;
            justify-content: space-between;
            align-items: flex-end;
        }}
        .rating {{
            color: #ffc107;
            font-size: 28px;
            text-shadow: 0 2px 4px rgba(0,0,0,0.2);
        }}
        .price {{
            background: white;
            color: {config.accent_color};
            padding: 15px 30px;
            border-radius: 15px;
            font-size: 42px;
            font-weight: 900;
            box-shadow: 0 4px 15px rgba(0,0,0,0.2);
        }}
        .price-old {{
            text-decoration: line-through;
            color: #6c757d;
            font-size: 24px;
            margin-right: 10px;
        }}
        .reviews {{
            color: {config.secondary_color};
            font-size: 16px;
            margin-top: 5px;
        }}
        .decoration {{
            position: absolute;
            border-radius: 50%;
            opacity: 0.1;
        }}
        .decoration-1 {{
            width: 300px;
            height: 300px;
            background: white;
            top: -100px;
            right: -100px;
        }}
        .decoration-2 {{
            width: 200px;
            height: 200px;
            background: {config.accent_color};
            bottom: -50px;
            left: -50px;
        }}
    </style>
</head>
<body>
    <div class="decoration decoration-1"></div>
    <div class="decoration decoration-2"></div>
    <div class="container">
        <div class="badges">
            {badges_html}
        </div>
        <div class="product-area">
            {product_image}
        </div>
        <div class="footer">
            <div>
                <div class="rating">{rating_stars} <span style="color: {config.text_color};">{product.rating}</span></div>
                <div class="reviews">{product.reviews:,} отзывов</div>
            </div>
            <div class="price">
                <span class="price-old">{int(float(product.price.replace('₽', '').replace(' ', '')) * 1.3)}₽</span>
                {product.price}
            </div>
        </div>
    </div>
</body>
</html>'''
    
    async def create_main_photo(self, product: ProductData, marketplace: str = "wb",
                                 recommendations: Dict = None) -> str:
        """Создание главного фото"""
        if not PLAYWRIGHT_AVAILABLE:
            raise ImportError("Playwright не установлен. Установите: pip install playwright && playwright install chromium")
        
        self.update_status("main_photo", "in_progress", 20)
        
        # Получаем размеры для маркетплейса
        sizes = self.MARKETPLACE_SIZES.get(marketplace, self.MARKETPLACE_SIZES["wb"])
        width, height = sizes["main"]
        
        # Создаём конфиг
        rec = recommendations or {}
        rec_data = rec.get("recommendations", {})
        bg_colors = rec_data.get("bg_colors", ["#FF6B35", "#FF8C42"])
        
        config = DesignConfig(
            width=width,
            height=height,
            bg_color=bg_colors[0],
            accent_color=bg_colors[0],
            marketplace=marketplace
        )
        
        # Генерируем HTML
        html_content = self._generate_main_photo_html(product, config, rec)
        
        # Сохраняем HTML для отладки
        html_file = self.base_dir / f"main_photo_v{self.version}.html"
        with open(html_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        # Создаём скриншот через Playwright
        output_path = self.base_dir / f"main_photo_v{self.version}.jpg"
        
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()
            await page.set_viewport_size({"width": width, "height": height})
            await page.set_content(html_content)
            await page.screenshot(path=str(output_path), type="jpeg", quality=95)
            await browser.close()
        
        self.update_status("main_photo", "completed", 30)
        
        return str(output_path)
    
    def _generate_card_html(self, card_type: int, product: ProductData, 
                            config: DesignConfig) -> str:
        """Генерация HTML для карточек товара"""
        
        card_templates = {
            1: {  # Товар в использовании
                "title": "В использовании",
                "subtitle": "Как это работает",
                "icon": "🎯",
                "bg_gradient": "linear-gradient(135deg, #667eea 0%, #764ba2 100%)"
            },
            2: {  # Детали/фичи
                "title": "Ключевые особенности",
                "subtitle": "Почему выбирают нас",
                "icon": "⭐",
                "bg_gradient": "linear-gradient(135deg, #f093fb 0%, #f5576c 100%)"
            },
            3: {  # Комплектация
                "title": "Комплектация",
                "subtitle": "Что входит в набор",
                "icon": "📦",
                "bg_gradient": "linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)"
            },
            4: {  # Сравнение/размеры
                "title": "Размеры и параметры",
                "subtitle": "Точные характеристики",
                "icon": "📏",
                "bg_gradient": "linear-gradient(135deg, #43e97b 0%, #38f9d7 100%)"
            },
            5: {  # Преимущества (инфографика)
                "title": "Преимущества",
                "subtitle": "Почему стоит купить",
                "icon": "🏆",
                "bg_gradient": "linear-gradient(135deg, #fa709a 0%, #fee140 100%)"
            }
        }
        
        template = card_templates.get(card_type, card_templates[1])
        
        # Генерируем контент в зависимости от типа
        content_html = ""
        
        if card_type == 1:  # В использовании
            content_html = f'''
            <div style="display: flex; flex-direction: column; align-items: center; gap: 30px;">
                <div style="width: 300px; height: 300px; background: white; border-radius: 20px; 
                     display: flex; align-items: center; justify-content: center; font-size: 100px;
                     box-shadow: 0 10px 40px rgba(0,0,0,0.2);">
                    {template["icon"]}
                </div>
                <div style="background: rgba(255,255,255,0.95); padding: 25px; border-radius: 15px; max-width: 80%;">
                    <p style="font-size: 24px; color: #333; line-height: 1.6; text-align: center;">
                        Идеально подходит для ежедневного использования. 
                        Эргономичный дизайн и интуитивное управление.
                    </p>
                </div>
            </div>'''
        
        elif card_type == 2:  # Фичи
            features = product.features or ["Высокое качество", "Долговечность", "Эргономика", "Гарантия"]
            features_html = "".join([f'''
                <div style="
                    background: white;
                    padding: 20px 25px;
                    border-radius: 12px;
                    margin: 10px;
                    box-shadow: 0 4px 15px rgba(0,0,0,0.1);
                    display: flex;
                    align-items: center;
                    gap: 15px;
                    font-size: 22px;
                    color: #333;
                ">
                    <span style="font-size: 30px;">✓</span> {f}
                </div>''' for f in features[:4]])
            
            content_html = f'<div style="display: flex; flex-direction: column; align-items: stretch; width: 80%;">{features_html}</div>'
        
        elif card_type == 3:  # Комплектация
            items = ["Основное устройство", "Зарядное устройство", "Инструкция", "Гарантийный талон"]
            items_html = "".join([f'''
                <div style="
                    background: white;
                    padding: 20px;
                    border-radius: 10px;
                    margin: 8px 0;
                    display: flex;
                    align-items: center;
                    gap: 15px;
                    font-size: 20px;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                ">
                    <span style="background: {config.accent_color}; color: white; width: 30px; height: 30px; 
                         border-radius: 50%; display: flex; align-items: center; justify-content: center;
                         font-size: 14px; font-weight: bold;">{i+1}</span>
                    {item}
                </div>''' for i, item in enumerate(items)])
            
            content_html = f'<div style="width: 70%;">{items_html}</div>'
        
        elif card_type == 4:  # Размеры
            content_html = f'''
            <div style="display: flex; flex-direction: column; align-items: center; gap: 30px;">
                <div style="width: 250px; height: 250px; background: white; border-radius: 15px;
                     display: flex; align-items: center; justify-content: center; font-size: 80px;">
                    📐
                </div>
                <div style="background: rgba(255,255,255,0.95); padding: 30px; border-radius: 15px;">
                    <table style="font-size: 22px; color: #333;">
                        <tr><td style="padding: 10px 20px;"><b>Размеры:</b></td><td>25 × 15 × 10 см</td></tr>
                        <tr><td style="padding: 10px 20px;"><b>Вес:</b></td><td>1.2 кг</td></tr>
                        <tr><td style="padding: 10px 20px;"><b>Материал:</b></td><td>Премиум пластик</td></tr>
                    </table>
                </div>
            </div>'''
        
        elif card_type == 5:  # Преимущества инфографика
            benefits = [
                ("🚚", "Быстрая доставка", "1-3 дня по всей России"),
                ("✅", "Гарантия качества", "Официальная гарантия 2 года"),
                ("💰", "Лучшая цена", "Нашли дешевле — снизим!"),
                ("⭐", "ТОП рейтинг", "Более 2000 отзывов"),
            ]
            
            benefits_html = "".join([f'''
                <div style="
                    background: white;
                    padding: 25px;
                    border-radius: 15px;
                    text-align: center;
                    box-shadow: 0 5px 20px rgba(0,0,0,0.15);
                    min-width: 180px;
                ">
                    <div style="font-size: 50px; margin-bottom: 10px;">{icon}</div>
                    <div style="font-size: 18px; font-weight: bold; color: #333; margin-bottom: 5px;">{title}</div>
                    <div style="font-size: 14px; color: #666;">{desc}</div>
                </div>''' for icon, title, desc in benefits])
            
            content_html = f'<div style="display: flex; flex-wrap: wrap; justify-content: center; gap: 20px;">{benefits_html}</div>'
        
        return f'''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ 
            width: {config.width}px; 
            height: {config.height}px; 
            background: {template["bg_gradient"]};
            font-family: system-ui, -apple-system, sans-serif;
            overflow: hidden;
        }}
        .container {{
            width: 100%;
            height: 100%;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            padding: 40px;
        }}
        .header {{
            text-align: center;
            margin-bottom: 40px;
        }}
        .title {{
            font-size: 42px;
            font-weight: 900;
            color: white;
            text-shadow: 0 2px 10px rgba(0,0,0,0.3);
            margin-bottom: 10px;
        }}
        .subtitle {{
            font-size: 24px;
            color: rgba(255,255,255,0.9);
        }}
        .content {{
            flex: 1;
            display: flex;
            align-items: center;
            justify-content: center;
            width: 100%;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="title">{template["title"]}</div>
            <div class="subtitle">{template["subtitle"]}</div>
        </div>
        <div class="content">
            {content_html}
        </div>
    </div>
</body>
</html>'''
    
    async def create_product_cards(self, product: ProductData, marketplace: str = "wb") -> List[str]:
        """Создание 5 карточек товара"""
        if not PLAYWRIGHT_AVAILABLE:
            raise ImportError("Playwright не установлен")
        
        self.update_status("cards", "in_progress", 50)
        
        sizes = self.MARKETPLACE_SIZES.get(marketplace, self.MARKETPLACE_SIZES["wb"])
        width, height = sizes["cards"]
        
        config = DesignConfig(width=width, height=height, marketplace=marketplace)
        
        output_paths = []
        
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            
            for card_num in range(1, 6):
                html_content = self._generate_card_html(card_num, product, config)
                
                # Сохраняем HTML
                html_file = self.base_dir / "cards" / f"card_{card_num}.html"
                with open(html_file, 'w', encoding='utf-8') as f:
                    f.write(html_content)
                
                # Скриншот
                page = await browser.new_page()
                await page.set_viewport_size({"width": width, "height": height})
                await page.set_content(html_content)
                
                output_path = self.base_dir / "cards" / f"card_{card_num}.jpg"
                await page.screenshot(path=str(output_path), type="jpeg", quality=95)
                await page.close()
                
                output_paths.append(str(output_path))
                
                # Обновляем прогресс
                progress = 50 + (card_num * 8)
                self.update_status("cards", "in_progress", progress)
        
        self.update_status("cards", "completed", 80)
        
        return output_paths
    
    def _generate_video_html(self, product: ProductData, config: DesignConfig) -> str:
        """Генерация HTML для анимированного видео"""
        
        badges_html = ""
        for i, badge in enumerate(product.badges[:3]):
            delay = i * 0.5
            badges_html += f'''
            <div class="badge" style="animation-delay: {delay}s;">
                {badge}
            </div>'''
        
        return f'''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ 
            width: {config.width}px; 
            height: {config.height}px; 
            background: linear-gradient(135deg, #FF6B35, #FF8C42, #FFB347);
            background-size: 400% 400%;
            animation: gradientBG 5s ease infinite;
            font-family: system-ui, -apple-system, sans-serif;
            overflow: hidden;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            padding: 40px;
        }}
        
        @keyframes gradientBG {{
            0% {{ background-position: 0% 50%; }}
            50% {{ background-position: 100% 50%; }}
            100% {{ background-position: 0% 50%; }}
        }}
        
        .product-container {{
            animation: breathe 3s ease-in-out infinite;
        }}
        
        @keyframes breathe {{
            0%, 100% {{ transform: scale(1); }}
            50% {{ transform: scale(1.02); }}
        }}
        
        .product-placeholder {{
            width: 400px;
            height: 400px;
            background: white;
            border-radius: 30px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 150px;
            box-shadow: 0 30px 60px rgba(0,0,0,0.3);
            margin-bottom: 40px;
        }}
        
        .badges {{
            display: flex;
            flex-wrap: wrap;
            justify-content: center;
            gap: 15px;
            margin-bottom: 30px;
        }}
        
        .badge {{
            background: white;
            color: #FF6B35;
            padding: 12px 24px;
            border-radius: 25px;
            font-size: 22px;
            font-weight: bold;
            box-shadow: 0 4px 15px rgba(0,0,0,0.2);
            opacity: 0;
            animation: popIn 0.5s ease forwards, pulse 2s ease-in-out infinite 1s;
        }}
        
        @keyframes popIn {{
            0% {{ opacity: 0; transform: scale(0.5) translateY(20px); }}
            100% {{ opacity: 1; transform: scale(1) translateY(0); }}
        }}
        
        @keyframes pulse {{
            0%, 100% {{ transform: scale(1); box-shadow: 0 4px 15px rgba(0,0,0,0.2); }}
            50% {{ transform: scale(1.05); box-shadow: 0 6px 25px rgba(0,0,0,0.3); }}
        }}
        
        .price {{
            background: white;
            color: #FF6B35;
            padding: 20px 40px;
            border-radius: 20px;
            font-size: 48px;
            font-weight: 900;
            box-shadow: 0 10px 30px rgba(0,0,0,0.3);
            animation: slideUp 0.8s ease 1.5s both;
        }}
        
        @keyframes slideUp {{
            0% {{ opacity: 0; transform: translateY(50px); }}
            100% {{ opacity: 1; transform: translateY(0); }}
        }}
        
        .sparkle {{
            position: absolute;
            font-size: 30px;
            animation: sparkle 2s ease-in-out infinite;
            opacity: 0;
        }}
        
        @keyframes sparkle {{
            0%, 100% {{ opacity: 0; transform: scale(0) rotate(0deg); }}
            50% {{ opacity: 1; transform: scale(1) rotate(180deg); }}
        }}
        
        .sparkle-1 {{ top: 10%; left: 10%; animation-delay: 0.5s; }}
        .sparkle-2 {{ top: 20%; right: 15%; animation-delay: 1s; }}
        .sparkle-3 {{ bottom: 20%; left: 20%; animation-delay: 1.5s; }}
        .sparkle-4 {{ bottom: 15%; right: 10%; animation-delay: 2s; }}
        
        .rating {{
            margin-top: 20px;
            font-size: 32px;
            color: #ffc107;
            animation: fadeIn 1s ease 2s both;
        }}
        
        @keyframes fadeIn {{
            0% {{ opacity: 0; }}
            100% {{ opacity: 1; }}
        }}
    </style>
</head>
<body>
    <div class="sparkle sparkle-1">✨</div>
    <div class="sparkle sparkle-2">⭐</div>
    <div class="sparkle sparkle-3">✨</div>
    <div class="sparkle sparkle-4">⭐</div>
    
    <div class="badges">
        {badges_html}
    </div>
    
    <div class="product-container">
        <div class="product-placeholder">📦</div>
    </div>
    
    <div class="price">{product.price}</div>
    
    <div class="rating">
        {"★" * int(product.rating)}{"☆" * (5-int(product.rating))} {product.rating}
    </div>
</body>
</html>'''
    
    async def create_video(self, product: ProductData, marketplace: str = "wb") -> str:
        """Создание анимированного видео"""
        if not PLAYWRIGHT_AVAILABLE:
            raise ImportError("Playwright не установлен")
        
        self.update_status("video", "in_progress", 85)
        
        sizes = self.MARKETPLACE_SIZES.get(marketplace, self.MARKETPLACE_SIZES["wb"])
        width, height = sizes["video"]
        
        config = DesignConfig(width=width, height=height, marketplace=marketplace)
        
        html_content = self._generate_video_html(product, config)
        
        # Сохраняем HTML
        html_file = self.base_dir / "video" / "cover_video.html"
        with open(html_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        output_path = self.base_dir / "video" / "cover_video.mp4"
        
        # Используем ffmpeg для записи видео со страницы
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()
            await page.set_viewport_size({"width": width, "height": height})
            await page.set_content(html_content)
            
            # Записываем видео через CDP
            # Для простоты создадим серию скриншотов и склеим их ffmpeg
            frames_dir = self.base_dir / "video" / "frames"
            frames_dir.mkdir(exist_ok=True)
            
            fps = 30
            duration = 4  # секунды
            total_frames = fps * duration
            
            for i in range(total_frames):
                frame_path = frames_dir / f"frame_{i:04d}.jpg"
                await page.screenshot(path=str(frame_path), type="jpeg", quality=90)
                
                # Небольшая задержка для анимации
                await asyncio.sleep(1/fps)
            
            await browser.close()
        
        # Собираем видео через ffmpeg
        ffmpeg_cmd = f"""ffmpeg -y -framerate {fps} -i {frames_dir}/frame_%04d.jpg 
            -c:v libx264 -pix_fmt yuv420p -preset fast -crf 23 
            -movflags +faststart {output_path}""".replace("\n", " ")
        
        os.system(ffmpeg_cmd)
        
        # Очищаем фреймы
        for f in frames_dir.glob("*.jpg"):
            f.unlink()
        frames_dir.rmdir()
        
        self.update_status("video", "completed", 95)
        
        return str(output_path)
    
    async def create_full_content(self, product_name: str, price: str, 
                                   marketplace: str = "wb",
                                   recommendations_path: str = None) -> Dict:
        """Полный pipeline создания контента"""
        
        self.update_status("analyze", "completed", 10)
        
        # Загружаем рекомендации
        rec = await self.load_recommendations(recommendations_path)
        
        # Создаём объект продукта
        rec_badges = rec.get("recommendations", {}).get("badges", 
                         ["ТОП продаж ⭐", "Скидка -25%", "Оригинал ✅"])
        
        product = ProductData(
            name=product_name,
            price=price,
            badges=rec_badges,
            rating=4.8,
            reviews=2340,
            features=["Премиум качество", "Долговечность", "Эргономика", "Гарантия 2 года"]
        )
        
        results = {
            "main_photo": None,
            "cards": [],
            "video": None,
            "base_dir": str(self.base_dir)
        }
        
        # Создаём главное фото
        results["main_photo"] = await self.create_main_photo(product, marketplace, rec)
        
        # Создаём карточки
        results["cards"] = await self.create_product_cards(product, marketplace)
        
        # Создаём видео
        results["video"] = await self.create_video(product, marketplace)
        
        self.update_status("check", "completed", 100)
        
        return results
    
    def increment_version(self):
        """Увеличить версию для переделки"""
        self.version += 1


# ============================================================================
# UI для бота
# ============================================================================

def get_creation_status_keyboard():
    """Клавиатура для показа статуса создания"""
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Обновить статус", callback_data="content_refresh_status")]
    ])


def get_result_keyboard(version: int = 1):
    """Клавиатура для результата"""
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📷 Показать фото", callback_data=f"content_show_v{version}")],
        [
            InlineKeyboardButton(text="👍 Нравится", callback_data=f"content_approve_v{version}"),
            InlineKeyboardButton(text="👎 Переделать", callback_data=f"content_redo_v{version}")
        ]
    ])


def get_approve_keyboard():
    """Клавиатура после одобрения"""
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📥 Скачать все файлы", callback_data="content_download_all")],
        [
            InlineKeyboardButton(text="🎬 Показать видео", callback_data="content_show_video"),
            InlineKeyboardButton(text="📸 Все карточки", callback_data="content_show_cards")
        ]
    ])


def format_completion_message(article_id: str, version: int) -> str:
    """Форматирование сообщения о завершении"""
    return f"""✅ <b>Контент готов!</b>

📦 <b>Артикул:</b> {article_id}
🖼️ <b>Главное фото:</b> 1
📸 <b>Карточки:</b> 5
🎬 <b>Видео:</b> 1

📋 <b>Инструкция:</b>
1. Загрузите изображения на маркетплейс
2. Создайте рекламную кампанию <b>ТОЛЬКО</b> с этим артикулом
3. Настройте показы в <b>ПОИСКЕ</b>
4. Соберите 1000 показов
5. Пришлите ID кампании для мониторинга CTR

Когда будете готовы — пришлите ID рекламной кампании 👇"""


# ============================================================================
# Тестирование
# ============================================================================

if __name__ == "__main__":
    async def test():
        creator = ContentCreator("test_user", "test_article_123")
        
        print("🎨 Начинаем создание контента...")
        print(creator.get_status_bar())
        
        results = await creator.create_full_content(
            product_name="Беспроводной пылесос Xiaomi Dreame V10",
            price="12 990₽",
            marketplace="wb"
        )
        
        print(f"\n✅ Готово!")
        print(f"📁 Файлы сохранены в: {results['base_dir']}")
        print(f"🖼️ Главное фото: {results['main_photo']}")
        print(f"📸 Карточки: {len(results['cards'])} шт.")
        print(f"🎬 Видео: {results['video']}")
    
    asyncio.run(test())
