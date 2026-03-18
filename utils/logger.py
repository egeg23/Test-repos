# utils/logger.py - Helper functions for logging
import logging
import os
from datetime import datetime

def setup_logger(name: str, log_dir: str = "/opt/clients/logs") -> logging.Logger:
    """
    Setup logger with file and console handlers.
    
    Args:
        name: Logger name (usually module name)
        log_dir: Directory for log files
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    
    # Create logs directory if not exists
    os.makedirs(log_dir, exist_ok=True)
    
    # File handler
    log_file = os.path.join(log_dir, f"{name}_{datetime.now().strftime('%Y%m%d')}.log")
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
        
    def log_request(self, endpoint: str, params: dict = None):
        """Log API request."""
        self.logger.info(f"API Request: {endpoint} | Params: {params}")
        
    def log_response(self, endpoint: str, status_code: int, response_time: float):
        """Log API response."""
        self.logger.info(
            f"API Response: {endpoint} | Status: {status_code} | Time: {response_time:.2f}s"
        )
        
    def log_error(self, endpoint: str, error: Exception, context: dict = None):
        """Log API error with context."""
        self.error_count += 1
        self.logger.error(
            f"API Error: {endpoint} | Error: {str(error)} | Context: {context}"
        )
        
    def get_stats(self) -> dict:
        """Get logger statistics."""
        return {
            "service": self.service_name,
            "error_count": self.error_count
        }