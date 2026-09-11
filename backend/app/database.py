"""
SQLAlchemy async database engine and session factory for KissanFlow.
Configured for Neon DB (serverless PostgreSQL) with SSL and connection pool limits.
"""
import os
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.environ["DATABASE_URL"]

# Local Docker PostgreSQL does not use TLS, while hosted providers such as Neon
# require it. Do not force TLS for every connection string.
_requires_ssl = "neon.tech" in DATABASE_URL or "ssl=require" in DATABASE_URL
_is_sqlite = DATABASE_URL.startswith("sqlite")

engine = create_async_engine(
    DATABASE_URL,
    connect_args={"ssl": "require"} if _requires_ssl else {},
    # SQLite (used by the automated test suite) does not support pool sizing.
    **({} if _is_sqlite else {"pool_size": 5, "max_overflow": 10}),
    echo=os.environ.get("ENVIRONMENT", "production") == "development",
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:
    """FastAPI dependency that provides an async DB session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
