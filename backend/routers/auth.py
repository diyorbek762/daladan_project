"""
Daladan Platform — Auth Router
OAuth2 Password Flow endpoints: login, refresh, logout, and current user profile.
"""
import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm
from jose import JWTError
from pydantic import BaseModel, Field
from sqlalchemy import select

from backend.auth import (
    RoleChecker,
    clear_refresh_cookie,
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
    get_current_user,
    get_refresh_token_from_cookie,
    hash_password,
    set_refresh_cookie,
    verify_password,
)
from backend.database import async_session
from backend.models import User

logger = logging.getLogger("daladan.auth")

router = APIRouter(prefix="/api/auth", tags=["Auth"])


# ═══════════════════════════════════════════════════════
#  Response Models
# ═══════════════════════════════════════════════════════


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int = Field(..., description="Token lifetime in seconds")
    user: dict


class UserProfileResponse(BaseModel):
    id: str
    full_name: str
    email: str
    role: str
    region: str | None = None
    is_verified: bool
    balance: float


# ═══════════════════════════════════════════════════════
#  POST /api/auth/login — OAuth2 Password Flow
# ═══════════════════════════════════════════════════════


@router.post("/login", response_model=TokenResponse)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """
    Authenticate with email and password.

    Returns a JWT access token in the response body and sets
    a refresh token as an HttpOnly cookie.

    Uses the standard OAuth2 Password Flow form fields:
      - username: the user's email address
      - password: the user's password
    """
    async with async_session() as session:
        result = await session.execute(
            select(User).where(User.email == form_data.username)
        )
        user = result.scalar_one_or_none()

    if not user or not user.password_hash:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not verify_password(form_data.password, user.password_hash):
        logger.warning("Failed login attempt for: %s", form_data.username)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Generate tokens
    access_token = create_access_token(
        user_id=str(user.id),
        role=user.role.value,
        full_name=user.full_name,
    )
    refresh_token = create_refresh_token(user_id=str(user.id))

    # Build response with access token in body
    from backend.config import get_settings
    settings = get_settings()

    response_data = TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user={
            "id": str(user.id),
            "full_name": user.full_name,
            "email": user.email,
            "role": user.role.value,
            "region": user.region,
        },
    )

    # Set refresh token as HttpOnly cookie
    response = JSONResponse(content=response_data.model_dump())
    set_refresh_cookie(response, refresh_token)

    logger.info("✅ Login successful: %s (%s)", user.email, user.role.value)
    return response


# ═══════════════════════════════════════════════════════
#  POST /api/auth/refresh — Rotate Tokens
# ═══════════════════════════════════════════════════════


@router.post("/refresh", response_model=TokenResponse)
async def refresh_tokens(request: Request):
    """
    Rotate the access and refresh tokens.

    Reads the refresh token from the HttpOnly cookie,
    validates it, and issues a new access token + a new
    rotated refresh token cookie.
    """
    refresh_token = get_refresh_token_from_cookie(request)
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No refresh token found. Please log in again.",
        )

    try:
        payload = decode_refresh_token(refresh_token)
        user_id = payload.get("sub")
        token_type = payload.get("type")

        if not user_id or token_type != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token",
            )

    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token expired or invalid. Please log in again.",
        )

    # Verify user still exists
    async with async_session() as session:
        result = await session.execute(
            select(User).where(User.id == UUID(user_id))
        )
        user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User no longer exists",
        )

    # Issue new tokens (rotation)
    new_access_token = create_access_token(
        user_id=str(user.id),
        role=user.role.value,
        full_name=user.full_name,
    )
    new_refresh_token = create_refresh_token(user_id=str(user.id))

    from backend.config import get_settings
    settings = get_settings()

    response_data = TokenResponse(
        access_token=new_access_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user={
            "id": str(user.id),
            "full_name": user.full_name,
            "email": user.email,
            "role": user.role.value,
            "region": user.region,
        },
    )

    response = JSONResponse(content=response_data.model_dump())
    set_refresh_cookie(response, new_refresh_token)

    logger.info("🔄 Token rotated for: %s", user.email)
    return response


# ═══════════════════════════════════════════════════════
#  POST /api/auth/logout — Clear Refresh Cookie
# ═══════════════════════════════════════════════════════


@router.post("/logout")
async def logout():
    """
    Log out by clearing the refresh token cookie.
    The client should also discard its access token.
    """
    response = JSONResponse(
        content={"message": "Logged out successfully"},
    )
    clear_refresh_cookie(response)
    return response


# ═══════════════════════════════════════════════════════
#  GET /api/auth/me — Current User Profile
# ═══════════════════════════════════════════════════════


@router.get("/me", response_model=UserProfileResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """Return the currently authenticated user's profile."""
    return UserProfileResponse(
        id=str(current_user.id),
        full_name=current_user.full_name,
        email=current_user.email,
        role=current_user.role.value,
        region=current_user.region,
        is_verified=current_user.is_verified,
        balance=float(current_user.balance or 0),
    )
