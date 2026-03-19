# agents/ads_agent.py - Подагент управления рекламой
"""
Ads Agent - управление рекламными кампаниями (ДРР, ставки)
"""

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
from modules.ai_learning_engine import AILearningEngine

logger = logging.getLogger('ads_agent')


class AdsAgent:
    """🤖 Ads Agent - управление рекламой (ДРР оптимизация)"""
    
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
        return {'last_run': None, 'campaigns_adjusted': 0}
    
    def _save_status(self):
        with open(self.status_file, 'w') as f:
            json.dump(self.status, f, default=str)
    
    async def run_cycle(self, client_id: str, platform: str = "wb"):
        """Цикл работы"""
        logger.info(f"📢 Ads Agent cycle for {client_id}")
        
        campaigns = await self._get_campaigns(client_id, platform)
        
        for campaign in campaigns:
            await self._optimize_campaign(client_id, campaign)
        
        self.status['last_run'] = datetime.now().isoformat()
        self._save_status()
        
        logger.info(f"✅ Ads Agent: {len(campaigns)} campaigns optimized")
    
    async def _get_campaigns(self, client_id: str, platform: str) -> List[Dict]:
        """Получает кампании"""
        return [
            {'id': 'camp_1', 'drr': 25.0, 'orders': 8, 'views': 500, 'ctr': 3.5, 'days': 5},
            {'id': 'camp_2', 'drr': 18.0, 'orders': 45, 'views': 2000, 'ctr': 4.2, 'days': 20},
        ]
    
    async def _optimize_campaign(self, client_id: str, campaign: Dict):
        """Оптимизирует кампанию"""
        analysis = self.ai_learning.analyze_drr_situation(
            campaign_id=campaign['id'],
            product_id='product_1',
            current_drr=campaign['drr'],
            target_drr=15.0,
            orders_count=campaign['orders'],
            total_views=campaign['views'],
            ctr=campaign['ctr'],
            days_since_start=campaign['days']
        )
        
        recommendation = analysis.get('recommendation')
        
        if recommendation == 'decrease_drr':
            action = "Снижаем ставку"
        elif recommendation == 'maintain_high_drr':
            action = "Поддерживаем высокий ДРР"
        elif recommendation == 'check_content':
            action = "Проверяем контент (низкий CTR)"
        else:
            action = "Норма"
        
        logger.info(f"📢 Campaign {campaign['id']}: ДРР {campaign['drr']}% → {action}")
        self.status['campaigns_adjusted'] = self.status.get('campaigns_adjusted', 0) + 1


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python ads_agent.py <client_id>")
        sys.exit(1)
    
    agent = AdsAgent()
    asyncio.run(agent.run_cycle(sys.argv[1]))
