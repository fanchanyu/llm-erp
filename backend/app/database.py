"""Async SQLAlchemy engine and session factory."""

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.config import settings

engine = create_async_engine(settings.database_url, echo=settings.debug, pool_size=10, max_overflow=20)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db() -> AsyncSession:
    """FastAPI dependency — yields an async DB session."""
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    """Create all tables (dev/test only; use Alembic in production)."""
    from app.models.inventory import Base
    from app.models.purchase import Base as PurchaseBase
    from app.models.bom import Base as BomBase
    from app.models.audit_log import Base as AuditBase

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
