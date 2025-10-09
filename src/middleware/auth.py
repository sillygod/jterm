"""Authentication middleware for session security.

This middleware handles JWT-based authentication, session validation,
and API key authentication for the web terminal application.
"""

import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from uuid import UUID

from fastapi import HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from starlette.middleware.base import BaseHTTPMiddleware

from src.models.user_profile import UserProfile
from src.database.base import AsyncSessionLocal

logger = logging.getLogger(__name__)

# Security configuration
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours
REFRESH_TOKEN_EXPIRE_DAYS = 30

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# HTTP Bearer token scheme
security = HTTPBearer(auto_error=False)


class TokenData:
    """Token payload data structure."""

    def __init__(
        self,
        user_id: UUID,
        username: str,
        exp: Optional[datetime] = None,
        iat: Optional[datetime] = None,
        token_type: str = "access"
    ):
        self.user_id = user_id
        self.username = username
        self.exp = exp
        self.iat = iat
        self.token_type = token_type


class AuthenticationError(Exception):
    """Custom authentication exception."""
    pass


class PasswordHasher:
    """Password hashing utilities."""

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify a password against a hash.

        Args:
            plain_password: Plain text password
            hashed_password: Hashed password to verify against

        Returns:
            True if password matches, False otherwise
        """
        return pwd_context.verify(plain_password, hashed_password)

    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a password.

        Args:
            password: Plain text password

        Returns:
            Hashed password
        """
        return pwd_context.hash(password)


class JWTHandler:
    """JWT token handling utilities."""

    @staticmethod
    def create_access_token(
        data: Dict[str, Any],
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """Create a JWT access token.

        Args:
            data: Payload data to encode
            expires_delta: Optional expiration time delta

        Returns:
            Encoded JWT token
        """
        to_encode = data.copy()

        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

        to_encode.update({
            "exp": expire,
            "iat": datetime.now(timezone.utc),
            "token_type": "access"
        })

        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt

    @staticmethod
    def create_refresh_token(data: Dict[str, Any]) -> str:
        """Create a JWT refresh token.

        Args:
            data: Payload data to encode

        Returns:
            Encoded JWT refresh token
        """
        to_encode = data.copy()
        expire = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)

        to_encode.update({
            "exp": expire,
            "iat": datetime.now(timezone.utc),
            "token_type": "refresh"
        })

        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt

    @staticmethod
    def decode_token(token: str) -> TokenData:
        """Decode and validate a JWT token.

        Args:
            token: JWT token to decode

        Returns:
            TokenData object with decoded payload

        Raises:
            AuthenticationError: If token is invalid or expired
        """
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

            user_id: str = payload.get("sub")
            username: str = payload.get("username")
            token_type: str = payload.get("token_type", "access")

            if user_id is None:
                raise AuthenticationError("Invalid token payload")

            return TokenData(
                user_id=UUID(user_id),
                username=username,
                exp=datetime.fromtimestamp(payload.get("exp"), tz=timezone.utc),
                iat=datetime.fromtimestamp(payload.get("iat"), tz=timezone.utc),
                token_type=token_type
            )
        except JWTError as e:
            logger.error(f"JWT decode error: {e}")
            raise AuthenticationError("Could not validate credentials")

    @staticmethod
    def refresh_access_token(refresh_token: str) -> str:
        """Create a new access token from a refresh token.

        Args:
            refresh_token: Valid refresh token

        Returns:
            New access token

        Raises:
            AuthenticationError: If refresh token is invalid
        """
        token_data = JWTHandler.decode_token(refresh_token)

        if token_data.token_type != "refresh":
            raise AuthenticationError("Invalid token type")

        # Create new access token
        access_token = JWTHandler.create_access_token(
            data={
                "sub": str(token_data.user_id),
                "username": token_data.username
            }
        )

        return access_token


async def get_current_user(
    credentials: HTTPAuthorizationCredentials,
    db: AsyncSession
) -> UserProfile:
    """Get current authenticated user from JWT token.

    Args:
        credentials: HTTP bearer token credentials
        db: Database session

    Returns:
        UserProfile object for authenticated user

    Raises:
        HTTPException: If authentication fails
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        token_data = JWTHandler.decode_token(credentials.credentials)
    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Get user from database
    query = select(UserProfile).where(UserProfile.user_id == token_data.user_id)
    result = await db.execute(query)
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


async def verify_api_key(api_key: str, db: AsyncSession) -> Optional[UserProfile]:
    """Verify an API key and return the associated user.

    Args:
        api_key: API key to verify
        db: Database session

    Returns:
        UserProfile if valid, None otherwise
    """
    # Query for user with this API key
    # Note: In production, API keys should be hashed and stored securely
    query = select(UserProfile).where(UserProfile.api_key == api_key)
    result = await db.execute(query)
    user = result.scalar_one_or_none()

    if user and user.api_key_enabled:
        return user

    return None


class AuthenticationMiddleware(BaseHTTPMiddleware):
    """Middleware for handling authentication across all requests.

    This middleware checks for JWT tokens or API keys and validates them.
    Public endpoints are excluded from authentication requirements.
    """

    # Public endpoints that don't require authentication
    PUBLIC_ENDPOINTS = {
        "/",
        "/health",
        "/docs",
        "/openapi.json",
        "/redoc",
        "/static",
        "/api/v1/auth/login",
        "/api/v1/auth/register",
        "/api/v1/auth/refresh",
        "/ws",  # WebSocket endpoints
    }

    async def dispatch(self, request: Request, call_next):
        """Process request and validate authentication.

        Args:
            request: Incoming HTTP request
            call_next: Next middleware/handler in chain

        Returns:
            Response from next handler

        Raises:
            HTTPException: If authentication is required but fails
        """
        # Check if endpoint is public
        path = request.url.path
        if self._is_public_endpoint(path):
            return await call_next(request)

        # Try to get authentication from headers
        user = None
        auth_header = request.headers.get("authorization")
        api_key = request.headers.get("x-api-key")

        async with AsyncSessionLocal() as db:
            try:
                # Try JWT authentication first
                if auth_header and auth_header.startswith("Bearer "):
                    token = auth_header.split(" ")[1]
                    try:
                        token_data = JWTHandler.decode_token(token)

                        # Get user from database
                        query = select(UserProfile).where(UserProfile.user_id == token_data.user_id)
                        result = await db.execute(query)
                        user = result.scalar_one_or_none()

                    except AuthenticationError as e:
                        logger.warning(f"JWT authentication failed: {e}")

                # Try API key authentication if JWT failed
                if not user and api_key:
                    user = await verify_api_key(api_key, db)

                # If no authentication method succeeded, deny access
                if not user:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Authentication required",
                        headers={"WWW-Authenticate": "Bearer"},
                    )

                # Attach user to request state
                request.state.user = user

            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Authentication middleware error: {e}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Authentication error"
                )

        return await call_next(request)

    def _is_public_endpoint(self, path: str) -> bool:
        """Check if an endpoint is public.

        Args:
            path: Request path

        Returns:
            True if endpoint is public, False otherwise
        """
        # Check exact matches
        if path in self.PUBLIC_ENDPOINTS:
            return True

        # Check prefix matches for static files
        for public_path in self.PUBLIC_ENDPOINTS:
            if path.startswith(public_path):
                return True

        return False


class RequireAuth:
    """Dependency for requiring authentication on specific routes.

    Usage:
        @app.get("/protected")
        async def protected_route(user: UserProfile = Depends(RequireAuth())):
            return {"user": user.username}
    """

    async def __call__(
        self,
        request: Request,
        credentials: HTTPAuthorizationCredentials = security
    ) -> UserProfile:
        """Get authenticated user from request.

        Args:
            request: HTTP request
            credentials: Bearer token credentials

        Returns:
            Authenticated user

        Raises:
            HTTPException: If authentication fails
        """
        # Check if user is already attached to request (from middleware)
        if hasattr(request.state, "user") and request.state.user:
            return request.state.user

        # Otherwise, validate credentials
        if not credentials:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated",
                headers={"WWW-Authenticate": "Bearer"},
            )

        async with AsyncSessionLocal() as db:
            user = await get_current_user(credentials, db)
            return user


class OptionalAuth:
    """Dependency for optional authentication on routes.

    Returns user if authenticated, None otherwise.

    Usage:
        @app.get("/optional")
        async def optional_route(user: Optional[UserProfile] = Depends(OptionalAuth())):
            if user:
                return {"message": f"Hello, {user.username}"}
            return {"message": "Hello, guest"}
    """

    async def __call__(
        self,
        request: Request,
        credentials: HTTPAuthorizationCredentials = security
    ) -> Optional[UserProfile]:
        """Get authenticated user from request if available.

        Args:
            request: HTTP request
            credentials: Bearer token credentials

        Returns:
            Authenticated user or None
        """
        # Check if user is already attached to request
        if hasattr(request.state, "user") and request.state.user:
            return request.state.user

        # Try to authenticate
        if credentials:
            try:
                async with AsyncSessionLocal() as db:
                    user = await get_current_user(credentials, db)
                    return user
            except HTTPException:
                pass

        return None


# Convenience instances for dependency injection
require_auth = RequireAuth()
optional_auth = OptionalAuth()
