"""Tests for purchase service."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from app.models.inventory import Base as InvBase
from app.models.purchase import Base as PurchBase
from app.services import purchase_service as svc
from app.services import inventory_service as inv_svc


@pytest.fixture
async def db_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(InvBase.metadata.create_all)

    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session
    await engine.dispose()


@pytest.mark.asyncio
async def test_create_supplier(db_session: AsyncSession):
    s = await svc.create_supplier(db_session, "測試供應商", "王先生", "0912345678")
    assert s.name == "測試供應商"
    assert s.contact == "王先生"


@pytest.mark.asyncio
async def test_create_purchase_order(db_session: AsyncSession):
    supplier = await svc.create_supplier(db_session, "供應商A")
    part = await inv_svc.create_part(db_session, "PO-TEST", "採購測試件", "pcs")

    po = await svc.create_purchase_order(db_session, supplier.id, [
        {"part_id": part.id, "quantity": 100, "unit_price": 10.0},
    ])
    assert po.po_no.startswith("PO-")
    assert po.status == "draft"
