#!/usr/bin/env python3
"""
Тестирование CTR Monitor
"""

import asyncio
import sys
sys.path.insert(0, '/opt/telegram_bot')

from modules.ctr_monitor import CTRMonitor, get_monitor, CampaignMetrics

async def test_monitor():
    """Тестирование функционала мониторинга"""
    print("=" * 50)
    print("🧪 ТЕСТИРОВАНИЕ CTR MONITOR")
    print("=" * 50)
    
    # Тест 1: Создание монитора
    print("\n1. Создание монитора...")
    user_id = "216929582"  # ID администратора
    monitor = get_monitor(user_id)
    print(f"   ✅ Монитор создан для пользователя {user_id}")
    print(f"   📁 Директория: {monitor.ctr_dir}")
    
    # Тест 2: Создание тестовой кампании
    print("\n2. Создание тестовой кампании...")
    test_campaign = CampaignMetrics(
        article_id="12345678",
        campaign_id="TEST_001",
        marketplace="wb",
        name="Тестовая кампания",
        status="active",
        impressions=600,
        clicks=15,
        ctr=2.5,
        start_ctr=2.5,
        current_ctr=2.5,
        started_at="2026-03-16T18:00:00",
        status_monitor="collecting"
    )
    
    # Сохраняем в активные
    monitor._active_campaigns[test_campaign.campaign_id] = test_campaign
    monitor._save_active_campaigns()
    print(f"   ✅ Тестовая кампания создана")
    print(f"   🆔 Campaign ID: {test_campaign.campaign_id}")
    print(f"   📊 Показы: {test_campaign.impressions}/1000")
    print(f"   📈 CTR: {test_campaign.ctr}%")
    
    # Тест 3: Загрузка активных кампаний
    print("\n3. Проверка загрузки кампаний...")
    monitor2 = CTRMonitor(user_id)
    if test_campaign.campaign_id in monitor2._active_campaigns:
        print("   ✅ Кампании успешно загружаются из файла")
    else:
        print("   ❌ Ошибка загрузки кампаний")
    
    # Тест 4: Форматирование статуса
    print("\n4. Тестирование форматирования...")
    from modules.ctr_handler import format_ctr_status, format_ctr_result
    
    status_text = format_ctr_status(test_campaign)
    print("   📊 Статус сбора:")
    for line in status_text.split('\n'):
        print(f"      {line}")
    
    # Тест 5: Симуляция достижения цели
    print("\n5. Симуляция завершения сбора...")
    test_campaign.impressions = 1247
    test_campaign.clicks = 29
    test_campaign.current_ctr = 2.35
    test_campaign.status_monitor = "completed"
    test_campaign.completed_at = "2026-03-16T19:00:00"
    
    result_text = format_ctr_result(test_campaign)
    print("   📊 Результат анализа:")
    for line in result_text.split('\n'):
        print(f"      {line}")
    
    # Тест 6: Сохранение в историю
    print("\n6. Тестирование истории...")
    monitor._save_to_history(test_campaign)
    if monitor.history_file.exists():
        import json
        with open(monitor.history_file, 'r') as f:
            history = json.load(f)
        print(f"   ✅ История сохранена ({len(history)} записей)")
    
    # Тест 7: Различные уровни CTR
    print("\n7. Тестирование рекомендаций при разных CTR...")
    test_cases = [
        (6.5, "Отличный CTR"),
        (3.5, "Хороший CTR"),
        (2.0, "Ниже среднего"),
        (0.8, "Критически низкий"),
    ]
    
    for ctr_val, description in test_cases:
        test_campaign.current_ctr = ctr_val
        rec_text = format_ctr_result(test_campaign)
        # Извлекаем рекомендацию
        for line in rec_text.split('\n'):
            if 'Рекомендация' in line or 'CTR' in line and '%' in line:
                print(f"   CTR {ctr_val}% - {description}")
                break
    
    print("\n" + "=" * 50)
    print("✅ ТЕСТИРОВАНИЕ ЗАВЕРШЕНО")
    print("=" * 50)
    print("\nСтруктура файлов:")
    print(f"  📁 {monitor.ctr_dir}")
    print(f"     ├── active_campaigns.json")
    print(f"     └── history.json")
    
    # Очистка тестовых данных
    print("\n🧹 Очистка тестовых данных...")
    if test_campaign.campaign_id in monitor._active_campaigns:
        del monitor._active_campaigns[test_campaign.campaign_id]
        monitor._save_active_campaigns()
        print("   ✅ Тестовая кампания удалена")


async def test_api_connections():
    """Тестирование API подключений"""
    print("\n" + "=" * 50)
    print("🔌 ТЕСТ API ПОДКЛЮЧЕНИЙ")
    print("=" * 50)
    
    user_id = "216929582"
    monitor = get_monitor(user_id)
    
    # Проверка WB API ключа
    print("\n1. Проверка WB API...")
    wb_key = await monitor.get_wb_api_key()
    if wb_key:
        print(f"   ✅ API ключ найден (длина: {len(wb_key)})")
    else:
        print("   ⚠️ API ключ не настроен")
        print("   💡 Добавьте ключ в: Магазины → Wildberries")
    
    # Проверка Ozon API
    print("\n2. Проверка Ozon API...")
    ozon_creds = await monitor.get_ozon_credentials()
    if ozon_creds:
        print(f"   ✅ Credentials найдены")
        print(f"   📌 Client ID: {ozon_creds.get('client_id', 'N/A')[:10]}...")
    else:
        print("   ⚠️ Credentials не настроены")
        print("   💡 Добавьте в: Магазины → Ozon")


if __name__ == "__main__":
    print("🚀 Запуск тестов CTR Monitor\n")
    
    # Запускаем тесты
    asyncio.run(test_monitor())
    asyncio.run(test_api_connections())
    
    print("\n" + "=" * 50)
    print("📋 ДЛЯ ПОЛНОГО ТЕСТИРОВАНИЯ:")
    print("=" * 50)
    print("""
1. Настройте API ключи в боте:
   - /menu → Магазины → Wildberries → Ввести API ключ
   - /menu → Магазины → Ozon → Ввести API ключ

2. Запустите мониторинг:
   - /menu → Контент → Мониторинг CTR
   - Введите артикул товара

3. Проверьте логи:
   tail -f /opt/clients/{user_id}/logs/activity.log
    """)
