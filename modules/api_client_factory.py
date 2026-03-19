# modules/api_client_factory.py
"""
API Client Factory - создание API клиентов из кабинетов пользователя

Связывает multi_cabinet_manager с wb_api_client и ozon_api_client
"""

import logging
from typing import Optional, Dict, List
from pathlib import Path

from .multi_cabinet_manager import cabinet_manager
from .wb_api_client import WBAPIClient
from .ozon_api_client import OzonAPIClient

logger = logging.getLogger('api_client_factory')


class CabinetNotFoundError(Exception):
    """Кабинет не найден"""
    pass


class CabinetNotActiveError(Exception):
    """Кабинет не активен"""
    pass


class APIClientFactory:
    """
    Фабрика API клиентов
    
    Создает API клиенты из данных кабинетов пользователя
    """
    
    @staticmethod
    def get_wb_client(user_id: str, cabinet_id: str) -> WBAPIClient:
        """
        Создает WB API клиент для кабинета
        
        Args:
            user_id: ID пользователя
            cabinet_id: ID кабинета
            
        Returns:
            WBAPIClient: Настроенный клиент
            
        Raises:
            CabinetNotFoundError: Кабинет не найден
            CabinetNotActiveError: Кабинет не активен
        """
        cabinet = cabinet_manager.get_cabinet(user_id, cabinet_id)
        
        if not cabinet:
            logger.error(f"Cabinet {cabinet_id} not found for user {user_id}")
            raise CabinetNotFoundError(f"Кабинет {cabinet_id} не найден")
        
        if not cabinet.is_active:
            logger.error(f"Cabinet {cabinet_id} is not active")
            raise CabinetNotActiveError(f"Кабинет {cabinet.name} не активен")
        
        if cabinet.platform != 'wb':
            logger.error(f"Cabinet {cabinet_id} is not WB platform")
            raise ValueError(f"Кабинет {cabinet.name} не является WB")
        
        logger.info(f"Creating WB client for cabinet: {cabinet.name}")
        return WBAPIClient(api_key=cabinet.api_key)
    
    @staticmethod
    def get_ozon_client(user_id: str, cabinet_id: str) -> OzonAPIClient:
        """
        Создает Ozon API клиент для кабинета
        
        Args:
            user_id: ID пользователя
            cabinet_id: ID кабинета
            
        Returns:
            OzonAPIClient: Настроенный клиент
            
        Raises:
            CabinetNotFoundError: Кабинет не найден
            CabinetNotActiveError: Кабинет не активен
        """
        cabinet = cabinet_manager.get_cabinet(user_id, cabinet_id)
        
        if not cabinet:
            logger.error(f"Cabinet {cabinet_id} not found for user {user_id}")
            raise CabinetNotFoundError(f"Кабинет {cabinet_id} не найден")
        
        if not cabinet.is_active:
            logger.error(f"Cabinet {cabinet_id} is not active")
            raise CabinetNotActiveError(f"Кабинет {cabinet.name} не активен")
        
        if cabinet.platform != 'ozon':
            logger.error(f"Cabinet {cabinet_id} is not Ozon platform")
            raise ValueError(f"Кабинет {cabinet.name} не является Ozon")
        
        if not cabinet.client_id:
            logger.error(f"Cabinet {cabinet_id} missing client_id")
            raise ValueError(f"У кабинета {cabinet.name} не указан Client ID")
        
        logger.info(f"Creating Ozon client for cabinet: {cabinet.name}")
        return OzonAPIClient(
            client_id=cabinet.client_id,
            api_key=cabinet.api_key
        )
    
    @staticmethod
    def get_all_wb_clients(user_id: str) -> Dict[str, WBAPIClient]:
        """
        Создает WB клиенты для всех активных кабинетов пользователя
        
        Args:
            user_id: ID пользователя
            
        Returns:
            Dict[str, WBAPIClient]: Словарь {cabinet_id: client}
        """
        clients = {}
        cabinets = cabinet_manager.get_active_cabinets(user_id, platform='wb')
        
        for cabinet in cabinets:
            try:
                client = APIClientFactory.get_wb_client(user_id, cabinet.id)
                clients[cabinet.id] = client
                logger.info(f"Created WB client for cabinet: {cabinet.name}")
            except Exception as e:
                logger.error(f"Failed to create WB client for {cabinet.name}: {e}")
        
        return clients
    
    @staticmethod
    def get_all_ozon_clients(user_id: str) -> Dict[str, OzonAPIClient]:
        """
        Создает Ozon клиенты для всех активных кабинетов пользователя
        
        Args:
            user_id: ID пользователя
            
        Returns:
            Dict[str, OzonAPIClient]: Словарь {cabinet_id: client}
        """
        clients = {}
        cabinets = cabinet_manager.get_active_cabinets(user_id, platform='ozon')
        
        for cabinet in cabinets:
            try:
                client = APIClientFactory.get_ozon_client(user_id, cabinet.id)
                clients[cabinet.id] = client
                logger.info(f"Created Ozon client for cabinet: {cabinet.name}")
            except Exception as e:
                logger.error(f"Failed to create Ozon client for {cabinet.name}: {e}")
        
        return clients
    
    @staticmethod
    def get_all_clients(user_id: str) -> Dict[str, Dict]:
        """
        Создает все API клиенты для пользователя
        
        Args:
            user_id: ID пользователя
            
        Returns:
            Dict: {
                'wb': {cabinet_id: WBAPIClient},
                'ozon': {cabinet_id: OzonAPIClient}
            }
        """
        return {
            'wb': APIClientFactory.get_all_wb_clients(user_id),
            'ozon': APIClientFactory.get_all_ozon_clients(user_id)
        }
    
    @staticmethod
    async def verify_cabinet_connection(user_id: str, cabinet_id: str) -> tuple[bool, str]:
        """
        Проверяет подключение к кабинету
        
        Args:
            user_id: ID пользователя
            cabinet_id: ID кабинета
            
        Returns:
            tuple[bool, str]: (успех, сообщение)
        """
        cabinet = cabinet_manager.get_cabinet(user_id, cabinet_id)
        
        if not cabinet:
            return False, "Кабинет не найден"
        
        if not cabinet.is_active:
            return False, "Кабинет не активен"
        
        try:
            if cabinet.platform == 'wb':
                client = APIClientFactory.get_wb_client(user_id, cabinet_id)
                # Пробуем получить список товаров
                products = await client.get_products(limit=1)
                return True, f"✅ Подключение к WB успешно ({len(products)} товаров доступно)"
            
            elif cabinet.platform == 'ozon':
                client = APIClientFactory.get_ozon_client(user_id, cabinet_id)
                # Пробуем получить список товаров
                products = await client.get_products(limit=1)
                return True, f"✅ Подключение к Ozon успешно ({len(products)} товаров доступно)"
            
            else:
                return False, f"Неизвестная платформа: {cabinet.platform}"
                
        except Exception as e:
            logger.error(f"Connection verification failed: {e}")
            return False, f"❌ Ошибка подключения: {str(e)}"


# Глобальный экземпляр фабрики
api_client_factory = APIClientFactory()
