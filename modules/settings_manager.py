# modules/settings_manager.py - Управление настройками автономности
"""
Управление пользовательскими настройками для автономного цикла.
Пользователь может задавать пороги через бота.
"""

import json
import logging
from pathlib import Path
from typing import Dict, Optional
from dataclasses import dataclass, asdict

logger = logging.getLogger('settings_manager')


@dataclass
class AutonomySettings:
    """Настройки автономности"""
    # Порог запасов (дней). По умолчанию 17, диапазон 10-30
    stock_days_threshold: int = 17
    
    # Макс. изменение цены (%). Дефолт 20%, диапазон 5-50
    max_price_change_percent: int = 20
    
    # Целевой ДРР (%). Дефолт 15%, диапазон 5-30
    target_drr_percent: int = 15
    
    # Минимальная маржа (%). Дефолт 15%, диапазон 5-30
    min_margin_percent: int = 15
    
    # Включить автоматическое изменение цен
    auto_price_adjustment: bool = False
    
    # Включить автоматическое управление рекламой
    auto_ad_management: bool = False
    
    # Уведомления (все/только критичные/отключены)
    notification_level: str = "all"  # all, critical, none


class SettingsManager:
    """Менеджер настроек пользователя"""
    
    # Валидация значений
    VALID_RANGES = {
        'stock_days_threshold': (10, 30),
        'max_price_change_percent': (5, 50),
        'target_drr_percent': (5, 30),
        'min_margin_percent': (5, 30),
    }
    
    def __init__(self, clients_dir: str = "/opt/clients"):
        self.clients_dir = Path(clients_dir)
    
    def _get_settings_file(self, client_id: str) -> Path:
        """Путь к файлу настроек"""
        settings_dir = self.clients_dir / client_id / "settings"
        settings_dir.mkdir(parents=True, exist_ok=True)
        return settings_dir / "autonomy.json"
    
    def get_settings(self, client_id: str) -> AutonomySettings:
        """Загружает настройки пользователя (или дефолт)"""
        settings_file = self._get_settings_file(client_id)
        
        if settings_file.exists():
            try:
                with open(settings_file, 'r') as f:
                    data = json.load(f)
                    return AutonomySettings(**data)
            except Exception as e:
                logger.error(f"❌ Ошибка загрузки настроек {client_id}: {e}")
        
        return AutonomySettings()  # Дефолтные
    
    def save_settings(self, client_id: str, settings: AutonomySettings) -> bool:
        """Сохраняет настройки пользователя"""
        settings_file = self._get_settings_file(client_id)
        
        try:
            with open(settings_file, 'w') as f:
                json.dump(asdict(settings), f, indent=2)
            logger.info(f"💾 Настройки сохранены для {client_id}")
            return True
        except Exception as e:
            logger.error(f"❌ Ошибка сохранения настроек {client_id}: {e}")
            return False
    
    def update_setting(self, client_id: str, field: str, value) -> bool:
        """
        Обновляет одну настройку с валидацией.
        Возвращает True если успешно.
        """
        # Получаем текущие настройки
        settings = self.get_settings(client_id)
        
        # Проверяем существование поля
        if not hasattr(settings, field):
            logger.warning(f"⚠️ Неизвестное поле настроек: {field}")
            return False
        
        # Валидация для числовых полей
        if field in self.VALID_RANGES:
            min_val, max_val = self.VALID_RANGES[field]
            try:
                value = int(value)
                if not (min_val <= value <= max_val):
                    logger.warning(f"⚠️ Значение {value} вне диапазона [{min_val}, {max_val}]")
                    return False
            except (ValueError, TypeError):
                logger.warning(f"⚠️ Некорректное значение: {value}")
                return False
        
        # Обновляем
        setattr(settings, field, value)
        return self.save_settings(client_id, settings)
    
    def reset_to_defaults(self, client_id: str) -> bool:
        """Сбрасывает настройки к дефолтным"""
        return self.save_settings(client_id, AutonomySettings())
    
    def format_settings_message(self, client_id: str) -> str:
        """Форматирует настройки для отображения в Telegram"""
        s = self.get_settings(client_id)
        
        return (
            "⚙️ <b>Настройки автономности</b>\n\n"
            f"📦 <b>Порог запасов:</b> {s.stock_days_threshold} дней\n"
            f"   (Алерт когда запасов меньше на X дней)\n\n"
            f"💰 <b>Макс. изменение цены:</b> ±{s.max_price_change_percent}%\n"
            f"   (Автоном не изменит цену больше чем на X%)\n\n"
            f"📢 <b>Целевой ДРР:</b> {s.target_drr_percent}%\n"
            f"   (Оптимальная доля рекламных расходов)\n\n"
            f"💸 <b>Мин. маржа:</b> {s.min_margin_percent}%\n"
            f"   (Алерт если маржа ниже X%)\n\n"
            f"🤖 <b>Авто-цены:</b> {'✅ Вкл' if s.auto_price_adjustment else '❌ Выкл'}\n"
            f"🤖 <b>Авто-реклама:</b> {'✅ Вкл' if s.auto_ad_management else '❌ Выкл'}\n\n"
            f"🔔 <b>Уведомления:</b> {s.notification_level.upper()}"
        )
