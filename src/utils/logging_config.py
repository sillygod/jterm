"""Centralized logging configuration for jterm application.

T060: Comprehensive logging for debugging and monitoring
"""

import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler
from datetime import datetime


def setup_logging(
    log_level: str = "INFO",
    log_to_file: bool = True,
    log_dir: str = "logs",
    max_bytes: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5
):
    """Setup comprehensive logging configuration.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_to_file: Whether to log to file
        log_dir: Directory for log files
        max_bytes: Maximum size of each log file before rotation
        backup_count: Number of backup log files to keep
    """
    # Convert log level string to constant
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)

    # Create log directory if it doesn't exist
    if log_to_file:
        log_path = Path(log_dir)
        log_path.mkdir(exist_ok=True)

    # Define log format
    log_format = (
        '%(asctime)s - %(name)s - %(levelname)s - '
        '[%(filename)s:%(lineno)d] - %(message)s'
    )
    date_format = '%Y-%m-%d %H:%M:%S'

    # Create formatter
    formatter = logging.Formatter(log_format, date_format)

    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)

    # Remove existing handlers to avoid duplicates
    root_logger.handlers.clear()

    # Console handler (stdout)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # File handler with rotation (if enabled)
    if log_to_file:
        # Main application log
        app_log_file = log_path / f"jterm_{datetime.now().strftime('%Y%m%d')}.log"
        file_handler = RotatingFileHandler(
            app_log_file,
            maxBytes=max_bytes,
            backupCount=backup_count
        )
        file_handler.setLevel(numeric_level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

        # Error-only log file
        error_log_file = log_path / f"jterm_errors_{datetime.now().strftime('%Y%m%d')}.log"
        error_handler = RotatingFileHandler(
            error_log_file,
            maxBytes=max_bytes,
            backupCount=backup_count
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(formatter)
        root_logger.addHandler(error_handler)

    # Set third-party loggers to WARNING to reduce noise
    logging.getLogger('uvicorn').setLevel(logging.WARNING)
    logging.getLogger('fastapi').setLevel(logging.WARNING)
    logging.getLogger('aiosqlite').setLevel(logging.WARNING)

    logging.info(f"Logging configured: level={log_level}, file_logging={log_to_file}")


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance with the given name.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Logger instance
    """
    return logging.getLogger(name)


class LoggingContext:
    """Context manager for adding context to log messages."""

    def __init__(self, logger: logging.Logger, **context):
        """Initialize logging context.

        Args:
            logger: Logger instance
            **context: Context key-value pairs to add to log messages
        """
        self.logger = logger
        self.context = context
        self.old_factory = None

    def __enter__(self):
        """Enter context."""
        self.old_factory = logging.getLogRecordFactory()

        def record_factory(*args, **kwargs):
            record = self.old_factory(*args, **kwargs)
            for key, value in self.context.items():
                setattr(record, key, value)
            return record

        logging.setLogRecordFactory(record_factory)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context."""
        logging.setLogRecordFactory(self.old_factory)


def log_function_call(logger: logging.Logger):
    """Decorator to log function calls with arguments and return values.

    Args:
        logger: Logger instance to use

    Returns:
        Decorator function
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            func_name = func.__name__
            logger.debug(f"Calling {func_name} with args={args}, kwargs={kwargs}")
            try:
                result = func(*args, **kwargs)
                logger.debug(f"{func_name} returned: {result}")
                return result
            except Exception as e:
                logger.error(f"{func_name} raised {type(e).__name__}: {str(e)}")
                raise
        return wrapper
    return decorator
