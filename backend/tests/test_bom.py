"""Tests for BOM service."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from app.models.inventory import Base as InvBase
from app.models.bom import Base as BomBase
from app.services import bom_service as svc
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
async def test_create_product(db_session: AsyncSession):
    p = await svc.create_product(db_session, "PROD-001", "測試產品")
    assert p.product_no == "PROD-001"
    assert p.name == "測試產品"


@pytest.mark.asyncio
async def test_bom_tree(db_session: AsyncSession):
    product = await svc.create_product(db_session, "PROD-002", "組裝件")
    part_a = await inv_svc.create_part(db_session, "SUB-001", "子件A", "pcs")
    part_b = await inv_svc.create_part(db_session, "SUB-002", "子件B", "pcs")

    await svc.add_bom_item(db_session, product.id, part_a.id, 2, level=1)
    await svc.add_bom_item(db_session, product.id, part_b.id, 1, level=1)

    tree = await svc.get_bom_tree(db_session, product.id)
    assert len(tree) == 2
