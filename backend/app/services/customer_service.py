"""Customer Master Service — customer CRUD operations."""

from __future__ import annotations
from typing import Optional
from sqlalchemy import select, or_, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.customer import Customer


async def list_customers(
    db: AsyncSession,
    search: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
) -> tuple[list[Customer], int]:
    """List/search customers with pagination. Returns (customers, total_count)."""
    q = select(Customer)
    if search:
        q = q.where(
            or_(
                Customer.customer_no.ilike(f"%{search}%"),
                Customer.name.ilike(f"%{search}%"),
                Customer.contact_person.ilike(f"%{search}%"),
            )
        )
    count_q = select(func.count()).select_from(q.subquery())
    total = (await db.execute(count_q)).scalar() or 0
    result = await db.execute(q.offset(skip).limit(limit).order_by(Customer.customer_no))
    return list(result.scalars().all()), total


async def get_customer(db: AsyncSession, customer_id: int) -> Optional[Customer]:
    """Get customer by primary key ID."""
    return await db.get(Customer, customer_id)


async def get_customer_by_no(db: AsyncSession, customer_no: str) -> Optional[Customer]:
    """Get customer by unique customer_no."""
    result = await db.execute(select(Customer).where(Customer.customer_no == customer_no))
    return result.scalar_one_or_none()


async def create_customer(
    db: AsyncSession,
    customer_no: str,
    name: str,
    contact_person: Optional[str] = None,
    phone: Optional[str] = None,
    email: Optional[str] = None,
    credit_limit: float = 0,
    level: str = "C",
    notes: Optional[str] = None,
) -> Customer:
    """Create a new customer record."""
    customer = Customer(
        customer_no=customer_no,
        name=name,
        contact_person=contact_person,
        phone=phone,
        email=email,
        credit_limit=credit_limit,
        level=level,
        notes=notes,
    )
    db.add(customer)
    await db.flush()
    return customer
