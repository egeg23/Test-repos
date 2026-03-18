# self_learning_engine.py - Движок самообучения Seller AI
# Система извлекает успешные паттерны из магазинов и применяет их ко всем клиентам

import json
import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
import statistics

class SelfLearningEngine:
    """
    Движок самообучения Seller AI
    
    Принцип: Каждый подключенный магазин = источник данных для обучения
    Успешные стратегии распространяются на всех клиентов в той же категории
    """
    
    BASE_PATH = Path("/opt/clients/GLOBAL_AI_LEARNING")
    
    # Категории товаров для кластеризации
    CATEGORIES = [
        "electronics", "clothing", "home", "beauty", 
        "sports", "toys", "food", "auto", "other"
    ]
    
    def __init__(self):
        self.BASE_PATH.mkdir(parents=True, exist_ok=True)
        self._ensure_databases()
    
    def _ensure_databases(self):
        """Создает структуру баз данных если не существует"""
        
        # База успешных паттернов по категориям
        self.success_patterns_file = self.BASE_PATH / "success_patterns.json"
        if not self.success_patterns_file.exists():
            self._save_json(self.success_patterns_file, {
                "version": "1.0",
                "updated_at": str(datetime.now()),
                "patterns": {}
            })
        
        # База неудач (чтобы не повторять)
        self.failure_patterns_file = self.BASE_PATH / "failure_patterns.json"
        if not self.failure_patterns_file.exists():
            self._save_json(self.failure_patterns_file, {
                "version": "1.0",
                "updated_at": str(datetime.now()),
                "failures": []
            })
        
        # База стратегий ценообразования
        self.pricing_strategies_file = self.BASE_PATH / "pricing_strategies.json"
        if not self.pricing_strategies_file.exists():
            strategies = {}
            for cat in self.CATEGORIES:
                strategies[cat] = {
                    "optimal_markup": None,  # % наценки
                    "price_elasticity": None,  # Эластичность цены
                    "competitive_position": "middle",  # Позиция среди конкурентов
                    "best_price_change_time": None,  # Лучшее время изменения цены
                    "seasonal_patterns": {},
                    "confidence": "low"
                }
            self._save_json(self.pricing_strategies_file, {
                "version": "1.0",
                "updated_at": str(datetime.now()),
                "strategies": strategies
            })
        
        # База рекламных стратегий
        self.ad_strategies_file = self.BASE_PATH / "ad_strategies.json"
        if not self.ad_strategies_file.exists():
            strategies = {}
            for cat in self.CATEGORIES:
                strategies[cat] = {
                    "optimal_drr": None,  # Целевой ДРР
                    "bid_adjustment_rules": [],  # Правила корректировки ставок
                    "best_keywords": [],  # Эффективные ключевые слова
                    "high_performing_placements": [],  # Лучшие размещения
                    "confidence": "low"
                }
            self._save_json(self.ad_strategies_file, {
                "version": "1.0",
                "updated_at": str(datetime.now()),
                "strategies": strategies
            })
        
        # Журнал обучения
        self.learning_log_file = self.BASE_PATH / "learning_log.json"
        if not self.learning_log_file.exists():
            self._save_json(self.learning_log_file, {
                "version": "1.0",
                "entries": []
            })
    
    def _save_json(self, path: Path, data: dict):
        """Сохраняет JSON файл"""
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def _load_json(self, path: Path) -> dict:
        """Загружает JSON файл"""
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    # =========================================================================
    # ОБУЧЕНИЕ НА ДАННЫХ МАГАЗИНА
    # =========================================================================
    
    async def learn_from_store(self, client_id: str, platform: str, category: str = None):
        """
        Основной метод обучения на магазине
        
        Args:
            client_id: ID клиента
            platform: 'wildberries', 'ozon', 'avito'
            category: Категория товаров (определяется автоматически если None)
        """
        print(f"[SelfLearning] Начинаю обучение на {platform} магазине клиента {client_id}")
        
        # 1. Определяем категорию если не указана
        if not category:
            category = await self._detect_category(client_id, platform)
        
        # 2. Собираем данные магазина
        store_data = await self._collect_store_data(client_id, platform)
        
        if not store_data or not store_data.get('products'):
            print(f"[SelfLearning] Нет данных для анализа")
            return
        
        # 3. Анализируем ценовые стратегии
        pricing_insights = self._analyze_pricing_strategy(store_data)
        if pricing_insights:
            await self._update_pricing_strategy(category, pricing_insights)
        
        # 4. Анализируем рекламные стратегии
        ad_insights = self._analyze_ad_strategy(store_data)
        if ad_insights:
            await self._update_ad_strategy(category, ad_insights)
        
        # 5. Ищем успешные паттерны
        success_patterns = self._extract_success_patterns(store_data)
        for pattern in success_patterns:
            await self._add_success_pattern(category, pattern, client_id)
        
        # 6. Логируем обучение
        self._log_learning("store_analysis", {
            "client_id": client_id,
            "platform": platform,
            "category": category,
            "patterns_found": len(success_patterns),
            "timestamp": str(datetime.now())
        })
        
        print(f"[SelfLearning] Обучение завершено. Найдено паттернов: {len(success_patterns)}")
    
    async def _detect_category(self, client_id: str, platform: str) -> str:
        """Определяет категорию магазина по товарам"""
        # TODO: Реальная классификация по названиям товаров
        # Пока возвращаем other
        return "other"
    
    async def _collect_store_data(self, client_id: str, platform: str) -> dict:
        """Собирает данные из API магазина"""
        data = {
            "client_id": client_id,
            "platform": platform,
            "products": [],
            "sales": [],
            "ads": []
        }
        
        # TODO: Реальные API вызовы
        # Пока проверяем есть ли локальные данные
        data_file = Path(f"/opt/clients/{client_id}/{platform}/store_data.json")
        if data_file.exists():
            with open(data_file, 'r') as f:
                return json.load(f)
        
        return data
    
    # =========================================================================
    # АНАЛИЗ СТРАТЕГИЙ
    # =========================================================================
    
    def _analyze_pricing_strategy(self, store_data: dict) -> Optional[dict]:
        """Анализирует ценовую стратегию магазина"""
        products = store_data.get('products', [])
        if len(products) < 3:
            return None
        
        # Анализируем изменения цен и их влияние на продажи
        price_changes = []
        for p in products:
            if 'price_history' in p and len(p['price_history']) >= 2:
                for i in range(1, len(p['price_history'])):
                    prev = p['price_history'][i-1]
                    curr = p['price_history'][i]
                    
                    price_change_pct = ((curr['price'] - prev['price']) / prev['price']) * 100
                    sales_change_pct = ((curr['sales'] - prev['sales']) / max(prev['sales'], 1)) * 100
                    
                    price_changes.append({
                        'price_change': price_change_pct,
                        'sales_change': sales_change_pct,
                        'date': curr.get('date')
                    })
        
        if not price_changes:
            return None
        
        # Ищем успешные изменения цен
        successful_increases = [x for x in price_changes if x['price_change'] > 0 and x['sales_change'] > 0]
        successful_decreases = [x for x in price_changes if x['price_change'] < 0 and x['sales_change'] > 0]
        
        insights = {}
        
        if successful_increases:
            avg_increase = statistics.mean([x['price_change'] for x in successful_increases])
            avg_sales_growth = statistics.mean([x['sales_change'] for x in successful_increases])
            insights['successful_price_increase'] = {
                'avg_price_change': round(avg_increase, 2),
                'avg_sales_growth': round(avg_sales_growth, 2),
                'count': len(successful_increases)
            }
        
        if successful_decreases:
            avg_decrease = statistics.mean([x['price_change'] for x in successful_decreases])
            avg_sales_growth = statistics.mean([x['sales_change'] for x in successful_decreases])
            insights['successful_price_decrease'] = {
                'avg_price_change': round(avg_decrease, 2),
                'avg_sales_growth': round(avg_sales_growth, 2),
                'count': len(successful_decreases)
            }
        
        return insights if insights else None
    
    def _analyze_ad_strategy(self, store_data: dict) -> Optional[dict]:
        """Анализирует рекламную стратегию"""
        ads = store_data.get('ads', [])
        if not ads:
            return None
        
        # Ищем кампании с хорошим ДРР
        good_campaigns = [a for a in ads if a.get('drr', 100) < 20]
        
        if len(good_campaigns) < 2:
            return None
        
        avg_drr = statistics.mean([a['drr'] for a in good_campaigns])
        avg_ctr = statistics.mean([a.get('ctr', 0) for a in good_campaigns])
        
        return {
            'optimal_drr': round(avg_drr, 2),
            'avg_ctr': round(avg_ctr, 4),
            'sample_size': len(good_campaigns),
            'common_keywords': self._extract_common_keywords(good_campaigns)
        }
    
    def _extract_common_keywords(self, campaigns: list) -> list:
        """Извлекает часто используемые ключевые слова"""
        # TODO: NLP анализ названий кампаний
        return []
    
    def _extract_success_patterns(self, store_data: dict) -> list:
        """Извлекает успешные паттерны из данных магазина"""
        patterns = []
        
        products = store_data.get('products', [])
        for product in products:
            # Ищем товары с ростом продаж
            if 'sales_history' in product and len(product['sales_history']) >= 2:
                recent_sales = product['sales_history'][-7:]  # Последняя неделя
                prev_sales = product['sales_history'][-14:-7]  # Предпоследняя неделя
                
                recent_avg = sum(recent_sales) / len(recent_sales)
                prev_avg = sum(prev_sales) / len(prev_sales)
                
                growth = ((recent_avg - prev_avg) / max(prev_avg, 1)) * 100
                
                if growth > 20:  # Рост > 20%
                    patterns.append({
                        'type': 'sales_growth',
                        'product_name': product.get('name', 'Unknown'),
                        'growth_percent': round(growth, 2),
                        'current_price': product.get('price'),
                        'category': product.get('category', 'other'),
                        'factors': self._identify_success_factors(product)
                    })
        
        return patterns
    
    def _identify_success_factors(self, product: dict) -> list:
        """Определяет факторы успеха товара"""
        factors = []
        
        # Проверяем цену относительно рынка
        if product.get('market_position') == 'below_average':
            factors.append('competitive_pricing')
        
        # Проверяем наличие рекламы
        if product.get('has_ads', False):
            factors.append('active_advertising')
        
        # Проверяем рейтинг
        if product.get('rating', 0) >= 4.5:
            factors.append('high_rating')
        
        # Проверяем количество отзывов
        if product.get('reviews_count', 0) > 50:
            factors.append('social_proof')
        
        return factors
    
    # =========================================================================
    # ОБНОВЛЕНИЕ СТРАТЕГИЙ
    # =========================================================================
    
    async def _update_pricing_strategy(self, category: str, insights: dict):
        """Обновляет стратегию ценообразования для категории"""
        data = self._load_json(self.pricing_strategies_file)
        
        if category not in data['strategies']:
            data['strategies'][category] = {}
        
        strategy = data['strategies'][category]
        
        # Обновляем на основе инсайтов
        if 'successful_price_increase' in insights:
            spi = insights['successful_price_increase']
            if spi['count'] >= 3:  # Минимум 3 примера
                strategy['optimal_markup'] = spi['avg_price_change']
                strategy['confidence'] = 'medium' if spi['count'] >= 5 else 'low'
        
        if 'successful_price_decrease' in insights:
            spd = insights['successful_price_decrease']
            if spd['count'] >= 3:
                strategy['price_elasticity'] = abs(spd['avg_sales_growth'] / spd['avg_price_change'])
        
        data['updated_at'] = str(datetime.now())
        self._save_json(self.pricing_strategies_file, data)
        
        print(f"[SelfLearning] Обновлена стратегия ценообразования для {category}")
    
    async def _update_ad_strategy(self, category: str, insights: dict):
        """Обновляет рекламную стратегию для категории"""
        data = self._load_json(self.ad_strategies_file)
        
        if category not in data['strategies']:
            data['strategies'][category] = {}
        
        strategy = data['strategies'][category]
        
        if 'optimal_drr' in insights:
            strategy['optimal_drr'] = insights['optimal_drr']
            strategy['confidence'] = 'medium' if insights.get('sample_size', 0) >= 5 else 'low'
        
        if 'common_keywords' in insights:
            strategy['best_keywords'] = insights['common_keywords']
        
        data['updated_at'] = str(datetime.now())
        self._save_json(self.ad_strategies_file, data)
        
        print(f"[SelfLearning] Обновлена рекламная стратегия для {category}")
    
    async def _add_success_pattern(self, category: str, pattern: dict, source_client: str):
        """Добавляет успешный паттерн в базу"""
        data = self._load_json(self.success_patterns_file)
        
        if category not in data['patterns']:
            data['patterns'][category] = []
        
        pattern['source_client'] = source_client
        pattern['discovered_at'] = str(datetime.now())
        pattern['usage_count'] = 0  # Сколько раз применен
        pattern['verified'] = False  # Подтвержден на других магазинах?
        
        data['patterns'][category].append(pattern)
        data['updated_at'] = str(datetime.now())
        
        self._save_json(self.success_patterns_file, data)
    
    # =========================================================================
    # ПРИМЕНЕНИЕ СТРАТЕГИЙ
    # =========================================================================
    
    async def get_recommendations(self, client_id: str, platform: str, category: str) -> dict:
        """
        Получает рекомендации для магазина на основе успешных паттернов
        
        Returns:
            dict: Рекомендации по ценам, рекламе, товарам
        """
        recommendations = {
            'pricing': None,
            'advertising': None,
            'products': None,
            'source': 'self_learning'
        }
        
        # Получаем стратегию ценообразования
        pricing_data = self._load_json(self.pricing_strategies_file)
        if category in pricing_data['strategies']:
            strategy = pricing_data['strategies'][category]
            if strategy.get('confidence') in ['medium', 'high']:
                recommendations['pricing'] = {
                    'recommended_markup': strategy.get('optimal_markup'),
                    'elasticity': strategy.get('price_elasticity'),
                    'confidence': strategy['confidence']
                }
        
        # Получаем рекламную стратегию
        ad_data = self._load_json(self.ad_strategies_file)
        if category in ad_data['strategies']:
            strategy = ad_data['strategies'][category]
            if strategy.get('confidence') in ['medium', 'high']:
                recommendations['advertising'] = {
                    'target_drr': strategy.get('optimal_drr'),
                    'best_keywords': strategy.get('best_keywords', []),
                    'confidence': strategy['confidence']
                }
        
        # Получаем успешные паттерны
        patterns_data = self._load_json(self.success_patterns_file)
        if category in patterns_data.get('patterns', {}):
            patterns = patterns_data['patterns'][category]
            # Берем последние 5 непроверенных паттернов
            unverified = [p for p in patterns if not p.get('verified')][-5:]
            if unverified:
                recommendations['products'] = {
                    'patterns_to_test': unverified,
                    'suggestion': f"Попробуйте применить {len(unverified)} успешных паттернов из категории {category}"
                }
        
        return recommendations
    
    async def apply_strategy(self, client_id: str, platform: str, strategy_type: str, params: dict):
        """
        Применяет стратегию к магазину
        
        Args:
            strategy_type: 'pricing', 'advertising', 'product'
            params: Параметры стратегии
        """
        print(f"[SelfLearning] Применяю стратегию {strategy_type} к магазину {client_id}")
        
        # TODO: Реальное применение через API
        # Пока только логируем намерение
        
        self._log_learning("strategy_applied", {
            "client_id": client_id,
            "platform": platform,
            "strategy_type": strategy_type,
            "params": params,
            "timestamp": str(datetime.now())
        })
    
    # =========================================================================
    # ЖУРНАЛИРОВАНИЕ
    # =========================================================================
    
    def _log_learning(self, event_type: str, details: dict):
        """Логирует событие обучения"""
        data = self._load_json(self.learning_log_file)
        
        entry = {
            'timestamp': str(datetime.now()),
            'event_type': event_type,
            'details': details
        }
        
        data['entries'].append(entry)
        
        # Храним последние 1000 записей
        if len(data['entries']) > 1000:
            data['entries'] = data['entries'][-1000:]
        
        self._save_json(self.learning_log_file, data)
    
    def get_learning_stats(self) -> dict:
        """Возвращает статистику обучения"""
        stats = {
            'total_patterns': 0,
            'patterns_by_category': {},
            'pricing_strategies_ready': [],
            'ad_strategies_ready': [],
            'last_learning': None
        }
        
        # Считаем паттерны
        patterns_data = self._load_json(self.success_patterns_file)
        for cat, patterns in patterns_data.get('patterns', {}).items():
            stats['patterns_by_category'][cat] = len(patterns)
            stats['total_patterns'] += len(patterns)
        
        # Проверяем готовность стратегий
        pricing_data = self._load_json(self.pricing_strategies_file)
        for cat, strategy in pricing_data.get('strategies', {}).items():
            if strategy.get('confidence') in ['medium', 'high']:
                stats['pricing_strategies_ready'].append(cat)
        
        ad_data = self._load_json(self.ad_strategies_file)
        for cat, strategy in ad_data.get('strategies', {}).items():
            if strategy.get('confidence') in ['medium', 'high']:
                stats['ad_strategies_ready'].append(cat)
        
        # Последнее обучение
        log_data = self._load_json(self.learning_log_file)
        if log_data['entries']:
            stats['last_learning'] = log_data['entries'][-1]['timestamp']
        
        return stats


# Singleton instance
_learning_engine = None

def get_learning_engine() -> SelfLearningEngine:
    """Возвращает singleton экземпляр движка обучения"""
    global _learning_engine
    if _learning_engine is None:
        _learning_engine = SelfLearningEngine()
    return _learning_engine


# ============================================================================
# ИНТЕГРАЦИЯ С БОТОМ
# ============================================================================

async def on_store_connected(client_id: str, platform: str):
    """
    Вызывается когда магазин успешно подключен
    Запускает процесс обучения
    """
    engine = get_learning_engine()
    
    # Запускаем обучение в фоне
    asyncio.create_task(engine.learn_from_store(client_id, platform))
    
    print(f"[SelfLearning] Запущено обучение для {client_id}/{platform}")


async def get_recommendations_for_user(client_id: str, platform: str, category: str = None):
    """
    Получает рекомендации для пользователя
    Вызывается при запросе советов в боте
    """
    engine = get_learning_engine()
    
    if not category:
        category = await engine._detect_category(client_id, platform)
    
    recommendations = await engine.get_recommendations(client_id, platform, category)
    
    return recommendations


# Для тестирования
if __name__ == "__main__":
    async def test():
        engine = get_learning_engine()
        print("Learning engine initialized")
        print("Stats:", engine.get_learning_stats())
    
    asyncio.run(test())
