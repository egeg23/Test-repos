# modules/rate_limiter.py - Rate limiting for API calls
"""
Rate limiter for WB/Ozon API calls
Prevents ban and ensures fair usage across users
"""

import time
import logging
from typing import Dict, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import json
from pathlib import Path

logger = logging.getLogger('rate_limiter')


@dataclass
class RateLimit:
    """Rate limit configuration"""
    requests_per_second: float = 1.0
    requests_per_minute: int = 30
    requests_per_hour: int = 500
    
    # Cooldown after hitting limit (seconds)
    cooldown_seconds: int = 60


class RateLimiter:
    """
    Token bucket rate limiter
    
    Supports:
    - Per-user limits
    - Per-platform limits (WB/Ozon)
    - Per-action limits
    """
    
    # Platform-specific limits
    PLATFORM_LIMITS = {
        'wb': RateLimit(
            requests_per_second=0.5,  # 1 request per 2 seconds
            requests_per_minute=20,
            requests_per_hour=300
        ),
        'ozon': RateLimit(
            requests_per_second=0.2,  # 1 request per 5 seconds
            requests_per_minute=10,
            requests_per_hour=200
        ),
        'mpstats': RateLimit(
            requests_per_second=0.1,  # 1 request per 10 seconds
            requests_per_minute=5,
            requests_per_hour=100
        )
    }
    
    def __init__(self, storage_dir: str = "/opt/clients/rate_limits"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        # In-memory cache for fast checks
        self._cache: Dict[str, Dict] = {}
        
        logger.info("Rate limiter initialized")
    
    def _get_key(self, user_id: str, platform: str, action: str = 'default') -> str:
        """Generate cache key"""
        return f"{user_id}:{platform}:{action}"
    
    def _load_state(self, key: str) -> Dict:
        """Load rate limit state from disk"""
        if key in self._cache:
            return self._cache[key]
        
        file_path = self.storage_dir / f"{key.replace(':', '_')}.json"
        if file_path.exists():
            try:
                with open(file_path) as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Failed to load rate limit state: {e}")
        
        # Default state
        return {
            'tokens': 10,  # Start with full bucket
            'last_update': time.time(),
            'requests_this_minute': 0,
            'requests_this_hour': 0,
            'minute_window_start': time.time(),
            'hour_window_start': time.time(),
            'cooldown_until': 0
        }
    
    def _save_state(self, key: str, state: Dict):
        """Save rate limit state to disk"""
        self._cache[key] = state
        
        file_path = self.storage_dir / f"{key.replace(':', '_')}.json"
        try:
            with open(file_path, 'w') as f:
                json.dump(state, f)
        except Exception as e:
            logger.error(f"Failed to save rate limit state: {e}")
    
    def check_limit(self, user_id: str, platform: str, action: str = 'default') -> bool:
        """
        Check if request is allowed
        
        Returns True if request can proceed, False if rate limited
        """
        key = self._get_key(user_id, platform, action)
        state = self._load_state(key)
        limit = self.PLATFORM_LIMITS.get(platform, RateLimit())
        
        now = time.time()
        
        # Check cooldown
        if now < state['cooldown_until']:
            logger.warning(f"Rate limit: {key} in cooldown")
            return False
        
        # Reset minute window
        if now - state['minute_window_start'] >= 60:
            state['requests_this_minute'] = 0
            state['minute_window_start'] = now
        
        # Reset hour window
        if now - state['hour_window_start'] >= 3600:
            state['requests_this_hour'] = 0
            state['hour_window_start'] = now
        
        # Check limits
        if state['requests_this_minute'] >= limit.requests_per_minute:
            logger.warning(f"Rate limit: {key} minute limit exceeded")
            state['cooldown_until'] = now + limit.cooldown_seconds
            self._save_state(key, state)
            return False
        
        if state['requests_this_hour'] >= limit.requests_per_hour:
            logger.warning(f"Rate limit: {key} hour limit exceeded")
            state['cooldown_until'] = now + limit.cooldown_seconds * 5
            self._save_state(key, state)
            return False
        
        # Token bucket
        time_passed = now - state['last_update']
        tokens_to_add = time_passed * limit.requests_per_second
        state['tokens'] = min(10, state['tokens'] + tokens_to_add)
        
        if state['tokens'] < 1:
            logger.warning(f"Rate limit: {key} token bucket empty")
            return False
        
        # Consume token
        state['tokens'] -= 1
        state['last_update'] = now
        state['requests_this_minute'] += 1
        state['requests_this_hour'] += 1
        
        self._save_state(key, state)
        return True
    
    def get_wait_time(self, user_id: str, platform: str, action: str = 'default') -> int:
        """Get seconds to wait before next request is allowed"""
        key = self._get_key(user_id, platform, action)
        state = self._load_state(key)
        
        now = time.time()
        
        # Check cooldown
        if now < state['cooldown_until']:
            return int(state['cooldown_until'] - now)
        
        # Check if we have tokens
        limit = self.PLATFORM_LIMITS.get(platform, RateLimit())
        time_passed = now - state['last_update']
        tokens = min(10, state['tokens'] + time_passed * limit.requests_per_second)
        
        if tokens >= 1:
            return 0
        
        # Calculate wait time for next token
        return int((1 - tokens) / limit.requests_per_second)
    
    def reset_limits(self, user_id: str = None, platform: str = None):
        """Reset rate limits (for testing or admin)"""
        if user_id and platform:
            key = self._get_key(user_id, platform)
            file_path = self.storage_dir / f"{key.replace(':', '_')}.json"
            if file_path.exists():
                file_path.unlink()
            if key in self._cache:
                del self._cache[key]
        else:
            # Reset all
            for file_path in self.storage_dir.glob('*.json'):
                file_path.unlink()
            self._cache.clear()
        
        logger.info(f"Rate limits reset for user={user_id}, platform={platform}")


# Global instance
rate_limiter = RateLimiter()
