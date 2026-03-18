#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Модуль инфографики для карточек товаров маркетплейсов
"""

from .infographic_analyzer import (
    InfographicAPI,
    InfographicGenerator,
    PatternManager,
    TopAnalyzer,
    Pattern,
    Block,
    ColorScheme,
    
    # Простые функции
    analyze_category,
    get_patterns,
    generate_card,
    get_api,
    
    # Константы
    STYLES,
    CATEGORIES,
    CATEGORY_NAMES,
    TRIGGERS_BY_CATEGORY,
    CARD_SIZE,
    HTML_TEMPLATES
)

__all__ = [
    'InfographicAPI',
    'InfographicGenerator',
    'PatternManager',
    'TopAnalyzer',
    'Pattern',
    'Block',
    'ColorScheme',
    'analyze_category',
    'get_patterns',
    'generate_card',
    'get_api',
    'STYLES',
    'CATEGORIES',
    'CATEGORY_NAMES',
    'TRIGGERS_BY_CATEGORY',
    'CARD_SIZE',
    'HTML_TEMPLATES'
]
