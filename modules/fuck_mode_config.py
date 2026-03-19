# modules/fuck_mode_config.py
"""
Конфигурация Fuck Mode

Включает dry run режим для безопасного тестирования
"""

import json
import logging
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional

logger = logging.getLogger('fuck_mode_config')


@dataclass
class FuckModeConfig:
    """
    Конфигурация автономного режима
    
    Attributes:
        dry_run: Если True - только показывает что бы сделал, не применяет
        max_price_change_percent: Максимальное изменение цены (default: 20%)
        min_margin_percent: Минимальная маржа (default: 15%)
        target_drr_percent: Целевой ДРР для рекламы (default: 15%)
        stock_days_threshold: Порог дней запаса (default: 17)
        enabled_notifications: Отправлять уведомления о решениях
    """
    dry_run: bool = True  # По умолчанию - безопасный режим
    max_price_change_percent: float = 20.0
    min_margin_percent: float = 15.0
    target_drr_percent: float = 15.0
    stock_days_threshold: int = 17
    enabled_notifications: bool = True
    
    def to_dict(self) -> dict:
        """Конвертирует в словарь"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> 'FuckModeConfig':
        """Создает из словаря"""
        return cls(**data)


class FuckModeConfigManager:
    """
    Менеджер конфигурации Fuck Mode
    
    Хранит настройки per-user
    """
    
    def __init__(self, clients_dir: str = "/opt/clients"):
        self.clients_dir = Path(clients_dir)
        self.config_file = "fuck_mode_config.json"
    
    def _get_config_path(self, user_id: str) -> Path:
        """Возвращает путь к файлу конфигурации пользователя"""
        user_dir = self.clients_dir / user_id / "settings"
        user_dir.mkdir(parents=True, exist_ok=True)
        return user_dir / self.config_file
    
    def get_config(self, user_id: str) -> FuckModeConfig:
        """
        Получает конфигурацию пользователя
        
        Если конфиг не существует - создает с дефолтными значениями
        """
        config_path = self._get_config_path(user_id)
        
        if config_path.exists():
            try:
                with open(config_path, 'r') as f:
                    data = json.load(f)
                return FuckModeConfig.from_dict(data)
            except Exception as e:
                logger.error(f"Failed to load config for {user_id}: {e}")
                return FuckModeConfig()  # Возвращаем дефолт
        else:
            # Создаем дефолтный конфиг
            config = FuckModeConfig()
            self.save_config(user_id, config)
            return config
    
    def save_config(self, user_id: str, config: FuckModeConfig):
        """Сохраняет конфигурацию"""
        config_path = self._get_config_path(user_id)
        
        try:
            with open(config_path, 'w') as f:
                json.dump(config.to_dict(), f, indent=2)
            logger.info(f"Config saved for user {user_id}")
        except Exception as e:
            logger.error(f"Failed to save config for {user_id}: {e}")
    
    def update_config(self, user_id: str, **kwargs) -> FuckModeConfig:
        """
        Обновляет конфигурацию
        
        Args:
            **kwargs: Поля для обновления
        """
        config = self.get_config(user_id)
        
        for key, value in kwargs.items():
            if hasattr(config, key):
                setattr(config, key, value)
                logger.info(f"Config updated: {key} = {value} for user {user_id}")
            else:
                logger.warning(f"Unknown config key: {key}")
        
        self.save_config(user_id, config)
        return config
    
    def is_dry_run(self, user_id: str) -> bool:
        """Проверяет включен ли dry run режим"""
        config = self.get_config(user_id)
        return config.dry_run
    
    def set_dry_run(self, user_id: str, enabled: bool):
        """Включает/выключает dry run режим"""
        self.update_config(user_id, dry_run=enabled)
        status = "включен" if enabled else "выключен"
        logger.info(f"Dry run {status} for user {user_id}")
    
    def get_limits(self, user_id: str) -> dict:
        """Возвращает лимиты пользователя"""
        config = self.get_config(user_id)
        return {
            'max_price_change': config.max_price_change_percent,
            'min_margin': config.min_margin_percent,
            'target_drr': config.target_drr_percent,
            'stock_days': config.stock_days_threshold
        }


# Глобальный менеджер
fuck_mode_config = FuckModeConfigManager()
