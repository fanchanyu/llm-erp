"""DecisionLog + AfterActionReview service — CRUD and AAR management."""

from __future__ import annotations
from datetime import datetime
from typing import Optional
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.decision_log import DecisionLog
from app.models.after_action_review import AfterActionReview


# ─── DecisionLog CRUD ─────────────────────────────────────────────

async def list_decisions(
    db: AsyncSession,
    status: Optional[str] = None,
    department: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
) -> tuple[list[DecisionLog], int]:
    """List/search decision logs with pagination."""
    q = select(DecisionLog)
    if status:
        q = q.where(DecisionLog.status == status)
    if department:
        q = q.where(DecisionLog.department == department)
    count_q = select(func.count()).select_from(q.subquery())
    total = (await db.execute(count_q)).scalar() or 0
    result = await db.execute(
        q.offset(skip).limit(limit).order_by(DecisionLog.created_at.desc())
    )
    return list(result.scalars().all()), total


async def get_decision(db: AsyncSession, decision_id: int) -> Optional[DecisionLog]:
    """Get a single decision log by ID."""
    return await db.get(DecisionLog, decision_id)


async def create_decision(
    db: AsyncSession,
    decision_type: str,
    description: str,
    department: str,
    actor: str,
    role: str,
    context_data: Optional[dict] = None,
    alternatives: Optional[list] = None,
) -> DecisionLog:
    """Create a new decision log entry."""
    decision = DecisionLog(
        decision_type=decision_type,
        description=description,
        department=department,
        actor=actor,
        role=role,
        context_data=context_data,
        alternatives=alternatives,
        status="pending",
    )
    db.add(decision)
    await db.flush()
    await db.refresh(decision)
    return decision


async def update_decision_outcome(
    db: AsyncSession,
    decision_id: int,
    outcome_summary: Optional[str] = None,
    status: Optional[str] = None,
) -> Optional[DecisionLog]:
    """Update decision outcome and/or status."""
    decision = await db.get(DecisionLog, decision_id)
    if not decision:
        return None

    if outcome_summary is not None:
        decision.outcome_summary = outcome_summary
    if status is not None:
        decision.status = status
    await db.flush()
    await db.refresh(decision)
    return decision


# ─── AfterActionReview CRUD ───────────────────────────────────────

async def list_aars(
    db: AsyncSession,
    department: Optional[str] = None,
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
) -> tuple[list[AfterActionReview], int]:
    """List/search AARs with pagination."""
    q = select(AfterActionReview)
    if department:
        q = q.where(AfterActionReview.department == department)
    if status:
        q = q.where(AfterActionReview.status == status)
    count_q = select(func.count()).select_from(q.subquery())
    total = (await db.execute(count_q)).scalar() or 0
    result = await db.execute(
        q.offset(skip).limit(limit).order_by(AfterActionReview.created_at.desc())
    )
    return list(result.scalars().all()), total


async def get_aar(db: AsyncSession, aar_id: int) -> Optional[AfterActionReview]:
    """Get a single AAR by ID."""
    return await db.get(AfterActionReview, aar_id)


async def create_aar(
    db: AsyncSession,
    title: str,
    department: str,
    expected_result: str,
    actual_result: str,
    decision_log_id: Optional[int] = None,
    variance_analysis: Optional[str] = None,
    root_cause: Optional[str] = None,
    corrective_action: Optional[str] = None,
    preventive_action: Optional[str] = None,
    lessons_learned: Optional[str] = None,
    system_rule_updates: Optional[list] = None,
    status: str = "draft",
    reviewer: Optional[str] = None,
) -> AfterActionReview:
    """Create a new After Action Review."""
    aar = AfterActionReview(
        decision_log_id=decision_log_id,
        title=title,
        department=department,
        expected_result=expected_result,
        actual_result=actual_result,
        variance_analysis=variance_analysis,
        root_cause=root_cause,
        corrective_action=corrective_action,
        preventive_action=preventive_action,
        lessons_learned=lessons_learned,
        system_rule_updates=system_rule_updates,
        status=status,
        reviewer=reviewer,
    )
    db.add(aar)
    await db.flush()
    await db.refresh(aar)
    return aar


async def update_aar(
    db: AsyncSession,
    aar_id: int,
    title: Optional[str] = None,
    department: Optional[str] = None,
    expected_result: Optional[str] = None,
    actual_result: Optional[str] = None,
    decision_log_id: Optional[int] = None,
    variance_analysis: Optional[str] = None,
    root_cause: Optional[str] = None,
    corrective_action: Optional[str] = None,
    preventive_action: Optional[str] = None,
    lessons_learned: Optional[str] = None,
    system_rule_updates: Optional[list] = None,
    status: Optional[str] = None,
    reviewer: Optional[str] = None,
) -> Optional[AfterActionReview]:
    """Update an existing AAR. Fields set to None are left unchanged."""
    aar = await db.get(AfterActionReview, aar_id)
    if not aar:
        return None

    if title is not None:
        aar.title = title
    if department is not None:
        aar.department = department
    if expected_result is not None:
        aar.expected_result = expected_result
    if actual_result is not None:
        aar.actual_result = actual_result
    if decision_log_id is not None:
        aar.decision_log_id = decision_log_id
    if variance_analysis is not None:
        aar.variance_analysis = variance_analysis
    if root_cause is not None:
        aar.root_cause = root_cause
    if corrective_action is not None:
        aar.corrective_action = corrective_action
    if preventive_action is not None:
        aar.preventive_action = preventive_action
    if lessons_learned is not None:
        aar.lessons_learned = lessons_learned
    if system_rule_updates is not None:
        aar.system_rule_updates = system_rule_updates
    if status is not None:
        aar.status = status
    if reviewer is not None:
        aar.reviewer = reviewer
    if status == "published" and aar.reviewed_at is None:
        aar.reviewed_at = datetime.utcnow()

    aar.updated_at = datetime.utcnow()
    await db.flush()
    await db.refresh(aar)
    return aar
