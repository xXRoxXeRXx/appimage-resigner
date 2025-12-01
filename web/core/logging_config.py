"""
Logging configuration for AppImage Re-Signer.
Provides structured logging with rotation and multiple handlers.
"""

import logging
import logging.handlers
import sys
from pathlib import Path
from typing import Optional

# Log directory
LOG_DIR = Path(__file__).parent.parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)

# Log file path
LOG_FILE = LOG_DIR / "appimage-resigner.log"

# Log format
LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(funcName)s:%(lineno)d | %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# Log levels
LOG_LEVEL = logging.INFO


def setup_logging(
    log_level: Optional[str] = None,
    log_to_file: bool = True,
    log_to_console: bool = True
) -> logging.Logger:
    """
    Set up logging configuration for the application.
    
    Args:
        log_level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_to_file: Whether to log to file
        log_to_console: Whether to log to console
        
    Returns:
        Configured root logger
    """
    # Determine log level
    if log_level:
        level = getattr(logging, log_level.upper(), LOG_LEVEL)
    else:
        level = LOG_LEVEL
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    # Remove existing handlers
    root_logger.handlers.clear()
    
    # Create formatter
    formatter = logging.Formatter(LOG_FORMAT, LOG_DATE_FORMAT)
    
    # Console handler
    if log_to_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)
    
    # File handler with rotation
    if log_to_file:
        try:
            # Ensure log directory exists and is writable
            log_dir = Path(LOG_FILE).parent
            log_dir.mkdir(parents=True, exist_ok=True)
            
            # Rotate log files: max 10 files, 10 MB each
            file_handler = logging.handlers.RotatingFileHandler(
                LOG_FILE,
                maxBytes=10 * 1024 * 1024,  # 10 MB
                backupCount=10,
                encoding='utf-8'
            )
            file_handler.setLevel(level)
            file_handler.setFormatter(formatter)
            root_logger.addHandler(file_handler)
        except (PermissionError, OSError) as e:
            # Log to console if file logging fails
            warning_msg = f"WARNING: Could not create log file {LOG_FILE}: {e}"
            if log_to_console:
                root_logger.warning(warning_msg)
                root_logger.warning("Continuing with console logging only")
            else:
                # Enable console logging as fallback
                console_handler = logging.StreamHandler(sys.stdout)
                console_handler.setLevel(level)
                console_handler.setFormatter(formatter)
                root_logger.addHandler(console_handler)
                root_logger.warning(warning_msg)
                root_logger.warning("Enabled console logging as fallback")
    
    # Log startup message
    root_logger.info("=" * 80)
    root_logger.info("AppImage Re-Signer - Logging initialized")
    root_logger.info(f"Log level: {logging.getLevelName(level)}")
    if log_to_file:
        root_logger.info(f"Log file: {LOG_FILE}")
    else:
        root_logger.info("File logging: Disabled")
    root_logger.info("=" * 80)
    
    return root_logger


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for a specific module.
    
    Args:
        name: Logger name (usually __name__)
        
    Returns:
        Logger instance
    """
    return logging.getLogger(name)


# Convenience function for structured logging
def log_operation(
    logger: logging.Logger,
    operation: str,
    status: str,
    **kwargs
) -> None:
    """
    Log an operation with structured data.
    
    Args:
        logger: Logger instance
        operation: Operation name (e.g., "sign_appimage", "verify_signature")
        status: Operation status (e.g., "started", "completed", "failed")
        **kwargs: Additional context (session_id, filename, error, etc.)
    """
    context = " | ".join(f"{k}={v}" for k, v in kwargs.items())
    message = f"{operation} | {status}"
    if context:
        message += f" | {context}"
    
    if status == "failed":
        logger.error(message)
    elif status == "started":
        logger.info(message)
    elif status == "completed":
        logger.info(message)
    else:
        logger.debug(message)
