"""
FastAPI dependencies for injection
"""

from typing import AsyncGenerator, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.security import verify_token

# Security scheme for JWT tokens
security = HTTPBearer(auto_error=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Database session dependency
    Use with: db: AsyncSession = Depends(get_db)
    """
    async for session in get_db_session():
        yield session


async def get_current_user_id(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[int]:
    """
    Get current user ID from JWT token (optional).
    Returns None if no token provided.
    """
    if credentials is None:
        return None

    subject = verify_token(credentials.credentials)
    if subject is None:
        return None

    try:
        return int(subject)
    except (ValueError, TypeError):
        return None


async def get_required_user_id(
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer())
) -> int:
    """
    Get current user ID from JWT token (required).
    Raises 401 if no valid token provided.
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )

    subject = verify_token(credentials.credentials)
    if subject is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )

    try:
        return int(subject)
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload"
        )
