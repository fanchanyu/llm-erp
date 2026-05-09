"""Opportunity Service — opportunity CRUD operations."""

from __future__ import annotations
from datetime import datetime
from typing import Optional
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.opportunity import Opportunity


async def list_opportunities(
    db: AsyncSession,
    stage: Optional[str] = None,
    customer_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 50,
) -> tuple[list[Opportunity], int]:
    """List/filter opportunities with pagination. Returns (opportunities, total_count)."""
    q = select(Opportunity)
    if stage:
        q = q.where(Opportunity.stage == stage)
    if customer_id is not None:
        q = q.where(Opportunity.customer_id == customer_id)
    count_q = select(func.count()).select_from(q.subquery())
    total = (await db.execute(count_q)).scalar() or 0
    result = await db.execute(
        q.offset(skip).limit(limit).order_by(Opportunity.created_at.desc())
    )
    return list(result.scalars().all()), total


async def get_opportunity(db: AsyncSession, opportunity_id: int) -> Optional[Opportunity]:
    """Get an opportunity by primary key ID."""
    return await db.get(Opportunity, opportunity_id)


async def create_opportunity(
    db: AsyncSession,
    lead_id: Optional[int] = None,
    customer_id: int = 0,
    name: str = "",
    amount: float = 0,
    probability: int = 50,
    stage: str = "qualification",
    expected_close_date: Optional[datetime] = None,
    notes: Optional[str] = None,
) -> Opportunity:
    """Create a new opportunity record."""
    opp = Opportunity(
        lead_id=lead_id,
        customer_id=customer_id,
        name=name,
        amount=amount,
        probability=probability,
        stage=stage,
        expected_close_date=expected_close_date,
        notes=notes,
    )
    db.add(opp)
    await db.flush()
    return opp


async def update_opportunity(
    db: AsyncSession,
    opportunity_id: int,
    **kwargs,
) -> Optional[Opportunity]:
    """Update an opportunity record with provided fields."""
    opp = await db.get(Opportunity, opportunity_id)
    if not opp:
        return None
    for key, value in kwargs.items():
        if value is not None and hasattr(opp, key):
            setattr(opp, key, value)
    opp.updated_at = datetime.utcnow()
    await db.flush()
    return opp


async def update_opportunity_stage(
    db: AsyncSession,
    opportunity_id: int,
    stage: str,
    win_reason: Optional[str] = None,
    lost_reason: Optional[str] = None,
) -> Optional[Opportunity]:
    """Update opportunity stage. Logs the change and sets win/lost reason when applicable."""
    opp = await db.get(Opportunity, opportunity_id)
    if not opp:
        return None
    # Log stage change by storing previous stage (could be expanded with an audit log)
    opp.stage = stage
    if stage == "closed_won" and win_reason is not None:
        opp.win_reason = win_reason
        opp.probability = 100
    if stage == "closed_lost" and lost_reason is not None:
        opp.lost_reason = lost_reason
        opp.probability = 0
    opp.updated_at = datetime.utcnow()
    await db.flush()
    return opp


async def delete_opportunity(db: AsyncSession, opportunity_id: int) -> bool:
    """Delete an opportunity by ID. Returns True if deleted, False if not found."""
    opp = await db.get(Opportunity, opportunity_id)
    if not opp:
        return False
    await db.delete(opp)
    await db.flush()
    return True
