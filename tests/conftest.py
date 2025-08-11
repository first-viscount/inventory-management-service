"""Test configuration and fixtures."""

import pytest
import pytest_asyncio
from collections.abc import AsyncGenerator
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool

from src.core.database import Base, get_db
from src.main import app
# Import models to register them with Base - must be imported after Base is created
from src.models.inventory import Inventory, Location, Reservation, InventoryAdjustment


# Test database URL - use temporary file SQLite for tests
TEST_DATABASE_URL = "sqlite+aiosqlite:///./test_inventory.db"


@pytest_asyncio.fixture(scope="function")
async def test_db_engine():
    """Create a test database engine."""
    import os
    
    # Remove test database file if it exists
    test_db_file = "./test_inventory.db"
    if os.path.exists(test_db_file):
        os.remove(test_db_file)
    
    # Ensure models are imported before creating tables
    from src.models.inventory import Inventory, Location, Reservation, InventoryAdjustment
    
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
async def test_db_session(test_db_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create a test database session."""
    async_session = async_sessionmaker(
        test_db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    
    async with async_session() as session:
        yield session


@pytest_asyncio.fixture(scope="function")
async def client(test_db_engine) -> AsyncGenerator[AsyncClient, None]:
    """Create a test client with test database."""
    
    # Create session maker with the test engine
    TestSessionLocal = async_sessionmaker(
        test_db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    
    async def get_test_db():
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
def sample_location_data():
    """Sample location data for testing."""
    return {
        "name": "Test Warehouse",
        "address": "123 Test St, Test City, TC 12345",
        "type": "warehouse"
    }


@pytest.fixture
def sample_inventory_data():
    """Sample inventory data for testing."""
    return {
        "quantity_available": 100,
        "quantity_reserved": 0,
        "reorder_point": 10,
        "reorder_quantity": 50
    }


@pytest.fixture
def sample_reservation_data():
    """Sample reservation data for testing."""
    return {
        "quantity": 5,
        "expires_minutes": 60
    }