"""
Daladan Platform — Authentication & Authorization Module
Implements OAuth2 with Password Flow, JWT tokens, and RBAC.

Components:
  - Password hashing via passlib + bcrypt
  - JWT access/refresh token creation via python-jose
  - get_current_user: FastAPI Dependency for token validation
  - RoleChecker: Factory class for role-based access control
  - Refresh token cookie helpers
"""
import logging
from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import get_settings
from backend.database import async_session
from backend.models import User, UserRole

logger = logging.getLogger("daladan.auth")
settings = get_settings()

# ═══════════════════════════════════════════════════════
#  Password Hashing (passlib + bcrypt)
# ═══════════════════════════════════════════════════════

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain_password: str) -> str:
    """Hash a plaintext password with bcrypt via passlib."""
    return pwd_context.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


# ═══════════════════════════════════════════════════════
#  JWT Token Creation (python-jose)
# ═══════════════════════════════════════════════════════


def create_access_token(
    user_id: str,
    role: str,
    full_name: str,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Create a signed JWT access token."""
    expire = datetime.utcnow() + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    payload = {
        "sub": user_id,
        "role": role,
        "name": full_name,
        "type": "access",
        "exp": expire,
        "iat": datetime.utcnow(),
    }
    return jwt.encode(
        payload,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )


def create_refresh_token(
    user_id: str,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Create a signed JWT refresh token (longer-lived)."""
    expire = datetime.utcnow() + (
        expires_delta or timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    )
    payload = {
        "sub": user_id,
        "type": "refresh",
        "exp": expire,
        "iat": datetime.utcnow(),
    }
    return jwt.encode(
        payload,
        settings.JWT_REFRESH_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )


def decode_access_token(token: str) -> dict:
    """Decode and validate an access token."""
    return jwt.decode(
        token,
        settings.JWT_SECRET_KEY,
        algorithms=[settings.JWT_ALGORITHM],
    )


def decode_refresh_token(token: str) -> dict:
    """Decode and validate a refresh token."""
    return jwt.decode(
        token,
        settings.JWT_REFRESH_SECRET_KEY,
        algorithms=[settings.JWT_ALGORITHM],
    )


# ═══════════════════════════════════════════════════════
#  OAuth2 Scheme
# ═══════════════════════════════════════════════════════

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


# ═══════════════════════════════════════════════════════
#  get_current_user — FastAPI Dependency
# ═══════════════════════════════════════════════════════


async def get_current_user(
    token: str = Depends(oauth2_scheme),
) -> User:
    """
    Validate the Bearer JWT access token and return the User.

    Raises HTTP 401 if the token is invalid, expired, or the user
    no longer exists in the database.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = decode_access_token(token)
        user_id: str = payload.get("sub")
        token_type: str = payload.get("type")

        if user_id is None:
            raise credentials_exception
        if token_type != "access":
            raise credentials_exception

    except JWTError:
        raise credentials_exception

    # Fetch the user from the database
    async with async_session() as session:
        result = await session.execute(
            select(User).where(User.id == UUID(user_id))
        )
        user = result.scalar_one_or_none()

    if user is None:
        raise credentials_exception

    return user


# ═══════════════════════════════════════════════════════
#  RoleChecker — RBAC Factory Class
# ═══════════════════════════════════════════════════════


class RoleChecker:
    """
    FastAPI dependency factory for role-based access control.

    Usage:
        @router.get(
            "/producer-only",
            dependencies=[Depends(RoleChecker(["producer"]))]
        )

    Or as a parameter dependency:
        async def endpoint(user: User = Depends(RoleChecker(["producer"]))):
            ...
    """

    def __init__(self, allowed_roles: list[str]):
        self.allowed_roles = allowed_roles

    async def __call__(
        self, user: User = Depends(get_current_user),
    ) -> User:
        if user.role.value not in self.allowed_roles:
            logger.warning(
                "RBAC denied: user %s (role=%s) tried accessing "
                "endpoint restricted to %s",
                user.email, user.role.value, self.allowed_roles,
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. This endpoint requires one of "
                       f"these roles: {', '.join(self.allowed_roles)}. "
                       f"Your role: {user.role.value}.",
            )
        return user


# ═══════════════════════════════════════════════════════
#  Refresh Cookie Helpers
# ═══════════════════════════════════════════════════════

REFRESH_COOKIE_NAME = "daladan_refresh_token"


def set_refresh_cookie(response, refresh_token: str) -> None:
    """
    Set the refresh token as an HttpOnly, Secure, SameSite=Strict cookie.
    """
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=refresh_token,
        httponly=True,
        secure=True,           # only sent over HTTPS
        samesite="strict",     # strict CSRF protection
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400,
        path="/api/auth",      # only sent to auth endpoints
    )


def clear_refresh_cookie(response) -> None:
    """Remove the refresh token cookie."""
    response.delete_cookie(
        key=REFRESH_COOKIE_NAME,
        path="/api/auth",
        httponly=True,
        secure=True,
        samesite="strict",
    )


def get_refresh_token_from_cookie(request: Request) -> Optional[str]:
    """Extract the refresh token from the request cookies."""
    return request.cookies.get(REFRESH_COOKIE_NAME)
