"""Lead API endpoints."""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.services import lead_service as svc
from app.schemas.lead import LeadCreate, LeadUpdate, LeadResponse

router = APIRouter(prefix="/leads", tags=["leads"])


@router.get("", response_model=dict)
async def list_leads(
    search: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    """List/search leads with pagination."""
    leads, total = await svc.list_leads(db, search, status, skip, limit)
    return {
        "leads": [
            LeadResponse(
                id=l.id,
                company=l.company,
                contact_person=l.contact_person,
                phone=l.phone,
                email=l.email,
                source=l.source,
                score=l.score,
                status=l.status,
                assigned_to=l.assigned_to,
                notes=l.notes,
                lost_reason=l.lost_reason,
                converted_to_customer_id=l.converted_to_customer_id,
                created_at=l.created_at,
                updated_at=l.updated_at,
            )
            for l in leads
        ],
        "total": total,
    }


@router.post("", response_model=LeadResponse, status_code=201)
async def create_lead(data: LeadCreate, db: AsyncSession = Depends(get_db)):
    """Create a new lead."""
    lead = await svc.create_lead(
        db,
        company=data.company,
        contact_person=data.contact_person,
        phone=data.phone,
        email=data.email,
        source=data.source,
        score=data.score,
        assigned_to=data.assigned_to,
        notes=data.notes,
    )
    return LeadResponse(
        id=lead.id,
        company=lead.company,
        contact_person=lead.contact_person,
        phone=lead.phone,
        email=lead.email,
        source=lead.source,
        score=lead.score,
        status=lead.status,
        assigned_to=lead.assigned_to,
        notes=lead.notes,
        lost_reason=lead.lost_reason,
        converted_to_customer_id=lead.converted_to_customer_id,
        created_at=lead.created_at,
        updated_at=lead.updated_at,
    )


@router.get("/{lead_id}", response_model=LeadResponse)
async def get_lead(lead_id: int, db: AsyncSession = Depends(get_db)):
    """Get a lead by ID."""
    lead = await svc.get_lead(db, lead_id)
    if not lead:
        raise HTTPException(404, f"Lead {lead_id} not found")
    return LeadResponse(
        id=lead.id,
        company=lead.company,
        contact_person=lead.contact_person,
        phone=lead.phone,
        email=lead.email,
        source=lead.source,
        score=lead.score,
        status=lead.status,
        assigned_to=lead.assigned_to,
        notes=lead.notes,
        lost_reason=lead.lost_reason,
        converted_to_customer_id=lead.converted_to_customer_id,
        created_at=lead.created_at,
        updated_at=lead.updated_at,
    )


@router.patch("/{lead_id}", response_model=LeadResponse)
async def update_lead(lead_id: int, data: LeadUpdate, db: AsyncSession = Depends(get_db)):
    """Update a lead."""
    # If status is being updated, use the specialized status update
    if data.status is not None:
        lead = await svc.update_lead_status(
            db, lead_id, status=data.status,
            lost_reason=data.lost_reason,
        )
    else:
        lead = await svc.update_lead(
            db, lead_id,
            company=data.company,
            contact_person=data.contact_person,
            phone=data.phone,
            email=data.email,
            source=data.source,
            score=data.score,
            assigned_to=data.assigned_to,
            notes=data.notes,
        )
    if not lead:
        raise HTTPException(404, f"Lead {lead_id} not found")
    return LeadResponse(
        id=lead.id,
        company=lead.company,
        contact_person=lead.contact_person,
        phone=lead.phone,
        email=lead.email,
        source=lead.source,
        score=lead.score,
        status=lead.status,
        assigned_to=lead.assigned_to,
        notes=lead.notes,
        lost_reason=lead.lost_reason,
        converted_to_customer_id=lead.converted_to_customer_id,
        created_at=lead.created_at,
        updated_at=lead.updated_at,
    )


@router.delete("/{lead_id}", status_code=204)
async def delete_lead(lead_id: int, db: AsyncSession = Depends(get_db)):
    """Delete a lead."""
    deleted = await svc.delete_lead(db, lead_id)
    if not deleted:
        raise HTTPException(404, f"Lead {lead_id} not found")
    return None
