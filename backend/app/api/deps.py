"""
FastAPI dependencies for injection
"""

from typing import AsyncGenerator, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session

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
    Get current user ID from JWT token (optional)
    Returns None if no token provided

    TODO: Implement proper JWT validation
    """
    if credentials is None:
        return None

    # TODO: Validate JWT token and extract user_id
    # For now, return None (anonymous user)
    return None


async def get_required_user_id(
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer())
) -> int:
    """
    Get current user ID from JWT token (required)
    Raises 401 if no valid token provided

    TODO: Implement proper JWT validation
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )

    # TODO: Validate JWT token and extract user_id
    # For now, raise error
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid authentication token"
    )
