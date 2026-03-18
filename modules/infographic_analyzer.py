#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Модуль анализа и генерации инфографики для карточек товаров маркетплейсов
Поддерживает: Wildberries, Ozon
"""

import os
import json
import hashlib
import base64
import io
import re
import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path

# PIL для рендеринга
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
from PIL.Image import Resampling

# HTML рендеринг
from html.parser import HTMLParser

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Константы
MODULE_DIR = Path(__file__).parent
PATTERNS_DIR = MODULE_DIR / "infographic" / "patterns"
TEMPLATES_DIR = MODULE_DIR / "infographic" / "templates"
CACHE_DIR = MODULE_DIR / "infographic" / "cache"
FONTS_DIR = MODULE_DIR / "infographic" / "fonts"

# Размеры для карточек маркетплейсов
CARD_SIZE = (1600, 1600)  # WB/Ozon стандарт
THUMBNAIL_SIZE = (400, 400)

# Категории для анализа
CATEGORIES = [
    "electronics",
    "clothing", 
    "cosmetics",
    "kids",
    "home",
    "sports"
]

# Русские названия категорий
CATEGORY_NAMES = {
    "electronics": "Электроника",
    "clothing": "Одежда",
    "cosmetics": "Косметика", 
    "kids": "Детские товары",
    "home": "Дом и интерьер",
    "sports": "Спорт"
}


@dataclass
class ColorScheme:
    """Цветовая схема паттерна"""
    primary: str
    accent: str
    background: str
    text: str = "#000000"
    text_secondary: str = "#666666"
    success: str = "#00c853"
    warning: str = "#ff9100"
    danger: str = "#ff1744"
    
    def to_dict(self) -> Dict:
        return {
            "primary": self.primary,
            "accent": self.accent,
            "background": self.background,
            "text": self.text,
            "text_secondary": self.text_secondary,
            "success": self.success,
            "warning": self.warning,
            "danger": self.danger
        }


@dataclass
class Block:
    """Блок инфографики"""
    type: str
    position: Tuple[int, int]
    size: Tuple[int, int] = (200, 100)
    font_size: int = 48
    bold: bool = False
    color: str = "#000000"
    icon: Optional[str] = None
    text: Optional[str] = None
    z_index: int = 0
    
    def to_dict(self) -> Dict:
        return {
            "type": self.type,
            "position": list(self.position),
            "size": list(self.size),
            "font_size": self.font_size,
            "bold": self.bold,
            "color": self.color,
            "icon": self.icon,
            "text": self.text,
            "z_index": self.z_index
        }


@dataclass
class Pattern:
    """Паттерн инфографики"""
    category: str
    pattern_name: str
    colors: ColorScheme
    blocks: List[Block]
    triggers: List[str]
    success_rate: float = 0.0
    style: str = "default"
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict:
        return {
            "category": self.category,
            "pattern_name": self.pattern_name,
            "colors": self.colors.to_dict(),
            "blocks": [b.to_dict() for b in self.blocks],
            "triggers": self.triggers,
            "success_rate": self.success_rate,
            "style": self.style,
            "created_at": self.created_at
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Pattern':
        colors = ColorScheme(**data.get("colors", {}))
        blocks = [Block(**b) for b in data.get("blocks", [])]
        return cls(
            category=data["category"],
            pattern_name=data["pattern_name"],
            colors=colors,
            blocks=blocks,
            triggers=data.get("triggers", []),
            success_rate=data.get("success_rate", 0.0),
            style=data.get("style", "default"),
            created_at=data.get("created_at", datetime.now().isoformat())
        )


# ============================================
# БАЗОВЫЕ СТИЛИ ДИЗАЙНА
# ============================================

STYLES = {
    "premium": {
        "name": "Premium",
        "description": "Тёмные тона, золото, минимализм",
        "colors": {
            "primary": "#1a1a1a",
            "accent": "#d4af37",
            "background": "#0d0d0d",
            "text": "#ffffff",
            "text_secondary": "#b0b0b0",
            "success": "#4caf50",
            "warning": "#ff9800",
            "danger": "#f44336"
        },
        "fonts": {
            "header": ("Montserrat-Bold.ttf", 96),
            "subheader": ("Montserrat-SemiBold.ttf", 64),
            "body": ("Montserrat-Regular.ttf", 48),
            "caption": ("Montserrat-Light.ttf", 36)
        },
        "effects": ["gradient_overlay", "shadow", "glow"]
    },
    "bright": {
        "name": "Bright",
        "description": "Яркие цвета, эмодзи, скидки",
        "colors": {
            "primary": "#ff6b00",
            "accent": "#ff1744",
            "background": "#fff8e1",
            "text": "#212121",
            "text_secondary": "#757575",
            "success": "#00e676",
            "warning": "#ffea00",
            "danger": "#ff1744"
        },
        "fonts": {
            "header": ("Roboto-Black.ttf", 108),
            "subheader": ("Roboto-Bold.ttf", 72),
            "body": ("Roboto-Medium.ttf", 52),
            "caption": ("Roboto-Regular.ttf", 40)
        },
        "effects": ["emoji", "badge_pulse", "price_highlight"]
    },
    "tech": {
        "name": "Tech",
        "description": "Голубой/белый, иконки, характеристики",
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
        "fonts": {
            "header": ("Inter-Bold.ttf", 88),
            "subheader": ("Inter-SemiBold.ttf", 60),
            "body": ("Inter-Regular.ttf", 44),
            "caption": ("Inter-Light.ttf", 32)
        },
        "effects": ["icons", "specs_grid", "tech_lines"]
    },
    "lifestyle": {
        "name": "Lifestyle",
        "description": "Фото в интерьере, мягкие тона",
        "colors": {
            "primary": "#5d4037",
            "accent": "#ff8a65",
            "background": "#fbe9e7",
            "text": "#3e2723",
            "text_secondary": "#8d6e63",
            "success": "#66bb6a",
            "warning": "#ffb74d",
            "danger": "#ef5350"
        },
        "fonts": {
            "header": ("PlayfairDisplay-Bold.ttf", 92),
            "subheader": ("PlayfairDisplay-SemiBold.ttf", 64),
            "body": ("Lato-Regular.ttf", 46),
            "caption": ("Lato-Light.ttf", 36)
        },
        "effects": ["photo_blend", "soft_shadow", "warm_filter"]
    },
    "minimal": {
        "name": "Minimal",
        "description": "Белый фон, чёрный текст, простота",
        "colors": {
            "primary": "#000000",
            "accent": "#424242",
            "background": "#ffffff",
            "text": "#000000",
            "text_secondary": "#757575",
            "success": "#212121",
            "warning": "#616161",
            "danger": "#000000"
        },
        "fonts": {
            "header": ("HelveticaNeue-Bold.ttf", 80),
            "subheader": ("HelveticaNeue-Medium.ttf", 56),
            "body": ("HelveticaNeue-Regular.ttf", 42),
            "caption": ("HelveticaNeue-Light.ttf", 32)
        },
        "effects": ["clean_lines", "white_space", "typography"]
    }
}


# ============================================
# ТРИГГЕРЫ ПРОДАЖ
# ============================================

TRIGGERS_BY_CATEGORY = {
    "electronics": [
        "Гарантия 2 года",
        "Оригинал",
        "Доставка 1 день",
        "Рассрочка 0%",
        "Тест 14 дней",
        "Сертифицирован",
        "Новинка 2025",
        "Топ продаж"
    ],
    "clothing": [
        "Натуральный материал",
        "Размеры XS-5XL",
        "Примерка перед покупкой",
        "Бесплатная доставка",
        "Сезонная скидка -30%",
        "Тренд сезона",
        "Эксклюзивный дизайн",
        "В наличии все размеры"
    ],
    "cosmetics": [
        "100% оригинал",
        "Сертифицировано",
        "Не тестируется на животных",
        "Натуральный состав",
        "Подарок при покупке",
        "Бестселлер",
        "Дерматологически тестировано",
        "Срок годности 3 года"
    ],
    "kids": [
        "Безопасные материалы",
        "Сертификат качества",
        "Для детей от 0+",
        "Гипоаллергенно",
        "Легко мыть",
        "Прочная конструкция",
        "Развивающая игрушка",
        "Подарочная упаковка"
    ],
    "home": [
        "Экологичные материалы",
        "Долговечное покрытие",
        "Легкий уход",
        "Современный дизайн",
        "В наличии на складе",
        "Быстрая отправка",
        "Гарантия качества",
        "Комплект со скидкой"
    ],
    "sports": [
        "Профессиональное качество",
        "Для начинающих и профи",
        "Эргономичный дизайн",
        "Противоскользящее покрытие",
        "Регулируемый размер",
        "Компактное хранение",
        "Гарантия производителя",
        "Топовая модель"
    ]
}


# ============================================
# HTML ШАБЛОНЫ
# ============================================

HTML_TEMPLATES = {
    "card_base": """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            width: 1600px; 
            height: 1600px; 
            font-family: '{{font_family}}', sans-serif;
            background: {{background}};
            position: relative;
            overflow: hidden;
        }
        .card-container {
            width: 100%;
            height: 100%;
            position: relative;
        }
        {{style_overrides}}
    </style>
</head>
<body>
    <div class="card-container">
        {{content}}
    </div>
</body>
</html>
""",

    "block_header": """
    <div class="header-block" style="
        position: absolute;
        left: {{x}}px;
        top: {{y}}px;
        width: {{width}}px;
        font-size: {{font_size}}px;
        font-weight: {{font_weight}};
        color: {{color}};
        line-height: 1.2;
        text-align: {{align}};
    ">{{text}}</div>
""",

    "block_image": """
    <div class="image-block" style="
        position: absolute;
        left: {{x}}px;
        top: {{y}}px;
        width: {{width}}px;
        height: {{height}}px;
        {{shadow}}
    ">
        <img src="{{image_url}}" style="
            width: 100%;
            height: 100%;
            object-fit: contain;
            border-radius: {{border_radius}}px;
        ">
    </div>
""",

    "block_price": """
    <div class="price-block" style="
        position: absolute;
        left: {{x}}px;
        top: {{y}}px;
        text-align: {{align}};
    ">
        <div class="old-price" style="
            font-size: {{old_font_size}}px;
            color: {{old_color}};
            text-decoration: line-through;
        ">{{old_price}} ₽</div>
        <div class="new-price" style="
            font-size: {{new_font_size}}px;
            font-weight: bold;
            color: {{new_color}};
        ">{{new_price}} ₽</div>
        <div class="discount" style="
            display: {{discount_display}};
            background: {{discount_bg}};
            color: {{discount_color}};
            padding: 8px 16px;
            border-radius: 8px;
            font-size: {{discount_font_size}}px;
            margin-top: 10px;
            display: inline-block;
        ">-{{discount}}%</div>
    </div>
""",

    "block_benefits": """
    <div class="benefits-block" style="
        position: absolute;
        left: {{x}}px;
        top: {{y}}px;
        width: {{width}}px;
    ">
        {{#benefits}}
        <div class="benefit-item" style="
            display: flex;
            align-items: center;
            margin-bottom: {{spacing}}px;
            font-size: {{font_size}}px;
            color: {{color}};
        ">
            <span class="benefit-icon" style="
                margin-right: 16px;
                color: {{icon_color}};
                font-size: {{icon_size}}px;
            ">{{icon}}</span>
            <span>{{text}}</span>
        </div>
        {{/benefits}}
    </div>
""",

    "block_badge": """
    <div class="badge" style="
        position: absolute;
        left: {{x}}px;
        top: {{y}}px;
        background: {{background}};
        color: {{color}};
        padding: 12px 24px;
        border-radius: {{border_radius}}px;
        font-size: {{font_size}}px;
        font-weight: {{font_weight}};
        {{pulse_effect}}
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        z-index: 100;
    ">{{text}}</div>
""",

    "block_cta": """
    <div class="cta-block" style="
        position: absolute;
        left: {{x}}px;
        top: {{y}}px;
        width: {{width}}px;
        background: {{background}};
        color: {{color}};
        padding: 24px 48px;
        border-radius: {{border_radius}}px;
        font-size: {{font_size}}px;
        font-weight: {{font_weight}};
        text-align: center;
        box-shadow: {{box_shadow}};
    ">{{text}}</div>
""",

    "block_rating": """
    <div class="rating-block" style="
        position: absolute;
        left: {{x}}px;
        top: {{y}}px;
        display: flex;
        align-items: center;
        gap: 12px;
    ">
        <div class="stars" style="
            color: {{star_color}};
            font-size: {{star_size}}px;
        ">{{stars}}</div>
        <div class="rating-text" style="
            font-size: {{font_size}}px;
            color: {{color}};
        ">{{rating}} ({{reviews}} отзывов)</div>
    </div>
""",

    "block_delivery": """
    <div class="delivery-block" style="
        position: absolute;
        left: {{x}}px;
        top: {{y}}px;
        display: flex;
        align-items: center;
        gap: 16px;
        padding: 16px 24px;
        background: {{background}};
        border-radius: {{border_radius}}px;
        font-size: {{font_size}}px;
        color: {{color}};
    ">
        <span style="font-size: {{icon_size}}px;">{{icon}}</span>
        <span>{{text}}</span>
    </div>
"""
}


# ============================================
# КЛАСС МЕНЕДЖЕРА ПАТТЕРНОВ
# ============================================

class PatternManager:
    """Управление паттернами инфографики"""
    
    def __init__(self):
        self.patterns: Dict[str, List[Pattern]] = {}
        self._ensure_directories()
        self._load_patterns()
        self._create_default_patterns()
    
    def _ensure_directories(self):
        """Создание необходимых директорий"""
        PATTERNS_DIR.mkdir(parents=True, exist_ok=True)
        TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        FONTS_DIR.mkdir(parents=True, exist_ok=True)
    
    def _load_patterns(self):
        """Загрузка паттернов из файлов"""
        for category in CATEGORIES:
            pattern_file = PATTERNS_DIR / f"{category}.json"
            if pattern_file.exists():
                try:
                    with open(pattern_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        self.patterns[category] = [
                            Pattern.from_dict(p) for p in data.get("patterns", [])
                        ]
                        logger.info(f"Загружено {len(self.patterns[category])} паттернов для {category}")
                except Exception as e:
                    logger.error(f"Ошибка загрузки паттернов {category}: {e}")
                    self.patterns[category] = []
            else:
                self.patterns[category] = []
    
    def _create_default_patterns(self):
        """Создание паттернов по умолчанию если они отсутствуют"""
        for category in CATEGORIES:
            if not self.patterns.get(category):
                self._generate_category_patterns(category)
    
    def _generate_category_patterns(self, category: str):
        """Генерация базовых паттернов для категории"""
        patterns = []
        triggers = TRIGGERS_BY_CATEGORY.get(category, TRIGGERS_BY_CATEGORY["electronics"])
        
        # Создаём паттерн для каждого стиля
        for style_name, style_config in STYLES.items():
            colors = ColorScheme(**style_config["colors"])
            
            # Базовые блоки для всех стилей
            blocks = [
                Block(type="header", position=(80, 80), size=(1440, 120),
                      font_size=style_config["fonts"]["header"][1], bold=True,
                      color=colors.text),
                Block(type="image", position=(100, 280), size=(700, 700),
                      z_index=1),
                Block(type="price", position=(1000, 1200), size=(500, 200),
                      font_size=style_config["fonts"]["header"][1], bold=True,
                      color=colors.primary),
                Block(type="benefits", position=(900, 300), size=(600, 600),
                      font_size=style_config["fonts"]["body"][1],
                      color=colors.text),
                Block(type="badge", position=(1300, 80), size=(200, 80),
                      font_size=style_config["fonts"]["caption"][1],
                      color=colors.background),
                Block(type="rating", position=(80, 1400), size=(400, 80),
                      font_size=style_config["fonts"]["caption"][1],
                      color=colors.text_secondary),
                Block(type="delivery", position=(550, 1400), size=(600, 80),
                      font_size=style_config["fonts"]["caption"][1],
                      color=colors.text_secondary)
            ]
            
            pattern = Pattern(
                category=category,
                pattern_name=f"{style_name}_default",
                colors=colors,
                blocks=blocks,
                triggers=triggers[:5],
                success_rate=0.75 + (hash(style_name) % 20) / 100,
                style=style_name
            )
            patterns.append(pattern)
        
        self.patterns[category] = patterns
        self._save_patterns(category)
    
    def _save_patterns(self, category: str):
        """Сохранение паттернов категории в файл"""
        pattern_file = PATTERNS_DIR / f"{category}.json"
        data = {
            "category": category,
            "updated_at": datetime.now().isoformat(),
            "patterns": [p.to_dict() for p in self.patterns.get(category, [])]
        }
        try:
            with open(pattern_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.info(f"Сохранено {len(self.patterns[category])} паттернов для {category}")
        except Exception as e:
            logger.error(f"Ошибка сохранения паттернов {category}: {e}")
    
    def get_patterns(self, category: str, style: Optional[str] = None) -> List[Pattern]:
        """Получение паттернов для категории"""
        patterns = self.patterns.get(category, [])
        if style:
            patterns = [p for p in patterns if p.style == style]
        return patterns
    
    def get_pattern(self, category: str, pattern_name: str) -> Optional[Pattern]:
        """Получение конкретного паттерна"""
        patterns = self.patterns.get(category, [])
        for p in patterns:
            if p.pattern_name == pattern_name:
                return p
        return None
    
    def add_pattern(self, pattern: Pattern) -> bool:
        """Добавление нового паттерна"""
        category = pattern.category
        if category not in self.patterns:
            self.patterns[category] = []
        
        # Проверяем уникальность имени
        existing = [p for p in self.patterns[category] if p.pattern_name == pattern.pattern_name]
        if existing:
            logger.warning(f"Паттерн {pattern.pattern_name} уже существует")
            return False
        
        self.patterns[category].append(pattern)
        self._save_patterns(category)
        return True
    
    def update_success_rate(self, category: str, pattern_name: str, new_rate: float):
        """Обновление success rate паттерна"""
        pattern = self.get_pattern(category, pattern_name)
        if pattern:
            pattern.success_rate = new_rate
            self._save_patterns(category)


# ============================================
# КЛАСС ГЕНЕРАТОРА ИНФОГРАФИКИ
# ============================================

class InfographicGenerator:
    """Генератор инфографики на основе паттернов"""
    
    def __init__(self):
        self.pattern_manager = PatternManager()
        self._font_cache: Dict[str, ImageFont.FreeTypeFont] = {}
        self._template_cache: Dict[str, str] = {}
        self._load_fonts()
    
    def _load_fonts(self):
        """Загрузка шрифтов (fallback на дефолтные)"""
        self.default_font = self._get_font("default", 48)
    
    def _get_font(self, font_name: str, size: int) -> ImageFont.FreeTypeFont:
        """Получение шрифта с кэшированием"""
        cache_key = f"{font_name}_{size}"
        if cache_key in self._font_cache:
            return self._font_cache[cache_key]
        
        # Пробуем загрузить системные шрифты
        font_paths = [
            f"/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            f"/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            f"/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
            f"/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
            "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
            "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
            "/System/Library/Fonts/Helvetica.ttc",  # macOS
            "C:/Windows/Fonts/arial.ttf",  # Windows
        ]
        
        for path in font_paths:
            if os.path.exists(path):
                try:
                    font = ImageFont.truetype(path, size)
                    self._font_cache[cache_key] = font
                    return font
                except:
                    continue
        
        # Fallback на дефолтный шрифт
        return ImageFont.load_default()
    
    def _hex_to_rgb(self, hex_color: str) -> Tuple[int, int, int]:
        """Конвертация HEX в RGB"""
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    
    def _wrap_text(self, text: str, font: ImageFont.FreeTypeFont, max_width: int) -> List[str]:
        """Перенос текста по ширине"""
        words = text.split()
        lines = []
        current_line = []
        
        for word in words:
            test_line = ' '.join(current_line + [word])
            bbox = font.getbbox(test_line)
            if bbox and bbox[2] <= max_width:
                current_line.append(word)
            else:
                if current_line:
                    lines.append(' '.join(current_line))
                current_line = [word]
        
        if current_line:
            lines.append(' '.join(current_line))
        
        return lines if lines else [text]
    
    def _draw_rounded_rectangle(self, draw: ImageDraw.Draw, xy: Tuple[int, int, int, int],
                                 radius: int, fill: Optional[Tuple[int, int, int]] = None,
                                 outline: Optional[Tuple[int, int, int]] = None, width: int = 1):
        """Отрисовка скруглённого прямоугольника"""
        x1, y1, x2, y2 = xy
        
        # Основной прямоугольник
        if fill:
            draw.rectangle([x1 + radius, y1, x2 - radius, y2], fill=fill)
            draw.rectangle([x1, y1 + radius, x2, y2 - radius], fill=fill)
        
        # Углы
        draw.pieslice([x1, y1, x1 + radius * 2, y1 + radius * 2], 180, 270, fill=fill)
        draw.pieslice([x2 - radius * 2, y1, x2, y1 + radius * 2], 270, 360, fill=fill)
        draw.pieslice([x1, y2 - radius * 2, x1 + radius * 2, y2], 90, 180, fill=fill)
        draw.pieslice([x2 - radius * 2, y2 - radius * 2, x2, y2], 0, 90, fill=fill)
        
        if outline:
            draw.arc([x1, y1, x1 + radius * 2, y1 + radius * 2], 180, 270, fill=outline, width=width)
            draw.arc([x2 - radius * 2, y1, x2, y1 + radius * 2], 270, 360, fill=outline, width=width)
            draw.arc([x1, y2 - radius * 2, x1 + radius * 2, y2], 90, 180, fill=outline, width=width)
            draw.arc([x2 - radius * 2, y2 - radius * 2, x2, y2], 0, 90, fill=outline, width=width)
            draw.line([(x1 + radius, y1), (x2 - radius, y1)], fill=outline, width=width)
            draw.line([(x1 + radius, y2), (x2 - radius, y2)], fill=outline, width=width)
            draw.line([(x1, y1 + radius), (x1, y2 - radius)], fill=outline, width=width)
            draw.line([(x2, y1 + radius), (x2, y2 - radius)], fill=outline, width=width)
    
    def _draw_gradient_background(self, img: Image.Image, color1: str, color2: str, direction: str = "vertical"):
        """Отрисовка градиентного фона"""
        c1 = self._hex_to_rgb(color1)
        c2 = self._hex_to_rgb(color2)
        
        width, height = img.size
        draw = ImageDraw.Draw(img)
        
        if direction == "vertical":
            for y in range(height):
                ratio = y / height
                r = int(c1[0] * (1 - ratio) + c2[0] * ratio)
                g = int(c1[1] * (1 - ratio) + c2[1] * ratio)
                b = int(c1[2] * (1 - ratio) + c2[2] * ratio)
                draw.line([(0, y), (width, y)], fill=(r, g, b))
        else:
            for x in range(width):
                ratio = x / width
                r = int(c1[0] * (1 - ratio) + c2[0] * ratio)
                g = int(c1[1] * (1 - ratio) + c2[1] * ratio)
                b = int(c1[2] * (1 - ratio) + c2[2] * ratio)
                draw.line([(x, 0), (x, height)], fill=(r, g, b))
    
    def _draw_block_header(self, draw: ImageDraw.Draw, block: Block, text: str, style_config: Dict):
        """Отрисовка заголовка"""
        font = self._get_font("header", block.font_size)
        color = self._hex_to_rgb(block.color)
        x, y = block.position
        max_width = block.size[0]
        
        # Перенос текста
        lines = self._wrap_text(text, font, max_width)
        line_height = block.font_size * 1.2
        
        for i, line in enumerate(lines):
            draw.text((x, y + i * line_height), line, font=font, fill=color)
    
    def _draw_block_price(self, draw: ImageDraw.Draw, block: Block, 
                          old_price: Optional[int], new_price: int, 
                          style_config: Dict, colors: ColorScheme):
        """Отрисовка цены"""
        x, y = block.position
        rgb_primary = self._hex_to_rgb(colors.primary)
        rgb_text = self._hex_to_rgb(colors.text_secondary)
        rgb_accent = self._hex_to_rgb(colors.accent)
        
        # Старая цена (зачёркнутая)
        if old_price and old_price > new_price:
            old_font = self._get_font("body", block.font_size // 2)
            draw.text((x, y), f"{old_price:,} ₽".replace(",", " "), 
                     font=old_font, fill=rgb_text)
            # Зачёркивание
            bbox = old_font.getbbox(f"{old_price:,} ₽".replace(",", " "))
            if bbox:
                y_strike = y + (bbox[3] - bbox[1]) // 2
                draw.line([(x, y_strike), (x + bbox[2], y_strike)], 
                         fill=rgb_text, width=2)
            y += block.font_size // 2 + 10
            
            # Скидка
            discount = int((1 - new_price / old_price) * 100)
            discount_font = self._get_font("body", 40)
            draw.rounded_rectangle(
                [(x + 250, y - 40), (x + 350, y + 10)],
                radius=8,
                fill=rgb_accent
            )
            draw.text((x + 260, y - 35), f"-{discount}%", 
                     font=discount_font, fill=(255, 255, 255))
        
        # Новая цена
        new_font = self._get_font("header", block.font_size)
        draw.text((x, y), f"{new_price:,} ₽".replace(",", " "), 
                 font=new_font, fill=rgb_primary)
    
    def _draw_block_benefits(self, draw: ImageDraw.Draw, block: Block, 
                             benefits: List[str], style_config: Dict, colors: ColorScheme):
        """Отрисовка блока выгод"""
        x, y = block.position
        font = self._get_font("body", block.font_size)
        icon_font = self._get_font("body", int(block.font_size * 1.2))
        color = self._hex_to_rgb(block.color)
        icon_color = self._hex_to_rgb(colors.success)
        
        line_height = block.font_size * 1.8
        
        for i, benefit in enumerate(benefits[:5]):  # Максимум 5 выгод
            y_pos = y + i * line_height
            # Иконка галочки
            draw.text((x, y_pos), "✓", font=icon_font, fill=icon_color)
            # Текст
            draw.text((x + 50, y_pos + 5), benefit, font=font, fill=color)
    
    def _draw_block_badge(self, draw: ImageDraw.Draw, block: Block, 
                          text: str, style_config: Dict, colors: ColorScheme):
        """Отрисовка бейджа"""
        x, y = block.position
        font = self._get_font("body", block.font_size)
        
        # Цвета в зависимости от типа бейджа
        if "Хит" in text or "Топ" in text:
            bg_color = self._hex_to_rgb(colors.danger)
        elif "Новинка" in text or "New" in text:
            bg_color = self._hex_to_rgb(colors.success)
        elif "%" in text or "Скидка" in text:
            bg_color = self._hex_to_rgb(colors.warning)
        else:
            bg_color = self._hex_to_rgb(colors.accent)
        
        text_color = (255, 255, 255)
        
        # Размеры текста
        bbox = font.getbbox(text)
        if bbox:
            padding_x, padding_y = 30, 15
            width = bbox[2] - bbox[0] + padding_x * 2
            height = bbox[3] - bbox[1] + padding_y * 2
            
            # Фон бейджа
            self._draw_rounded_rectangle(
                draw,
                (x, y, x + width, y + height),
                radius=12,
                fill=bg_color
            )
            
            # Текст
            draw.text((x + padding_x, y + padding_y // 2), text, 
                     font=font, fill=text_color)
    
    def _draw_block_rating(self, draw: ImageDraw.Draw, block: Block, 
                           rating: float, reviews: int, style_config: Dict, colors: ColorScheme):
        """Отрисовка рейтинга"""
        x, y = block.position
        font = self._get_font("caption", block.font_size)
        star_font = self._get_font("body", int(block.font_size * 1.3))
        
        star_color = self._hex_to_rgb(colors.warning)
        text_color = self._hex_to_rgb(colors.text_secondary)
        
        # Звёзды
        full_stars = int(rating)
        stars_text = "★" * full_stars + "☆" * (5 - full_stars)
        draw.text((x, y), stars_text, font=star_font, fill=star_color)
        
        # Текст рейтинга
        bbox = star_font.getbbox(stars_text)
        if bbox:
            text_x = x + bbox[2] + 15
            draw.text((text_x, y + 5), f"{rating} ({reviews} отзывов)", 
                     font=font, fill=text_color)
    
    def _draw_block_delivery(self, draw: ImageDraw.Draw, block: Block, 
                             text: str, icon: str, style_config: Dict, colors: ColorScheme):
        """Отрисовка блока доставки"""
        x, y = block.position
        font = self._get_font("caption", block.font_size)
        icon_font = self._get_font("body", int(block.font_size * 1.3))
        
        bg_color = self._hex_to_rgb(colors.background)
        text_color = self._hex_to_rgb(colors.text_secondary)
        icon_color = self._hex_to_rgb(colors.success)
        
        # Фон
        bbox = font.getbbox(text)
        if bbox:
            padding = 20
            width = bbox[2] + bbox[0] + 60 + padding * 2
            height = max(50, bbox[3] - bbox[1] + padding)
            
            self._draw_rounded_rectangle(
                draw,
                (x, y, x + width, y + height),
                radius=10,
                fill=tuple(min(255, c + 10) for c in bg_color)
            )
            
            # Иконка
            draw.text((x + 15, y + 5), icon, font=icon_font, fill=icon_color)
            
            # Текст
            draw.text((x + 55, y + 10), text, font=font, fill=text_color)
    
    def generate(self, product_data: Dict, category: str, 
                 pattern_name: Optional[str] = None,
                 style: Optional[str] = None) -> str:
        """
        Генерация инфографики
        
        Args:
            product_data: Данные товара
            category: Категория товара
            pattern_name: Имя паттерна (опционально)
            style: Стиль дизайна (опционально)
            
        Returns:
            Путь к сгенерированному файлу PNG
        """
        # Получаем паттерн
        if pattern_name:
            pattern = self.pattern_manager.get_pattern(category, pattern_name)
        elif style:
            patterns = self.pattern_manager.get_patterns(category, style)
            pattern = patterns[0] if patterns else None
        else:
            patterns = self.pattern_manager.get_patterns(category)
            # Берём паттерн с наивысшим success_rate
            pattern = max(patterns, key=lambda p: p.success_rate) if patterns else None
        
        if not pattern:
            raise ValueError(f"Паттерн не найден для {category}/{style}/{pattern_name}")
        
        # Создаём изображение
        img = Image.new('RGB', CARD_SIZE, self._hex_to_rgb(pattern.colors.background))
        draw = ImageDraw.Draw(img)
        
        # Получаем конфиг стиля
        style_config = STYLES.get(pattern.style, STYLES["minimal"])
        
        # Эффекты фона
        if "gradient_overlay" in style_config.get("effects", []):
            self._draw_gradient_background(
                img, 
                pattern.colors.background,
                pattern.colors.primary,
                "vertical"
            )
        
        # Отрисовываем блоки
        for block in sorted(pattern.blocks, key=lambda b: b.z_index):
            if block.type == "header":
                text = product_data.get("name", "Товар")[:60]
                self._draw_block_header(draw, block, text, style_config)
            
            elif block.type == "image":
                # Загружаем и отрисовываем изображение товара
                self._draw_product_image(img, block, product_data.get("image_url"))
            
            elif block.type == "price":
                old_price = product_data.get("old_price")
                new_price = product_data.get("price", 0)
                self._draw_block_price(draw, block, old_price, new_price, 
                                      style_config, pattern.colors)
            
            elif block.type == "benefits":
                benefits = product_data.get("benefits", pattern.triggers[:3])
                self._draw_block_benefits(draw, block, benefits, 
                                         style_config, pattern.colors)
            
            elif block.type == "badge":
                badge_text = product_data.get("badge", "Хит продаж")
                self._draw_block_badge(draw, block, badge_text, 
                                      style_config, pattern.colors)
            
            elif block.type == "rating":
                rating = product_data.get("rating", 4.8)
                reviews = product_data.get("reviews", 100)
                self._draw_block_rating(draw, block, rating, reviews, 
                                       style_config, pattern.colors)
            
            elif block.type == "delivery":
                delivery_text = product_data.get("delivery", "Доставка 1 день")
                icon = product_data.get("delivery_icon", "🚚")
                self._draw_block_delivery(draw, block, delivery_text, icon,
                                         style_config, pattern.colors)
        
        # Сохраняем результат
        cache_key = hashlib.md5(
            f"{json.dumps(product_data, sort_keys=True)}_{pattern.pattern_name}".encode()
        ).hexdigest()
        output_path = CACHE_DIR / f"{cache_key}.png"
        
        img.save(output_path, "PNG", quality=95)
        logger.info(f"Инфографика сохранена: {output_path}")
        
        return str(output_path)
    
    def _draw_product_image(self, img: Image.Image, block: Block, image_url: Optional[str]):
        """Отрисовка изображения товара"""
        if not image_url:
            # Рисуем placeholder
            draw = ImageDraw.Draw(img)
            x, y = block.position
            w, h = block.size
            draw.rectangle([x, y, x + w, y + h], outline=(200, 200, 200), width=2)
            draw.text((x + w//2 - 50, y + h//2), "[Фото]", fill=(150, 150, 150))
            return
        
        try:
            # Загружаем изображение
            from urllib.request import urlopen
            response = urlopen(image_url, timeout=10)
            product_img = Image.open(io.BytesIO(response.read()))
            
            # Конвертируем в RGB если нужно
            if product_img.mode in ('RGBA', 'P'):
                product_img = product_img.convert('RGBA')
            
            # Масштабируем
            product_img.thumbnail(block.size, Resampling.LANCZOS)
            
            # Центрируем
            x, y = block.position
            w, h = block.size
            img_w, img_h = product_img.size
            paste_x = x + (w - img_w) // 2
            paste_y = y + (h - img_h) // 2
            
            # Вставляем
            if product_img.mode == 'RGBA':
                img.paste(product_img, (paste_x, paste_y), product_img)
            else:
                img.paste(product_img, (paste_x, paste_y))
                
        except Exception as e:
            logger.error(f"Ошибка загрузки изображения: {e}")
            # Рисуем placeholder при ошибке
            draw = ImageDraw.Draw(img)
            x, y = block.position
            w, h = block.size
            draw.rectangle([x, y, x + w, y + h], outline=(200, 200, 200), width=2)


# ============================================
# КЛАСС АНАЛИЗАТОРА ТОПОВ
# ============================================

class TopAnalyzer:
    """Анализ топовых карточек с MPStats (заглушка для API интеграции)"""
    
    def __init__(self):
        self.pattern_manager = PatternManager()
        self.analyzed_data: Dict[str, Dict] = {}
    
    def analyze_category(self, category: str, limit: int = 50) -> Dict:
        """
        Анализ топовых карточек категории
        
        Это заглушка - в реальности здесь будет интеграция с MPStats API
        
        Args:
            category: Категория товара
            limit: Количество карточек для анализа
            
        Returns:
            Результаты анализа
        """
        logger.info(f"Анализ категории {category} (топ-{limit})")
        
        # Симулируем анализ
        # В реальности: вызов MPStats API, скачивание карточек, анализ изображений
        
        analysis = {
            "category": category,
            "category_name": CATEGORY_NAMES.get(category, category),
            "analyzed_at": datetime.now().isoformat(),
            "total_analyzed": limit,
            "popular_blocks": self._get_popular_blocks(category),
            "color_schemes": self._get_popular_colors(category),
            "font_sizes": self._get_font_statistics(category),
            "top_triggers": TRIGGERS_BY_CATEGORY.get(category, [])[:8],
            "average_success_rate": 0.82,
            "recommendations": self._generate_recommendations(category)
        }
        
        self.analyzed_data[category] = analysis
        return analysis
    
    def _get_popular_blocks(self, category: str) -> List[Dict]:
        """Популярные блоки для категории"""
        blocks = [
            {"type": "header", "frequency": 0.98, "avg_position": [80, 80]},
            {"type": "image", "frequency": 0.95, "avg_position": [100, 250]},
            {"type": "price", "frequency": 0.92, "avg_position": [1000, 1200]},
            {"type": "benefits", "frequency": 0.87, "avg_position": [900, 350]},
            {"type": "badge", "frequency": 0.76, "avg_position": [1250, 100]},
            {"type": "rating", "frequency": 0.71, "avg_position": [100, 1400]},
            {"type": "delivery", "frequency": 0.65, "avg_position": [600, 1400]},
            {"type": "cta", "frequency": 0.43, "avg_position": [1000, 1450]}
        ]
        return blocks
    
    def _get_popular_colors(self, category: str) -> List[Dict]:
        """Популярные цветовые схемы для категории"""
        schemes = {
            "electronics": [
                {"primary": "#1a1a1a", "accent": "#ff6b00", "background": "#ffffff"},
                {"primary": "#1565c0", "accent": "#00b0ff", "background": "#e3f2fd"},
                {"primary": "#0d47a1", "accent": "#2962ff", "background": "#f5f5f5"}
            ],
            "clothing": [
                {"primary": "#e91e63", "accent": "#ff4081", "background": "#fce4ec"},
                {"primary": "#9c27b0", "accent": "#e040fb", "background": "#f3e5f5"},
                {"primary": "#3f51b5", "accent": "#536dfe", "background": "#e8eaf6"}
            ],
            "cosmetics": [
                {"primary": "#d81b60", "accent": "#ff80ab", "background": "#fff0f3"},
                {"primary": "#8e24aa", "accent": "#ea80fc", "background": "#f3e5f5"},
                {"primary": "#f06292", "accent": "#ff4081", "background": "#fff"}
            ],
            "kids": [
                {"primary": "#ff9800", "accent": "#ffc107", "background": "#fff8e1"},
                {"primary": "#4caf50", "accent": "#8bc34a", "background": "#f1f8e9"},
                {"primary": "#03a9f4", "accent": "#00bcd4", "background": "#e1f5fe"}
            ],
            "home": [
                {"primary": "#795548", "accent": "#a1887f", "background": "#efebe9"},
                {"primary": "#607d8b", "accent": "#90a4ae", "background": "#eceff1"},
                {"primary": "#5d4037", "accent": "#8d6e63", "background": "#fbe9e7"}
            ],
            "sports": [
                {"primary": "#ff5722", "accent": "#ff9800", "background": "#fbe9e7"},
                {"primary": "#009688", "accent": "#4db6ac", "background": "#e0f2f1"},
                {"primary": "#2196f3", "accent": "#64b5f6", "background": "#e3f2fd"}
            ]
        }
        return schemes.get(category, schemes["electronics"])
    
    def _get_font_statistics(self, category: str) -> Dict:
        """Статистика размеров шрифтов"""
        return {
            "header": {"min": 56, "max": 120, "avg": 78},
            "subheader": {"min": 36, "max": 64, "avg": 52},
            "body": {"min": 28, "max": 48, "avg": 38},
            "caption": {"min": 20, "max": 36, "avg": 28}
        }
    
    def _generate_recommendations(self, category: str) -> List[str]:
        """Генерация рекомендаций на основе анализа"""
        return [
            "Используйте яркий бейдж с акцией в верхнем правом углу",
            "Размещайте основное фото товара слева, выгоды справа",
            "Цена должна занимать не менее 15% площади карточки",
            "Добавляйте минимум 3 выгоды (триггера) на карточку",
            "Используйте контрастные цвета для CTA элементов"
        ]


# ============================================
# API ФУНКЦИИ ДЛЯ БОТА
# ============================================

class InfographicAPI:
    """API для интеграции с ботом"""
    
    def __init__(self):
        self.pattern_manager = PatternManager()
        self.generator = InfographicGenerator()
        self.analyzer = TopAnalyzer()
    
    def analyze_category(self, category: str) -> Dict:
        """
        Анализ категории товаров
        
        Args:
            category: Код категории (electronics, clothing, и т.д.)
            
        Returns:
            Данные анализа
        """
        if category not in CATEGORIES:
            return {
                "error": f"Неизвестная категория. Доступные: {', '.join(CATEGORIES)}"
            }
        
        return self.analyzer.analyze_category(category)
    
    def get_patterns(self, category: Optional[str] = None, 
                     style: Optional[str] = None) -> List[Dict]:
        """
        Получение списка паттернов
        
        Args:
            category: Фильтр по категории
            style: Фильтр по стилю
            
        Returns:
            Список паттернов
        """
        result = []
        
        categories = [category] if category else CATEGORIES
        
        for cat in categories:
            patterns = self.pattern_manager.get_patterns(cat, style)
            for p in patterns:
                result.append({
                    "category": p.category,
                    "pattern_name": p.pattern_name,
                    "style": p.style,
                    "success_rate": p.success_rate,
                    "triggers": p.triggers,
                    "block_count": len(p.blocks)
                })
        
        # Сортируем по success_rate
        result.sort(key=lambda x: x["success_rate"], reverse=True)
        return result
    
    def generate_card(self, product_data: Dict, style: str = "bright",
                      category: str = "electronics") -> str:
        """
        Генерация карточки товара
        
        Args:
            product_data: Данные товара
            style: Стиль дизайна (premium, bright, tech, lifestyle, minimal)
            category: Категория товара
            
        Returns:
            Путь к сгенерированному файлу
        """
        if style not in STYLES:
            raise ValueError(f"Неизвестный стиль. Доступные: {', '.join(STYLES.keys())}")
        
        return self.generator.generate(product_data, category, style=style)
    
    def get_styles(self) -> Dict:
        """Получение списка доступных стилей"""
        return {
            name: {
                "name": config["name"],
                "description": config["description"],
                "colors": config["colors"]
            }
            for name, config in STYLES.items()
        }
    
    def get_categories(self) -> Dict:
        """Получение списка категорий"""
        return CATEGORY_NAMES


# ============================================
# ГЛОБАЛЬНЫЙ ЭКЗЕМПЛЯР API
# ============================================

_api: Optional[InfographicAPI] = None

def get_api() -> InfographicAPI:
    """Получение глобального экземпляра API"""
    global _api
    if _api is None:
        _api = InfographicAPI()
    return _api


# ============================================
# ПРОСТЫЕ ФУНКЦИИ ДЛЯ БЫСТРОГО ИСПОЛЬЗОВАНИЯ
# ============================================

def analyze_category(category: str) -> Dict:
    """Анализ категории"""
    return get_api().analyze_category(category)

def get_patterns(category: Optional[str] = None, style: Optional[str] = None) -> List[Dict]:
    """Получение паттернов"""
    return get_api().get_patterns(category, style)

def generate_card(product_data: Dict, style: str = "bright", 
                  category: str = "electronics") -> str:
    """Генерация карточки"""
    return get_api().generate_card(product_data, style, category)


# ============================================
# ТЕСТИРОВАНИЕ
# ============================================

if __name__ == "__main__":
    # Пример использования
    print("=" * 60)
    print("ДЕМО: Система анализа и генерации инфографики")
    print("=" * 60)
    
    # 1. Получаем категории
    print("\n1. Доступные категории:")
    for code, name in CATEGORY_NAMES.items():
        print(f"   {code}: {name}")
    
    # 2. Получаем стили
    print("\n2. Доступные стили:")
    for code, config in STYLES.items():
        print(f"   {code}: {config['name']} - {config['description']}")
    
    # 3. Анализ категории
    print("\n3. Анализ категории 'electronics':")
    analysis = analyze_category("electronics")
    print(f"   Проанализировано: {analysis['total_analyzed']} карточек")
    print(f"   Популярные блоки: {[b['type'] for b in analysis['popular_blocks'][:4]]}")
    
    # 4. Получаем паттерны
    print("\n4. Паттерны для electronics:")
    patterns = get_patterns("electronics")
    for p in patterns[:3]:
        print(f"   {p['pattern_name']} (style: {p['style']}, rate: {p['success_rate']:.2f})")
    
    # 5. Генерируем карточку
    print("\n5. Генерация тестовой карточки...")
    test_product = {
        "name": "Беспроводные наушники Pro Max",
        "price": 4990,
        "old_price": 7990,
        "rating": 4.9,
        "reviews": 2847,
        "badge": "Топ продаж",
        "delivery": "Доставка 1 день",
        "delivery_icon": "🚚",
        "benefits": [
            "Активное шумоподавление",
            "30 часов работы",
            "Быстрая зарядка USB-C",
            "Гарантия 2 года"
        ],
        "image_url": None  # В реальности - URL изображения
    }
    
    for style in ["bright", "tech", "premium"]:
        output_path = generate_card(test_product, style=style, category="electronics")
        print(f"   ✓ {style}: {output_path}")
    
    print("\n" + "=" * 60)
    print("Готово! Проверьте сгенерированные файлы в:")
    print(f"   {CACHE_DIR}")
    print("=" * 60)
