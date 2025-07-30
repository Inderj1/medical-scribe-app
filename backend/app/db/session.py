from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool
import redis

from app.core.config import settings

# Sync engine for migrations
engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)

# Async engine for application (optional)
try:
    async_engine = create_async_engine(
        settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://"),
        echo=settings.DEBUG,
        poolclass=NullPool
    )
except ImportError:
    # asyncpg not installed, use sync engine only
    async_engine = None
    import warnings
    warnings.warn("asyncpg not installed, async database operations will not be available")

# Session makers
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

if async_engine:
    async_session_maker = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=async_engine,
        class_=AsyncSession
    )
else:
    async_session_maker = None


# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


async def get_async_session():
    if async_session_maker:
        async with async_session_maker() as session:
            yield session
    else:
        raise RuntimeError("Async database sessions not available. Install asyncpg.")


# Redis client
def get_redis():
    return redis.from_url(settings.REDIS_URL, decode_responses=True)