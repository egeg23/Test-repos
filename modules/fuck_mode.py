# modules/fuck_mode.py - Полная автономия управления
"""
Fuck Mode - полное автоматическое управление кабинетами
Бета-функция: требует предварительного тестирования

Возможности:
- Автоматическое принятие решений по ценам
- Управление рекламой (ДРР биддинг)
- Мониторинг остатков
- Автозаказ поставок

⚠️ DRY RUN режим: По умолчанию только показывает что бы сделал,
   не применяет изменения. Для включения реальных изменений
   установите dry_run=False в конфигурации.
"""

import json
import logging
import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
from enum import Enum

from .fuck_mode_config import fuck_mode_config
from .fuck_mode_pricing import fuck_mode_pricing, PricingDecision
from .operation_log import operation_log

logger = logging.getLogger('fuck_mode')


class FuckModeStatus(Enum):
    """Статусы Fuck Mode"""
    DISABLED = "disabled"
    ENABLED = "enabled"
    PAUSED = "paused"
    ERROR = "error"


class FuckModeEngine:
    """
    🤖 Fuck Mode Engine - Полная автономия
    
    Автоматически управляет всеми подключенными кабинетами:
    1. Ценообразование (каждые 10 мин)
    2. Реклама (каждые 30 мин)
    3. Остатки (каждый час)
    4. Отчеты (каждое утро)
    """
    
    def __init__(self, clients_dir: str = "/opt/clients"):
        self.clients_dir = Path(clients_dir)
        self.storage_dir = self.clients_dir / "GLOBAL_AI_LEARNING" / "fuck_mode"
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        self.status_file = self.storage_dir / "status.json"
        self.decisions_file = self.storage_dir / "decisions.log"
        self.errors_file = self.storage_dir / "errors.log"
        
        self.status = self._load_status()
    
    def _load_status(self) -> Dict:
        """Загружает статус Fuck Mode"""
        if self.status_file.exists():
            with open(self.status_file, 'r') as f:
                return json.load(f)
        return {
            'global_status': FuckModeStatus.DISABLED.value,
            'user_statuses': {},  # user_id -> status
            'last_run': None,
            'total_decisions': 0,
            'errors_count': 0
        }
    
    def _save_status(self):
        """Сохраняет статус"""
        with open(self.status_file, 'w') as f:
            json.dump(self.status, f, indent=2)
    
    def enable_for_user(self, user_id: str, platforms: List[str] = None) -> tuple[bool, str]:
        """
        Включает Fuck Mode для пользователя
        
        Args:
            platforms: ['wb'], ['ozon'], ['wb', 'ozon'], или None (все)
        """
        # Проверяем есть ли API ключи
        from modules.multi_cabinet_manager import cabinet_manager
        
        user_cabs = cabinet_manager.get_active_cabinets(user_id)
        
        if not user_cabs:
            return False, "❌ Нет подключенных кабинетов с API"
        
        # Фильтруем по платформам
        if platforms:
            user_cabs = [c for c in user_cabs if c.platform in platforms]
        
        if not user_cabs:
            return False, f"❌ Нет кабинетов для выбранных платформ"
        
        # Проверяем конфигурацию
        config = fuck_mode_config.get_config(user_id)
        dry_run_status = "🧪 ТЕСТОВЫЙ" if config.dry_run else "⚡ РЕАЛЬНЫЙ"
        
        # Активируем
        self.status['user_statuses'][user_id] = {
            'status': FuckModeStatus.ENABLED.value,
            'platforms': platforms or ['wb', 'ozon'],
            'enabled_at': datetime.now().isoformat(),
            'cabinets_count': len(user_cabs),
            'decisions_today': 0,
            'dry_run': config.dry_run
        }
        
        self._save_status()
        
        platform_text = ', '.join(platforms).upper() if platforms else 'ВСЕ'
        logger.info(f"🚀 Fuck Mode ENABLED for user {user_id} ({platform_text}) [{dry_run_status}]")
        
        result_msg = f"✅ Fuck Mode активирован\n"
        result_msg += f"📊 Кабинетов: {len(user_cabs)}\n"
        result_msg += f"🛒 Платформы: {platform_text}\n"
        result_msg += f"\n{dry_run_status} режим:\n"
        
        if config.dry_run:
            result_msg += "🧪 Бот показывает что БЫ сделал,\n"
            result_msg += "   но НЕ применяет изменения.\n"
            result_msg += "\n💡 Для реальных изменений:\n"
            result_msg += "   /fuck_config dry_run off"
        else:
            result_msg += "⚡ Бот реально меняет цены и рекламу!\n"
            result_msg += "\n⚠️ Будьте осторожны!"
        
        return True, result_msg
    
    def disable_for_user(self, user_id: str) -> tuple[bool, str]:
        """Отключает Fuck Mode"""
        if user_id not in self.status['user_statuses']:
            return False, "❌ Fuck Mode не был активен"
        
        self.status['user_statuses'][user_id]['status'] = FuckModeStatus.DISABLED.value
        self.status['user_statuses'][user_id]['disabled_at'] = datetime.now().isoformat()
        
        self._save_status()
        logger.info(f"⏹️ Fuck Mode DISABLED for user {user_id}")
        
        return True, "✅ Fuck Mode отключен"
    
    def pause_for_user(self, user_id: str) -> tuple[bool, str]:
        """Приостанавливает Fuck Mode"""
        if user_id not in self.status['user_statuses']:
            return False, "❌ Fuck Mode не активен"
        
        self.status['user_statuses'][user_id]['status'] = FuckModeStatus.PAUSED.value
        self.status['user_statuses'][user_id]['paused_at'] = datetime.now().isoformat()
        
        self._save_status()
        logger.info(f"⏸️ Fuck Mode PAUSED for user {user_id}")
        
        return True, "⏸️ Fuck Mode приостановлен"
    
    def get_user_status(self, user_id: str) -> Dict:
        """Возвращает статус для пользователя"""
        return self.status['user_statuses'].get(user_id, {
            'status': FuckModeStatus.DISABLED.value
        })
    
    def is_enabled_for_user(self, user_id: str) -> bool:
        """Проверяет активен ли Fuck Mode"""
        user_status = self.get_user_status(user_id)
        return user_status.get('status') == FuckModeStatus.ENABLED.value
    
    async def run_cycle_for_user(self, user_id: str):
        """
        Один цикл автономии для пользователя
        Вызывается из Orchestrator каждые 10 минут
        """
        if not self.is_enabled_for_user(user_id):
            return
        
        logger.info(f"🤖 Fuck Mode cycle for user {user_id}")
        
        try:
            # Получаем активные кабинеты
            from modules.multi_cabinet_manager import cabinet_manager
            
            user_status = self.get_user_status(user_id)
            platforms = user_status.get('platforms', ['wb', 'ozon'])
            
            for platform in platforms:
                cabinets = cabinet_manager.get_active_cabinets(user_id, platform)
                
                for cabinet in cabinets:
                    await self._process_cabinet(user_id, cabinet)
            
            # Обновляем статистику
            self.status['last_run'] = datetime.now().isoformat()
            self._save_status()
            
        except Exception as e:
            logger.error(f"❌ Fuck Mode error for {user_id}: {e}")
            self._log_error(user_id, str(e))
    
    async def _process_cabinet(self, user_id: str, cabinet):
        """Обрабатывает один кабинет"""
        logger.info(f"🔧 Processing cabinet: {cabinet.name} ({cabinet.platform})")
        
        # 1. Получаем товары через API
        products = await self._get_cabinet_products(user_id, cabinet)
        
        if not products:
            logger.warning(f"No products found for cabinet: {cabinet.name}")
            return
        
        logger.info(f"Found {len(products)} products in cabinet: {cabinet.name}")
        
        # 2. Для каждого товара принимаем решения
        for product in products[:10]:  # Ограничиваем 10 товарами за цикл
            try:
                await self._make_product_decisions(user_id, cabinet, product)
            except Exception as e:
                logger.error(f"Error processing product {product.get('id')}: {e}")
                continue
    
    async def _get_cabinet_products(self, user_id: str, cabinet) -> List[Dict]:
        """Получает список товаров кабинета через API (РЕАЛЬНЫЕ ВЫЗОВЫ)"""
        try:
            from .api_client_factory import api_client_factory
            
            if cabinet.platform == 'wb':
                client = api_client_factory.get_wb_client(user_id, cabinet.id)
                products = await client.get_products(limit=50)
                
                # Нормализуем формат
                return [
                    {
                        'id': str(p.get('nmId') or p.get('id')),
                        'name': p.get('name', 'Unknown'),
                        'price': float(p.get('price', 0)) / 100 if p.get('price', 0) > 1000 else float(p.get('price', 0)),
                        'cost_price': float(p.get('cost_price', 0)),
                        'stock': int(p.get('stock', 0)),
                        'rating': float(p.get('rating', 0)),
                        'reviews': int(p.get('reviews', 0)),
                        'category': p.get('category', 'unknown')
                    }
                    for p in products
                ]
            
            elif cabinet.platform == 'ozon':
                client = api_client_factory.get_ozon_client(user_id, cabinet.id)
                products = await client.get_products(limit=50)
                
                return [
                    {
                        'id': str(p.get('offer_id') or p.get('id')),
                        'name': p.get('name', 'Unknown'),
                        'price': float(p.get('price', 0)),
                        'cost_price': float(p.get('cost_price', 0)),
                        'stock': int(p.get('stock', 0)),
                        'rating': float(p.get('rating', 0)),
                        'reviews': int(p.get('reviews', 0)),
                        'category': p.get('category', 'unknown')
                    }
                    for p in products
                ]
            
            else:
                logger.error(f"Unknown platform: {cabinet.platform}")
                return []
                
        except Exception as e:
            logger.error(f"Failed to get products from API: {e}")
            return []
    
    async def _make_product_decisions(self, user_id: str, cabinet, product: Dict):
        """Принимает решения по товару с учетом dry run режима"""
        decisions = []
        config = fuck_mode_config.get_config(user_id)
        
        # 1. Анализ цены
        price_decision = await self._analyze_price(user_id, cabinet, product)
        if price_decision:
            price_decision['dry_run'] = config.dry_run
            decisions.append(price_decision)
            
            # Если не dry_run - применяем изменение
            if not config.dry_run:
                await self._apply_price_change(user_id, cabinet, product, price_decision)
        
        # 2. Анализ остатков
        stock_decision = await self._analyze_stock(cabinet, product)
        if stock_decision:
            stock_decision['dry_run'] = config.dry_run
            decisions.append(stock_decision)
        
        # 3. Анализ рекламы
        ads_decision = await self._analyze_ads(cabinet, product)
        if ads_decision:
            ads_decision['dry_run'] = config.dry_run
            decisions.append(ads_decision)
        
        # Логируем решения
        for decision in decisions:
            self._log_decision(user_id, cabinet.id, product['id'], decision)
        
        # Отправляем уведомление если есть решения
        if decisions and config.enabled_notifications:
            await self._notify_decisions(user_id, cabinet, product, decisions)
    
    async def _apply_price_change(self, user_id: str, cabinet, product: Dict, decision: Dict):
        """Применяет изменение цены через API (только если не dry_run)"""
        try:
            from .api_client_factory import api_client_factory
            
            new_price = decision.get('new_price')
            if not new_price:
                return
            
            if cabinet.platform == 'wb':
                client = api_client_factory.get_wb_client(user_id, cabinet.id)
                # Конвертируем в копейки для WB
                price_in_cents = int(new_price * 100)
                await client.update_price(product['id'], price_in_cents)
                logger.info(f"[REAL] WB price updated: {product['id']} -> {new_price}")
            
            elif cabinet.platform == 'ozon':
                client = api_client_factory.get_ozon_client(user_id, cabinet.id)
                await client.update_price(product['id'], new_price)
                logger.info(f"[REAL] Ozon price updated: {product['id']} -> {new_price}")
            
        except Exception as e:
            logger.error(f"Failed to apply price change: {e}")
            raise  # Перебрасываем для обработки выше
    
    async def _notify_decisions(self, user_id: str, cabinet, product: Dict, decisions: List[Dict]):
        """Отправляет уведомление о принятых решениях в Telegram"""
        from .notification_service import notification_service
        
        config = fuck_mode_config.get_config(user_id)
        
        if config.dry_run:
            mode_emoji = "🧪"
            mode_text = "[DRY RUN - Только показано]"
        else:
            mode_emoji = "⚡"
            mode_text = "[ПРИМЕНЕНО]"
        
        logger.info(f"{mode_emoji} Decisions for {product['name']}: {len(decisions)} {mode_text}")
        
        # Отправляем уведомление пользователю
        try:
            for decision in decisions:
                if decision.get('type') == 'price_change':
                    change_pct = decision.get('change_percent', 0)
                    direction = "📈 Повышена" if change_pct > 0 else "📉 Снижена"
                    
                    message = f"{mode_emoji} <b>Fuck Mode {mode_text}</b>\n\n"
                    message += f"🏪 {cabinet.name} ({cabinet.platform.upper()})\n"
                    message += f"📦 {product['name'][:50]}...\n\n"
                    message += f"{direction} цена:\n"
                    message += f"• Было: {decision['current_price']}₽\n"
                    message += f"• Стало: {decision['new_price']}₽\n"
                    message += f"• Изменение: {change_pct:+.1f}%\n\n"
                    message += f"🤖 Причина: {decision.get('reason', 'Не указана')}"
                    
                    await notification_service.send_notification(
                        user_id=int(user_id),
                        message=message
                    )
                    
        except Exception as e:
            logger.error(f"Failed to send notification: {e}")
    
    async def _analyze_price(self, user_id: str, cabinet, product: Dict) -> Optional[Dict]:
        """Анализирует цену и принимает решение используя Pricing Engine v2.0"""
        try:
            decision = await fuck_mode_pricing.analyze_product_price(
                user_id=user_id,
                cabinet=cabinet,
                product=product
            )
            
            if decision and decision.action in ['increase', 'decrease']:
                return {
                    'type': 'price_change',
                    'action': decision.action,
                    'current_price': decision.current_price,
                    'new_price': decision.recommended_price,
                    'change_percent': round(
                        (decision.recommended_price - decision.current_price) / decision.current_price * 100,
                        2
                    ),
                    'reason': decision.reason,
                    'confidence': decision.confidence,
                    'factors': decision.factors,
                    'product_name': product.get('name', 'Unknown')  # Для уведомлений
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Error in price analysis: {e}")
            return None
    
    async def _analyze_stock(self, cabinet, product: Dict) -> Optional[Dict]:
        """Анализирует остатки"""
        # TODO: Реальная логика запасов
        return None
    
    async def _analyze_ads(self, cabinet, product: Dict) -> Optional[Dict]:
        """Анализирует рекламу через WB Ads API"""
        try:
            from .wb_ads_client import WBAdsClient
            from .rate_limiter import rate_limiter
            
            # Проверяем rate limit
            if not rate_limiter.check_limit(cabinet.user_id, 'wb', 'ads'):
                logger.warning(f"Rate limit for ads API, skipping")
                return None
            
            # Получаем API ключ
            api_key = cabinet.api_key
            if not api_key:
                return None
            
            async with WBAdsClient(api_key) as client:
                if not client.is_valid:
                    return None
                
                # Ищем кампании для этого товара
                campaigns = await client.get_campaigns(status='9')  # Активные
                
                product_campaigns = []
                for campaign in campaigns:
                    # Проверяем, относится ли кампания к товару
                    if str(product.get('id')) in str(campaign.get('name', '')):
                        product_campaigns.append(campaign)
                
                if not product_campaigns:
                    return None
                
                decisions = []
                for campaign in product_campaigns[:3]:  # Максимум 3 кампании
                    campaign_id = campaign.get('id')
                    
                    # Получаем статистику
                    daily_stats = await client.get_daily_statistics(campaign_id, days=3)
                    
                    if not daily_stats:
                        continue
                    
                    total_spent = sum(day.get('spent', 0) for day in daily_stats)
                    total_orders = sum(day.get('orders', 0) for day in daily_stats)
                    
                    # Рассчитываем ДРР
                    avg_order_value = product.get('price', 0)
                    revenue = total_orders * avg_order_value
                    drr = client.calculate_drr(total_spent, revenue)
                    
                    # Принимаем решение
                    if drr > 25:  # ДРР слишком высокий
                        decisions.append({
                            'type': 'ad_alert',
                            'campaign_id': campaign_id,
                            'campaign_name': campaign.get('name', 'Unknown'),
                            'drr': drr,
                            'spent': total_spent,
                            'orders': total_orders,
                            'action': 'review',
                            'reason': f'Высокий ДРР: {drr:.1f}% (рекомендуется проверить)'
                        })
                
                return decisions[0] if decisions else None
                
        except Exception as e:
            logger.error(f"Error analyzing ads: {e}")
            return None
    
    def _log_decision(self, user_id: str, cabinet_id: str, product_id: str, decision: Dict):
        """Логирует решение в файл и operation_log"""
        
        # Лог в JSONL файл (для совместимости)
        entry = {
            'timestamp': datetime.now().isoformat(),
            'user_id': user_id,
            'cabinet_id': cabinet_id,
            'product_id': product_id,
            'decision': decision
        }
        
        with open(self.decisions_file, 'a') as f:
            f.write(json.dumps(entry) + '\n')
        
        self.status['total_decisions'] += 1
        self._save_status()
        
        # Лог в OperationLog (для отката и статистики)
        if decision.get('type') == 'price_change':
            from .multi_cabinet_manager import cabinet_manager
            
            cabinet = cabinet_manager.get_cabinet(user_id, cabinet_id)
            if cabinet:
                operation_log.log_operation(
                    user_id=user_id,
                    cabinet_id=cabinet_id,
                    cabinet_name=cabinet.name,
                    product_id=product_id,
                    product_name=decision.get('product_name', 'Unknown'),
                    operation_type='price_change',
                    old_value=decision.get('current_price'),
                    new_value=decision.get('new_price'),
                    reason=decision.get('reason', ''),
                    dry_run=decision.get('dry_run', True),
                    success=True
                )
    
    def _log_error(self, user_id: str, error: str):
        """Логирует ошибку"""
        entry = {
            'timestamp': datetime.now().isoformat(),
            'user_id': user_id,
            'error': error
        }
        
        with open(self.errors_file, 'a') as f:
            f.write(json.dumps(entry) + '\n')
        
        self.status['errors_count'] += 1
        self._save_status()
    
    def get_daily_report(self, user_id: str) -> str:
        """Генерирует ежедневный отчет"""
        user_status = self.get_user_status(user_id)
        
        if user_status.get('status') == FuckModeStatus.DISABLED.value:
            return "🔴 Fuck Mode отключен"
        
        text = "🤖 <b>Fuck Mode Report</b>\n\n"
        text += f"Статус: {'🟢 Активен' if self.is_enabled_for_user(user_id) else '⏸️ На паузе'}\n"
        text += f"Кабинетов: {user_status.get('cabinets_count', 0)}\n"
        text += f"Платформы: {', '.join(user_status.get('platforms', [])).upper()}\n"
        text += f"Решений сегодня: {user_status.get('decisions_today', 0)}\n\n"
        
        text += "📊 Принятые решения:\n"
        text += "• Цены: автокорректировка\n"
        text += "• Реклама: оптимизация ДРР\n"
        text += "• Остатки: мониторинг\n"
        
        return text


# Глобальный экземпляр
fuck_mode_engine = FuckModeEngine()
