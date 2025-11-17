"""
Authentication API Endpoints.

Handles user signup, signin, and signout via Supabase Auth.
"""

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field, EmailStr
from typing import Dict, Any, Optional
import logging

from ...auth.supabase_client import sign_up, sign_in, sign_out

logger = logging.getLogger(__name__)

router = APIRouter()


class SignUpRequest(BaseModel):
    """User signup request"""
    email: EmailStr = Field(..., description="User's email address")
    password: str = Field(..., min_length=6, description="Password (min 6 characters)")


class SignInRequest(BaseModel):
    """User signin request"""
    email: EmailStr = Field(..., description="User's email address")
    password: str = Field(..., description="Password")


class AuthResponse(BaseModel):
    """Authentication response"""
    success: bool
    user: Optional[Dict[str, Any]] = None
    session: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    message: Optional[str] = None


@router.post("/auth/signup", response_model=AuthResponse)
async def signup(request: SignUpRequest):
    """
    Register a new user with email and password.

    **Request Body:**
    - `email`: Valid email address
    - `password`: Password (minimum 6 characters)

    **Returns:**
    - `success`: Whether signup succeeded
    - `user`: User info (id, email) if successful
    - `session`: Auth session with access_token if successful
    - `error`: Error message if failed

    **Example:**
    ```json
    {
      "email": "user@example.com",
      "password": "securepassword123"
    }
    ```
    """
    try:
        result = sign_up(request.email, request.password)

        if not result["success"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.get("error", "Sign up failed")
            )

        return AuthResponse(**result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Signup error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Sign up failed: {str(e)}"
        )


@router.post("/auth/signin", response_model=AuthResponse)
async def signin(request: SignInRequest):
    """
    Sign in an existing user with email and password.

    **Request Body:**
    - `email`: User's email address
    - `password`: User's password

    **Returns:**
    - `success`: Whether signin succeeded
    - `user`: User info (id, email) if successful
    - `session`: Auth session with access_token and refresh_token if successful
    - `error`: Error message if failed

    **Example:**
    ```json
    {
      "email": "user@example.com",
      "password": "securepassword123"
    }
    ```

    **Note:** Save the `access_token` to use in subsequent API requests:
    ```
    Authorization: Bearer <access_token>
    ```
    """
    try:
        result = sign_in(request.email, request.password)

        if not result["success"]:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=result.get("error", "Invalid email or password")
            )

        return AuthResponse(**result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Signin error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Sign in failed: {str(e)}"
        )


@router.post("/auth/signout")
async def signout(authorization: str = None):
    """
    Sign out the current user (invalidate session).

    **Headers:**
    - `Authorization`: Bearer token (optional)

    **Returns:**
    - Success message
    """
    try:
        if authorization:
            # Extract token
            parts = authorization.split()
            if len(parts) == 2 and parts[0].lower() == "bearer":
                token = parts[1]
                sign_out(token)

        return {"success": True, "message": "Signed out successfully"}

    except Exception as e:
        logger.error(f"Signout error: {e}", exc_info=True)
        # Don't fail signout - just return success
        return {"success": True, "message": "Signed out successfully"}
