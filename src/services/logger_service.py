"""
Centralized logging service for the application.
"""
import logging
import os
from datetime import datetime
from typing import Optional


def setup_logging(log_file: Optional[str] = None, level: int = logging.INFO, enable_file_logging: bool = False) -> logging.Logger:
    """
    Setup centralized logging for the application.
    
    Args:
        log_file: Optional custom log file path
        level: Logging level (default: INFO)
        enable_file_logging: Whether to log to file (default: False)
    
    Returns:
        Configured logger instance
    """
    handlers = []
    handlers.append(logging.StreamHandler())  # Always print to console
    
    if enable_file_logging:
        if log_file is None:
            log_file = f'submarine_color_correction_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
        
        # Create logs directory if it doesn't exist
        log_dir = os.path.dirname(log_file) if os.path.dirname(log_file) else "logs"
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir)
        
        handlers.append(logging.FileHandler(log_file))
    
    # Configure logging
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=handlers,
        force=True  # Force reconfiguration if already configured
    )
    
    logger = logging.getLogger('submarine_color_correction')
    if enable_file_logging:
        logger.info(f"Logging initialized - Log file: {log_file}")
    else:
        logger.info("Logging initialized - Console only (file logging disabled)")
    
    return logger


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance for a specific module."""
    return logging.getLogger(f'submarine_color_correction.{name}')
