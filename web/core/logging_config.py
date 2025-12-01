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


# ============================================================================
# Audit Logging Functions
# ============================================================================

def log_audit_event(
    logger: logging.Logger,
    event_type: str,
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    details: Optional[dict] = None,
) -> None:
    """
    Log an audit event for compliance and security monitoring.
    
    This function creates structured audit logs that can be used for:
    - Security incident response
    - Compliance reporting (ISO 27001, SOC 2, etc.)
    - User activity tracking
    - Forensic analysis
    
    Args:
        logger: Logger instance
        event_type: Type of event (e.g., "sign_appimage", "import_key", "delete_key")
        user_id: User identifier (if authentication is enabled)
        session_id: Session identifier
        ip_address: Client IP address
        user_agent: Client User-Agent string
        details: Additional event details (filename, key_id, error, etc.)
    """
    # Build audit message
    parts = [f"AUDIT: {event_type}"]
    
    if session_id:
        parts.append(f"session={session_id}")
    
    if user_id:
        parts.append(f"user={user_id}")
    
    if ip_address:
        parts.append(f"ip={ip_address}")
    
    if user_agent:
        # Truncate user agent to prevent log bloat
        ua_short = user_agent[:100] + "..." if len(user_agent) > 100 else user_agent
        parts.append(f"user_agent={ua_short}")
    
    if details:
        details_str = " ".join(f"{k}={v}" for k, v in details.items())
        parts.append(details_str)
    
    message = " | ".join(parts)
    
    # Always log audit events at INFO level (or higher)
    logger.info(message)


def log_security_event(
    logger: logging.Logger,
    event_type: str,
    severity: str = "info",
    ip_address: Optional[str] = None,
    details: Optional[dict] = None,
) -> None:
    """
    Log a security-related event for monitoring and alerting.
    
    Use this for events that may indicate security issues:
    - Failed authentication attempts
    - Rate limiting triggered
    - Invalid input detected
    - Suspicious activity
    
    Args:
        logger: Logger instance
        event_type: Type of security event
        severity: Severity level (info, warning, error, critical)
        ip_address: Client IP address
        details: Additional event details
    """
    parts = [f"SECURITY: {event_type}"]
    
    if ip_address:
        parts.append(f"ip={ip_address}")
    
    if details:
        details_str = " ".join(f"{k}={v}" for k, v in details.items())
        parts.append(details_str)
    
    message = " | ".join(parts)
    
    # Log at appropriate level based on severity
    if severity == "critical":
        logger.critical(message)
    elif severity == "error":
        logger.error(message)
    elif severity == "warning":
        logger.warning(message)
    else:
        logger.info(message)


def log_file_operation(
    logger: logging.Logger,
    operation: str,
    file_path: str,
    session_id: Optional[str] = None,
    success: bool = True,
    error: Optional[str] = None,
) -> None:
    """
    Log file operations for audit trail.
    
    Args:
        logger: Logger instance
        operation: Operation type (upload, sign, download, delete)
        file_path: Path to file (will be sanitized)
        session_id: Session identifier
        success: Whether operation succeeded
        error: Error message if failed
    """
    from pathlib import Path
    
    # Sanitize file path (only log filename, not full path)
    filename = Path(file_path).name
    
    parts = [f"FILE: {operation}"]
    parts.append(f"file={filename}")
    
    if session_id:
        parts.append(f"session={session_id}")
    
    if success:
        parts.append("status=success")
    else:
        parts.append("status=failed")
        if error:
            # Sanitize error message
            error_safe = error.replace('\n', ' ').replace('\r', ' ')[:200]
            parts.append(f"error={error_safe}")
    
    message = " | ".join(parts)
    
    if success:
        logger.info(message)
    else:
        logger.error(message)
