# agents/content_agent.py - Подагент генерации контента
"""
Content Agent - генерация и оптимизация карточек товаров
"""

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
from modules.content_generator import ContentGenerator

logger = logging.getLogger('content_agent')


class ContentAgent:
    """🤖 Content Agent - генерация контента для товаров"""
    
    def __init__(self, clients_dir: str = "/opt/clients"):
        self.clients_dir = Path(clients_dir)
        self.agent_dir = self.clients_dir / "agents" / "content"
        self.agent_dir.mkdir(parents=True, exist_ok=True)
        
        self.content_gen = ContentGenerator(clients_dir)
        
        self.status_file = self.agent_dir / "status.json"
        self.status = self._load_status()
    
    def _load_status(self) -> Dict:
        if self.status_file.exists():
            with open(self.status_file) as f:
                return json.load(f)
        return {'last_run': None, 'cards_generated': 0}
    
    def _save_status(self):
        with open(self.status_file, 'w') as f:
            json.dump(self.status, f, default=str)
    
    async def run_cycle(self, client_id: str, platform: str = "wb"):
        """Цикл работы"""
        logger.info(f"✍️ Content Agent cycle for {client_id}")
        
        # Находим товары без описаний или с низким CTR
        products = await self._get_products_needing_content(client_id, platform)
        
        for product in products:
            await self._generate_content(client_id, product)
        
        self.status['last_run'] = datetime.now().isoformat()
        self._save_status()
        
        logger.info(f"✅ Content Agent: {len(products)} cards processed")
    
    async def _get_products_needing_content(self, client_id: str, platform: str) -> List[Dict]:
        """Находит товары нуждающиеся в контенте"""
        return [
            {'id': '12345', 'name': 'Наушники Sony', 'category': 'electronics', 'features': ['Шумоподавление', '30ч работы']},
        ]
    
    async def _generate_content(self, client_id: str, product: Dict):
        """Генерирует контент"""
        content = self.content_gen.generate_product_description(
            product_name=product['name'],
            category=product['category'],
            key_features=product['features']
        )
        
        # Сохраняем для клиента
        output_file = self.agent_dir / f"{client_id}_{product['id']}_content.json"
        with open(output_file, 'w') as f:
            json.dump({
                'product_id': product['id'],
                'content': {
                    'title': content.title,
                    'description': content.description,
                    'bullets': content.bullet_points
                },
                'generated_at': datetime.now().isoformat()
            }, f, indent=2)
        
        self.status['cards_generated'] = self.status.get('cards_generated', 0) + 1
        logger.info(f"✍️ Content generated for {product['id']}")


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python content_agent.py <client_id>")
        sys.exit(1)
    
    agent = ContentAgent()
    asyncio.run(agent.run_cycle(sys.argv[1]))
