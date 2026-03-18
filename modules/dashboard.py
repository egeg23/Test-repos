"""
DASHBOARD MODULE
Модуль для сбора и отображения данных о продажах с маркетплейсов
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional, Tuple

# Импорт API классов из INTEGRATION_LAYER
import sys
sys.path.insert(0, '/opt/telegram_bot')
from modules.INTEGRATION_LAYER import WildberriesAPI, OzonAPI, AvitoAPI

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BASE_DIR = Path("/opt/clients")
CACHE_TTL = 300  # 5 минут кэширования


class DashboardManager:
    """Менеджер дашборда продаж"""
    
    def __init__(self, user_id: str):
        self.user_id = str(user_id)
        self.user_dir = BASE_DIR / self.user_id
        self.cache_file = self.user_dir / "dashboard" / "cache.json"
        self.cache_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Загружаем кэш
        self.cache = self._load_cache()
        
        # Загружаем credentials для API
        self.wb_creds = self._load_credentials('wildberries')
        self.ozon_creds = self._load_credentials('ozon')
        self.avito_creds = self._load_credentials('avito')
    
    def _load_cache(self) -> Dict:
        """Загрузка кэша дашборда"""
        if self.cache_file.exists():
            try:
                with open(self.cache_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading cache: {e}")
        return {}
    
    def _save_cache(self, data: Dict):
        """Сохранение кэша дашборда"""
        try:
            cache_data = {
                'timestamp': datetime.now().isoformat(),
                'wb_data': data.get('wb', {}),
                'ozon_data': data.get('ozon', {}),
                'avito_data': data.get('avito', {})
            }
            with open(self.cache_file, 'w') as f:
                json.dump(cache_data, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving cache: {e}")
    
    def _load_credentials(self, platform: str) -> Dict:
        """Загрузка credentials для платформы"""
        # Проверяем новую структуру (credentials/)
        creds_file = self.user_dir / "credentials" / platform / "credentials.json"
        if creds_file.exists():
            try:
                with open(creds_file, 'r') as f:
                    creds = json.load(f)
                    if creds.get('verified', False):
                        return creds
            except Exception as e:
                logger.error(f"Error loading {platform} credentials: {e}")
        
        # Проверяем старую структуру (api_keys.json)
        api_keys_file = self.user_dir / "api_keys.json"
        if api_keys_file.exists():
            try:
                with open(api_keys_file, 'r') as f:
                    keys = json.load(f)
                    if platform in keys and keys[platform].get('active', False):
                        return keys[platform]
            except Exception as e:
                logger.error(f"Error loading api_keys: {e}")
        
        return {}
    
    def is_cache_valid(self) -> bool:
        """Проверка валидности кэша (5 минут)"""
        if not self.cache or 'timestamp' not in self.cache:
            return False
        
        try:
            cache_time = datetime.fromisoformat(self.cache['timestamp'])
            return (datetime.now() - cache_time).seconds < CACHE_TTL
        except:
            return False
    
    def check_agent_status(self) -> Tuple[str, str]:
        """Проверка статуса агента через heartbeat"""
        heartbeat_file = self.user_dir / "agents" / "heartbeat.json"
        
        if not heartbeat_file.exists():
            # Проверяем альтернативные пути
            heartbeat_file = self.user_dir / "autonomous" / "heartbeat.json"
        
        if heartbeat_file.exists():
            try:
                with open(heartbeat_file, 'r') as f:
                    heartbeat = json.load(f)
                
                last_update = heartbeat.get('last_update') or heartbeat.get('timestamp')
                if last_update:
                    last_time = datetime.fromisoformat(last_update.replace('Z', '+00:00').replace('+00:00', ''))
                    # Убираем timezone info для сравнения
                    last_time = last_time.replace(tzinfo=None)
                    now = datetime.now()
                    
                    diff_minutes = (now - last_time).total_seconds() / 60
                    
                    if diff_minutes < 15:
                        return "🟢", "Активен"
                    else:
                        return "🔴", f"Не активен ({int(diff_minutes)} мин)"
            except Exception as e:
                logger.error(f"Error checking heartbeat: {e}")
        
        return "⚪", "Нет данных"
    
    async def fetch_wb_sales(self) -> Dict:
        """Получение данных о продажах Wildberries"""
        if not self.wb_creds:
            return {'connected': False, 'error': 'Не подключен'}
        
        try:
            # Используем API WB для получения заказов
            token = self.wb_creds.get('stat_api_key') or self.wb_creds.get('token')
            if not token:
                return {'connected': True, 'error': 'Нет API ключа'}
            
            async with WildberriesAPI({'token': token}) as api:
                # Получаем заказы за последние 60 дней
                date_from = datetime.now() - timedelta(days=60)
                orders = await api.get_orders(date_from)
                
                # Рассчитываем статистику
                today = datetime.now().date()
                
                sales_today = []
                sales_yesterday = []
                sales_week = []
                sales_last_week = []
                sales_month = []
                sales_last_month = []
                
                for order in orders:
                    order_date_str = order.get('dateCreated') or order.get('createdAt', '')
                    if not order_date_str:
                        continue
                    
                    try:
                        order_date = datetime.fromisoformat(order_date_str.replace('Z', '+00:00').replace('+00:00', '')).date()
                    except:
                        continue
                    
                    # Считаем сумму заказа
                    price = float(order.get('totalPrice', 0) or order.get('price', 0) or 0)
                    
                    # Сегодня
                    if order_date == today:
                        sales_today.append(price)
                    # Вчера
                    elif order_date == today - timedelta(days=1):
                        sales_yesterday.append(price)
                    
                    # Текущая неделя (последние 7 дней)
                    if today - timedelta(days=7) <= order_date <= today:
                        sales_week.append(price)
                    # Прошлая неделя
                    elif today - timedelta(days=14) <= order_date < today - timedelta(days=7):
                        sales_last_week.append(price)
                    
                    # Текущий месяц (последние 30 дней)
                    if today - timedelta(days=30) <= order_date <= today:
                        sales_month.append(price)
                    # Прошлый месяц
                    elif today - timedelta(days=60) <= order_date < today - timedelta(days=30):
                        sales_last_month.append(price)
                
                today_sum = sum(sales_today)
                yesterday_sum = sum(sales_yesterday)
                week_sum = sum(sales_week)
                last_week_sum = sum(sales_last_week)
                month_sum = sum(sales_month)
                last_month_sum = sum(sales_last_month)
                
                return {
                    'connected': True,
                    'today': today_sum,
                    'yesterday': yesterday_sum,
                    'week': week_sum,
                    'last_week': last_week_sum,
                    'month': month_sum,
                    'last_month': last_month_sum,
                    'orders_count': len(orders)
                }
        
        except Exception as e:
            logger.error(f"WB sales fetch error: {e}")
            return {'connected': True, 'error': str(e)}
    
    async def fetch_ozon_sales(self) -> Dict:
        """Получение данных о продажах Ozon"""
        if not self.ozon_creds:
            return {'connected': False, 'error': 'Не подключен'}
        
        try:
            client_id = self.ozon_creds.get('client_id')
            api_key = self.ozon_creds.get('api_key')
            
            if not client_id or not api_key:
                return {'connected': True, 'error': 'Нет API ключей'}
            
            async with OzonAPI({'client_id': client_id, 'api_key': api_key}) as api:
                # Для Ozon используем аналитику для получения данных о продажах
                # Пока возвращаем заглушку с нулями (API Ozon требует отдельной реализации)
                # TODO: Реализовать получение реальных данных из Ozon
                
                return {
                    'connected': True,
                    'today': 0,
                    'yesterday': 0,
                    'week': 0,
                    'last_week': 0,
                    'month': 0,
                    'last_month': 0,
                    'orders_count': 0,
                    'note': 'API Ozon - требуется настройка'
                }
        
        except Exception as e:
            logger.error(f"Ozon sales fetch error: {e}")
            return {'connected': True, 'error': str(e)}
    
    async def fetch_avito_sales(self) -> Dict:
        """Получение данных о продажах Авито"""
        if not self.avito_creds:
            return {'connected': False, 'error': 'Не подключен'}
        
        # Для Авито используем сохраненные данные или возвращаем заглушку
        # TODO: Реализовать парсинг или API Авито
        
        return {
            'connected': True,
            'today': 0,
            'yesterday': 0,
            'week': 0,
            'last_week': 0,
            'month': 0,
            'last_month': 0,
            'orders_count': 0,
            'note': 'Авито - требуется настройка'
        }
    
    def calculate_change(self, current: float, previous: float) -> Tuple[float, str]:
        """Расчет изменения в процентах и эмодзи"""
        if previous == 0:
            if current == 0:
                return 0, "➖"
            return 100, "📈"
        
        change = ((current - previous) / previous) * 100
        emoji = "📈" if change > 0 else "📉" if change < 0 else "➖"
        return change, emoji
    
    def format_money(self, amount: float) -> str:
        """Форматирование суммы денег"""
        return f"{amount:,.0f}".replace(",", " ")
    
    async def get_dashboard_data(self, use_cache: bool = True) -> Dict:
        """Получение полных данных дашборда"""
        
        # Проверяем кэш
        if use_cache and self.is_cache_valid():
            logger.info(f"Using cache for user {self.user_id}")
            return {
                'wb': self.cache.get('wb_data', {}),
                'ozon': self.cache.get('ozon_data', {}),
                'avito': self.cache.get('avito_data', {}),
                'from_cache': True
            }
        
        # Получаем свежие данные
        logger.info(f"Fetching fresh data for user {self.user_id}")
        
        wb_data, ozon_data, avito_data = await asyncio.gather(
            self.fetch_wb_sales(),
            self.fetch_ozon_sales(),
            self.fetch_avito_sales()
        )
        
        data = {
            'wb': wb_data,
            'ozon': ozon_data,
            'avito': avito_data,
            'from_cache': False
        }
        
        # Сохраняем в кэш
        self._save_cache(data)
        
        return data
    
    def format_platform_line(self, name: str, icon: str, data: Dict) -> str:
        """Форматирование строки для одного маркетплейса"""
        if not data.get('connected', False):
            return f"{icon} {name}\n├─ Сегодня: ❌ Не подключен"
        
        if 'error' in data and data['error']:
            return f"{icon} {name}\n├─ Сегодня: ⚠️ Нет данных"
        
        today = data.get('today', 0)
        yesterday = data.get('yesterday', 0)
        week = data.get('week', 0)
        last_week = data.get('last_week', 0)
        month = data.get('month', 0)
        last_month = data.get('last_month', 0)
        
        day_change, day_emoji = self.calculate_change(today, yesterday)
        week_change, week_emoji = self.calculate_change(week, last_week)
        month_change, month_emoji = self.calculate_change(month, last_month)
        
        lines = [
            f"{icon} {name}",
            f"├─ Сегодня: {self.format_money(today)} ₽ ({day_change:+.0f}% {day_emoji})",
            f"├─ Неделя: {self.format_money(week)} ₽ ({week_change:+.0f}% {week_emoji})",
            f"└─ Месяц: {self.format_money(month)} ₽ ({month_change:+.0f}% {month_emoji})"
        ]
        
        return "\n".join(lines)
    
    async def generate_dashboard_text(self) -> str:
        """Генерация текста дашборда для Telegram"""
        
        # Проверяем статус агента
        agent_icon, agent_status = self.check_agent_status()
        
        # Получаем данные
        data = await self.get_dashboard_data()
        
        # Форматируем каждый маркетплейс
        wb_text = self.format_platform_line("Wildberries", "📦", data['wb'])
        ozon_text = self.format_platform_line("Ozon", "🛒", data['ozon'])
        avito_text = self.format_platform_line("Авито", "🏷️", data['avito'])
        
        # Считаем итоги
        wb_today = data['wb'].get('today', 0) if data['wb'].get('connected') else 0
        wb_week = data['wb'].get('week', 0) if data['wb'].get('connected') else 0
        wb_month = data['wb'].get('month', 0) if data['wb'].get('connected') else 0
        
        ozon_today = data['ozon'].get('today', 0) if data['ozon'].get('connected') else 0
        ozon_week = data['ozon'].get('week', 0) if data['ozon'].get('connected') else 0
        ozon_month = data['ozon'].get('month', 0) if data['ozon'].get('connected') else 0
        
        avito_today = data['avito'].get('today', 0) if data['avito'].get('connected') else 0
        avito_week = data['avito'].get('week', 0) if data['avito'].get('connected') else 0
        avito_month = data['avito'].get('month', 0) if data['avito'].get('connected') else 0
        
        total_today = wb_today + ozon_today + avito_today
        total_week = wb_week + ozon_week + avito_week
        total_month = wb_month + ozon_month + avito_month
        
        # Собираем полный текст
        lines = [
            "📊 <b>ДАШБОРД ПРОДАЖ</b>",
            "",
            f"{agent_icon} <b>Статус агента:</b> {agent_status}",
            "",
            wb_text,
            "",
            ozon_text,
            "",
            avito_text,
            "",
            "💰 <b>ИТОГО:</b>",
            f"Сегодня: {self.format_money(total_today)} ₽",
            f"Неделя: {self.format_money(total_week)} ₽",
            f"Месяц: {self.format_money(total_month)} ₽"
        ]
        
        if data.get('from_cache'):
            lines.append(f"\n<i>🕐 Данные из кэша (обновлены в {self.cache.get('timestamp', 'неизвестно')[:16]})</i>")
        
        return "\n".join(lines)


async def get_dashboard_for_user(user_id: str) -> str:
    """Публичная функция для получения дашборда пользователя"""
    manager = DashboardManager(user_id)
    return await manager.generate_dashboard_text()


# Тест
if __name__ == "__main__":
    async def test():
        # Тест с админом
        text = await get_dashboard_for_user("216929582")
        print(text)
    
    asyncio.run(test())
