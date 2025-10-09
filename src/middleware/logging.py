"""Request/response logging middleware.

This middleware provides comprehensive logging of HTTP requests and responses,
including timing, status codes, error tracking, and structured logging.
"""

import json
import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Callable, Optional, Dict, Any

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import Message

logger = logging.getLogger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for logging HTTP requests and responses.

    This middleware logs:
    - Request method, path, headers, query parameters
    - Response status code, headers, timing
    - Request/response bodies (configurable)
    - User information (if authenticated)
    - Errors and exceptions
    """

    def __init__(
        self,
        app,
        *,
        log_request_body: bool = False,
        log_response_body: bool = False,
        log_headers: bool = True,
        max_body_length: int = 1000,
        exclude_paths: Optional[list] = None,
    ):
        """Initialize logging middleware.

        Args:
            app: FastAPI application
            log_request_body: Whether to log request bodies
            log_response_body: Whether to log response bodies
            log_headers: Whether to log headers
            max_body_length: Maximum body length to log (bytes)
            exclude_paths: List of paths to exclude from logging
        """
        super().__init__(app)
        self.log_request_body = log_request_body
        self.log_response_body = log_response_body
        self.log_headers = log_headers
        self.max_body_length = max_body_length
        self.exclude_paths = exclude_paths or ["/health", "/metrics"]

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and log details.

        Args:
            request: Incoming HTTP request
            call_next: Next middleware/handler in chain

        Returns:
            Response from next handler
        """
        # Generate request ID
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id

        # Check if path should be excluded
        if self._should_exclude(request.url.path):
            return await call_next(request)

        # Start timing
        start_time = time.time()

        # Log request
        await self._log_request(request, request_id)

        # Process request and capture response
        try:
            response = await call_next(request)

            # Calculate processing time
            process_time = time.time() - start_time

            # Add custom headers
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Process-Time"] = str(process_time)

            # Log response
            await self._log_response(
                request,
                response,
                request_id,
                process_time,
                status_code=response.status_code
            )

            return response

        except Exception as e:
            # Calculate processing time
            process_time = time.time() - start_time

            # Log error
            await self._log_error(request, e, request_id, process_time)

            # Re-raise exception
            raise

    async def _log_request(self, request: Request, request_id: str) -> None:
        """Log incoming request details.

        Args:
            request: HTTP request
            request_id: Unique request identifier
        """
        log_data = {
            "event": "http_request",
            "request_id": request_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "method": request.method,
            "url": str(request.url),
            "path": request.url.path,
            "query_params": dict(request.query_params),
            "client_ip": self._get_client_ip(request),
            "user_agent": request.headers.get("user-agent"),
        }

        # Add user info if authenticated
        if hasattr(request.state, "user") and request.state.user:
            log_data["user_id"] = str(request.state.user.user_id)
            log_data["username"] = request.state.user.username

        # Add headers if enabled
        if self.log_headers:
            # Filter sensitive headers
            log_data["headers"] = self._filter_headers(dict(request.headers))

        # Add request body if enabled
        if self.log_request_body and request.method in ["POST", "PUT", "PATCH"]:
            try:
                body = await self._get_request_body(request)
                if body:
                    log_data["request_body"] = body
            except Exception as e:
                logger.warning(f"Failed to read request body: {e}")

        # Log at INFO level
        logger.info(json.dumps(log_data))

    async def _log_response(
        self,
        request: Request,
        response: Response,
        request_id: str,
        process_time: float,
        status_code: int
    ) -> None:
        """Log response details.

        Args:
            request: HTTP request
            response: HTTP response
            request_id: Unique request identifier
            process_time: Time taken to process request (seconds)
            status_code: HTTP status code
        """
        log_data = {
            "event": "http_response",
            "request_id": request_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "method": request.method,
            "path": request.url.path,
            "status_code": status_code,
            "process_time": round(process_time, 4),
            "process_time_ms": round(process_time * 1000, 2),
        }

        # Add headers if enabled
        if self.log_headers:
            log_data["response_headers"] = dict(response.headers)

        # Determine log level based on status code
        if status_code >= 500:
            log_level = logging.ERROR
        elif status_code >= 400:
            log_level = logging.WARNING
        else:
            log_level = logging.INFO

        # Log response
        logger.log(log_level, json.dumps(log_data))

    async def _log_error(
        self,
        request: Request,
        error: Exception,
        request_id: str,
        process_time: float
    ) -> None:
        """Log error details.

        Args:
            request: HTTP request
            error: Exception that occurred
            request_id: Unique request identifier
            process_time: Time taken before error (seconds)
        """
        log_data = {
            "event": "http_error",
            "request_id": request_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "method": request.method,
            "path": request.url.path,
            "error_type": type(error).__name__,
            "error_message": str(error),
            "process_time": round(process_time, 4),
        }

        # Add user info if authenticated
        if hasattr(request.state, "user") and request.state.user:
            log_data["user_id"] = str(request.state.user.user_id)

        # Log at ERROR level
        logger.error(json.dumps(log_data), exc_info=True)

    async def _get_request_body(self, request: Request) -> Optional[str]:
        """Get request body for logging.

        Args:
            request: HTTP request

        Returns:
            Request body as string, or None if unavailable
        """
        try:
            # Read body
            body = await request.body()

            # Truncate if too long
            if len(body) > self.max_body_length:
                body = body[:self.max_body_length] + b"... (truncated)"

            # Try to decode as JSON for better formatting
            try:
                body_json = json.loads(body)
                return json.dumps(body_json)
            except (json.JSONDecodeError, UnicodeDecodeError):
                # Return as string if not JSON
                return body.decode("utf-8", errors="replace")

        except Exception:
            return None

    def _filter_headers(self, headers: Dict[str, str]) -> Dict[str, str]:
        """Filter sensitive headers for logging.

        Args:
            headers: Request/response headers

        Returns:
            Filtered headers dictionary
        """
        # Headers to mask
        sensitive_headers = {
            "authorization",
            "x-api-key",
            "cookie",
            "set-cookie",
            "x-csrf-token",
        }

        filtered = {}
        for key, value in headers.items():
            key_lower = key.lower()
            if key_lower in sensitive_headers:
                filtered[key] = "***REDACTED***"
            else:
                filtered[key] = value

        return filtered

    def _get_client_ip(self, request: Request) -> str:
        """Get client IP address from request.

        Args:
            request: HTTP request

        Returns:
            Client IP address
        """
        # Check for forwarded headers (when behind proxy)
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            # X-Forwarded-For can contain multiple IPs, get the first one
            return forwarded_for.split(",")[0].strip()

        # Check for real IP header
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip

        # Fall back to client host
        if request.client:
            return request.client.host

        return "unknown"

    def _should_exclude(self, path: str) -> bool:
        """Check if path should be excluded from logging.

        Args:
            path: Request path

        Returns:
            True if path should be excluded, False otherwise
        """
        for exclude_path in self.exclude_paths:
            if path.startswith(exclude_path):
                return True
        return False


class StructuredLogger:
    """Structured logging helper for application-wide logging.

    This class provides methods for logging structured data in JSON format,
    making it easier to parse and analyze logs.
    """

    def __init__(self, name: str):
        """Initialize structured logger.

        Args:
            name: Logger name (usually __name__)
        """
        self.logger = logging.getLogger(name)

    def log(
        self,
        level: int,
        message: str,
        **kwargs: Any
    ) -> None:
        """Log a structured message.

        Args:
            level: Log level (logging.INFO, logging.ERROR, etc.)
            message: Log message
            **kwargs: Additional structured data
        """
        log_data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "message": message,
            **kwargs
        }

        self.logger.log(level, json.dumps(log_data))

    def info(self, message: str, **kwargs: Any) -> None:
        """Log info level message."""
        self.log(logging.INFO, message, **kwargs)

    def warning(self, message: str, **kwargs: Any) -> None:
        """Log warning level message."""
        self.log(logging.WARNING, message, **kwargs)

    def error(self, message: str, **kwargs: Any) -> None:
        """Log error level message."""
        self.log(logging.ERROR, message, **kwargs)

    def debug(self, message: str, **kwargs: Any) -> None:
        """Log debug level message."""
        self.log(logging.DEBUG, message, **kwargs)

    def critical(self, message: str, **kwargs: Any) -> None:
        """Log critical level message."""
        self.log(logging.CRITICAL, message, **kwargs)


def setup_logging(
    log_level: str = "INFO",
    log_format: str = "json",
    log_file: Optional[str] = None
) -> None:
    """Setup application-wide logging configuration.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_format: Log format ("json" or "text")
        log_file: Optional log file path
    """
    # Convert log level string to constant
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)

    # Create formatter
    if log_format == "json":
        formatter = logging.Formatter(
            '%(message)s'  # Messages are already JSON formatted
        )
    else:
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)

    # Remove existing handlers
    root_logger.handlers.clear()

    # Add console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(numeric_level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # Add file handler if specified
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(numeric_level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

    # Log startup message
    logger.info(
        json.dumps({
            "event": "logging_configured",
            "log_level": log_level,
            "log_format": log_format,
            "log_file": log_file
        })
    )


class PerformanceLogger:
    """Context manager for logging performance metrics.

    Usage:
        async with PerformanceLogger("operation_name") as perf:
            # Do work
            perf.add_metric("items_processed", 100)
    """

    def __init__(
        self,
        operation: str,
        logger_name: Optional[str] = None,
        log_level: int = logging.INFO
    ):
        """Initialize performance logger.

        Args:
            operation: Operation name
            logger_name: Logger name (defaults to __name__)
            log_level: Log level for performance logs
        """
        self.operation = operation
        self.logger = logging.getLogger(logger_name or __name__)
        self.log_level = log_level
        self.start_time = None
        self.metrics = {}

    def add_metric(self, name: str, value: Any) -> None:
        """Add a custom metric.

        Args:
            name: Metric name
            value: Metric value
        """
        self.metrics[name] = value

    async def __aenter__(self):
        """Start performance tracking."""
        self.start_time = time.time()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Log performance metrics."""
        duration = time.time() - self.start_time

        log_data = {
            "event": "performance_metric",
            "operation": self.operation,
            "duration": round(duration, 4),
            "duration_ms": round(duration * 1000, 2),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **self.metrics
        }

        if exc_type:
            log_data["error"] = str(exc_val)
            log_data["error_type"] = exc_type.__name__

        self.logger.log(self.log_level, json.dumps(log_data))


# Create default structured logger instance
default_logger = StructuredLogger(__name__)
