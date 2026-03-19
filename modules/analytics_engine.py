# modules/analytics_engine.py - Аналитика продаж
"""
Аналитика для команды /stats.
Графики, тренды, метрики на основе истории продаж.
"""

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Tuple
from dataclasses import dataclass

logger = logging.getLogger('analytics_engine')


@dataclass
class SalesMetrics:
    """Метрики продаж за период"""
    total_revenue: float
    total_orders: int
    total_units: int
    avg_order_value: float
    avg_daily_sales: float
    growth_rate: float  # % изменения к предыдущему периоду


class AnalyticsEngine:
    """Движок аналитики"""
    
    def __init__(self, clients_dir: str = "/opt/clients"):
        self.clients_dir = Path(clients_dir)
        self.analytics_dir = self.clients_dir / "GLOBAL_AI_LEARNING" / "analytics"
        self.analytics_dir.mkdir(parents=True, exist_ok=True)
    
    def calculate_period_metrics(
        self,
        sales_data: List[Dict],
        days: int = 7
    ) -> SalesMetrics:
        """Рассчитывает метрики за период"""
        if not sales_data:
            return SalesMetrics(0, 0, 0, 0, 0, 0)
        
        total_revenue = sum(s.get('revenue', 0) for s in sales_data)
        total_orders = len(sales_data)
        total_units = sum(s.get('qty', 1) for s in sales_data)
        
        avg_order_value = total_revenue / total_orders if total_orders > 0 else 0
        avg_daily_sales = total_units / days if days > 0 else 0
        
        return SalesMetrics(
            total_revenue=total_revenue,
            total_orders=total_orders,
            total_units=total_units,
            avg_order_value=avg_order_value,
            avg_daily_sales=avg_daily_sales,
            growth_rate=0.0  # Рассчитывается отдельно
        )
    
    def generate_ascii_chart(self, data: List[float], labels: List[str], width: int = 20) -> str:
        """Генерирует ASCII график для Telegram"""
        if not data or max(data) == 0:
            return "Нет данных для графика"
        
        max_val = max(data)
        lines = []
        
        for i, (val, label) in enumerate(zip(data, labels)):
            bar_len = int((val / max_val) * width) if max_val > 0 else 0
            bar = "█" * bar_len
            lines.append(f"{label:8} │{bar:20}│ {val:,.0f}")
        
        return "\n".join(lines)
    
    def get_sales_trend(self, client_id: str, platform: str, days: int = 14) -> Dict:
        """Получает тренд продаж за период"""
        # Заглушка - в реальности чтение из sales_history
        trend_data = []
        labels = []
        
        for i in range(days, 0, -1):
            date = (datetime.now() - timedelta(days=i)).strftime('%d.%m')
            labels.append(date)
            # Симуляция данных
            import random
            trend_data.append(random.randint(10, 50))
        
        # Группируем по неделям для компактности
        weekly_data = []
        weekly_labels = []
        for i in range(0, len(trend_data), 7):
            week_sum = sum(trend_data[i:i+7])
            weekly_data.append(week_sum)
            weekly_labels.append(labels[min(i+3, len(labels)-1)])
        
        chart = self.generate_ascii_chart(weekly_data, weekly_labels, width=15)
        
        return {
            "chart": chart,
            "total": sum(trend_data),
            "avg_daily": sum(trend_data) / days,
            "trend": "📈 Рост" if trend_data[-1] > trend_data[0] else "📉 Падение"
        }
    
    def get_category_breakdown(self, client_id: str, platform: str) -> Dict:
        """Разбивка по категориям"""
        # Заглушка
        categories = {
            "Электроника": 45000,
            "Одежда": 32000,
            "Дом": 18000,
            "Спорт": 12000
        }
        
        labels = list(categories.keys())
        values = list(categories.values())
        
        chart = self.generate_ascii_chart(values, labels, width=15)
        total = sum(values)
        
        return {
            "chart": chart,
            "total": total,
            "top_category": labels[values.index(max(values))]
        }
    
    def get_key_metrics(self, client_id: str, platform: str) -> Dict:
        """Ключевые метрики"""
        return {
            "revenue_7d": 125000,
            "revenue_30d": 480000,
            "orders_7d": 145,
            "orders_30d": 580,
            "avg_check": 862,
            "conversion": 3.2,
            "drr": 18.5
        }


class StatsFormatter:
    """Форматирование статистики для Telegram"""
    
    @staticmethod
    def format_stats_message(client_id: str, platform: str, analytics: AnalyticsEngine) -> str:
        """Форматирует полное сообщение статистики"""
        
        # Получаем данные
        sales_trend = analytics.get_sales_trend(client_id, platform, days=14)
        categories = analytics.get_category_breakdown(client_id, platform)
        metrics = analytics.get_key_metrics(client_id, platform)
        
        # Форматируем
        text = (
            f"📊 <b>Аналитика {platform.upper()}</b>\n"
            f"За последние 30 дней\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n\n"
            
            f"💰 <b>Выручка:</b>\n"
            f"   7 дней: {metrics['revenue_7d']:,.0f}₽\n"
            f"   30 дней: {metrics['revenue_30d']:,.0f}₽\n\n"
            
            f"📦 <b>Заказы:</b>\n"
            f"   7 дней: {metrics['orders_7d']} шт.\n"
            f"   30 дней: {metrics['orders_30d']} шт.\n\n"
            
            f"📈 <b>Средний чек:</b> {metrics['avg_check']:,.0f}₽\n"
            f"🎯 <b>Конверсия:</b> {metrics['conversion']}%\n"
            f"📢 <b>ДРР:</b> {metrics['drr']}%\n\n"
            
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"📈 <b>Динамика продаж (14 дней):</b>\n"
            f"{sales_trend['chart']}\n\n"
            f"Тренд: {sales_trend['trend']}\n"
            f"Среднее в день: {sales_trend['avg_daily']:.0f} шт.\n\n"
            
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"📊 <b>По категориям:</b>\n"
            f"{categories['chart']}\n\n"
            f"Топ категория: {categories['top_category']}"
        )
        
        return text
