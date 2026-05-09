"""Lead Service — lead CRUD operations."""

from __future__ import annotations
from datetime import datetime
from typing import Optional
from sqlalchemy import select, or_, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.lead import Lead


async def list_leads(
    db: AsyncSession,
    search: Optional[str] = None,
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
) -> tuple[list[Lead], int]:
    """List/search leads with pagination. Returns (leads, total_count)."""
    q = select(Lead)
    if search:
        q = q.where(
            or_(
                Lead.company.ilike(f"%{search}%"),
                Lead.contact_person.ilike(f"%{search}%"),
                Lead.email.ilike(f"%{search}%"),
            )
        )
    if status:
        q = q.where(Lead.status == status)
    count_q = select(func.count()).select_from(q.subquery())
    total = (await db.execute(count_q)).scalar() or 0
    result = await db.execute(
        q.offset(skip).limit(limit).order_by(Lead.created_at.desc())
    )
    return list(result.scalars().all()), total


async def get_lead(db: AsyncSession, lead_id: int) -> Optional[Lead]:
    """Get a lead by primary key ID."""
    return await db.get(Lead, lead_id)


async def create_lead(
    db: AsyncSession,
    company: str,
    contact_person: Optional[str] = None,
    phone: Optional[str] = None,
    email: Optional[str] = None,
    source: str = "web",
    score: int = 0,
    assigned_to: Optional[str] = None,
    notes: Optional[str] = None,
) -> Lead:
    """Create a new lead record."""
    lead = Lead(
        company=company,
        contact_person=contact_person,
        phone=phone,
        email=email,
        source=source,
        score=score,
        assigned_to=assigned_to,
        notes=notes,
    )
    db.add(lead)
    await db.flush()
    return lead


async def update_lead(
    db: AsyncSession,
    lead_id: int,
    **kwargs,
) -> Optional[Lead]:
    """Update a lead record with provided fields."""
    lead = await db.get(Lead, lead_id)
    if not lead:
        return None
    for key, value in kwargs.items():
        if value is not None and hasattr(lead, key):
            setattr(lead, key, value)
    lead.updated_at = datetime.utcnow()
    await db.flush()
    return lead


async def update_lead_status(
    db: AsyncSession,
    lead_id: int,
    status: str,
    customer_id: Optional[int] = None,
    lost_reason: Optional[str] = None,
) -> Optional[Lead]:
    """Update lead status. If 'converted', also set converted_to_customer_id."""
    lead = await db.get(Lead, lead_id)
    if not lead:
        return None
    lead.status = status
    if status == "converted" and customer_id is not None:
        lead.converted_to_customer_id = customer_id
    if status == "lost" and lost_reason is not None:
        lead.lost_reason = lost_reason
    lead.updated_at = datetime.utcnow()
    await db.flush()
    return lead


async def delete_lead(db: AsyncSession, lead_id: int) -> bool:
    """Delete a lead by ID. Returns True if deleted, False if not found."""
    lead = await db.get(Lead, lead_id)
    if not lead:
        return False
    await db.delete(lead)
    await db.flush()
    return True
