# celery_app.py - Celery configuration for distributed tasks
"""
Celery application for Seller AI Bot
Handles distributed task processing for 300+ users
"""

import os
from celery import Celery
from celery.signals import task_failure, task_success
import logging

logger = logging.getLogger('celery')

# Create Celery app
app = Celery('seller_ai')

# Configuration
app.conf.update(
    # Broker (Redis)
    broker_url=os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/1'),
    result_backend=os.getenv('CELERY_RESULT_BACKEND', 'redis://localhost:6379/2'),
    
    # Serialization
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    
    # Task settings
    task_track_started=True,
    task_time_limit=300,  # 5 minutes max per task
    task_soft_time_limit=240,  # Soft limit 4 minutes
    
    # Worker settings
    worker_prefetch_multiplier=1,  # One task at a time
    worker_max_tasks_per_child=1000,  # Restart worker after 1000 tasks
    
    # Result settings
    result_expires=3600,  # Results expire after 1 hour
    
    # Rate limits (respect API limits)
    task_default_rate_limit='10/m',
    
    # Queues
    task_routes={
        'tasks.api.*': {'queue': 'api_jobs'},
        'tasks.mpstats.*': {'queue': 'mpstats_jobs'},
        'tasks.notifications.*': {'queue': 'notifications'},
        'tasks.fuck_mode.*': {'queue': 'api_jobs'},
    },
    
    # Beat schedule (periodic tasks)
    beat_schedule={
        'fuck_mode_cycle_all_users': {
            'task': 'celery_app.run_fuck_mode_for_all_users',
            'schedule': 300.0,  # Every 5 minutes
            'options': {'queue': 'api_jobs'}
        },
        'mpstats_update_all': {
            'task': 'celery_app.update_mpstats_for_all',
            'schedule': 1800.0,  # Every 30 minutes
            'options': {'queue': 'mpstats_jobs'}
        },
        'cleanup_old_data': {
            'task': 'celery_app.cleanup_old_data',
            'schedule': 86400.0,  # Daily
            'options': {'queue': 'api_jobs'}
        },
    },
)


# Import tasks
@app.task(bind=True, max_retries=3, default_retry_delay=60)
def process_api_request(self, user_id: str, action: str, params: dict):
    """Process API request with retry logic"""
    try:
        # Import here to avoid circular imports
        from modules.api_client_factory import api_client_factory
        
        logger.info(f"Processing API request: {action} for user {user_id}")
        
        # Rate limiting check
        from modules.rate_limiter import rate_limiter
        if not rate_limiter.check_limit(user_id, action):
            logger.warning(f"Rate limit exceeded for user {user_id}")
            raise self.retry(countdown=60)
        
        # Process the request
        # ... (specific logic based on action)
        
        return {'status': 'success', 'user_id': user_id, 'action': action}
        
    except Exception as exc:
        logger.error(f"API request failed: {exc}")
        raise self.retry(exc=exc)


@app.task(bind=True, max_retries=3, default_retry_delay=300)
def mpstats_analyze_product(self, user_id: str, product_id: str, category: str = None):
    """Analyze product with Mpstats (slow, rate limited)"""
    try:
        from modules.mpstats_browser import mpstats_browser
        
        logger.info(f"Mpstats analysis for product {product_id}")
        
        # This is slow - 10-30 seconds
        result = mpstats_browser.analyze_product(product_id, category)
        
        return {
            'status': 'success',
            'product_id': product_id,
            'competitors_count': len(result.get('competitors', [])),
            'avg_price': result.get('avg_price')
        }
        
    except Exception as exc:
        logger.error(f"Mpstats analysis failed: {exc}")
        raise self.retry(exc=exc)


@app.task(bind=True)
def send_notification(self, user_id: int, message: str, parse_mode: str = 'HTML'):
    """Send Telegram notification"""
    try:
        from modules.notification_service import notification_service
        
        asyncio.run(notification_service.send_notification(
            user_id=user_id,
            message=message,
            parse_mode=parse_mode
        ))
        
        return {'status': 'sent', 'user_id': user_id}
        
    except Exception as exc:
        logger.error(f"Notification failed: {exc}")
        # Don't retry notifications - they're time-sensitive
        return {'status': 'failed', 'error': str(exc)}


@app.task(bind=True, max_retries=2, default_retry_delay=30)
def fuck_mode_process_cabinet(self, user_id: str, cabinet_id: str):
    """Process one cabinet in Fuck Mode"""
    try:
        from modules.fuck_mode import fuck_mode
        from modules.multi_cabinet_manager import cabinet_manager
        
        logger.info(f"Fuck Mode: processing cabinet {cabinet_id} for user {user_id}")
        
        cabinet = cabinet_manager.get_cabinet(user_id, cabinet_id)
        if not cabinet or not cabinet.is_active:
            return {'status': 'skipped', 'reason': 'cabinet_not_active'}
        
        # Process cabinet
        import asyncio
        asyncio.run(fuck_mode._process_cabinet(user_id, cabinet))
        
        return {
            'status': 'completed',
            'user_id': user_id,
            'cabinet_id': cabinet_id
        }
        
    except Exception as exc:
        logger.error(f"Fuck Mode cabinet processing failed: {exc}")
        raise self.retry(exc=exc)


@app.task
def run_fuck_mode_for_all_users():
    """Run Fuck Mode cycle for all active users"""
    try:
        from modules.fuck_mode import fuck_mode
        from modules.multi_cabinet_manager import cabinet_manager
        
        # Get all users with Fuck Mode enabled
        all_users = cabinet_manager.get_all_users()
        
        tasks_created = 0
        for user_id in all_users:
            if fuck_mode.is_user_enabled(user_id):
                # Get user's cabinets
                cabinets = cabinet_manager.get_all_user_cabinets(user_id)
                
                for cabinet in cabinets:
                    if cabinet.is_active:
                        # Create task for each cabinet
                        fuck_mode_process_cabinet.delay(user_id, cabinet.id)
                        tasks_created += 1
        
        logger.info(f"Fuck Mode: Created {tasks_created} cabinet tasks")
        return {'status': 'scheduled', 'tasks': tasks_created}
        
    except Exception as exc:
        logger.error(f"Fuck Mode scheduling failed: {exc}")
        return {'status': 'error', 'error': str(exc)}


@app.task
def update_mpstats_for_all():
    """Update Mpstats data for all tracked products"""
    try:
        from modules.mpstats_storage import mpstats_storage
        
        # Get all tracked products
        products = mpstats_storage.get_all_tracked_products()
        
        tasks_created = 0
        for product in products:
            mpstats_analyze_product.delay(
                user_id=product['user_id'],
                product_id=product['product_id'],
                category=product.get('category')
            )
            tasks_created += 1
        
        logger.info(f"Mpstats: Created {tasks_created} analysis tasks")
        return {'status': 'scheduled', 'tasks': tasks_created}
        
    except Exception as exc:
        logger.error(f"Mpstats scheduling failed: {exc}")
        return {'status': 'error', 'error': str(exc)}


@app.task
def cleanup_old_data():
    """Clean up old data (logs, temporary files)"""
    try:
        import datetime
        from pathlib import Path
        
        # Clean old operation logs (keep 30 days)
        cutoff = datetime.datetime.now() - datetime.timedelta(days=30)
        
        # Clean up old files
        logs_dir = Path('/opt/telegram_bot/logs')
        if logs_dir.exists():
            for log_file in logs_dir.glob('*.log'):
                if log_file.stat().st_mtime < cutoff.timestamp():
                    log_file.unlink()
                    logger.info(f"Deleted old log: {log_file}")
        
        return {'status': 'cleaned'}
        
    except Exception as exc:
        logger.error(f"Cleanup failed: {exc}")
        return {'status': 'error', 'error': str(exc)}


# Event handlers
@task_success.connect
def handle_task_success(sender=None, result=None, **kwargs):
    """Handle successful task completion"""
    logger.debug(f"Task {sender.name} completed successfully")


@task_failure.connect
def handle_task_failure(sender=None, task_id=None, exception=None, **kwargs):
    """Handle task failure"""
    logger.error(f"Task {sender.name} failed: {exception}")
    # Could send alert to admin here


if __name__ == '__main__':
    app.start()
