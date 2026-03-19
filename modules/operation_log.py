# modules/operation_log.py
"""
Логирование операций Fuck Mode

История всех действий + возможность отката
"""

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict

logger = logging.getLogger('operation_log')


@dataclass
class OperationRecord:
    """Запись об операции"""
    id: str
    timestamp: str
    user_id: str
    cabinet_id: str
    cabinet_name: str
    product_id: str
    product_name: str
    operation_type: str  # 'price_change', 'stock_alert', 'ads_update'
    
    # До операции
    old_value: any
    
    # После операции
    new_value: any
    
    # Метаданные
    reason: str
    dry_run: bool
    success: bool
    error_message: Optional[str] = None


class OperationLog:
    """
    Менеджер истории операций Fuck Mode
    
    Хранит все действия бота с возможностью:
    - Просмотра истории
    - Отката изменений
    - Статистики эффективности
    """
    
    def __init__(self, clients_dir: str = "/opt/clients"):
        self.clients_dir = Path(clients_dir)
        self.logs_dir = self.clients_dir / "GLOBAL_AI_LEARNING" / "operation_logs"
        self.logs_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_user_log_path(self, user_id: str) -> Path:
        """Возвращает путь к файлу логов пользователя"""
        user_dir = self.logs_dir / user_id
        user_dir.mkdir(parents=True, exist_ok=True)
        return user_dir / "operations.jsonl"
    
    def log_operation(
        self,
        user_id: str,
        cabinet_id: str,
        cabinet_name: str,
        product_id: str,
        product_name: str,
        operation_type: str,
        old_value: any,
        new_value: any,
        reason: str,
        dry_run: bool = True,
        success: bool = True,
        error_message: Optional[str] = None
    ) -> str:
        """
        Логирует операцию
        
        Returns:
            str: ID операции
        """
        import uuid
        
        operation_id = str(uuid.uuid4())[:8]
        
        record = {
            'id': operation_id,
            'timestamp': datetime.now().isoformat(),
            'user_id': user_id,
            'cabinet_id': cabinet_id,
            'cabinet_name': cabinet_name,
            'product_id': product_id,
            'product_name': product_name,
            'operation_type': operation_type,
            'old_value': old_value,
            'new_value': new_value,
            'reason': reason,
            'dry_run': dry_run,
            'success': success,
            'error_message': error_message
        }
        
        log_path = self._get_user_log_path(user_id)
        
        try:
            with open(log_path, 'a') as f:
                f.write(json.dumps(record, ensure_ascii=False) + '\n')
            
            status = "DRY RUN" if dry_run else "APPLIED"
            logger.info(f"Operation logged [{status}]: {operation_type} for {product_name}")
            return operation_id
            
        except Exception as e:
            logger.error(f"Failed to log operation: {e}")
            return ""
    
    def get_user_operations(
        self,
        user_id: str,
        days: int = 7,
        operation_type: Optional[str] = None,
        only_real: bool = False
    ) -> List[Dict]:
        """
        Получает историю операций пользователя
        
        Args:
            user_id: ID пользователя
            days: За сколько последних дней
            operation_type: Фильтр по типу
            only_real: Только реальные (не dry_run)
            
        Returns:
            Список операций
        """
        log_path = self._get_user_log_path(user_id)
        
        if not log_path.exists():
            return []
        
        operations = []
        cutoff_date = datetime.now() - timedelta(days=days)
        
        try:
            with open(log_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    
                    try:
                        record = json.loads(line)
                        record_date = datetime.fromisoformat(record['timestamp'])
                        
                        # Фильтр по дате
                        if record_date < cutoff_date:
                            continue
                        
                        # Фильтр по типу
                        if operation_type and record['operation_type'] != operation_type:
                            continue
                        
                        # Фильтр по dry_run
                        if only_real and record.get('dry_run', True):
                            continue
                        
                        operations.append(record)
                        
                    except json.JSONDecodeError:
                        continue
            
            # Сортируем по дате (новые сверху)
            operations.sort(key=lambda x: x['timestamp'], reverse=True)
            return operations
            
        except Exception as e:
            logger.error(f"Failed to read operations: {e}")
            return []
    
    def get_operation_by_id(self, user_id: str, operation_id: str) -> Optional[Dict]:
        """Находит операцию по ID"""
        operations = self.get_user_operations(user_id, days=365)
        
        for op in operations:
            if op['id'] == operation_id:
                return op
        
        return None
    
    def get_statistics(self, user_id: str, days: int = 30) -> Dict:
        """
        Получает статистику операций
        
        Returns:
            {
                'total_operations': 100,
                'price_changes': 50,
                'stock_alerts': 30,
                'ads_updates': 20,
                'success_rate': 95.0,
                'avg_price_change': 5.2
            }
        """
        operations = self.get_user_operations(user_id, days=days, only_real=True)
        
        if not operations:
            return {
                'total_operations': 0,
                'price_changes': 0,
                'stock_alerts': 0,
                'ads_updates': 0,
                'success_rate': 0.0,
                'avg_price_change': 0.0
            }
        
        total = len(operations)
        successful = sum(1 for op in operations if op.get('success', True))
        
        price_changes = [op for op in operations if op['operation_type'] == 'price_change']
        
        # Считаем среднее изменение цены
        price_changes_pct = []
        for op in price_changes:
            old_val = op.get('old_value', 0)
            new_val = op.get('new_value', 0)
            if old_val and isinstance(old_val, (int, float)) and isinstance(new_val, (int, float)):
                pct = abs((new_val - old_val) / old_val * 100)
                price_changes_pct.append(pct)
        
        avg_price_change = sum(price_changes_pct) / len(price_changes_pct) if price_changes_pct else 0
        
        return {
            'total_operations': total,
            'price_changes': len(price_changes),
            'stock_alerts': sum(1 for op in operations if op['operation_type'] == 'stock_alert'),
            'ads_updates': sum(1 for op in operations if op['operation_type'] == 'ads_update'),
            'success_rate': round(successful / total * 100, 1) if total > 0 else 0,
            'avg_price_change': round(avg_price_change, 2)
        }
    
    async def rollback_operation(
        self,
        user_id: str,
        operation_id: str
    ) -> tuple[bool, str]:
        """
        Откатывает операцию к предыдущему значению
        
        Returns:
            tuple[bool, str]: (успех, сообщение)
        """
        from .api_client_factory import api_client_factory
        from .multi_cabinet_manager import cabinet_manager
        
        # Находим операцию
        operation = self.get_operation_by_id(user_id, operation_id)
        
        if not operation:
            return False, "Операция не найдена"
        
        if operation.get('dry_run', True):
            return False, "Нельзя откатить DRY RUN операцию"
        
        if operation['operation_type'] != 'price_change':
            return False, f"Откат {operation['operation_type']} не поддерживается"
        
        try:
            cabinet_id = operation['cabinet_id']
            product_id = operation['product_id']
            old_price = operation['old_value']
            
            cabinet = cabinet_manager.get_cabinet(user_id, cabinet_id)
            
            if not cabinet:
                return False, "Кабинет не найден"
            
            # Применяем старую цену
            if cabinet.platform == 'wb':
                client = api_client_factory.get_wb_client(user_id, cabinet_id)
                await client.update_price(product_id, int(old_price * 100))
            
            elif cabinet.platform == 'ozon':
                client = api_client_factory.get_ozon_client(user_id, cabinet_id)
                await client.update_price(product_id, old_price)
            
            # Логируем откат
            self.log_operation(
                user_id=user_id,
                cabinet_id=cabinet_id,
                cabinet_name=cabinet.name,
                product_id=product_id,
                product_name=operation['product_name'],
                operation_type='rollback',
                old_value=operation['new_value'],
                new_value=old_price,
                reason=f"Откат операции {operation_id}",
                dry_run=False,
                success=True
            )
            
            logger.info(f"Operation {operation_id} rolled back successfully")
            return True, f"✅ Цена возвращена к {old_price}"
            
        except Exception as e:
            logger.error(f"Failed to rollback operation: {e}")
            return False, f"❌ Ошибка отката: {str(e)}"


# Глобальный экземпляр
operation_log = OperationLog()
