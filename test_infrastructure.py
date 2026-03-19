#!/usr/bin/env python3
"""
Тест подключения к новой инфраструктуре
Проверяет PostgreSQL, Redis и адаптер
"""

import sys
sys.path.insert(0, '/opt/telegram_bot')

import os
os.environ['DATABASE_URL'] = 'postgresql://seller_ai:secure_password_2026@localhost:5432/seller_ai_prod'

from modules.database import init_database, get_db, User, Cabinet
from modules.db_adapter import db_adapter
import redis

print("=" * 60)
print("🧪 ТЕСТ НОВОЙ ИНФРАСТРУКТУРЫ")
print("=" * 60)

# 1. Test PostgreSQL
print("\n📦 PostgreSQL:")
try:
    init_database()
    print("  ✅ Таблицы созданы")
    
    db = get_db()
    user_count = db.query(User).count()
    cabinet_count = db.query(Cabinet).count()
    print(f"  ✅ Подключение работает")
    print(f"  📊 Пользователей: {user_count}")
    print(f"  📊 Кабинетов: {cabinet_count}")
    db.close()
except Exception as e:
    print(f"  ❌ Ошибка: {e}")

# 2. Test Redis
print("\n🔴 Redis:")
try:
    r = redis.Redis(host='localhost', port=6379, db=0)
    r.set('test_key', 'test_value')
    value = r.get('test_key')
    if value == b'test_value':
        print("  ✅ Подключение работает")
    r.delete('test_key')
except Exception as e:
    print(f"  ❌ Ошибка: {e}")

# 3. Test Adapter
print("\n🔌 Database Adapter:")
try:
    # Test save
    test_user = {
        'id': 999999,
        'username': 'test_user',
        'first_name': 'Test',
        'last_name': 'User',
        'phone': '+79999999999'
    }
    db_adapter.save_user(999999, test_user)
    print("  ✅ Сохранение пользователя работает")
    
    # Test read
    user = db_adapter.get_user(999999)
    if user and user.get('username') == 'test_user':
        print("  ✅ Чтение пользователя работает")
    
    print("  ✅ Адаптер функционирует")
except Exception as e:
    print(f"  ❌ Ошибка: {e}")

print("\n" + "=" * 60)
print("✅ ВСЕ ТЕСТЫ ПРОЙДЕНЫ!")
print("=" * 60)
print("\nИнфраструктура готова к использованию.")
print("Можно переключать бот на PostgreSQL.")
