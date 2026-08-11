"""Shared fixtures for the persistence-layer tests.

These tests use an in-memory SQLite database (via aiosqlite) instead of a
real Postgres instance. That's a deliberate choice for this V1: it needs no
docker-compose/network setup, so the test suite stays fast and hermetic and
can run in any environment (including plain CI) without a database service
available. Base.metadata (shared by both SQLite here and the real Postgres
schema via Alembic) is what's actually under test — the repository/ORM
logic doesn't rely on anything Postgres-specific. The real Postgres schema
itself is still exercised separately by the `integration`-marked tests in
test_races_api.py, which run against docker-compose's "db" service.
"""

from collections.abc import AsyncIterator

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.db.session import get_db
from app.main import app
from app.models import Base


@pytest_asyncio.fixture
async def db_session() -> AsyncIterator[AsyncSession]:
    # StaticPool keeps the single in-memory SQLite connection alive for the
    # whole fixture instead of a fresh (and empty) database per checkout.
    engine = create_async_engine("sqlite+aiosqlite://", poolclass=StaticPool)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session

    await engine.dispose()


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncIterator[AsyncClient]:
    async def _override_get_db() -> AsyncIterator[AsyncSession]:
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as async_client:
        yield async_client
    app.dependency_overrides.clear()
