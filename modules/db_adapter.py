# modules/db_adapter.py - Adapter for transitioning from JSON to PostgreSQL
"""
Database adapter for smooth transition from JSON files to PostgreSQL
Phase 1: Read from JSON, write to both
Phase 2: Read from PG, fallback to JSON
Phase 3: PostgreSQL only
"""

import json
import os
from pathlib import Path
from typing import Optional, Dict, List, Any
from datetime import datetime
import logging

from .database import get_db, User, Cabinet, FuckModeConfig

logger = logging.getLogger('db_adapter')


class DatabaseAdapter:
    """
    Adapter that bridges JSON storage and PostgreSQL
    
    Current phase: Transition (read JSON, write both)
    """
    
    def __init__(self, clients_dir: str = "/opt/clients"):
        self.clients_dir = Path(clients_dir)
        self.clients_dir.mkdir(parents=True, exist_ok=True)
        self._use_postgres = True  # Try PG first, fallback to JSON
    
    # ============ USERS ============
    
    def get_user(self, user_id: int) -> Optional[Dict]:
        """Get user data (PG first, fallback to JSON)"""
        # Try PostgreSQL first
        if self._use_postgres:
            try:
                db = get_db()
                user = db.query(User).filter(User.id == user_id).first()
                if user:
                    return {
                        'id': user.id,
                        'username': user.username,
                        'first_name': user.first_name,
                        'last_name': user.last_name,
                        'phone': user.phone,
                        'language': user.language,
                        'notifications_enabled': user.notifications_enabled,
                        'created_at': user.created_at.isoformat() if user.created_at else None
                    }
            except Exception as e:
                logger.warning(f"PG get_user failed, falling back to JSON: {e}")
            finally:
                db.close()
        
        # Fallback to JSON
        return self._get_user_json(user_id)
    
    def save_user(self, user_id: int, user_data: Dict) -> bool:
        """Save user data (to both PG and JSON)"""
        success = True
        
        # Save to JSON (current system)
        if not self._save_user_json(user_id, user_data):
            success = False
        
        # Save to PostgreSQL (new system)
        if self._use_postgres:
            try:
                db = get_db()
                user = db.query(User).filter(User.id == user_id).first()
                
                if not user:
                    user = User(
                        id=user_id,
                        username=user_data.get('username'),
                        first_name=user_data.get('first_name'),
                        last_name=user_data.get('last_name'),
                        phone=user_data.get('phone'),
                        created_at=datetime.utcnow()
                    )
                    db.add(user)
                else:
                    user.username = user_data.get('username', user.username)
                    user.first_name = user_data.get('first_name', user.first_name)
                    user.last_name = user_data.get('last_name', user.last_name)
                    user.phone = user_data.get('phone', user.phone)
                    user.last_activity = datetime.utcnow()
                
                db.commit()
                logger.info(f"User {user_id} saved to PostgreSQL")
            except Exception as e:
                logger.error(f"Failed to save user to PG: {e}")
                success = False
            finally:
                db.close()
        
        return success
    
    def _get_user_json(self, user_id: int) -> Optional[Dict]:
        """Get user from JSON file"""
        user_file = self.clients_dir / str(user_id) / "user_data.json"
        if user_file.exists():
            try:
                with open(user_file) as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Failed to read user JSON: {e}")
        return None
    
    def _save_user_json(self, user_id: int, user_data: Dict) -> bool:
        """Save user to JSON file"""
        user_dir = self.clients_dir / str(user_id)
        user_dir.mkdir(parents=True, exist_ok=True)
        user_file = user_dir / "user_data.json"
        
        try:
            with open(user_file, 'w') as f:
                json.dump(user_data, f, indent=2, default=str)
            return True
        except Exception as e:
            logger.error(f"Failed to save user JSON: {e}")
            return False
    
    # ============ CABINETS ============
    
    def get_cabinets(self, user_id: int) -> List[Dict]:
        """Get all cabinets for user"""
        cabinets = []
        
        # Try PostgreSQL
        if self._use_postgres:
            try:
                db = get_db()
                db_cabinets = db.query(Cabinet).filter(
                    Cabinet.user_id == user_id
                ).all()
                
                for cab in db_cabinets:
                    cabinets.append({
                        'id': cab.id,
                        'name': cab.name,
                        'platform': cab.platform,
                        'is_active': cab.is_active,
                        'api_key': cab.api_key,
                        'api_secret': cab.api_secret,
                        'settings': cab.settings or {},
                        'created_at': cab.created_at.isoformat() if cab.created_at else None
                    })
            except Exception as e:
                logger.warning(f"PG get_cabinets failed: {e}")
            finally:
                db.close()
        
        # Fallback to JSON if no PG data
        if not cabinets:
            cabinets = self._get_cabinets_json(user_id)
        
        return cabinets
    
    def save_cabinet(self, user_id: int, cabinet_id: str, cabinet_data: Dict) -> bool:
        """Save cabinet (to both)"""
        success = True
        
        # JSON
        if not self._save_cabinet_json(user_id, cabinet_id, cabinet_data):
            success = False
        
        # PostgreSQL
        if self._use_postgres:
            try:
                db = get_db()
                cabinet = db.query(Cabinet).filter(Cabinet.id == cabinet_id).first()
                
                if not cabinet:
                    cabinet = Cabinet(
                        id=cabinet_id,
                        user_id=user_id,
                        name=cabinet_data.get('name', 'Unknown'),
                        platform=cabinet_data.get('platform', 'wb'),
                        is_active=cabinet_data.get('is_active', True),
                        api_key=cabinet_data.get('api_key'),
                        api_secret=cabinet_data.get('api_secret'),
                        settings=cabinet_data.get('settings', {}),
                        created_at=datetime.utcnow()
                    )
                    db.add(cabinet)
                else:
                    cabinet.name = cabinet_data.get('name', cabinet.name)
                    cabinet.is_active = cabinet_data.get('is_active', cabinet.is_active)
                    cabinet.api_key = cabinet_data.get('api_key', cabinet.api_key)
                    cabinet.api_secret = cabinet_data.get('api_secret', cabinet.api_secret)
                    cabinet.settings = cabinet_data.get('settings', cabinet.settings)
                
                db.commit()
            except Exception as e:
                logger.error(f"Failed to save cabinet to PG: {e}")
                success = False
            finally:
                db.close()
        
        return success
    
    def _get_cabinets_json(self, user_id: int) -> List[Dict]:
        """Get cabinets from JSON files"""
        cabinets = []
        user_dir = self.clients_dir / str(user_id)
        
        if user_dir.exists():
            for cabinet_file in user_dir.glob('cabinet_*.json'):
                try:
                    with open(cabinet_file) as f:
                        cabinet_data = json.load(f)
                        cabinet_data['id'] = cabinet_file.stem.replace('cabinet_', '')
                        cabinets.append(cabinet_data)
                except Exception as e:
                    logger.error(f"Failed to read cabinet JSON: {e}")
        
        return cabinets
    
    def _save_cabinet_json(self, user_id: int, cabinet_id: str, cabinet_data: Dict) -> bool:
        """Save cabinet to JSON file"""
        user_dir = self.clients_dir / str(user_id)
        user_dir.mkdir(parents=True, exist_ok=True)
        cabinet_file = user_dir / f"cabinet_{cabinet_id}.json"
        
        try:
            with open(cabinet_file, 'w') as f:
                json.dump(cabinet_data, f, indent=2, default=str)
            return True
        except Exception as e:
            logger.error(f"Failed to save cabinet JSON: {e}")
            return False
    
    # ============ FUCK MODE CONFIG ============
    
    def get_fuck_mode_config(self, user_id: int) -> Dict:
        """Get Fuck Mode config"""
        # Try PostgreSQL
        if self._use_postgres:
            try:
                db = get_db()
                config = db.query(FuckModeConfig).filter(
                    FuckModeConfig.user_id == user_id
                ).first()
                
                if config:
                    return {
                        'enabled': config.enabled,
                        'dry_run': config.dry_run,
                        'max_price_change_percent': config.max_price_change_percent,
                        'min_margin_percent': config.min_margin_percent,
                        'target_drr': config.target_drr,
                        'platforms': config.platforms or ['wb', 'ozon'],
                        'enabled_notifications': config.enabled_notifications,
                        'check_interval_minutes': config.check_interval_minutes
                    }
            except Exception as e:
                logger.warning(f"PG get_fuck_mode_config failed: {e}")
            finally:
                db.close()
        
        # Fallback to JSON
        return self._get_fuck_mode_config_json(user_id)
    
    def save_fuck_mode_config(self, user_id: int, config: Dict) -> bool:
        """Save Fuck Mode config (to both)"""
        success = True
        
        # JSON
        if not self._save_fuck_mode_config_json(user_id, config):
            success = False
        
        # PostgreSQL
        if self._use_postgres:
            try:
                db = get_db()
                db_config = db.query(FuckModeConfig).filter(
                    FuckModeConfig.user_id == user_id
                ).first()
                
                if not db_config:
                    db_config = FuckModeConfig(
                        user_id=user_id,
                        enabled=config.get('enabled', False),
                        dry_run=config.get('dry_run', True),
                        max_price_change_percent=config.get('max_price_change_percent', 20.0),
                        min_margin_percent=config.get('min_margin_percent', 15.0),
                        target_drr=config.get('target_drr', 15.0),
                        platforms=config.get('platforms', ['wb', 'ozon']),
                        enabled_notifications=config.get('enabled_notifications', True),
                        check_interval_minutes=config.get('check_interval_minutes', 30)
                    )
                    db.add(db_config)
                else:
                    db_config.enabled = config.get('enabled', db_config.enabled)
                    db_config.dry_run = config.get('dry_run', db_config.dry_run)
                    db_config.max_price_change_percent = config.get(
                        'max_price_change_percent', db_config.max_price_change_percent
                    )
                
                db.commit()
            except Exception as e:
                logger.error(f"Failed to save fuck mode config to PG: {e}")
                success = False
            finally:
                db.close()
        
        return success
    
    def _get_fuck_mode_config_json(self, user_id: int) -> Dict:
        """Get Fuck Mode config from JSON"""
        config_file = self.clients_dir / str(user_id) / "settings" / "fuck_mode_config.json"
        if config_file.exists():
            try:
                with open(config_file) as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Failed to read fuck mode config JSON: {e}")
        
        # Default config
        return {
            'enabled': False,
            'dry_run': True,
            'max_price_change_percent': 20.0,
            'min_margin_percent': 15.0,
            'target_drr': 15.0,
            'platforms': ['wb', 'ozon'],
            'enabled_notifications': True,
            'check_interval_minutes': 30
        }
    
    def _save_fuck_mode_config_json(self, user_id: int, config: Dict) -> bool:
        """Save Fuck Mode config to JSON"""
        settings_dir = self.clients_dir / str(user_id) / "settings"
        settings_dir.mkdir(parents=True, exist_ok=True)
        config_file = settings_dir / "fuck_mode_config.json"
        
        try:
            with open(config_file, 'w') as f:
                json.dump(config, f, indent=2, default=str)
            return True
        except Exception as e:
            logger.error(f"Failed to save fuck mode config JSON: {e}")
            return False


# Global instance
db_adapter = DatabaseAdapter()
