# MPSTATS_KNOWLEDGE_BASE.md - База знаний Mpstats
"""
Структура, URL и логика работы Mpstats
Для использования в парсерах и автоматизации
"""

## 🔗 Базовые URL

```python
MPSTATS_URLS = {
    'base': 'https://mpstats.io',
    'login': 'https://mpstats.io/auth/login',
    'dashboard': 'https://mpstats.io/dashboard',
    
    # Товар
    'product_wb': 'https://mpstats.io/wb/item/{nmId}',
    'product_ozon': 'https://mpstats.io/ozon/item/{offer_id}',
    
    # Категория
    'category_wb': 'https://mpstats.io/wb/category/{category_id}',
    'category_ozon': 'https://mpstats.io/ozon/category/{category_id}',
    
    # Поиск
    'search': 'https://mpstats.io/search?q={query}',
    
    # Аналитика
    'analytics_wb': 'https://mpstats.io/wb/analytics',
    'analytics_ozon': 'https://mpstats.io/ozon/analytics',
}
```

## 📦 Структура карточки товара

### URL шаблон
- WB: `/wb/item/{nmId}`
- Ozon: `/ozon/item/{offer_id}`

### Данные на странице

#### 1. Основной блок (верх страницы)
```
Название товара
├── h1.product-title или .item-name
└── Текст: Полное название товара

Цена
├── .price-current или [data-testid="price"]
└── Формат: "1 299 ₽" → float(1299)

Рейтинг
├── .rating-stars, .rating-value
└── Формат: "4.8" → float(4.8)

Количество отзывов
├── .reviews-count
└── Формат: "1 234 отзыва" → int(1234)
```

#### 2. Блок продаж (левая колонка)
```
Продажи за 30 дней
├── .sales-count или [data-metric="sales"]
└── Число проданных штук

Выручка за 30 дней
├── .revenue-value или [data-metric="revenue"]
└── Формат: "1.2 млн ₽"

Остатки
├── .stock-count или [data-metric="stock"]
└── Текущий остаток на складах
```

#### 3. Блок конкурентов (правая колонка или таблица)
```
Таблица конкурентов
├── .competitors-table или [data-section="competitors"]
└── Строки:
    ├── Продавец (seller name)
    ├── Цена (price)
    ├── Рейтинг (rating)
    └── Позиция в поиске (position)
```

#### 4. Графики (обычно внизу)
```
График цен
├── .price-chart или [data-chart="price"]
└── Canvas/SVG элемент

График продаж
├── .sales-chart или [data-chart="sales"]
└── Canvas/SVG элемент
```

## 📁 Структура категории

### URL
- WB: `/wb/category/{category_id}?is_price=false`
- Ozon: `/ozon/category/{category_id}`

### Данные

#### 1. Фильтры (верх страницы)
```
Диапазон цен
├── input[name="price_min"]
└── input[name="price_max"]

Рейтинг
├── input[name="rating_min"]
└── Значение: 4.0, 4.5 и т.д.

Наличие
├── checkbox[name="in_stock"]
└── true/false
```

#### 2. Таблица товаров
```
Таблица
├── .category-table или [data-table="products"]
└── Строки:
    ├── Фото (thumbnail)
    ├── nmId/OfferId
    ├── Название
    ├── Цена
    ├── Рейтинг
    ├── Отзывы
    ├── Продажи (30d)
    ├── Выручка (30d)
    ├── Продавец
    └── Динамика (стрелка вверх/вниз)
```

## 🎯 Селекторы для парсинга

### CSS селекторы (приоритет по точности)

#### Название товара
```css
/* Первый вариант - самый надежный */
h1.product-title
.item-header h1
[data-testid="product-name"]
.content h1:first-child
```

#### Цена
```css
.price-current .value
[data-testid="price"] .amount
.product-price-main
span:has-text("₽"):first-of-type
```

#### Рейтинг
```css
.rating-value
.stars-container [aria-label*="звезд"]
[data-testid="rating"]
```

#### Продажи
```css
[data-metric="sales"] .value
.sales-30d .number
.metric-sales strong
```

#### Выручка
```css
[data-metric="revenue"] .value
.revenue-30d .number
.metric-revenue strong
```

## 📊 JSON данные в странице

Mpstats часто хранит данные в `<script>` тегах:

### window.__INITIAL_STATE__
```javascript
// Ищем этот объект в скриптах
window.__INITIAL_STATE__ = {
    product: {
        nmId: 12345678,
        name: "Название товара",
        price: 1299,
        rating: 4.8,
        reviewsCount: 1234,
        sales: {
            '30d': 567,
            revenue: 736533
        },
        stock: 890
    },
    competitors: [...],
    charts: {...}
}
```

### window.__DATA__
```javascript
// Альтернативное расположение
window.__DATA__ = {
    item: {...},
    category: {...}
}
```

## 🔐 Авторизация

### Форма логина
```
URL: /auth/login
Method: POST
Fields:
    - email: строка
    - password: строка
    - _token: CSRF токен (из meta или form)
```

### Проверка авторизации
```
После логина редирект на /dashboard
Если не авторизован - редирект обратно на /auth/login
```

### Cookies
```
mpstats_session - основная сессия
mpstats_token - JWT токен
XSRF-TOKEN - CSRF защита
```

## 📈 API endpoints (неофициальные)

### Получение данных товара (JSON)
```
GET /api/wb/item/{nmId}/summary
Headers:
    Accept: application/json
    Authorization: Bearer {token}

Response:
{
    "nmId": 12345678,
    "name": "...",
    "price": 1299,
    "rating": 4.8,
    "reviews": 1234,
    "sales30": 567,
    "revenue30": 736533
}
```

### Получение конкурентов
```
GET /api/wb/item/{nmId}/competitors
Response:
{
    "competitors": [
        {
            "nmId": 87654321,
            "seller": "Название продавца",
            "price": 1199,
            "rating": 4.7,
            "position": 3
        }
    ]
}
```

## 🎨 Типы графиков

### 1. График цен (Price History)
- URL: содержит `/charts/price`
- Тип: Line chart
- Данные: массив [timestamp, price]

### 2. График продаж (Sales)
- URL: содержит `/charts/sales`
- Тип: Bar chart
- Данные: массив [date, quantity]

### 3. График выручки (Revenue)
- URL: содержит `/charts/revenue`
- Тип: Line chart
- Данные: массив [date, revenue]

### 4. График остатков (Stock)
- URL: содержит `/charts/stock`
- Тип: Area chart
- Данные: массив [date, stock_level]

## 🚨 Анти-бот защита

### Что использует Mpstats:
1. **Cloudflare** - проверка браузера
   - Решение: Playwright с реальным User-Agent

2. **Rate limiting** - ограничение запросов
   - Лимит: ~60 запросов/минуту
   - Решение: Задержки между запросами (1-2 сек)

3. **Fingerprinting** - проверка уникальности браузера
   - Решение: Сохранение сессий, куки

4. **CAPTCHA** - редко, при подозрительной активности
   - Решение: Ручное прохождение или сервисы типа 2captcha

## 💡 Best Practices

### Для парсинга:
1. Использовать headless браузер (Playwright/Selenium)
2. Сохранять сессии между запросами
3. Делать паузы 1-3 секунды между действиями
4. Использовать мобильный User-Agent иногда
5. Проверять наличие элемента перед кликом

### Для авторизации:
1. Сохранять cookies после логина
2. Проверять валидность сессии перед запросами
3. Авто-перелогин при 401/403
4. Использовать один аккаунт для всей системы

## 📋 Чеклист интеграции

- [x] Авторизация через браузер
- [x] Сохранение сессии
- [x] Парсинг карточки товара
- [x] Парсинг категории ✅
- [x] Парсинг графиков ✅
- [x] Получение списка конкурентов ✅
- [x] Автоматический мониторинг цен ✅
- [ ] Экспорт данных в Excel/CSV

---

*Создано: 2026-03-19*
*Обновляется по мере изучения функционала*
