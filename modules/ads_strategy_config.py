# modules/ads_strategy_config.py - Конфигурация стратегий рекламы
"""
Система стратегий управления ДРР для рекламных кампаний

Стратегии:
1. new_product - Запустить новый товар (высокий допустимый ДРР)
2. maintain_margin - Держать маржу (стандартный ДРР)
3. maintain_top_position - Поддержание топ позиции (минимальный ДРР, 5%)
4. break_into_top - Точное попадание в топ (для плохих продаж, 20%)
"""

import json
import logging
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger('ads_strategy_config')


class AdsStrategyType(Enum):
    """Типы стратегий управления рекламой"""
    NEW_PRODUCT = "new_product"           # Запустить новый товар
    MAINTAIN_MARGIN = "maintain_margin"   # Держать маржу
    MAINTAIN_TOP_POSITION = "maintain_top_position"  # Поддержание топ позиции
    BREAK_INTO_TOP = "break_into_top"     # Точное попадание в топ (для плохих продаж)


@dataclass
class AdsStrategy:
    """Конфигурация стратегии"""
    name: str                    # Название для отображения
    description: str             # Описание
    target_drr: float           # Целевой ДРР (%)
    max_drr: float              # Максимальный допустимый ДРР (%)
    min_drr: float              # Минимальный ДРР для увеличения ставки (%)
    bid_aggression: float       # Агрессивность изменения ставки (0.5-2.5)
    pause_threshold: float      # Порог для паузы (множитель к target_drr)
    priority: str               # Приоритет: sales | margin | position


# Предустановленные стратегии
DEFAULT_STRATEGIES = {
    AdsStrategyType.NEW_PRODUCT: AdsStrategy(
        name="🚀 Запустить новый товар",
        description="Высокий ДРР допустим для раскрутки. Фокус на выход в топ и первые продажи.",
        target_drr=25.0,
        max_drr=50.0,
        min_drr=15.0,
        bid_aggression=1.5,      # Быстрее повышаем ставки
        pause_threshold=2.0,     # Пауза только при ДРР > 50%
        priority="sales"
    ),
    
    AdsStrategyType.MAINTAIN_MARGIN: AdsStrategy(
        name="💰 Держать маржу",
        description="Баланс между продажами и прибылью. Стандартная стратегия.",
        target_drr=15.0,
        max_drr=25.0,
        min_drr=10.0,
        bid_aggression=1.0,      # Стандартная агрессивность
        pause_threshold=1.67,    # Пауза при ДРР > 25%
        priority="margin"
    ),
    
    AdsStrategyType.MAINTAIN_TOP_POSITION: AdsStrategy(
        name="🏆 Поддержание топ позиции",
        description="Топ-товары уже имеют органический буст в выдаче, поэтому целевой ДРР минимален (5%). Фокус на удержание позиции с минимальными рекламными затратами.",
        target_drr=5.0,          # Низкий ДРР — органика бустит
        max_drr=12.0,            # Макс допустимый ДРР
        min_drr=3.0,             # Минимальный ДРР для повышения ставки
        bid_aggression=2.0,      # Очень агрессивно
        pause_threshold=2.4,     # Пауза при ДРР > 12%
        priority="position"
    ),
    
    AdsStrategyType.BREAK_INTO_TOP: AdsStrategy(
        name="🎯 Точное попадание в топ",
        description="Агрессивная стратегия для товаров с плохими продажами. Высокие ставки для входа в топ-5, затем автопереключение на 'Поддержание топ позиции'.",
        target_drr=20.0,         # Высокий допустимый ДРР (временно)
        max_drr=35.0,            # Критический ДРР
        min_drr=15.0,            # Для увеличения ставки
        bid_aggression=2.5,      # Максимальная агрессивность
        pause_threshold=1.75,    # Пауза при ДРР > 35%
        priority="breakthrough"
    )
}


class AdsStrategyConfig:
    """Управление стратегиями рекламы для пользователей"""
    
    def __init__(self, storage_dir: str = "/opt/clients"):
        self.storage_dir = Path(storage_dir)
        self.config_file = self.storage_dir / "GLOBAL_AI_LEARNING" / "ads_strategies.json"
        self.config_file.parent.mkdir(parents=True, exist_ok=True)
        
        self._config = self._load_config()
    
    def _load_config(self) -> Dict:
        """Загружает конфигурацию стратегий"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading strategy config: {e}")
        return {}
    
    def _save_config(self):
        """Сохраняет конфигурацию"""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self._config, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving strategy config: {e}")
    
    def get_user_strategy(self, user_id: str) -> AdsStrategyType:
        """
        Получает стратегию пользователя
        
        Returns:
            AdsStrategyType (по умолчанию MAINTAIN_MARGIN)
        """
        strategy_str = self._config.get(user_id, AdsStrategyType.MAINTAIN_MARGIN.value)
        
        # Миграция: старое значение "top_position_low_drr" -> "maintain_top_position"
        if strategy_str == "top_position_low_drr":
            strategy_str = AdsStrategyType.MAINTAIN_TOP_POSITION.value
            self._config[user_id] = strategy_str
            self._save_config()
            logger.info(f"Migrated user {user_id} from top_position_low_drr to maintain_top_position")
        
        try:
            return AdsStrategyType(strategy_str)
        except ValueError:
            return AdsStrategyType.MAINTAIN_MARGIN
        except ValueError:
            return AdsStrategyType.MAINTAIN_MARGIN
    
    def set_user_strategy(self, user_id: str, strategy: AdsStrategyType):
        """Устанавливает стратегию пользователя"""
        self._config[user_id] = strategy.value
        self._save_config()
        logger.info(f"User {user_id} strategy set to {strategy.value}")
    
    def get_strategy_config(self, strategy_type: AdsStrategyType) -> AdsStrategy:
        """Получает конфигурацию стратегии"""
        return DEFAULT_STRATEGIES.get(strategy_type, DEFAULT_STRATEGIES[AdsStrategyType.MAINTAIN_MARGIN])
    
    def get_user_strategy_config(self, user_id: str) -> AdsStrategy:
        """Получает конфигурацию стратегии пользователя"""
        strategy_type = self.get_user_strategy(user_id)
        return self.get_strategy_config(strategy_type)
    
    def get_all_strategies(self) -> Dict[AdsStrategyType, AdsStrategy]:
        """Возвращает все доступные стратегии"""
        return DEFAULT_STRATEGIES.copy()


# Глобальный экземпляр
ads_strategy_config = AdsStrategyConfig()


if __name__ == "__main__":
    # Тестирование
    config = AdsStrategyConfig()
    
    print("Доступные стратегии:")
    for stype, sconfig in config.get_all_strategies().items():
        print(f"\n{stype.value}:")
        print(f"  Name: {sconfig.name}")
        print(f"  Target DRR: {sconfig.target_drr}%")
        print(f"  Max DRR: {sconfig.max_drr}%")
