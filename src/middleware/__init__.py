"""Middleware package for Web Terminal application."""

from src.middleware.auth import (
    AuthenticationMiddleware,
    RequireAuth,
    OptionalAuth,
    require_auth,
    optional_auth,
    JWTHandler,
    PasswordHasher,
)
from src.middleware.logging import (
    RequestLoggingMiddleware,
    StructuredLogger,
    PerformanceLogger,
    setup_logging,
)
from src.middleware.security import (
    SecurityValidationMiddleware,
    FileValidator,
    SecurityConfig,
    default_validator,
    strict_validator,
    permissive_validator,
    validate_file_upload,
)

__all__ = [
    "AuthenticationMiddleware",
    "RequireAuth",
    "OptionalAuth",
    "require_auth",
    "optional_auth",
    "JWTHandler",
    "PasswordHasher",
    "RequestLoggingMiddleware",
    "StructuredLogger",
    "PerformanceLogger",
    "setup_logging",
    "SecurityValidationMiddleware",
    "FileValidator",
    "SecurityConfig",
    "default_validator",
    "strict_validator",
    "permissive_validator",
    "validate_file_upload",
]
