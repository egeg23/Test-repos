# modules/multi_cabinet_manager.py - Управление множественными кабинетами
"""
Управление до 5 кабинетов WB и 5 кабинетов Ozon на пользователя
Этап 1: Мульти-кабинетная поддержка
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict

logger = logging.getLogger('multi_cabinet_manager')


@dataclass
class Cabinet:
    """Модель кабинета"""
    id: str  # Уникальный ID кабинета
    name: str  # Название (задает пользователь)
    platform: str  # 'wb' или 'ozon'
    api_key: str
    client_id: Optional[str] = None  # Для Ozon
    is_active: bool = True
    added_at: str = None
    last_used: Optional[str] = None
    
    def __post_init__(self):
        if not self.added_at:
            self.added_at = datetime.now().isoformat()


class MultiCabinetManager:
    """
    🏪 Менеджер множественных кабинетов
    
    Лимиты:
    - До 5 кабинетов Wildberries
    - До 5 кабинетов Ozon
    """
    
    LIMITS = {
        'wb': 5,
        'ozon': 5
    }
    
    def __init__(self, clients_dir: str = "/opt/clients"):
        self.clients_dir = Path(clients_dir)
        self.storage_file = self.clients_dir / "cabinets_config.json"
        self.cabinets: Dict[str, List[Cabinet]] = self._load_cabinets()
    
    def _load_cabinets(self) -> Dict[str, List[Cabinet]]:
        """Загружает конфигурацию кабинетов"""
        if not self.storage_file.exists():
            return {}
        
        try:
            with open(self.storage_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Конвертируем обратно в объекты Cabinet
            result = {}
            for user_id, cabinets_list in data.items():
                result[user_id] = [
                    Cabinet(**cab_data) for cab_data in cabinets_list
                ]
            return result
        except Exception as e:
            logger.error(f"❌ Error loading cabinets: {e}")
            return {}
    
    def _save_cabinets(self):
        """Сохраняет конфигурацию"""
        # Конвертируем Cabinet в dict
        data = {}
        for user_id, cabinets_list in self.cabinets.items():
            data[user_id] = [asdict(cab) for cab in cabinets_list]
        
        with open(self.storage_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def get_user_cabinets(self, user_id: str, platform: Optional[str] = None) -> List[Cabinet]:
        """Возвращает кабинеты пользователя"""
        user_cabs = self.cabinets.get(user_id, [])
        
        if platform:
            return [c for c in user_cabs if c.platform == platform]
        
        return user_cabs
    
    def get_cabinet(self, user_id: str, cabinet_id: str) -> Optional[Cabinet]:
        """Возвращает конкретный кабинет"""
        user_cabs = self.cabinets.get(user_id, [])
        for cab in user_cabs:
            if cab.id == cabinet_id:
                return cab
        return None
    
    def add_cabinet(
        self,
        user_id: str,
        name: str,
        platform: str,
        api_key: str,
        client_id: Optional[str] = None
    ) -> tuple[bool, str]:
        """
        Добавляет кабинет
        
        Returns:
            (success, message)
        """
        platform = platform.lower()
        
        # Проверяем платформу
        if platform not in self.LIMITS:
            return False, f"❌ Неизвестная платформа: {platform}"
        
        # Получаем текущие кабинеты пользователя
        user_cabs = self.cabinets.get(user_id, [])
        platform_cabs = [c for c in user_cabs if c.platform == platform]
        
        # Проверяем лимит
        if len(platform_cabs) >= self.LIMITS[platform]:
            return False, f"❌ Лимит кабинетов {platform.upper()}: {self.LIMITS[platform]}"
        
        # Проверяем уникальность названия
        existing_names = [c.name.lower() for c in user_cabs]
        if name.lower() in existing_names:
            return False, f"❌ Кабинет с названием '{name}' уже существует"
        
        # Создаем ID
        cabinet_id = f"{platform}_{user_id}_{len(user_cabs) + 1}"
        
        # Создаем кабинет
        cabinet = Cabinet(
            id=cabinet_id,
            name=name,
            platform=platform,
            api_key=api_key,
            client_id=client_id
        )
        
        # Добавляем
        if user_id not in self.cabinets:
            self.cabinets[user_id] = []
        
        self.cabinets[user_id].append(cabinet)
        self._save_cabinets()
        
        logger.info(f"✅ Cabinet added: {name} ({platform}) for user {user_id}")
        return True, f"✅ Кабинет '{name}' добавлен"
    
    def remove_cabinet(self, user_id: str, cabinet_id: str) -> tuple[bool, str]:
        """Удаляет кабинет"""
        user_cabs = self.cabinets.get(user_id, [])
        
        for i, cab in enumerate(user_cabs):
            if cab.id == cabinet_id:
                removed = user_cabs.pop(i)
                self._save_cabinets()
                logger.info(f"✅ Cabinet removed: {removed.name}")
                return True, f"✅ Кабинет '{removed.name}' удален"
        
        return False, "❌ Кабинет не найден"
    
    def update_cabinet(
        self,
        user_id: str,
        cabinet_id: str,
        name: Optional[str] = None,
        api_key: Optional[str] = None,
        is_active: Optional[bool] = None
    ) -> tuple[bool, str]:
        """Обновляет данные кабинета"""
        cabinet = self.get_cabinet(user_id, cabinet_id)
        
        if not cabinet:
            return False, "❌ Кабинет не найден"
        
        if name:
            cabinet.name = name
        if api_key:
            cabinet.api_key = api_key
        if is_active is not None:
            cabinet.is_active = is_active
        
        cabinet.last_used = datetime.now().isoformat()
        self._save_cabinets()
        
        return True, f"✅ Кабинет '{cabinet.name}' обновлен"
    
    def get_active_cabinets(self, user_id: str, platform: Optional[str] = None) -> List[Cabinet]:
        """Возвращает активные кабинеты"""
        cabs = self.get_user_cabinets(user_id, platform)
        return [c for c in cabs if c.is_active]
    
    def get_cabinet_count(self, user_id: str, platform: Optional[str] = None) -> Dict[str, int]:
        """Возвращает количество кабинетов"""
        user_cabs = self.cabinets.get(user_id, [])
        
        if platform:
            return {
                'total': len([c for c in user_cabs if c.platform == platform]),
                'limit': self.LIMITS[platform]
            }
        
        return {
            'wb': len([c for c in user_cabs if c.platform == 'wb']),
            'ozon': len([c for c in user_cabs if c.platform == 'ozon']),
            'wb_limit': self.LIMITS['wb'],
            'ozon_limit': self.LIMITS['ozon']
        }
    
    def can_add_cabinet(self, user_id: str, platform: str) -> tuple[bool, str]:
        """Проверяет можно ли добавить кабинет"""
        platform = platform.lower()
        
        if platform not in self.LIMITS:
            return False, "Неизвестная платформа"
        
        user_cabs = self.cabinets.get(user_id, [])
        platform_cabs = [c for c in user_cabs if c.platform == platform]
        
        if len(platform_cabs) >= self.LIMITS[platform]:
            return False, f"Достигнут лимит: {self.LIMITS[platform]}"
        
        remaining = self.LIMITS[platform] - len(platform_cabs)
        return True, f"Можно добавить: {remaining}"
    
    def format_cabinet_list(self, user_id: str) -> str:
        """Форматирует список кабинетов для отображения"""
        cabs = self.get_user_cabinets(user_id)
        
        if not cabs:
            return "📭 У вас пока нет подключенных кабинетов"
        
        wb_cabs = [c for c in cabs if c.platform == 'wb']
        ozon_cabs = [c for c in cabs if c.platform == 'ozon']
        
        text = "🏪 <b>Ваши кабинеты</b>\n\n"
        
        if wb_cabs:
            text += f"🟣 <b>Wildberries</b> ({len(wb_cabs)}/5):\n"
            for i, cab in enumerate(wb_cabs, 1):
                status = "🟢" if cab.is_active else "🔴"
                text += f"{i}. {status} {cab.name}\n"
            text += "\n"
        
        if ozon_cabs:
            text += f"🔵 <b>Ozon</b> ({len(ozon_cabs)}/5):\n"
            for i, cab in enumerate(ozon_cabs, 1):
                status = "🟢" if cab.is_active else "🔴"
                text += f"{i}. {status} {cab.name}\n"
        
        return text


# Глобальный экземпляр
cabinet_manager = MultiCabinetManager()
