from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from backend.app.config import settings
from backend.app.db.models import Base

# Create async engine
engine = create_async_engine(
    settings.database_url,
    echo=False,
    future=True
)

# Async session factory
async_session_factory = async_sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
    class_=AsyncSession
)

async def init_db():
    """Initializes database tables."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for providing database sessions."""
    async with async_session_factory() as session:
        try:
            yield session
        finally:
            await session.close()
