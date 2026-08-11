from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import get_settings

# NullPool: don't keep pooled asyncpg connections around across requests.
# asyncpg connections are bound to the event loop that created them, and
# this engine is constructed once at import time — with a real pool, a
# process that spins up more than one event loop over its lifetime (as
# pytest-asyncio does, one per test function) would hand out a connection
# tied to an already-closed loop and crash with "Event loop is closed".
# Under uvicorn there's only ever one loop, so this only costs a fresh
# connection handshake per request rather than a reused pooled one.
engine = create_async_engine(get_settings().database_url, echo=False, poolclass=NullPool)

async_session_factory = async_sessionmaker(engine, expire_on_commit=False)


async def get_db() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency yielding a request-scoped AsyncSession."""
    async with async_session_factory() as session:
        yield session
