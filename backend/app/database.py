"""Async SQLAlchemy engine and session factory."""

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.config import settings

# SQLite: no pool needed; PostgreSQL: pool params set via env
engine = create_async_engine(settings.database_url, echo=settings.debug)

if "postgresql" in settings.database_url:
    engine = create_async_engine(
        settings.database_url,
        echo=settings.debug,
        pool_size=10,
        max_overflow=20,
    )

async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

from typing import AsyncGenerator


async def get_db() -> AsyncGenerator[AsyncSession, None]:
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
    from app.models.dispatch import Base as DispatchBase
    from app.models.accounting import Base as AccountingBase
    from app.models.quality import Base as QualityBase
    from app.models.conversation import Base as ConversationBase
    from app.models.crm_event import Base as CrmEventBase
    from app.models.contract import Base as ContractBase
    from app.models.decision_log import Base as DecisionLogBase
    from app.models.after_action_review import Base as AARBase
    from app.models.organization import Base as OrgBase

    async with engine.begin() as conn:
        for base in [Base, PurchaseBase, BomBase, AuditBase, DispatchBase, AccountingBase, QualityBase, ConversationBase, CrmEventBase, ContractBase, DecisionLogBase, AARBase, OrgBase]:
            await conn.run_sync(base.metadata.create_all)
