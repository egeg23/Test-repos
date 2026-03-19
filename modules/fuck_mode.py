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

            # Применяем изменения если не dry_run
            if not config.dry_run:
                try:
                    await self._apply_ads_change(cabinet, ads_decision)
                except Exception as e:
                    logger.error(f"Failed to apply ads change: {e}")

        # Логируем решения
        for decision in decisions:
            self._log_decision(user_id, cabinet.id, product['id'], decision)

        # Отправляем уведомление если есть решения
        try:
            for decision in decisions:
                if decision.get('type') == 'price_change':
                    await self._notify_price_change(user_id, cabinet, product, decision, config)
                elif decision.get('type') == 'ads_optimization':
                    await self._notify_ads_change(user_id, cabinet, product, decision, config)
        except Exception as e:
            logger.error(f"Failed to send notification: {e}")

    async def _notify_price_change(self, user_id: str, cabinet, product: Dict, decision: Dict, config):
        """Отправляет уведомление об изменении цены"""
        from .notification_service import notification_service

        mode_emoji = "🧪" if config.dry_run else "⚡"
        mode_text = "[DRY RUN]" if config.dry_run else "[ПРИМЕНЕНО]"

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

    async def _notify_ads_change(self, user_id: str, cabinet, product: Dict, decision: Dict, config):
        """Отправляет уведомление об изменении рекламы"""
        from .notification_service import notification_service

        mode_emoji = "🧪" if config.dry_run else "⚡"
        mode_text = "[DRY RUN]" if config.dry_run else "[ПРИМЕНЕНО]"

        action = decision.get('action', '')
        action_text = {
            'pause': '⏸ Кампания на паузе',
            'decrease_bid': '💰 Снижена ставка',
            'increase_bid': '💰 Повышена ставка',
            'decrease_budget': '💰 Снижен бюджет',
            'increase_budget': '💰 Повышен бюджет',
        }.get(action, f'🔄 {action}')

        message = f"{mode_emoji} <b>Fuck Mode Ads {mode_text}</b>\n\n"
        message += f"🏪 {cabinet.name} ({cabinet.platform.upper()})\n"
        message += f"📦 {product['name'][:50]}...\n"
        message += f"📢 {decision.get('campaign_name', 'Unknown')[:30]}...\n\n"
        message += f"{action_text}\n"

        if decision.get('new_bid'):
            message += f"• Ставка: {decision['current_bid']:.0f}₽ → {decision['new_bid']:.0f}₽\n"
        if decision.get('new_budget'):
            message += f"• Бюджет: {decision['current_budget']:.0f}₽ → {decision['new_budget']:.0f}₽\n"

        message += f"• ДРР: {decision.get('drr', 0):.1f}%\n"
        message += f"• Расход: {decision.get('spent', 0):.0f}₽\n\n"
        message += f"🤖 Причина: {decision.get('reason', 'Не указана')}"

        await notification_service.send_notification(
            user_id=int(user_id),
            message=message
        )

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
        """Анализирует рекламу через API с автоматической оптимизацией"""
        try:
            if cabinet.platform == 'wb':
                return await self._analyze_wb_ads(cabinet, product)
            elif cabinet.platform == 'ozon':
                return await self._analyze_ozon_ads(cabinet, product)
            return None
        except Exception as e:
            logger.error(f"Error analyzing ads: {e}")
            return None

    async def _analyze_wb_ads(self, cabinet, product: Dict) -> Optional[Dict]:
        """Анализ WB рекламы"""
        from .wb_ads_client import WBAdsClient
        from .rate_limiter import rate_limiter

        if not rate_limiter.check_limit(cabinet.user_id, 'wb', 'ads'):
            return None

        async with WBAdsClient(cabinet.api_key) as client:
            if not client.is_valid:
                return None

            campaigns = await client.get_campaigns(status='9')  # Активные
            product_campaigns = [
                c for c in campaigns
                if str(product.get('id')) in str(c.get('name', ''))
            ]

            if not product_campaigns:
                return None

            # Анализируем первую кампанию
            campaign = product_campaigns[0]
            campaign_id = campaign.get('id')

            # Получаем статистику за 7 дней
            stats = await client.get_daily_statistics(campaign_id, days=7)
            if not stats:
                return None

            total_spent = sum(day.get('spent', 0) for day in stats)
            total_orders = sum(day.get('orders', 0) for day in stats)
            total_views = sum(day.get('views', 0) for day in stats)
            total_clicks = sum(day.get('clicks', 0) for day in stats)

            avg_price = product.get('price', 0)
            revenue = total_orders * avg_price
            drr = client.calculate_drr(total_spent, revenue)
            ctr = (total_clicks / total_views * 100) if total_views > 0 else 0

            current_bid = campaign.get('cpm', 0) / 100

            # Принимаем решение
            target_drr = 15.0
            action = None
            new_bid = None

            if drr > 30:  # Критический ДРР
                action = 'pause'
            elif drr > target_drr * 1.2:
                action = 'decrease_bid'
                new_bid = await client.calculate_optimal_bid(drr, target_drr, current_bid, total_orders)
            elif drr < target_drr * 0.8 and ctr > 2.0:
                action = 'increase_bid'
                new_bid = await client.calculate_optimal_bid(drr, target_drr, current_bid, total_orders)

            if action:
                return {
                    'type': 'ads_optimization',
                    'platform': 'wb',
                    'campaign_id': campaign_id,
                    'campaign_name': campaign.get('name', 'Unknown'),
                    'action': action,
                    'current_bid': current_bid,
                    'new_bid': new_bid,
                    'drr': drr,
                    'ctr': ctr,
                    'spent': total_spent,
                    'orders': total_orders,
                    'reason': f'ДРР {drr:.1f}% (CTR {ctr:.2f}%)'
                }
            return None

    async def _analyze_ozon_ads(self, cabinet, product: Dict) -> Optional[Dict]:
        """Анализ Ozon рекламы"""
        from .ozon_ads_client import OzonAdsClient
        from .rate_limiter import rate_limiter

        if not rate_limiter.check_limit(cabinet.user_id, 'ozon', 'ads'):
            return None

        client_id = getattr(cabinet, 'client_id', '')
        if not client_id:
            return None

        async with OzonAdsClient(cabinet.api_key, client_id) as client:
            if not client.is_valid:
                return None

            campaigns = await client.get_campaigns(state='CAMPAIGN_STATE_RUNNING')

            # Ищем кампании по названию товара
            product_campaigns = [
                c for c in campaigns
                if str(product.get('id')) in str(c.get('title', ''))
            ]

            if not product_campaigns:
                return None

            campaign = product_campaigns[0]
            campaign_id = campaign.get('id')

            stats = await client.get_daily_statistics(campaign_id, days=7)
            if not stats:
                return None

            total_spent = sum(s.get('spent', 0) for s in stats)
            total_orders = sum(s.get('orders', 0) for s in stats)
            avg_price = product.get('price', 0)
            revenue = total_orders * avg_price
            drr = client.calculate_drr(total_spent, revenue)

            current_budget = float(campaign.get('daily_budget', 0))
            target_drr = 15.0
            action = None
            new_budget = None

            if drr > 30:
                action = 'pause'
            elif drr > target_drr * 1.2:
                action = 'decrease_budget'
                new_budget = await client.calculate_optimal_budget(drr, target_drr, current_budget, total_orders)
            elif drr < target_drr * 0.8:
                action = 'increase_budget'
                new_budget = await client.calculate_optimal_budget(drr, target_drr, current_budget, total_orders)

            if action:
                return {
                    'type': 'ads_optimization',
                    'platform': 'ozon',
                    'campaign_id': campaign_id,
                    'campaign_name': campaign.get('title', 'Unknown'),
                    'action': action,
                    'current_budget': current_budget,
                    'new_budget': new_budget,
                    'drr': drr,
                    'spent': total_spent,
                    'orders': total_orders,
                    'reason': f'ДРР {drr:.1f}%'
                }
            return None

    async def _apply_ads_change(self, cabinet, decision: Dict):
        """Применяет изменения в рекламе"""
        try:
            if decision['platform'] == 'wb':
                from .wb_ads_client import WBAdsClient
                async with WBAdsClient(cabinet.api_key) as client:
                    action = decision['action']
                    campaign_id = decision['campaign_id']

                    if action == 'pause':
                        await client.pause_campaign(campaign_id)
                    elif action in ['decrease_bid', 'increase_bid'] and decision['new_bid']:
                        await client.set_bid(campaign_id, decision['new_bid'])

                    logger.info(f"[REAL] WB Ads {action}: campaign {campaign_id}")

            elif decision['platform'] == 'ozon':
                from .ozon_ads_client import OzonAdsClient
                client_id = getattr(cabinet, 'client_id', '')
                async with OzonAdsClient(cabinet.api_key, client_id) as client:
                    action = decision['action']
                    campaign_id = decision['campaign_id']

                    if action == 'pause':
                        await client.pause_campaign(campaign_id)
                    elif action in ['decrease_budget', 'increase_budget'] and decision['new_budget']:
                        await client.set_daily_budget(campaign_id, decision['new_budget'])

                    logger.info(f"[REAL] Ozon Ads {action}: campaign {campaign_id}")

        except Exception as e:
            logger.error(f"Failed to apply ads change: {e}")
            raise

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
