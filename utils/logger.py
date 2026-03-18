# utils/logger.py - Helper functions for logging (FIXED)
import logging
import os
from datetime import datetime
from typing import Any, Dict, Optional


def _sanitize_for_logging(data: Any) -> Any:
    """
    Recursively sanitize data for logging by redacting sensitive fields.
    
    Args:
        data: Data to sanitize (dict, list, or primitive)
        
    Returns:
        Sanitized copy of data
    """
    SENSITIVE_KEYS = {'token', 'api_key', 'password', 'secret', 'authorization', 
                      'key', 'credential', 'auth', 'ssn', 'credit_card', 'cvv'}
    
    if isinstance(data, dict):
        sanitized = {}
        for key, value in data.items():
            # Check if key contains sensitive word
            key_lower = str(key).lower()
            is_sensitive = any(sensitive in key_lower for sensitive in SENSITIVE_KEYS)
            
            if is_sensitive:
                sanitized[key] = '<REDACTED>'
            else:
                sanitized[key] = _sanitize_for_logging(value)
        return sanitized
    elif isinstance(data, list):
        return [_sanitize_for_logging(item) for item in data]
    else:
        return data


def _get_log_dir(preferred_dir: Optional[str] = None) -> str:
    """
    Get log directory with fallback logic.
    
    Priority:
    1. Provided preferred_dir
    2. LOG_DIR environment variable
    3. Current working directory /logs
    
    Returns:
        Valid log directory path
    """
    # Try preferred dir first
    if preferred_dir:
        try:
            os.makedirs(preferred_dir, exist_ok=True)
            return preferred_dir
        except (PermissionError, OSError):
            pass  # Fall through to next option
    
    # Try environment variable
    env_dir = os.getenv('LOG_DIR')
    if env_dir:
        try:
            os.makedirs(env_dir, exist_ok=True)
            return env_dir
        except (PermissionError, OSError):
            pass  # Fall through
    
    # Fallback to current working directory
    fallback_dir = os.path.join(os.getcwd(), 'logs')
    os.makedirs(fallback_dir, exist_ok=True)
    return fallback_dir


def setup_logger(name: str, log_dir: Optional[str] = None) -> logging.Logger:
    """
    Setup logger with file and console handlers.
    Prevents duplicate handlers on repeated calls.
    
    Args:
        name: Logger name (usually module name)
        log_dir: Preferred directory for log files (optional)
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    
    # Check if handlers already exist to prevent duplicates
    if logger.handlers:
        return logger
    
    # Get valid log directory
    resolved_log_dir = _get_log_dir(log_dir)
    
    # File handler
    log_file = os.path.join(resolved_log_dir, f"{name}_{datetime.now().strftime('%Y%m%d')}.log")
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.INFO)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    
    # Formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    # Add handlers
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger


class APILogger:
    """Logger specifically for API calls with error tracking."""
    
    def __init__(self, service_name: str):
        self.service_name = service_name
        self.logger = setup_logger(f"api_{service_name}")
        self.error_count = 0
        
    def log_request(self, endpoint: str, params: Optional[Dict[str, Any]] = None):
        """Log API request with sanitized params."""
        safe_params = _sanitize_for_logging(params) if params else None
        self.logger.info(f"API Request: {endpoint} | Params: {safe_params}")
        
    def log_response(self, endpoint: str, status_code: int, response_time: float):
        """Log API response."""
        self.logger.info(
            f"API Response: {endpoint} | Status: {status_code} | Time: {response_time:.2f}s"
        )
        
    def log_error(self, endpoint: str, error: Exception, context: Optional[Dict[str, Any]] = None):
        """Log API error with sanitized context."""
        self.error_count += 1
        safe_context = _sanitize_for_logging(context) if context else None
        self.logger.error(
            f"API Error: {endpoint} | Error: {str(error)} | Context: {safe_context}"
        )
        
    def get_stats(self) -> Dict[str, Any]:
        """Get logger statistics."""
        return {
            "service": self.service_name,
            "error_count": self.error_count
        }