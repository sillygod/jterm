"""JWT verification REST API endpoints.

This module provides HTTP endpoints for jwtcat functionality including:
- JWT signature verification with various algorithms
- Support for HMAC (HS256, HS384, HS512) and RSA (RS256, RS384, RS512) signatures
- Secret/key encoding support (UTF-8, Base64, Hex)

JWT decoding is performed entirely on the frontend for performance.
"""

import jwt
import base64
from typing import Optional, Literal
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

# Initialize router
router = APIRouter(prefix="/api/jwt", tags=["JWT"])


# Pydantic models for request/response validation
class VerifyJWTRequest(BaseModel):
    """Request model for JWT signature verification."""
    token: str = Field(..., description="JWT token to verify")
    secret: str = Field(..., description="Secret key or public key for verification")
    encoding: Literal['utf8', 'base64', 'hex'] = Field(
        'utf8',
        description="Encoding of the secret (utf8, base64, or hex)"
    )
    algorithms: Optional[list[str]] = Field(
        None,
        description="List of allowed algorithms (default: auto-detect from token header)"
    )


class VerifyJWTResponse(BaseModel):
    """Response model for JWT verification."""
    verified: bool
    algorithm: Optional[str] = None
    error: Optional[str] = None


@router.post("/verify", response_model=VerifyJWTResponse)
async def verify_jwt(request: VerifyJWTRequest):
    """Verify JWT signature using the provided secret.

    Args:
        request: VerifyJWTRequest with token, secret, and optional parameters

    Returns:
        VerifyJWTResponse with verification status and algorithm used

    Raises:
        HTTPException: If verification fails or token is invalid
    """
    try:
        # Decode secret based on encoding
        secret_bytes = decode_secret(request.secret, request.encoding)

        # If algorithms not specified, try to detect from token header
        algorithms = request.algorithms
        if not algorithms:
            # Decode header to get algorithm (without verification)
            try:
                header = jwt.get_unverified_header(request.token)
                alg = header.get('alg')
                if alg:
                    algorithms = [alg]
                else:
                    # Default to common HMAC algorithms
                    algorithms = ['HS256', 'HS384', 'HS512']
            except Exception:
                # If header decode fails, try common algorithms
                algorithms = ['HS256', 'HS384', 'HS512', 'RS256', 'RS384', 'RS512']

        # Try to verify with each algorithm
        for alg in algorithms:
            try:
                # Verify signature
                jwt.decode(
                    request.token,
                    secret_bytes,
                    algorithms=[alg],
                    options={
                        "verify_signature": True,
                        "verify_exp": False,  # Don't verify expiration
                        "verify_nbf": False,  # Don't verify not-before
                        "verify_iat": False,  # Don't verify issued-at
                        "verify_aud": False,  # Don't verify audience
                    }
                )

                # If we get here, verification succeeded
                return VerifyJWTResponse(
                    verified=True,
                    algorithm=alg,
                    error=None
                )

            except jwt.InvalidSignatureError:
                # Wrong algorithm or secret, try next one
                continue
            except jwt.DecodeError as e:
                # Token format error
                return VerifyJWTResponse(
                    verified=False,
                    algorithm=None,
                    error=f"Invalid token format: {str(e)}"
                )
            except Exception as e:
                # Other error, continue trying
                continue

        # If we get here, none of the algorithms worked
        return VerifyJWTResponse(
            verified=False,
            algorithm=None,
            error="Invalid signature or secret"
        )

    except Exception as e:
        # Unexpected error
        return VerifyJWTResponse(
            verified=False,
            algorithm=None,
            error=f"Verification error: {str(e)}"
        )


def decode_secret(secret: str, encoding: str) -> bytes:
    """Decode secret from string to bytes based on encoding.

    Args:
        secret: Secret string
        encoding: Encoding format (utf8, base64, hex)

    Returns:
        Secret as bytes

    Raises:
        ValueError: If encoding is invalid or decoding fails
    """
    if encoding == 'utf8':
        return secret.encode('utf-8')
    elif encoding == 'base64':
        try:
            return base64.b64decode(secret)
        except Exception as e:
            raise ValueError(f"Invalid base64 encoding: {str(e)}")
    elif encoding == 'hex':
        try:
            return bytes.fromhex(secret)
        except Exception as e:
            raise ValueError(f"Invalid hex encoding: {str(e)}")
    else:
        raise ValueError(f"Unsupported encoding: {encoding}")
