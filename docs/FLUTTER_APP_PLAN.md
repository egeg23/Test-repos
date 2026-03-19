# ПЛАН: Мобильное приложение Seller AI (Flutter)

**Платформы:** iOS + Android  
**Магазины:** App Store, Google Play  
**Технология:** Flutter + Dart  
**Бэкенд:** FastAPI (Python) + PostgreSQL  

---

## 📱 Структура приложения

```
lib/
├── main.dart                    # Точка входа
├── app.dart                     # Корневой виджет
├── config/
│   ├── theme.dart              # Темы (светлая/темная)
│   ├── constants.dart          # API endpoints, константы
│   └── routes.dart             # Навигация
├── models/
│   ├── user.dart               # Модель пользователя
│   ├── cabinet.dart            # Модель кабинета
│   ├── product.dart            # Модель товара
│   ├── analytics.dart          # Модель аналитики
│   └── alert.dart              # Модель уведомлений
├── services/
│   ├── api_service.dart        # HTTP клиент
│   ├── auth_service.dart       # Авторизация
│   ├── storage_service.dart    # Локальное хранилище
│   └── notification_service.dart # Push-уведомления
├── providers/
│   ├── auth_provider.dart      # Состояние авторизации
│   ├── cabinets_provider.dart  # Состояние кабинетов
│   ├── products_provider.dart  # Состояние товаров
│   └── analytics_provider.dart # Состояние аналитики
├── screens/
│   ├── auth/
│   │   ├── login_screen.dart
│   │   └── register_screen.dart
│   ├── dashboard/
│   │   └── dashboard_screen.dart
│   ├── cabinets/
│   │   ├── cabinets_list_screen.dart
│   │   ├── add_cabinet_screen.dart
│   │   └── cabinet_detail_screen.dart
│   ├── products/
│   │   ├── products_list_screen.dart
│   │   ├── product_detail_screen.dart
│   │   └── product_edit_screen.dart
│   ├── analytics/
│   │   ├── analytics_screen.dart
│   │   ├── competitors_screen.dart
│   │   └── charts_screen.dart
│   ├── pricing/
│   │   ├── pricing_screen.dart
│   │   └── pricing_rules_screen.dart
│   ├── autonomy/
│   │   ├── autonomy_screen.dart
│   │   └── fuck_mode_screen.dart
│   ├── settings/
│   │   └── settings_screen.dart
│   └── notifications/
│       └── notifications_screen.dart
├── widgets/
│   ├── common/
│   │   ├── app_bar.dart
│   │   ├── bottom_nav.dart
│   │   ├── loading_indicator.dart
│   │   └── error_widget.dart
│   ├── dashboard/
│   │   ├── stats_card.dart
│   │   ├── revenue_chart.dart
│   │   └── alerts_list.dart
│   ├── products/
│   │   ├── product_card.dart
│   │   ├── product_list_item.dart
│   │   └── price_badge.dart
│   └── analytics/
│       ├── line_chart.dart
│       ├── bar_chart.dart
│       └── competitor_row.dart
└── utils/
    ├── formatters.dart         # Форматирование чисел/дат
    ├── validators.dart         # Валидация форм
    └── helpers.dart            # Утилиты
```

---

## 🔗 API Endpoints (Backend)

### Авторизация
```
POST   /api/v1/auth/login          # Вход
POST   /api/v1/auth/register       # Регистрация
POST   /api/v1/auth/refresh        # Обновление токена
POST   /api/v1/auth/logout         # Выход
```

### Пользователь
```
GET    /api/v1/user/profile        # Профиль
PUT    /api/v1/user/profile        # Обновление профиля
```

### Кабинеты
```
GET    /api/v1/cabinets            # Список кабинетов
POST   /api/v1/cabinets            # Добавить кабинет
GET    /api/v1/cabinets/{id}       # Детали кабинета
PUT    /api/v1/cabinets/{id}       # Обновить кабинет
DELETE /api/v1/cabinets/{id}       # Удалить кабинет
```

### Товары
```
GET    /api/v1/products            # Список товаров
GET    /api/v1/products/{id}       # Детали товара
PUT    /api/v1/products/{id}/price # Изменить цену
GET    /api/v1/products/{id}/history # История цен
```

### Аналитика
```
GET    /api/v1/analytics/dashboard   # Дашборд
GET    /api/v1/analytics/revenue     # Выручка
GET    /api/v1/analytics/sales       # Продажи
GET    /api/v1/analytics/competitors/{product_id} # Конкуренты
```

### Mpstats
```
GET    /api/v1/mpstats/product/{id}  # Данные товара
GET    /api/v1/mpstats/category/{id} # Данные категории
GET    /api/v1/mpstats/competitors/{id} # Конкуренты
```

### Автономия (Fuck Mode)
```
GET    /api/v1/autonomy/status       # Статус
POST   /api/v1/autonomy/enable       # Включить
POST   /api/v1/autonomy/disable      # Выключить
POST   /api/v1/autonomy/pause        # Пауза
GET    /api/v1/autonomy/decisions    # История решений
GET    /api/v1/autonomy/report       # Отчет
```

### Push-уведомления
```
POST   /api/v1/notifications/token   # Регистрация токена
DELETE /api/v1/notifications/token   # Удаление токена
GET    /api/v1/notifications         # Список уведомлений
```

---

## 🎨 Дизайн и UI

### Основные экраны

#### 1. Дашборд (Главный)
```
┌─────────────────────────┐
│  💰 Доход: +15%         │
│  📦 Товаров: 156        │
│  🔔 Алертов: 3          │
├─────────────────────────┤
│  📈 График выручки      │
│     [линейный]          │
├─────────────────────────┤
│  ⚡ Быстрые действия    │
│  [Цены] [Реклама] [📊]  │
└─────────────────────────┘
```

#### 2. Товары
```
┌─────────────────────────┐
│  🔍 Поиск...            │
├─────────────────────────┤
│  📦 Товар 1        ₽999 │
│  В наличии: 45 шт.      │
│  ⭐ 4.8 | 💬 123        │
├─────────────────────────┤
│  📦 Товар 2       ₽1499 │
│  В наличии: 12 шт. ⚠️   │
│  ⭐ 4.5 | 💬 89         │
├─────────────────────────┤
│  ➕ Фильтры | Сортировка│
└─────────────────────────┘
```

#### 3. Fuck Mode (Автономия)
```
┌─────────────────────────┐
│  🤖 Fuck Mode           │
│  ━━━━━━━━━━━            │
│  🟢 АКТИВЕН            │
│                         │
│  Кабинетов: 3           │
│  Решений сегодня: 12    │
│                         │
│  [⏸️ ПАУЗА] [🛑 СТОП]  │
├─────────────────────────┤
│  Последние действия:    │
│  ✓ Цена #123: -5%       │
│  ✓ ДРР #456: оптимизирован
│  ✓ Поставка #789        │
└─────────────────────────┘
```

---

## 📊 Архитектура системы

```
┌─────────────────────────────────────────────────┐
│           МОБИЛЬНОЕ ПРИЛОЖЕНИЕ                 │
│              (Flutter)                         │
│  ┌─────────┐  ┌─────────┐  ┌─────────────┐    │
│  │   iOS   │  │ Android │  │    Web      │    │
│  └────┬────┘  └────┬────┘  └──────┬──────┘    │
└───────┼────────────┼──────────────┼───────────┘
        │            │              │
        └────────────┴──────────────┘
                     │ HTTPS
                     ▼
┌─────────────────────────────────────────────────┐
│              API GATEWAY                        │
│         (Nginx / CloudFlare)                    │
└─────────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────┐
│              BACKEND API                        │
│           (FastAPI + Python)                    │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────┐ │
│  │  Auth       │  │  Business   │  │  Mpstats│ │
│  │  Service    │  │  Logic      │  │  Parser │ │
│  └─────────────┘  └─────────────┘  └─────────┘ │
└─────────────────────────────────────────────────┘
        │                    │              │
        ▼                    ▼              ▼
┌──────────────┐   ┌────────────────┐  ┌──────────┐
│  PostgreSQL  │   │     Redis      │  │ Mpstats  │
│  (Database)  │   │   (Cache)      │  │ (Parser) │
└──────────────┘   └────────────────┘  └──────────┘
        │                    │              │
        ▼                    ▼              ▼
┌──────────────┐   ┌────────────────┐  ┌──────────┐
│  WB API      │   │   Ozon API     │  │ Telegram │
└──────────────┘   └────────────────┘  └──────────┘
```

---

## 🚀 План разработки

### Этап 1: Подготовка (Неделя 1)
- [ ] Настройка Flutter проекта
- [ ] Настройка backend (FastAPI)
- [ ] Создание базы данных
- [ ] Настройка CI/CD

### Этап 2: Авторизация (Неделя 2)
- [ ] Экраны login/register
- [ ] JWT токены
- [ ] Сохранение сессии
- [ ] Push-уведомления (FCM/APNs)

### Этап 3: Кабинеты (Неделя 3)
- [ ] Список кабинетов
- [ ] Добавление кабинета
- [ ] Удаление кабинета
- [ ] Backend API для кабинетов

### Этап 4: Товары (Неделя 4)
- [ ] Список товаров
- [ ] Детали товара
- [ ] Изменение цены
- [ ] Backend API для товаров

### Этап 5: Аналитика (Неделя 5)
- [ ] Дашборд
- [ ] Графики (flutter_chart)
- [ ] Конкуренты
- [ ] Backend API для аналитики

### Этап 6: Fuck Mode (Неделя 6)
- [ ] Экран автономии
- [ ] Включение/выключение
- [ ] История решений
- [ ] Backend интеграция

### Этап 7: Тестирование (Неделя 7)
- [ ] Unit тесты
- [ ] Интеграционные тесты
- [ ] Тестирование на устройствах

### Этап 8: Публикация (Неделя 8)
- [ ] App Store Review
- [ ] Google Play Review
- [ ] Релиз

**Итого: 8 недель (2 месяца)**

---

## 💰 Стоимость

### Разработка (если нанимать)
| Роль | Время | Ставка | Сумма |
|------|-------|--------|-------|
| Flutter разработчик | 8 недель | $50/час | $16,000 |
| Backend разработчик | 4 недели | $40/час | $6,400 |
| Дизайнер | 2 недели | $30/час | $2,400 |
| **Итого** | | | **$24,800** |

### Инфраструктура (ежемесячно)
| Сервис | Стоимость |
|--------|-----------|
| Сервер (VPS) | $50-100 |
| PostgreSQL | $15-30 |
| Redis | $10-20 |
| Push-уведомления | $10-50 |
| **Итого** | **$85-200/мес** |

### Магазины (разовые)
- Apple Developer: $99/год
- Google Play: $25 один раз

---

## ⚡ Альтернатива: React Native

| Критерий | Flutter | React Native |
|----------|---------|--------------|
| Производительность | ⭐⭐⭐ | ⭐⭐ |
| Сообщество | Растет | Больше |
| UI компоненты | Много | Очень много |
| Наши навыки | Python бэкенд | JS бэкенд |
| Сложность | Средняя | Средняя |

**Рекомендация:** Flutter - лучше для сложных UI и производительности.

---

## 🎯 Что делаем?

### Вариант A: Сначала Backend API (2 недели)
- Делаем полноценный REST API
- Потом мобильное приложение
- **Плюс:** Можно использовать и для веба

### Вариант B: Параллельно (2 месяца)
- Разработчик Flutter + Ты (backend)
- Одновременная работа
- **Плюс:** Быстрее, но дороже

### Вариант C: Сначала MVP WebApp (2 недели)
- PWA на Flutter Web
- Потом нативное приложение
- **Плюс:** Быстрый старт, потом масштабирование

---

**Какой вариант выбираем?**
