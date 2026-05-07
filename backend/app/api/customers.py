"""Customer Master API endpoints."""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.services import customer_service as svc
from app.schemas.customer import CustomerCreate, CustomerResponse

router = APIRouter(prefix="/customers", tags=["customers"])


@router.get("", response_model=dict)
async def list_customers(
    search: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    """List/search customers with pagination."""
    customers, total = await svc.list_customers(db, search, skip, limit)
    return {
        "customers": [
            CustomerResponse(
                id=c.id,
                customer_no=c.customer_no,
                name=c.name,
                contact_person=c.contact_person,
                phone=c.phone,
                email=c.email,
                credit_limit=float(c.credit_limit or 0),
                level=c.level,
                notes=c.notes,
                is_active=c.is_active,
                created_at=c.created_at,
                updated_at=c.updated_at,
            )
            for c in customers
        ],
        "total": total,
    }


@router.post("", response_model=CustomerResponse, status_code=201)
async def create_customer(data: CustomerCreate, db: AsyncSession = Depends(get_db)):
    """Create a new customer."""
    existing = await svc.get_customer_by_no(db, data.customer_no)
    if existing:
        raise HTTPException(400, f"Customer {data.customer_no} already exists")
    customer = await svc.create_customer(
        db,
        customer_no=data.customer_no,
        name=data.name,
        contact_person=data.contact_person,
        phone=data.phone,
        email=data.email,
        credit_limit=data.credit_limit or 0,
        level=data.level or "C",
        notes=data.notes,
    )
    return CustomerResponse(
        id=customer.id,
        customer_no=customer.customer_no,
        name=customer.name,
        contact_person=customer.contact_person,
        phone=customer.phone,
        email=customer.email,
        credit_limit=float(customer.credit_limit or 0),
        level=customer.level,
        notes=customer.notes,
        is_active=customer.is_active,
        created_at=customer.created_at,
        updated_at=customer.updated_at,
    )


@router.get("/{customer_id}", response_model=CustomerResponse)
async def get_customer(customer_id: int, db: AsyncSession = Depends(get_db)):
    """Get a customer by ID."""
    customer = await svc.get_customer(db, customer_id)
    if not customer:
        raise HTTPException(404, f"Customer {customer_id} not found")
    return CustomerResponse(
        id=customer.id,
        customer_no=customer.customer_no,
        name=customer.name,
        contact_person=customer.contact_person,
        phone=customer.phone,
        email=customer.email,
        credit_limit=float(customer.credit_limit or 0),
        level=customer.level,
        notes=customer.notes,
        is_active=customer.is_active,
        created_at=customer.created_at,
        updated_at=customer.updated_at,
    )
