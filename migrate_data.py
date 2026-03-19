#!/usr/bin/env python3
"""
Миграция данных из JSON файлов в PostgreSQL
Запускать ПЕРЕД переходом на новую архитектуру
"""

import json
import sys
from pathlib import Path
from datetime import datetime

# Добавляем путь к модулям
sys.path.insert(0, '/opt/telegram_bot')

from modules.database import (
    init_database, get_db, migrate_from_json,
    User, Cabinet, Product, FuckModeConfig
)


def migrate_users():
    """Миграция пользователей"""
    print("🔄 Миграция пользователей...")
    
    registry_path = Path('/opt/clients/USER_REGISTRY.json')
    if not registry_path.exists():
        print("❌ USER_REGISTRY.json не найден")
        return 0
    
    with open(registry_path) as f:
        registry = json.load(f)
    
    db = get_db()
    migrated = 0
    
    try:
        for user_id, user_data in registry.items():
            # Проверяем существование
            existing = db.query(User).filter(User.id == int(user_id)).first()
            if existing:
                print(f"  ⚠️ Пользователь {user_id} уже существует")
                continue
            
            # Создаем пользователя
            user = User(
                id=int(user_id),
                username=user_data.get('username'),
                first_name=user_data.get('first_name'),
                last_name=user_data.get('last_name'),
                phone=user_data.get('phone'),
                created_at=datetime.fromisoformat(
                    user_data.get('registered_at', datetime.utcnow().isoformat())
                )
            )
            db.add(user)
            migrated += 1
            print(f"  ✅ Пользователь {user_id} добавлен")
        
        db.commit()
        print(f"✅ Мигрировано {migrated} пользователей")
        return migrated
        
    except Exception as e:
        db.rollback()
        print(f"❌ Ошибка миграции пользователей: {e}")
        return 0
    finally:
        db.close()


def migrate_cabinets():
    """Миграция кабинетов"""
    print("\n🔄 Миграция кабинетов...")
    
    db = get_db()
    migrated = 0
    
    try:
        # Ищем все cabinet_*.json файлы
        clients_dir = Path('/opt/clients')
        for user_dir in clients_dir.iterdir():
            if not user_dir.is_dir() or user_dir.name.startswith('.'):
                continue
            
            user_id = user_dir.name
            
            # Ищем файлы кабинетов
            for cabinet_file in user_dir.glob('cabinet_*.json'):
                try:
                    with open(cabinet_file) as f:
                        cabinet_data = json.load(f)
                    
                    cabinet_id = cabinet_data.get('id') or cabinet_file.stem.replace('cabinet_', '')
                    
                    # Проверяем существование
                    existing = db.query(Cabinet).filter(Cabinet.id == cabinet_id).first()
                    if existing:
                        print(f"  ⚠️ Кабинет {cabinet_id} уже существует")
                        continue
                    
                    # Создаем кабинет
                    cabinet = Cabinet(
                        id=cabinet_id,
                        user_id=int(user_id) if user_id.isdigit() else 0,
                        name=cabinet_data.get('name', 'Unknown'),
                        platform=cabinet_data.get('platform', 'wb'),
                        is_active=cabinet_data.get('is_active', True),
                        api_key=cabinet_data.get('api_key'),
                        api_secret=cabinet_data.get('api_secret'),
                        settings=cabinet_data.get('settings', {}),
                        created_at=datetime.fromisoformat(
                            cabinet_data.get('created_at', datetime.utcnow().isoformat())
                        )
                    )
                    db.add(cabinet)
                    migrated += 1
                    print(f"  ✅ Кабинет {cabinet_id} добавлен")
                    
                except Exception as e:
                    print(f"  ❌ Ошибка миграции {cabinet_file}: {e}")
                    continue
        
        db.commit()
        print(f"✅ Мигрировано {migrated} кабинетов")
        return migrated
        
    except Exception as e:
        db.rollback()
        print(f"❌ Ошибка миграции кабинетов: {e}")
        return 0
    finally:
        db.close()


def migrate_fuck_mode_configs():
    """Миграция настроек Fuck Mode"""
    print("\n🔄 Миграция настроек Fuck Mode...")
    
    db = get_db()
    migrated = 0
    
    try:
        # Ищем все fuck_mode_config.json
        clients_dir = Path('/opt/clients')
        for config_file in clients_dir.rglob('fuck_mode_config.json'):
            try:
                with open(config_file) as f:
                    config_data = json.load(f)
                
                # Извлекаем user_id из пути
                user_id = config_file.parent.parent.name
                if not user_id.isdigit():
                    continue
                
                # Проверяем существование
                existing = db.query(FuckModeConfig).filter(
                    FuckModeConfig.user_id == int(user_id)
                ).first()
                if existing:
                    print(f"  ⚠️ Конфиг для {user_id} уже существует")
                    continue
                
                # Создаем конфиг
                config = FuckModeConfig(
                    user_id=int(user_id),
                    enabled=config_data.get('enabled', False),
                    dry_run=config_data.get('dry_run', True),
                    max_price_change_percent=config_data.get('max_price_change_percent', 20.0),
                    min_margin_percent=config_data.get('min_margin_percent', 15.0),
                    target_drr=config_data.get('target_drr', 15.0),
                    platforms=config_data.get('platforms', ['wb', 'ozon']),
                    enabled_notifications=config_data.get('enabled_notifications', True),
                    check_interval_minutes=config_data.get('check_interval_minutes', 30)
                )
                db.add(config)
                migrated += 1
                print(f"  ✅ Конфиг для {user_id} добавлен")
                
            except Exception as e:
                print(f"  ❌ Ошибка миграции {config_file}: {e}")
                continue
        
        db.commit()
        print(f"✅ Мигрировано {migrated} конфигов")
        return migrated
        
    except Exception as e:
        db.rollback()
        print(f"❌ Ошибка миграции конфигов: {e}")
        return 0
    finally:
        db.close()


def main():
    """Главная функция миграции"""
    print("=" * 60)
    print("🚀 МИГРАЦИЯ ДАННЫХ: JSON → PostgreSQL")
    print("=" * 60)
    
    # 1. Инициализация БД
    print("\n📦 Инициализация базы данных...")
    try:
        init_database()
        print("✅ База данных инициализирована")
    except Exception as e:
        print(f"❌ Ошибка инициализации БД: {e}")
        return 1
    
    # 2. Миграция пользователей
    users_count = migrate_users()
    
    # 3. Миграция кабинетов
    cabinets_count = migrate_cabinets()
    
    # 4. Миграция конфигов
    configs_count = migrate_fuck_mode_configs()
    
    # Итог
    print("\n" + "=" * 60)
    print("📊 РЕЗУЛЬТАТ МИГРАЦИИ:")
    print(f"  Пользователей: {users_count}")
    print(f"  Кабинетов: {cabinets_count}")
    print(f"  Конфигов Fuck Mode: {configs_count}")
    print("=" * 60)
    
    total = users_count + cabinets_count + configs_count
    if total > 0:
        print("\n✅ Миграция успешно завершена!")
        print("\nСледующий шаг: Запуск docker-compose up -d")
        return 0
    else:
        print("\n⚠️ Нечего мигрировать (возможно, уже выполнено)")
        return 0


if __name__ == '__main__':
    sys.exit(main())
