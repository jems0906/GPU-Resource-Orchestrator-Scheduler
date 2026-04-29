"""FastAPI dependencies — database sessions, authentication."""

import logging
from typing import Optional
from fastapi import Header, HTTPException, status, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.db.models import User
from app.config import settings

logger = logging.getLogger(__name__)


async def get_current_user(
    x_api_key: Optional[str] = Header(default=None),
    db: AsyncSession = Depends(get_db),
) -> Optional[User]:
    """
    Validate the API key from the X-API-Key header.
    Returns None for the default dev key (anonymous access).
    Raises 401 for invalid keys in non-dev mode.
    """
    if not x_api_key:
        if settings.DEBUG:
            return None
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="X-API-Key header is required",
        )

    # Accept the default dev API key
    if x_api_key == settings.DEFAULT_API_KEY:
        return None

    result = await db.execute(
        select(User).where(User.api_key == x_api_key, User.is_active.is_(True))
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or inactive API key",
        )
    return user


async def require_auth(
    user: Optional[User] = Depends(get_current_user),
) -> Optional[User]:
    """Dependency that allows anonymous access in DEBUG mode only."""
    return user
