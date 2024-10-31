import pytest
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
from typing import AsyncGenerator
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.database import Base, get_db

# Test database URL
TEST_DATABASE_URL = "sqlite+aiosqlite:///./test.db"

@pytest.fixture(scope="function")
async def test_engine():
    """Create a test database engine."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=True,
        future=True
    )
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    await engine.dispose()

@pytest.fixture(scope="function")
async def test_db(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create a test database session."""
    TestingSessionLocal = sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )
    
    async with TestingSessionLocal() as session:
        yield session
        # Clean up after each test
        await session.rollback()
        for table in reversed(Base.metadata.sorted_tables):
            await session.execute(text(f'DELETE FROM {table.name}'))
        await session.commit()

@pytest.fixture(scope="function")
async def client(test_db) -> AsyncGenerator[AsyncClient, None]:
    """Create a test client with the test database."""
    async def override_get_db():
        yield test_db

    app.dependency_overrides[get_db] = override_get_db
    
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        follow_redirects=True
    ) as ac:
        yield ac
    app.dependency_overrides.clear()
