"""DecisionLog + AfterActionReview API endpoints with real DB integration."""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.services import decision_service as svc
from app.schemas.decision import (
    DecisionLogCreate,
    DecisionLogUpdate,
    DecisionLogResponse,
    AARCreate,
    AARUpdate,
    AARResponse,
)

router = APIRouter(prefix="/decisions", tags=["decisions"])


# ─── DecisionLog Endpoints ─────────────────────────────────────────

@router.get("", response_model=dict)
async def list_decisions(
    status: Optional[str] = Query(None),
    department: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    decisions, total = await svc.list_decisions(db, status, department, skip, limit)
    return {
        "decisions": [
            DecisionLogResponse(
                id=d.id,
                decision_type=d.decision_type,
                description=d.description,
                department=d.department,
                actor=d.actor,
                role=d.role,
                context_data=d.context_data,
                alternatives=d.alternatives,
                outcome_summary=d.outcome_summary,
                status=d.status,
                created_at=d.created_at,
            )
            for d in decisions
        ],
        "total": total,
    }


@router.post("", response_model=DecisionLogResponse, status_code=201)
async def create_decision(
    data: DecisionLogCreate,
    db: AsyncSession = Depends(get_db),
):
    decision = await svc.create_decision(
        db,
        decision_type=data.decision_type,
        description=data.description,
        department=data.department,
        actor=data.actor,
        role=data.role,
        context_data=data.context_data,
        alternatives=data.alternatives,
    )
    return DecisionLogResponse(
        id=decision.id,
        decision_type=decision.decision_type,
        description=decision.description,
        department=decision.department,
        actor=decision.actor,
        role=decision.role,
        context_data=decision.context_data,
        alternatives=decision.alternatives,
        outcome_summary=decision.outcome_summary,
        status=decision.status,
        created_at=decision.created_at,
    )


@router.get("/{decision_id}", response_model=DecisionLogResponse)
async def get_decision(
    decision_id: int,
    db: AsyncSession = Depends(get_db),
):
    decision = await svc.get_decision(db, decision_id)
    if not decision:
        raise HTTPException(404, f"Decision log not found: {decision_id}")
    return DecisionLogResponse(
        id=decision.id,
        decision_type=decision.decision_type,
        description=decision.description,
        department=decision.department,
        actor=decision.actor,
        role=decision.role,
        context_data=decision.context_data,
        alternatives=decision.alternatives,
        outcome_summary=decision.outcome_summary,
        status=decision.status,
        created_at=decision.created_at,
    )


@router.patch("/{decision_id}", response_model=DecisionLogResponse)
async def update_decision(
    decision_id: int,
    data: DecisionLogUpdate,
    db: AsyncSession = Depends(get_db),
):
    decision = await svc.update_decision_outcome(
        db,
        decision_id,
        outcome_summary=data.outcome_summary,
        status=data.status,
    )
    if not decision:
        raise HTTPException(404, f"Decision log not found: {decision_id}")
    return DecisionLogResponse(
        id=decision.id,
        decision_type=decision.decision_type,
        description=decision.description,
        department=decision.department,
        actor=decision.actor,
        role=decision.role,
        context_data=decision.context_data,
        alternatives=decision.alternatives,
        outcome_summary=decision.outcome_summary,
        status=decision.status,
        created_at=decision.created_at,
    )


# ─── AfterActionReview Endpoints ───────────────────────────────────

@router.get("/aar", response_model=dict)
async def list_aars(
    department: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    aars, total = await svc.list_aars(db, department, status, skip, limit)
    return {
        "aars": [
            AARResponse(
                id=a.id,
                decision_log_id=a.decision_log_id,
                title=a.title,
                department=a.department,
                expected_result=a.expected_result,
                actual_result=a.actual_result,
                variance_analysis=a.variance_analysis,
                root_cause=a.root_cause,
                corrective_action=a.corrective_action,
                preventive_action=a.preventive_action,
                lessons_learned=a.lessons_learned,
                system_rule_updates=a.system_rule_updates,
                status=a.status,
                reviewer=a.reviewer,
                reviewed_at=a.reviewed_at,
                created_at=a.created_at,
                updated_at=a.updated_at,
            )
            for a in aars
        ],
        "total": total,
    }


@router.post("/aar", response_model=AARResponse, status_code=201)
async def create_aar(
    data: AARCreate,
    db: AsyncSession = Depends(get_db),
):
    aar = await svc.create_aar(
        db,
        title=data.title,
        department=data.department,
        expected_result=data.expected_result,
        actual_result=data.actual_result,
        decision_log_id=data.decision_log_id,
        variance_analysis=data.variance_analysis,
        root_cause=data.root_cause,
        corrective_action=data.corrective_action,
        preventive_action=data.preventive_action,
        lessons_learned=data.lessons_learned,
        system_rule_updates=data.system_rule_updates,
        status=data.status,
        reviewer=data.reviewer,
    )
    return AARResponse(
        id=aar.id,
        decision_log_id=aar.decision_log_id,
        title=aar.title,
        department=aar.department,
        expected_result=aar.expected_result,
        actual_result=aar.actual_result,
        variance_analysis=aar.variance_analysis,
        root_cause=aar.root_cause,
        corrective_action=aar.corrective_action,
        preventive_action=aar.preventive_action,
        lessons_learned=aar.lessons_learned,
        system_rule_updates=aar.system_rule_updates,
        status=aar.status,
        reviewer=aar.reviewer,
        reviewed_at=aar.reviewed_at,
        created_at=aar.created_at,
        updated_at=aar.updated_at,
    )


@router.get("/aar/{aar_id}", response_model=AARResponse)
async def get_aar(
    aar_id: int,
    db: AsyncSession = Depends(get_db),
):
    aar = await svc.get_aar(db, aar_id)
    if not aar:
        raise HTTPException(404, f"After Action Review not found: {aar_id}")
    return AARResponse(
        id=aar.id,
        decision_log_id=aar.decision_log_id,
        title=aar.title,
        department=aar.department,
        expected_result=aar.expected_result,
        actual_result=aar.actual_result,
        variance_analysis=aar.variance_analysis,
        root_cause=aar.root_cause,
        corrective_action=aar.corrective_action,
        preventive_action=aar.preventive_action,
        lessons_learned=aar.lessons_learned,
        system_rule_updates=aar.system_rule_updates,
        status=aar.status,
        reviewer=aar.reviewer,
        reviewed_at=aar.reviewed_at,
        created_at=aar.created_at,
        updated_at=aar.updated_at,
    )


@router.patch("/aar/{aar_id}", response_model=AARResponse)
async def update_aar(
    aar_id: int,
    data: AARUpdate,
    db: AsyncSession = Depends(get_db),
):
    aar = await svc.update_aar(
        db,
        aar_id,
        title=data.title,
        department=data.department,
        expected_result=data.expected_result,
        actual_result=data.actual_result,
        decision_log_id=data.decision_log_id,
        variance_analysis=data.variance_analysis,
        root_cause=data.root_cause,
        corrective_action=data.corrective_action,
        preventive_action=data.preventive_action,
        lessons_learned=data.lessons_learned,
        system_rule_updates=data.system_rule_updates,
        status=data.status,
        reviewer=data.reviewer,
    )
    if not aar:
        raise HTTPException(404, f"After Action Review not found: {aar_id}")
    return AARResponse(
        id=aar.id,
        decision_log_id=aar.decision_log_id,
        title=aar.title,
        department=aar.department,
        expected_result=aar.expected_result,
        actual_result=aar.actual_result,
        variance_analysis=aar.variance_analysis,
        root_cause=aar.root_cause,
        corrective_action=aar.corrective_action,
        preventive_action=aar.preventive_action,
        lessons_learned=aar.lessons_learned,
        system_rule_updates=aar.system_rule_updates,
        status=aar.status,
        reviewer=aar.reviewer,
        reviewed_at=aar.reviewed_at,
        created_at=aar.created_at,
        updated_at=aar.updated_at,
    )
