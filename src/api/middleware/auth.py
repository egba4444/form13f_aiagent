"""
Authentication Middleware for FastAPI.

Provides dependency injection for protected routes.
"""

from typing import Optional
from fastapi import Header, HTTPException, status
from ...auth.supabase_client import verify_token
import logging

logger = logging.getLogger(__name__)


async def get_current_user(authorization: str = Header(None)) -> str:
    """
    Dependency to get current authenticated user from JWT token.

    Used for protected routes that require authentication.

    Args:
        authorization: Authorization header with Bearer token

    Returns:
        User ID (UUID string)

    Raises:
        HTTPException: 401 if token is missing or invalid
    """
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Extract token from "Bearer <token>"
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header format. Use: Bearer <token>",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = parts[1]

    # Verify token
    user_info = verify_token(token)

    if not user_info:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user_info["id"]


async def get_optional_user(authorization: str = Header(None)) -> Optional[str]:
    """
    Dependency to optionally get current user from JWT token.

    Used for routes that work both with and without authentication.

    Args:
        authorization: Authorization header with Bearer token (optional)

    Returns:
        User ID (UUID string) if authenticated, None otherwise
    """
    if not authorization:
        return None

    # Extract token
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None

    token = parts[1]

    # Verify token (don't raise error if invalid)
    user_info = verify_token(token)

    return user_info["id"] if user_info else None
