# agents/ads_agent.py - Подагент управления рекламой (REAL API)
"""
Ads Agent - управление рекламными кампаниями с реальным WB API
"""

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import sys
import html

sys.path.insert(0, str(Path(__file__).parent.parent))
from modules.ai_learning_engine import AILearningEngine
from modules.wb_ads_client import WBAdsClient
from modules.api_client_factory import api_client_factory, CabinetNotFoundError
from modules.ads_strategy_config import ads_strategy_config

logger = logging.getLogger('ads_agent')


class AdsAgent:
    """🤖 Ads Agent - управление рекламой с реальным API"""
    
    def __init__(self, clients_dir: str = "/opt/clients"):
        self.clients_dir = Path(clients_dir)
        self.agent_dir = self.clients_dir / "agents" / "ads"
        self.agent_dir.mkdir(parents=True, exist_ok=True)
        
        self.ai_learning = AILearningEngine(clients_dir)
        
        self.status_file = self.agent_dir / "status.json"
        self.status = self._load_status()
    
    def _load_status(self) -> Dict:
        if self.status_file.exists():
            with open(self.status_file) as f:
                return json.load(f)
        return {
            'last_run': None,
            'campaigns_adjusted': 0,
            'total_campaigns': 0,
            'api_calls': 0
        }
    
    def _save_status(self):
        with open(self.status_file, 'w') as f:
            json.dump(self.status, f, default=str)
    
    async def run_cycle(self, user_id: str, platform: str = "wb"):
        """
        Цикл работы с реальным API
        
        Args:
            user_id: ID пользователя
            platform: Платформа (wb/ozon)
        """
        logger.info(f"📢 Ads Agent cycle for {user_id} ({platform})")
        
        if platform != 'wb':
            logger.warning(f"Platform {platform} not yet supported for ads")
            return
        
        try:
            # Получаем API ключ пользователя
            api_key = await self._get_api_key(user_id, platform)
            if not api_key:
                logger.warning(f"No API key found for user {user_id}")
                return
            
            # Подключаемся к API
            async with WBAdsClient(api_key) as client:
                if not client.is_valid:
                    logger.error(f"Invalid WB Ads API key for user {user_id}")
                    return
                
                # Получаем активные кампании
                campaigns = await client.get_campaigns(status='9')  # 9 = активна
                
                if not campaigns:
                    logger.info(f"No active campaigns for user {user_id}")
                    return
                
                self.status['total_campaigns'] = len(campaigns)
                
                # Обрабатываем каждую кампанию
                adjusted_count = 0
                for campaign in campaigns:
                    try:
                        adjusted = await self._optimize_campaign(
                            user_id=user_id,
                            client=client,
                            campaign=campaign
                        )
                        if adjusted:
                            adjusted_count += 1
                    except Exception as e:
                        logger.error(f"Error optimizing campaign {campaign.get('id')}: {e}")
                        continue
                
                self.status['campaigns_adjusted'] = adjusted_count
                self.status['api_calls'] = self.status.get('api_calls', 0) + len(campaigns)
                
                logger.info(f"✅ Ads Agent: {adjusted_count}/{len(campaigns)} campaigns optimized")
        
        except Exception as e:
            logger.error(f"Ads Agent error for {user_id}: {e}")
        
        finally:
            self.status['last_run'] = datetime.now().isoformat()
            self._save_status()
    
    async def _get_api_key(self, user_id: str, platform: str) -> Optional[str]:
        """Получает API ключ пользователя"""
        try:
            from modules.multi_cabinet_manager import cabinet_manager
            
            cabinets = cabinet_manager.get_all_user_cabinets(user_id)
            for cabinet in cabinets:
                if cabinet.platform == platform and cabinet.api_key:
                    return cabinet.api_key
            
            return None
        except Exception as e:
            logger.error(f"Failed to get API key: {e}")
            return None
    
    async def _optimize_campaign(
        self,
        user_id: str,
        client: WBAdsClient,
        campaign: Dict
    ) -> bool:
        """
        Оптимизирует кампанию на основе ДРР
        
        Returns:
            True если были внесены изменения
        """
        campaign_id = campaign.get('id')
        if not campaign_id:
            return False
        
        try:
            # Получаем детальную информацию о кампании
            campaign_info = await client.get_campaign_info(campaign_id)
            
            # Получаем статистику за последние 7 дней
            daily_stats = await client.get_daily_statistics(campaign_id, days=7)
            
            if not daily_stats:
                logger.info(f"No statistics for campaign {campaign_id}")
                return False
            
            # Считаем суммарную статистику
            total_spent = sum(day.get('spent', 0) for day in daily_stats)
            total_orders = sum(day.get('orders', 0) for day in daily_stats)
            total_views = sum(day.get('views', 0) for day in daily_stats)
            total_clicks = sum(day.get('clicks', 0) for day in daily_stats)
            
            # Рассчитываем метрики
            campaign_price = campaign_info.get('price', 0) or 0
            current_drr = client.calculate_drr(total_spent, total_orders * campaign_price)
            ctr = (total_clicks / total_views * 100) if total_views > 0 else 0
            
            current_bid = campaign_info.get('cpm', 0) / 100  # Копейки → рубли
            
            # Проверяем валидность current_bid
            if current_bid <= 0:
                logger.warning(f"Campaign {campaign_id}: Invalid bid {current_bid}, skipping")
                return False
            
            # Получаем стратегию пользователя
            strategy_config = ads_strategy_config.get_user_strategy_config(user_id)
            target_drr = strategy_config.target_drr
            max_drr = strategy_config.max_drr
            bid_aggression = strategy_config.bid_aggression
            
            logger.info(
                f"Campaign {campaign_id}: "
                f"ДРР={current_drr:.1f}%, "
                f"CTR={ctr:.2f}%, "
                f"Ставка={current_bid:.0f}₽, "
                f"Стратегия={strategy_config.name}"
            )
            
            # Анализируем через AI
            analysis = self.ai_learning.analyze_drr_situation(
                campaign_id=str(campaign_id),
                product_id=str(campaign_info.get('nmId', 'unknown')),
                current_drr=current_drr,
                target_drr=target_drr,
                orders_count=total_orders,
                total_views=total_views,
                ctr=ctr,
                days_since_start=len(daily_stats)
            )
            
            recommendation = analysis.get('recommendation')
            
            # Применяем решение с учетом стратегии
            if recommendation == 'decrease_drr':
                new_bid = await client.calculate_optimal_bid(
                    current_drr=current_drr,
                    target_drr=target_drr,
                    current_bid=current_bid,
                    orders=total_orders
                )
                
                # Учитываем агрессивность стратегии
                if bid_aggression != 1.0:
                    adjustment = (new_bid - current_bid) * bid_aggression + current_bid
                    new_bid = max(50.0, min(adjustment, 5000.0))  # Ограничения
                
                if current_bid > 0 and abs(new_bid - current_bid) / current_bid > 0.05:
                    success = await client.set_bid(campaign_id, new_bid)
                    if success:
                        logger.info(
                            f"💰 Campaign {campaign_id}: "
                            f"Ставка {current_bid:.0f}₽ → {new_bid:.0f}₽ "
                            f"(ДРР {current_drr:.1f}%, цель {target_drr}%)")
                        return True
            
            elif recommendation == 'pause_campaign':
                # Используем max_drr из стратегии для паузы
                if current_drr > max_drr:
                    success = await client.pause_campaign(campaign_id)
                    if success:
                        logger.warning(f"⏸ Campaign {campaign_id} paused (ДРР {current_drr:.1f}% > {max_drr}%)")
                        return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error optimizing campaign {campaign_id}: {e}")
            return False
    
    async def get_campaigns_report(self, user_id: str) -> str:
        """
        Генерирует отчёт по кампаниям для Telegram
        
        Returns:
            Текст отчёта
        """
        try:
            api_key = await self._get_api_key(user_id, 'wb')
            if not api_key:
                return "❌ API ключ не найден. Добавьте кабинет WB."
            
            async with WBAdsClient(api_key) as client:
                campaigns = await client.get_campaigns()
                
                if not campaigns:
                    return "📢 Нет рекламных кампаний."
                
                # Собираем статистику по всем кампаниям
                total_spent = 0
                total_orders = 0
                total_views = 0
                total_clicks = 0
                
                lines = ["📢 <b>Рекламные кампании</b>\n"]
                
                for campaign in campaigns[:10]:  # Показываем первые 10
                    camp_id = campaign.get('id')
                    camp_name = campaign.get('name', f'Campaign #{camp_id}')
                    # Экранируем HTML
                    camp_name = html.escape(camp_name)
                    status = campaign.get('status')
                    
                    # Статус текстом
                    status_emoji = {
                        '9': '🟢',   # Активна
                        '11': '⏸',  # Пауза
                    }.get(str(status), '⚪')
                    
                    lines.append(f"{status_emoji} {camp_name}")
                
                lines.append(f"\n📊 Всего кампаний: {len(campaigns)}")
                lines.append(f"🕐 Обновлено: {datetime.now().strftime('%H:%M')}")
                
                return "\n".join(lines)
                
        except Exception as e:
            logger.error(f"Error generating report: {e}")
            return f"❌ Ошибка получения данных: {e}"


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python ads_agent.py <user_id>")
        sys.exit(1)
    
    agent = AdsAgent()
    asyncio.run(agent.run_cycle(sys.argv[1]))
