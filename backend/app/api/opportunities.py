"""Opportunity API endpoints."""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.services import opportunity_service as svc
from app.schemas.opportunity import OpportunityCreate, OpportunityUpdate, OpportunityStageUpdate, OpportunityResponse

router = APIRouter(prefix="/opportunities", tags=["opportunities"])


@router.get("", response_model=dict)
async def list_opportunities(
    stage: Optional[str] = Query(None),
    customer_id: Optional[int] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    """List/filter opportunities with pagination."""
    opps, total = await svc.list_opportunities(db, stage, customer_id, skip, limit)
    return {
        "opportunities": [
            OpportunityResponse(
                id=o.id,
                lead_id=o.lead_id,
                customer_id=o.customer_id,
                name=o.name,
                amount=float(o.amount or 0),
                probability=o.probability,
                stage=o.stage,
                expected_close_date=o.expected_close_date,
                win_reason=o.win_reason,
                lost_reason=o.lost_reason,
                notes=o.notes,
                created_at=o.created_at,
                updated_at=o.updated_at,
            )
            for o in opps
        ],
        "total": total,
    }


@router.post("", response_model=OpportunityResponse, status_code=201)
async def create_opportunity(data: OpportunityCreate, db: AsyncSession = Depends(get_db)):
    """Create a new opportunity."""
    opp = await svc.create_opportunity(
        db,
        lead_id=data.lead_id,
        customer_id=data.customer_id,
        name=data.name,
        amount=data.amount,
        probability=data.probability,
        stage=data.stage,
        expected_close_date=data.expected_close_date,
        notes=data.notes,
    )
    return OpportunityResponse(
        id=opp.id,
        lead_id=opp.lead_id,
        customer_id=opp.customer_id,
        name=opp.name,
        amount=float(opp.amount or 0),
        probability=opp.probability,
        stage=opp.stage,
        expected_close_date=opp.expected_close_date,
        win_reason=opp.win_reason,
        lost_reason=opp.lost_reason,
        notes=opp.notes,
        created_at=opp.created_at,
        updated_at=opp.updated_at,
    )


@router.get("/{opportunity_id}", response_model=OpportunityResponse)
async def get_opportunity(opportunity_id: int, db: AsyncSession = Depends(get_db)):
    """Get an opportunity by ID."""
    opp = await svc.get_opportunity(db, opportunity_id)
    if not opp:
        raise HTTPException(404, f"Opportunity {opportunity_id} not found")
    return OpportunityResponse(
        id=opp.id,
        lead_id=opp.lead_id,
        customer_id=opp.customer_id,
        name=opp.name,
        amount=float(opp.amount or 0),
        probability=opp.probability,
        stage=opp.stage,
        expected_close_date=opp.expected_close_date,
        win_reason=opp.win_reason,
        lost_reason=opp.lost_reason,
        notes=opp.notes,
        created_at=opp.created_at,
        updated_at=opp.updated_at,
    )


@router.patch("/{opportunity_id}/stage", response_model=OpportunityResponse)
async def update_opportunity_stage(
    opportunity_id: int,
    data: OpportunityStageUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update opportunity stage (with win/lost reasons)."""
    opp = await svc.update_opportunity_stage(
        db, opportunity_id,
        stage=data.stage,
        win_reason=data.win_reason,
        lost_reason=data.lost_reason,
    )
    if not opp:
        raise HTTPException(404, f"Opportunity {opportunity_id} not found")
    return OpportunityResponse(
        id=opp.id,
        lead_id=opp.lead_id,
        customer_id=opp.customer_id,
        name=opp.name,
        amount=float(opp.amount or 0),
        probability=opp.probability,
        stage=opp.stage,
        expected_close_date=opp.expected_close_date,
        win_reason=opp.win_reason,
        lost_reason=opp.lost_reason,
        notes=opp.notes,
        created_at=opp.created_at,
        updated_at=opp.updated_at,
    )


@router.delete("/{opportunity_id}", status_code=204)
async def delete_opportunity(opportunity_id: int, db: AsyncSession = Depends(get_db)):
    """Delete an opportunity."""
    deleted = await svc.delete_opportunity(db, opportunity_id)
    if not deleted:
        raise HTTPException(404, f"Opportunity {opportunity_id} not found")
    return None
