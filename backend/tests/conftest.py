"""
Pytest configuration and fixtures for backend tests
"""

import os
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

# Set test environment before importing app
os.environ["ENVIRONMENT"] = "test"
os.environ["DEBUG"] = "false"

# Import models first to ensure relationships are set up
from app.models import user, campaign, lookup_result, data_source

from app.main import app
from app.core.database import Base, get_db_session
from app.core.config import settings


# Use SQLite for tests (faster, no external dependencies)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture(loop_scope="session")
async def test_engine():
    """Create test database engine

    Uses in-memory SQLite with StaticPool to maintain a single connection.
    Session-scoped to share across all tests.
    """
    engine = create_async_engine(
        TEST_DATABASE_URL,
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
        echo=False,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    await engine.dispose()


@pytest_asyncio.fixture(loop_scope="session")
async def async_session_factory(test_engine):
    """Create session factory - session scoped"""
    return async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )


@pytest_asyncio.fixture
async def db_session(async_session_factory) -> AsyncGenerator[AsyncSession, None]:
    """Create test database session - function scoped"""
    session = async_session_factory()
    try:
        yield session
        await session.rollback()
    finally:
        await session.close()


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Create test HTTP client with database override"""

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db_session] = override_get_db

    transport = ASGITransport(app=app)
    ac = AsyncClient(transport=transport, base_url="http://test")
    try:
        yield ac
    finally:
        await ac.aclose()
        app.dependency_overrides.clear()


# Sample data fixtures
@pytest.fixture
def sample_lookup_request():
    """Sample lookup request data"""
    return {
        "first_name": "John",
        "last_name": "Smith",
        "city": "Boston",
        "state": "MA",
        "age": 35,
    }


@pytest.fixture
def sample_user_data():
    """Sample user registration data"""
    return {
        "email": "test@example.com",
        "password": "SecurePass123!",
        "full_name": "Test User",
    }
