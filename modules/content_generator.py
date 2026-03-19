# modules/content_generator.py - Генерация контента для товаров
"""
Генерация SEO-оптимизированных описаний товаров для WB/Ozon.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass

logger = logging.getLogger('content_generator')


@dataclass
class ProductContent:
    """Контент товара"""
    title: str
    description: str
    bullet_points: List[str]
    keywords: List[str]
    seo_title: str
    seo_description: str


class ContentGenerator:
    """Генератор контента для маркетплейсов"""
    
    # Шаблоны для разных категорий
    CATEGORY_TEMPLATES = {
        "electronics": {
            "features": ["Технические характеристики", "Гарантия", "Совместимость"],
            "keywords": ["оригинал", "гарантия", "доставка"]
        },
        "clothing": {
            "features": ["Состав", "Размерная сетка", "Уход"],
            "keywords": ["качество", "размер", "доставка"]
        },
        "home": {
            "features": ["Материал", "Размеры", "Уход"],
            "keywords": ["удобство", "качество", "доставка"]
        },
        "beauty": {
            "features": ["Состав", "Применение", "Срок годности"],
            "keywords": ["оригинал", "натуральное", "эффект"]
        },
        "sports": {
            "features": ["Материал", "Назначение", "Уход"],
            "keywords": ["прочность", "комфорт", "спорт"]
        }
    }
    
    def __init__(self, clients_dir: str = "/opt/clients"):
        self.clients_dir = Path(clients_dir)
        self.templates_dir = self.clients_dir / "GLOBAL_AI_LEARNING" / "content_templates"
        self.templates_dir.mkdir(parents=True, exist_ok=True)
    
    def generate_product_description(
        self,
        product_name: str,
        category: str,
        key_features: List[str],
        target_keywords: List[str] = None
    ) -> ProductContent:
        """Генерирует описание товара"""
        
        template = self.CATEGORY_TEMPLATES.get(category, self.CATEGORY_TEMPLATES["electronics"])
        
        # Генерируем заголовок
        title = self._generate_title(product_name, category, target_keywords)
        
        # Генерируем описание
        description = self._generate_description(product_name, category, key_features, template)
        
        # Генерируем bullet points
        bullet_points = self._generate_bullet_points(key_features, template)
        
        # SEO компоненты
        keywords = target_keywords or template["keywords"]
        seo_title = self._generate_seo_title(product_name, keywords)
        seo_description = self._generate_seo_description(product_name, key_features, keywords)
        
        return ProductContent(
            title=title,
            description=description,
            bullet_points=bullet_points,
            keywords=keywords,
            seo_title=seo_title,
            seo_description=seo_description
        )
    
    def _generate_title(self, product_name: str, category: str, keywords: List[str] = None) -> str:
        """Генерирует заголовок товара"""
        # Базовый шаблон: [Бренд] [Название] [Ключевое слово] [Особенность]
        
        category_boosters = {
            "electronics": ["Оригинал", "Гарантия 2 года"],
            "clothing": ["Тренд 2026", "Премиум качество"],
            "home": ["Бестселлер", "Новинка"],
            "beauty": ["Оригинал", "Сертифицировано"],
            "sports": ["Профессиональный", "Прочный"]
        }
        
        boosters = category_boosters.get(category, ["Хит продаж"])
        booster = boosters[0] if boosters else ""
        
        if keywords:
            title = f"{product_name} {keywords[0].title()} {booster}"
        else:
            title = f"{product_name} {booster}"
        
        # Ограничение для WB/Ozon (обычно 60-120 символов)
        return title[:100]
    
    def _generate_description(
        self,
        product_name: str,
        category: str,
        key_features: List[str],
        template: Dict
    ) -> str:
        """Генерирует описание"""
        
        parts = [
            f"✨ {product_name} — лучший выбор в своей категории.",
            "",
            "📌 Основные преимущества:",
        ]
        
        for i, feature in enumerate(key_features[:5], 1):
            parts.append(f"{i}. {feature}")
        
        parts.extend([
            "",
            f"📦 Комплектация: {product_name}, упаковка, инструкция.",
            "",
            "🚚 Доставка: 1-3 дня по всей России.",
            "✅ Гарантия: 14 дней на возврат, 2 года на обмен."
        ])
        
        return "\n".join(parts)
    
    def _generate_bullet_points(self, key_features: List[str], template: Dict) -> List[str]:
        """Генерирует bullet points для карточки"""
        bullets = []
        
        # Добавляем ключевые характеристики
        for feature in key_features[:3]:
            bullets.append(f"✓ {feature}")
        
        # Добавляем стандартные пункты
        standard_bullets = [
            "✓ Быстрая доставка 1-3 дня",
            "✓ Гарантия качества 2 года",
            "✓ Возврат 14 дней без вопросов"
        ]
        
        bullets.extend(standard_bullets)
        return bullets[:5]  # Максимум 5 пунктов
    
    def _generate_seo_title(self, product_name: str, keywords: List[str]) -> str:
        """SEO-заголовок"""
        keyword_str = " ".join(keywords[:2])
        return f"{product_name} купить {keyword_str} недорого"
    
    def _generate_seo_description(self, product_name: str, features: List[str], keywords: List[str]) -> str:
        """SEO-описание"""
        features_str = ", ".join(features[:2])
        keywords_str = ", ".join(keywords[:3])
        return f"{product_name} — {features_str}. {keywords_str}. Доставка 1-3 дня. Гарантия 2 года."
    
    def optimize_for_keywords(self, text: str, keywords: List[str]) -> str:
        """Оптимизирует текст под ключевые слова"""
        # Простая оптимизация - добавляем ключевики если их нет
        for keyword in keywords:
            if keyword.lower() not in text.lower():
                text += f" {keyword}"
        return text
    
    def generate_seo_report(self, content: ProductContent) -> Dict:
        """Генерирует SEO-отчет для контента"""
        return {
            "title_length": len(content.title),
            "description_length": len(content.description),
            "bullet_points_count": len(content.bullet_points),
            "keywords_used": content.keywords,
            "recommendations": [
                "Заголовок оптимален" if 40 <= len(content.title) <= 100 else "Длина заголовка не оптимальна",
                "Описание подробное" if len(content.description) > 200 else "Добавьте больше деталей",
            ]
        }
    
    def save_template(self, name: str, template: Dict):
        """Сохраняет пользовательский шаблон"""
        template_file = self.templates_dir / f"{name}.json"
        with open(template_file, 'w') as f:
            json.dump(template, f, indent=2)
        logger.info(f"💾 Шаблон сохранен: {name}")
    
    def load_template(self, name: str) -> Optional[Dict]:
        """Загружает шаблон"""
        template_file = self.templates_dir / f"{name}.json"
        if template_file.exists():
            with open(template_file, 'r') as f:
                return json.load(f)
        return None


class ContentOptimizer:
    """Оптимизация существующего контента"""
    
    @staticmethod
    def check_wb_requirements(title: str, description: str) -> Dict:
        """Проверяет соответствие требованиям WB"""
        issues = []
        
        if len(title) > 120:
            issues.append("Заголовок слишком длинный (макс. 120 символов)")
        elif len(title) < 20:
            issues.append("Заголовок слишком короткий")
        
        if len(description) < 100:
            issues.append("Описание слишком короткое")
        
        forbidden_words = ["скидка", "акция", "распродажа", "%"]
        for word in forbidden_words:
            if word in title.lower():
                issues.append(f"Запрещенное слово в заголовке: '{word}'")
        
        return {
            "valid": len(issues) == 0,
            "issues": issues
        }
    
    @staticmethod
    def check_ozon_requirements(title: str, description: str) -> Dict:
        """Проверяет соответствие требованиям Ozon"""
        issues = []
        
        if len(title) > 200:
            issues.append("Заголовок слишком длинный (макс. 200 символов)")
        
        if len(description) > 3000:
            issues.append("Описание слишком длинное (макс. 3000 символов)")
        
        return {
            "valid": len(issues) == 0,
            "issues": issues
        }
