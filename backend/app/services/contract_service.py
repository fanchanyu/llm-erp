"""Contract service — CRUD operations and pricing lookups."""

from __future__ import annotations
from datetime import datetime
from typing import Optional
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.contract import Contract, ContractPricing


async def list_contracts(
    db: AsyncSession,
    customer_id: Optional[int] = None,
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
) -> tuple[list[Contract], int]:
    """List/search contracts with pagination."""
    q = select(Contract)
    if customer_id is not None:
        q = q.where(Contract.customer_id == customer_id)
    if status:
        q = q.where(Contract.status == status)
    count_q = select(func.count()).select_from(q.subquery())
    total = (await db.execute(count_q)).scalar() or 0
    result = await db.execute(
        q.offset(skip).limit(limit).order_by(Contract.created_at.desc())
    )
    return list(result.scalars().all()), total


async def get_contract(db: AsyncSession, contract_id: int) -> Optional[Contract]:
    """Get a single contract by ID."""
    return await db.get(Contract, contract_id)


async def get_contract_by_no(db: AsyncSession, contract_no: str) -> Optional[Contract]:
    """Get a single contract by contract number."""
    result = await db.execute(
        select(Contract).where(Contract.contract_no == contract_no)
    )
    return result.scalar_one_or_none()


async def create_contract(
    db: AsyncSession,
    contract_no: str,
    customer_id: int,
    type: str,
    start_date: datetime,
    end_date: Optional[datetime] = None,
    pricing_json: Optional[dict] = None,
    payment_terms: Optional[str] = None,
    status: str = "draft",
    auto_renew: bool = False,
    notes: Optional[str] = None,
) -> Contract:
    """Create a new contract."""
    contract = Contract(
        contract_no=contract_no,
        customer_id=customer_id,
        type=type,
        start_date=start_date,
        end_date=end_date,
        pricing_json=pricing_json,
        payment_terms=payment_terms,
        status=status,
        auto_renew=auto_renew,
        notes=notes,
    )
    db.add(contract)
    await db.flush()
    await db.refresh(contract)
    return contract


async def update_contract(
    db: AsyncSession,
    contract_id: int,
    contract_no: Optional[str] = None,
    customer_id: Optional[int] = None,
    type: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    pricing_json: Optional[dict] = None,
    payment_terms: Optional[str] = None,
    status: Optional[str] = None,
    auto_renew: Optional[bool] = None,
    notes: Optional[str] = None,
) -> Optional[Contract]:
    """Update an existing contract. Fields set to None are left unchanged."""
    contract = await db.get(Contract, contract_id)
    if not contract:
        return None

    if contract_no is not None:
        contract.contract_no = contract_no
    if customer_id is not None:
        contract.customer_id = customer_id
    if type is not None:
        contract.type = type
    if start_date is not None:
        contract.start_date = start_date
    if end_date is not None:
        contract.end_date = end_date
    if pricing_json is not None:
        contract.pricing_json = pricing_json
    if payment_terms is not None:
        contract.payment_terms = payment_terms
    if status is not None:
        contract.status = status
    if auto_renew is not None:
        contract.auto_renew = auto_renew
    if notes is not None:
        contract.notes = notes
    contract.updated_at = datetime.utcnow()
    await db.flush()
    await db.refresh(contract)
    return contract


async def delete_contract(db: AsyncSession, contract_id: int) -> bool:
    """Delete a contract by ID. Returns True if deleted, False if not found."""
    contract = await db.get(Contract, contract_id)
    if not contract:
        return False
    await db.delete(contract)
    await db.flush()
    return True


async def get_pricing(
    db: AsyncSession, contract_id: int, part_no: str
) -> Optional[dict]:
    """Get unit price for a part within a contract.

    First checks the ContractPricing table (explicit pricing lines).
    Falls back to the pricing_json embedded field.
    Returns dict with unit_price, min_qty, discount_pct or None.
    """
    # Try explicit pricing line first
    result = await db.execute(
        select(ContractPricing).where(
            ContractPricing.contract_id == contract_id,
            ContractPricing.part_no == part_no,
        )
    )
    pricing = result.scalar_one_or_none()
    if pricing:
        return {
            "part_no": pricing.part_no,
            "unit_price": pricing.unit_price,
            "min_qty": pricing.min_qty,
            "discount_pct": pricing.discount_pct,
        }

    # Fall back to pricing_json
    contract = await db.get(Contract, contract_id)
    if not contract or not contract.pricing_json:
        return None

    part_pricing = contract.pricing_json.get(part_no)
    if not part_pricing:
        return None

    return {
        "part_no": part_no,
        **part_pricing,
    }
