import logging
import os
import sys
from pathlib import Path
from datetime import datetime

from .paths import ROOT_DIR

# Paths
LOG_DIR = ROOT_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)

# Log Levels
LEVEL_MAP = {
    "Debug (All)": logging.DEBUG,
    "Info (Standard)": logging.INFO,
    "Errors Only": logging.ERROR,
    "Disabled": 100
}

def setup_logger(log_level_str="Debug (All)", file_prefix="debug"):
    """
    Sets up the global logger based on the provided string level.
    """
    level = LEVEL_MAP.get(log_level_str, logging.DEBUG)
    
    # Create logger
    logger = logging.getLogger("ContextUp")
    logger.setLevel(logging.DEBUG) # Capture all, handlers will filter
    
    # Clear existing handlers
    if logger.hasHandlers():
        logger.handlers.clear()
        
    # Formatter
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    
    # File Handler (Daily Log)
    if level < 100:
        try:
            date_str = datetime.now().strftime("%Y-%m-%d")
            log_file = LOG_DIR / f"{file_prefix}_{date_str}.log"
            
            file_handler = logging.FileHandler(log_file, encoding='utf-8')
            file_handler.setLevel(level)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        except Exception as e:
            print(f"Failed to setup file logging: {e}")

    # Console Handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO) # Keep console clean
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    return logger

# Global instance
logger = setup_logger()

def log_execution(tool_name, args=None):
    """Helper to log tool execution start."""
    msg = f"Executing: {tool_name}"
    if args:
        msg += f" | Args: {args}"
    logger.info(msg)

def log_error(tool_name, error):
    """Helper to log errors."""
    logger.error(f"Error in {tool_name}: {error}", exc_info=True)
