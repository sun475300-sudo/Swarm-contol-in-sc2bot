# -*- coding: utf-8 -*-
"""
Centralized Logger Utility
"""

import logging
import sys
from pathlib import Path
from typing import Optional

# Singleton logger instance
_LOGGER_INITIALIZED = False

def setup_logger(
    name: str = "WickedZergBot",
    log_file: Optional[str] = "logs/bot.log",
    level: int = logging.INFO,
    log_to_console: bool = True
) -> logging.Logger:
    """
    Setup and return a standardized logger.
    
    Args:
        name: Logger name
        log_file: Path to log file (relative to bot root)
        level: Logging level (default: INFO)
        log_to_console: Whether to print to stdout
    """
    global _LOGGER_INITIALIZED
    
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Avoid duplicate handlers if setup is called multiple times
    if logger.handlers:
        return logger

    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S'
    )

    # File Handler
    if log_file:
        try:
            log_path = Path(log_file)
            log_path.parent.mkdir(parents=True, exist_ok=True)
            
            file_handler = logging.FileHandler(str(log_path), encoding='utf-8')
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        except Exception as e:
            print(f"[LOGGER_ERROR] Failed to setup file logging: {e}")

    # Console Handler
    if log_to_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    
    _LOGGER_INITIALIZED = True
    return logger

def get_logger(name: str = "WickedZergBot") -> logging.Logger:
    """Get the existing logger or create a default one."""
    if not logging.getLogger(name).handlers:
        return setup_logger(name)
    return logging.getLogger(name)
