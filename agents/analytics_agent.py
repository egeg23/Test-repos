# agents/analytics_agent.py - Подагент аналитики
"""
Analytics Agent - сбор и анализ метрик
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
from modules.analytics_engine import AnalyticsEngine

logger = logging.getLogger('analytics_agent')


class AnalyticsAgent:
    """🤖 Analytics Agent - сбор и анализ метрик"""
    
    def __init__(self, clients_dir: str = "/opt/clients"):
        self.clients_dir = Path(clients_dir)
        self.agent_dir = self.clients_dir / "agents" / "analytics"
        self.agent_dir.mkdir(parents=True, exist_ok=True)
        
        self.analytics = AnalyticsEngine(clients_dir)
        
        self.status_file = self.agent_dir / "status.json"
        self.status = self._load_status()
    
    def _load_status(self) -> Dict:
        if self.status_file.exists():
            with open(self.status_file) as f:
                return json.load(f)
        return {'last_run': None, 'reports_generated': 0}
    
    def _save_status(self):
        with open(self.status_file, 'w') as f:
            json.dump(self.status, f, default=str)
    
    async def run_cycle(self, client_id: str, platform: str = "wb"):
        """Цикл работы"""
        logger.info(f"📊 Analytics Agent cycle for {client_id}")
        
        # Генерируем отчет
        report = await self._generate_report(client_id, platform)
        
        # Сохраняем
        report_file = self.agent_dir / f"{client_id}_{platform}_report.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        self.status['last_run'] = datetime.now().isoformat()
        self.status['reports_generated'] = self.status.get('reports_generated', 0) + 1
        self._save_status()
        
        logger.info(f"✅ Analytics Agent: report saved")
    
    async def _generate_report(self, client_id: str, platform: str) -> Dict:
        """Генерирует отчет"""
        # Используем analytics_engine
        trend = self.analytics.get_sales_trend(client_id, platform, days=14)
        categories = self.analytics.get_category_breakdown(client_id, platform)
        metrics = self.analytics.get_key_metrics(client_id, platform)
        
        return {
            'generated_at': datetime.now().isoformat(),
            'client_id': client_id,
            'platform': platform,
            'revenue_7d': metrics['revenue_7d'],
            'revenue_30d': metrics['revenue_30d'],
            'orders_7d': metrics['orders_7d'],
            'drr': metrics['drr'],
            'trend': trend['trend'],
            'top_category': categories['top_category']
        }


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python analytics_agent.py <client_id>")
        sys.exit(1)
    
    agent = AnalyticsAgent()
    asyncio.run(agent.run_cycle(sys.argv[1]))
