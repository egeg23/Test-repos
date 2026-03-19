# modules/evirma_integration.py - Интеграция с Chrome расширением Evirma
"""
Интеграция с Evirma (Chrome extension) для получения ставок для топ позиций.

Evirma - бесплатное расширение для Chrome, показывающее:
- Ставки (cpm) для позиций 1-10 в поиске WB
- Тренд ставок
- Конкурентов на позициях
- Рекомендуемую ставку

Архитектура:
1. Playwright/Selenium управляет Chrome с установленным расширением
2. Открывает wildberries.ru/search?search={артикул}
3. Evirma показывает ставки - парсим их
4. Возвращаем рекомендуемую ставку для целевой позиции

Требования:
- Chrome с установленным расширением Evirma
- GUI или headless с xvfb (для сервера)
- Для сервера: возможно потребуется VNC/display
"""

import asyncio
import json
import logging
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from pathlib import Path

logger = logging.getLogger('evirma_integration')


@dataclass
class PositionBid:
    """Ставка для конкретной позиции"""
    position: int           # Позиция (1-10)
    bid: float             # Ставка CPM (руб)
    trend: str             # Тренд: up/down/stable
    competitors: int       # Количество конкурентов


@dataclass
class EvirmaData:
    """Данные от Evirma для артикула"""
    artikul: str
    query: str             # Поисковый запрос
    position_bids: List[PositionBid]  # Ставки по позициям
    recommended_bid: float # Рекомендуемая ставка
    avg_bid: float         # Средняя ставка
    timestamp: str


class EvirmaIntegration:
    """
    Интеграция с Evirma Chrome Extension
    
    ВНИМАНИЕ: Требует Chrome с установленным расширением Evirma.
    На сервере без GUI потребуется xvfb или аналог.
    """
    
    def __init__(self, chrome_extension_path: Optional[str] = None):
        self.extension_path = chrome_extension_path
        self._browser = None
        self._page = None
        self._initialized = False
        
    async def initialize(self):
        """Инициализирует браузер с расширением Evirma"""
        try:
            # Здесь будет инициализация Playwright/Selenium
            # с Chrome + Evirma extension
            # 
            # Пример с Playwright:
            # from playwright.async_api import async_playwright
            # self._playwright = await async_playwright().start()
            # self._browser = await self._playwright.chromium.launch(
            #     headless=False,  # Evirma требует GUI
            #     args=[f'--disable-extensions-except={self.extension_path}']
            # )
            # self._page = await self._browser.new_page()
            
            logger.info("Evirma integration initialized (mock)")
            self._initialized = True
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize Evirma: {e}")
            return False
    
    async def get_bids_for_artikul(self, artikul: str, search_query: Optional[str] = None) -> Optional[EvirmaData]:
        """
        Получает ставки для артикула через Evirma
        
        Args:
            artikul: Артикул WB
            search_query: Поисковый запрос (если None - используем артикул)
        
        Returns:
            EvirmaData или None если ошибка
        """
        if not self._initialized:
            success = await self.initialize()
            if not success:
                return None
        
        query = search_query or artikul
        
        try:
            # Здесь будет реальная логика:
            # 1. Открываем wildberries.ru/catalog/0/search.aspx?search={query}
            # 2. Ждем загрузки Evirma (оно встраивается в страницу)
            # 3. Парсим данные из DOM/через API Evirma
            
            # Мок для примера:
            logger.info(f"Getting bids for artikul {artikul}, query: {query}")
            
            # TODO: Реальная интеграция с Evirma
            # Сейчас возвращаем мок-данные
            return self._generate_mock_data(artikul, query)
            
        except Exception as e:
            logger.error(f"Error getting bids for {artikul}: {e}")
            return None
    
    def get_bid_for_position(self, evirma_data: EvirmaData, target_position: int) -> Tuple[float, float]:
        """
        Получает ставку для целевой позиции + рекомендуемую надбавку
        
        Args:
            evirma_data: Данные от Evirma
            target_position: Целевая позиция (1-10)
        
        Returns:
            (bid_for_position, recommended_with_margin)
        """
        # Ищем ставку для целевой позиции
        for pb in evirma_data.position_bids:
            if pb.position == target_position:
                # Добавляем 10-20% для уверенного входа в топ
                margin = 1.15 if target_position <= 3 else 1.10
                return (pb.bid, round(pb.bid * margin, 2))
        
        # Если нет данных для этой позиции - используем среднюю
        return (evirma_data.avg_bid, round(evirma_data.avg_bid * 1.2, 2))
    
    async def close(self):
        """Закрывает браузер"""
        if self._browser:
            await self._browser.close()
            self._initialized = False
            logger.info("Evirma integration closed")
    
    def _generate_mock_data(self, artikul: str, query: str) -> EvirmaData:
        """Генерирует мок-данные для тестирования"""
        import random
        from datetime import datetime
        
        # Генерируем моковые ставки для позиций 1-10
        # В реальности позиция 1 = самая высокая ставка
        base_bid = random.uniform(150, 500)
        position_bids = []
        
        for pos in range(1, 11):
            # Чем ниже позиция, тем выше ставка (в среднем)
            position_factor = 1.0 + (10 - pos) * 0.1  # 1.9 для позиции 1, 1.0 для позиции 10
            bid = round(base_bid * position_factor * random.uniform(0.8, 1.2), 2)
            
            position_bids.append(PositionBid(
                position=pos,
                bid=bid,
                trend=random.choice(['up', 'down', 'stable']),
                competitors=random.randint(1, 15)
            ))
        
        avg_bid = round(sum(pb.bid for pb in position_bids) / len(position_bids), 2)
        
        return EvirmaData(
            artikul=artikul,
            query=query,
            position_bids=position_bids,
            recommended_bid=round(avg_bid * 1.15, 2),
            avg_bid=avg_bid,
            timestamp=datetime.now().isoformat()
        )


class EvirmaCache:
    """Кэш для данных Evirma (чтобы не спамить запросами)"""
    
    def __init__(self, cache_dir: str = "/opt/clients/GLOBAL_AI_LEARNING"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_file = self.cache_dir / "evirma_cache.json"
        self._cache = self._load_cache()
        self._ttl_hours = 2  # Кэш живет 2 часа
    
    def _load_cache(self) -> Dict:
        """Загружает кэш"""
        if self.cache_file.exists():
            try:
                with open(self.cache_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading Evirma cache: {e}")
        return {}
    
    def _save_cache(self):
        """Сохраняет кэш"""
        try:
            with open(self.cache_file, 'w') as f:
                json.dump(self._cache, f, indent=2, default=lambda o: o.__dict__)
        except Exception as e:
            logger.error(f"Error saving Evirma cache: {e}")
    
    def get(self, artikul: str) -> Optional[EvirmaData]:
        """Получает данные из кэша если они свежие"""
        from datetime import datetime, timedelta
        
        if artikul not in self._cache:
            return None
        
        entry = self._cache[artikul]
        timestamp = datetime.fromisoformat(entry['timestamp'])
        
        if datetime.now() - timestamp > timedelta(hours=self._ttl_hours):
            return None  # Устарело
        
        # Восстанавливаем объект
        position_bids = [PositionBid(**pb) for pb in entry['position_bids']]
        return EvirmaData(
            artikul=entry['artikul'],
            query=entry['query'],
            position_bids=position_bids,
            recommended_bid=entry['recommended_bid'],
            avg_bid=entry['avg_bid'],
            timestamp=entry['timestamp']
        )
    
    def set(self, artikul: str, data: EvirmaData):
        """Сохраняет данные в кэш"""
        self._cache[artikul] = {
            'artikul': data.artikul,
            'query': data.query,
            'position_bids': [{'position': pb.position, 'bid': pb.bid, 
                              'trend': pb.trend, 'competitors': pb.competitors} 
                             for pb in data.position_bids],
            'recommended_bid': data.recommended_bid,
            'avg_bid': data.avg_bid,
            'timestamp': data.timestamp
        }
        self._save_cache()


# Глобальный экземпляр
evirma_integration = EvirmaIntegration()
evirma_cache = EvirmaCache()


async def get_optimal_bid_for_top(artikul: str, target_position: int = 5) -> Optional[Tuple[float, float]]:
    """
    Получает оптимальную ставку для входа в топ через Evirma
    
    Args:
        artikul: Артикул товара
        target_position: Целевая позиция (1-10, по умолчанию 5)
    
    Returns:
        (текущая_ставка_для_позиции, рекомендуемая_ставка) или None
    """
    # Сначала проверяем кэш
    cached = evirma_cache.get(artikul)
    if cached:
        logger.info(f"Using cached Evirma data for {artikul}")
        return evirma_integration.get_bid_for_position(cached, target_position)
    
    # Получаем свежие данные
    data = await evirma_integration.get_bids_for_artikul(artikul)
    if not data:
        return None
    
    # Сохраняем в кэш
    evirma_cache.set(artikul, data)
    
    return evirma_integration.get_bid_for_position(data, target_position)


if __name__ == "__main__":
    # Тестирование
    async def test():
        await evirma_integration.initialize()
        
        artikul = "12345678"
        data = await evirma_integration.get_bids_for_artikul(artikul)
        
        if data:
            print(f"Данные для артикула {artikul}:")
            print(f"Поисковый запрос: {data.query}")
            print(f"Средняя ставка: {data.avg_bid}₽")
            print(f"Рекомендуемая: {data.recommended_bid}₽")
            print("\nСтавки по позициям:")
            for pb in data.position_bids:
                print(f"  Позиция {pb.position}: {pb.bid}₽ ({pb.trend})")
            
            # Тестируем получение ставки для позиции
            bid, recommended = evirma_integration.get_bid_for_position(data, target_position=3)
            print(f"\nДля входа в топ-3: текущая ~{bid}₽, рекомендуемая ~{recommended}₽")
        
        await evirma_integration.close()
    
    asyncio.run(test())
