"""Test configuration and fixtures."""

from collections.abc import AsyncGenerator
from typing import Any

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from src.core.database import Base, get_db
from src.main import app

# Import models to register them with Base - must be imported after Base is created

# Test database URL - use temporary file SQLite for tests
TEST_DATABASE_URL = "sqlite+aiosqlite:///./test_inventory.db"


@pytest_asyncio.fixture(scope="function")
async def test_db_engine() -> AsyncGenerator[Any, None]:
    """Create a test database engine."""
    import os
    
    # Remove test database file if it exists
    test_db_file = "./test_inventory.db"
    if os.path.exists(test_db_file):
        os.remove(test_db_file)
    
    # Ensure models are imported before creating tables
    
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        poolclass=NullPool,
    )
    
    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    # Cleanup
    await engine.dispose()
    
    # Remove test database file after test
    if os.path.exists(test_db_file):
        os.remove(test_db_file)


@pytest_asyncio.fixture(scope="function")
async def test_db_session(test_db_engine) -> AsyncGenerator[AsyncSession]:
    """Create a test database session."""
    async_session = async_sessionmaker(
        test_db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    
    async with async_session() as session:
        yield session


@pytest_asyncio.fixture(scope="function")
async def client(test_db_engine) -> AsyncGenerator[AsyncClient]:
    """Create a test client with test database."""
    
    # Create session maker with the test engine
    TestSessionLocal = async_sessionmaker(
        test_db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    
    async def get_test_db() -> AsyncGenerator[AsyncSession, None]:
        async with TestSessionLocal() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
    
    app.dependency_overrides[get_db] = get_test_db
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client
    
    # Cleanup
    app.dependency_overrides.clear()


@pytest.fixture
def sample_location_data() -> dict[str, str]:
    """Sample location data for testing."""
    return {
        "name": "Test Warehouse",
        "address": "123 Test St, Test City, TC 12345",
        "type": "warehouse",
    }


@pytest.fixture
def sample_inventory_data() -> dict[str, int]:
    """Sample inventory data for testing."""
    return {
        "quantity_available": 100,
        "quantity_reserved": 0,
        "reorder_point": 10,
        "reorder_quantity": 50,
    }


@pytest.fixture
def sample_reservation_data() -> dict[str, int]:
    """Sample reservation data for testing."""
    return {
        "quantity": 5,
        "expires_minutes": 60,
    }