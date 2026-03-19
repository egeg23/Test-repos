# ПЛАН: Доделка интеграции маркетплейсов

**Цель:** Сделать Fuck Mode рабочим (реальные API вызовы)
**Время:** 12-16 часов
**Этапы:** 4 PR через CodeRabbit

---

## Этап 1: Фабрика API клиентов (2-3 часа)

**Задача:** Связать cabinet_manager с wb_api_client и ozon_api_client

**Что создаем:**
```python
# modules/api_client_factory.py
class APIClientFactory:
    """Создает API клиенты из кабинетов пользователя"""
    
    @staticmethod
    def get_wb_client(user_id: str, cabinet_id: str) -> WBAPIClient:
        cabinet = cabinet_manager.get_cabinet(user_id, cabinet_id)
        return WBAPIClient(api_key=cabinet.api_key)
    
    @staticmethod
    def get_ozon_client(user_id: str, cabinet_id: str) -> OzonAPIClient:
        cabinet = cabinet_manager.get_cabinet(user_id, cabinet_id)
        return OzonAPIClient(
            client_id=cabinet.client_id,
            api_key=cabinet.api_key
        )
```

**Результат:** Можно получать клиентов по ID кабинета

---

## Этап 2: Dry Run режим (2 часа)

**Задача:** Добавить безопасный тестовый режим

**Что создаем:**
```python
# modules/fuck_mode_config.py
@dataclass
class FuckModeConfig:
    dry_run: bool = True  # По умолчанию - только показываем, не меняем
    
    # Лимиты
    max_price_change_percent: float = 20.0
    min_margin_percent: float = 15.0
    target_drr_percent: float = 15.0
```

**В Fuck Mode:**
- Если dry_run=True: показываем "Что бы сделал бот", но не применяем
- Логируем все решения
- Пользователь видит preview

**Результат:** Можно тестировать без риска

---

## Этап 3: Реальная логика ценообразования (4-6 часов)

**Задача:** Интегрировать Pricing Engine с реальными данными

**Что делаем:**
1. Получаем список товаров через API
2. Получаем цены конкурентов через Mpstats
3. Применяем Pricing Engine v2.0:
   - Buy Box Targeting
   - Profit Optimizer
   - Velocity-Based pricing
4. Рассчитываем новую цену
5. Если не dry_run — меняем цену через API

**Файлы:**
- Обновить `modules/fuck_mode.py`
- Интегрировать `modules/pricing_engine.py`

**Результат:** Цены меняются автоматически

---

## Этап 4: Логирование и откат (2-3 часа)

**Задача:** История операций + возможность отката

**Что создаем:**
```python
# modules/operation_log.py
class OperationLog:
    """Логирует все операции Fuck Mode"""
    
    def log_price_change(self, user_id, cabinet_id, product_id, 
                         old_price, new_price, reason)
    
    def rollback_operation(self, operation_id)  # Откат изменения
    
    def get_history(self, user_id, days=7)  # История операций
```

**Результат:**
- Видно что бот сделал
- Можно откатить изменения
- Статистика эффективности

---

## Приоритет

| Этап | Критичность | Блокирует запуск |
|------|-------------|------------------|
| 1 | 🔴 Высокая | Да |
| 2 | 🔴 Высокая | Да |
| 3 | 🔴 Высокая | Да |
| 4 | 🟡 Средняя | Нет |

---

## Готов начать с Этапа 1?
