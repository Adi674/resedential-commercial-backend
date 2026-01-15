# app/core/logging_config.py
import logging
import sys
from logging.handlers import RotatingFileHandler
import os

def setup_logging():
    """
    Configure application-wide logging with console and file handlers
    """
    
    # Create logs directory if it doesn't exist
    if not os.path.exists('logs'):
        os.makedirs('logs')
    
    # Configure root logger
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    
    # Remove existing handlers to avoid duplicates
    logger.handlers = []
    
    # ==========================================
    # 1. CONSOLE HANDLER (stdout)
    # ==========================================
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_format = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(console_format)
    
    # ==========================================
    # 2. FILE HANDLER (rotating log files)
    # ==========================================
    file_handler = RotatingFileHandler(
        'logs/app.log',
        maxBytes=10485760,  # 10MB per file
        backupCount=5        # Keep 5 backup files
    )
    file_handler.setLevel(logging.INFO)
    file_format = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(file_format)
    
    # ==========================================
    # 3. ERROR FILE HANDLER (only errors)
    # ==========================================
    error_file_handler = RotatingFileHandler(
        'logs/error.log',
        maxBytes=10485760,  # 10MB per file
        backupCount=5
    )
    error_file_handler.setLevel(logging.ERROR)
    error_file_handler.setFormatter(file_format)
    
    # Add all handlers to root logger
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    logger.addHandler(error_file_handler)
    
    # ==========================================
    # 4. REDUCE NOISE FROM THIRD-PARTY LIBRARIES
    # ==========================================
    logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)
    logging.getLogger('uvicorn.access').setLevel(logging.WARNING)
    logging.getLogger('uvicorn.error').setLevel(logging.INFO)
    
    logger.info("=" * 50)
    logger.info("Logging system initialized")
    logger.info("=" * 50)
    
    return logger