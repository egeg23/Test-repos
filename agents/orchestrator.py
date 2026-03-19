# agents/orchestrator.py - Оркестратор подагентов
"""
Orchestrator - координирует работу всех подагентов
"""

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List
import sys
import subprocess

sys.path.insert(0, str(Path(__file__).parent.parent))

logger = logging.getLogger('orchestrator')


class Orchestrator:
    """
    🎼 Orchestrator - управление подагентами
    
    Подагенты:
    - Pricing Agent: ценообразование
    - Inventory Agent: запасы
    - Content Agent: контент
    - Ads Agent: реклама
    - Analytics Agent: аналитика
    """
    
    AGENTS = ['pricing', 'inventory', 'content', 'ads', 'analytics']
    
    def __init__(self, clients_dir: str = "/opt/clients"):
        self.clients_dir = Path(clients_dir)
        self.orchestrator_dir = self.clients_dir / "orchestrator"
        self.orchestrator_dir.mkdir(parents=True, exist_ok=True)
        
        self.status_file = self.orchestrator_dir / "status.json"
        self.status = self._load_status()
    
    def _load_status(self) -> Dict:
        if self.status_file.exists():
            with open(self.status_file) as f:
                return json.load(f)
        return {
            'last_run': None,
            'cycles_completed': 0,
            'agent_statuses': {}
        }
    
    def _save_status(self):
        with open(self.status_file, 'w') as f:
            json.dump(self.status, f, default=str)
    
    async def run_cycle(self, client_id: str, platform: str = "wb"):
        """
        Один цикл оркестратора - запускает всех агентов
        """
        logger.info(f"🎼 Orchestrator cycle for {client_id}")
        
        results = {}
        
        for agent_name in self.AGENTS:
            try:
                result = await self._run_agent(agent_name, client_id, platform)
                results[agent_name] = result
                logger.info(f"✅ {agent_name}_agent completed")
            except Exception as e:
                logger.error(f"❌ {agent_name}_agent failed: {e}")
                results[agent_name] = {'status': 'error', 'error': str(e)}
        
        # Обновляем статус
        self.status['last_run'] = datetime.now().isoformat()
        self.status['cycles_completed'] = self.status.get('cycles_completed', 0) + 1
        self.status['agent_statuses'] = results
        self._save_status()
        
        # Генерируем сводку
        await self._generate_summary(client_id, results)
        
        logger.info(f"🎼 Orchestrator cycle completed")
    
    async def _run_agent(self, agent_name: str, client_id: str, platform: str) -> Dict:
        """Запускает одного агента"""
        agent_script = Path(__file__).parent / f"{agent_name}_agent.py"
        
        if not agent_script.exists():
            return {'status': 'skipped', 'reason': 'script not found'}
        
        # Запускаем через subprocess
        cmd = ['python3', str(agent_script), client_id, platform]
        
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        return {
            'status': 'success' if process.returncode == 0 else 'error',
            'returncode': process.returncode,
            'output': stdout.decode()[-500:] if stdout else '',  # Последние 500 символов
        }
    
    async def _generate_summary(self, client_id: str, results: Dict):
        """Генерирует сводку для пользователя"""
        summary = {
            'timestamp': datetime.now().isoformat(),
            'client_id': client_id,
            'cycle_results': results,
            'overall_status': 'success' if all(r.get('status') == 'success' for r in results.values()) else 'partial'
        }
        
        summary_file = self.orchestrator_dir / f"{client_id}_latest_summary.json"
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)
        
        logger.info(f"📋 Summary saved: {summary_file}")
    
    def get_status(self) -> Dict:
        """Возвращает статус оркестратора"""
        return {
            'orchestrator': {
                'last_run': self.status.get('last_run'),
                'cycles_completed': self.status.get('cycles_completed', 0)
            },
            'agents': self.status.get('agent_statuses', {})
        }


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python orchestrator.py <client_id>")
        sys.exit(1)
    
    orch = Orchestrator()
    asyncio.run(orch.run_cycle(sys.argv[1]))
