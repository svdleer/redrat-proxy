import logging
from logging.handlers import RotatingFileHandler
from app.config import Config
import os

def setup_logger(name):
    logger = logging.getLogger(name)
    logger.setLevel(Config.LOG_LEVEL)
    
    # Create logs directory if not exists
    os.makedirs('logs', exist_ok=True)
    
    # File handler with rotation
    file_handler = RotatingFileHandler(
        'logs/redrat.log',
        maxBytes=1024*1024,
        backupCount=5
    )
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    ))
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter(
        '%(name)s - %(levelname)s - %(message)s'
    ))
    
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    return logger

logger = setup_logger('redrat')