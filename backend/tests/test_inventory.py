"""Tests for inventory service."""

import pytest
import uuid
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from app.models.inventory import Base, Part, Inventory
from app.services import inventory_service as svc


@pytest.fixture
async def db_session():
    """In-memory SQLite for testing."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session

    await engine.dispose()


@pytest.mark.asyncio
async def test_create_part(db_session: AsyncSession):
    part = await svc.create_part(db_session, "TEST-001", "測試零件", "pcs", "測試用")
    assert part.part_no == "TEST-001"
    assert part.name == "測試零件"
    assert part.unit == "pcs"


@pytest.mark.asyncio
async def test_get_part_by_no(db_session: AsyncSession):
    await svc.create_part(db_session, "TEST-002", "測試零件2", "kg")
    part = await svc.get_part_by_no(db_session, "TEST-002")
    assert part is not None
    assert part.part_no == "TEST-002"


@pytest.mark.asyncio
async def test_inbound_outbound(db_session: AsyncSession):
    part = await svc.create_part(db_session, "STOCK-001", "庫存測試", "pcs")
    inv = await svc.inbound(db_session, part.id, 100, "A-01")
    assert float(inv.quantity) == 100

    inv2 = await svc.outbound(db_session, part.id, 30, "A-01")
    assert float(inv2.quantity) == 70

    with pytest.raises(ValueError):
        await svc.outbound(db_session, part.id, 999, "A-01")
