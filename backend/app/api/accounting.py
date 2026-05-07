"""Accounting API endpoints with real DB integration."""

import uuid
from datetime import datetime, date
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.services import accounting_service as svc
from app.schemas.accounting import (
    AccountCreate, AccountResponse,
    JournalEntryCreate, JournalEntryResponse, JournalLineResponse,
    ARCreate, ARPaymentInput, ARResponse, ARSummaryResponse, ARSummaryItem,
)
from app.event_engine.service_enforcer import ConstraintBlocked

router = APIRouter(prefix="/accounting", tags=["accounting"])


# ─── Accounts ──────────────────────────────────────────────────────

@router.get("/accounts", response_model=dict)
async def list_accounts(
    account_type: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    accounts, total = await svc.list_accounts(db, account_type, skip, limit)
    return {
        "accounts": [
            AccountResponse(
                id=str(a.id), account_no=a.account_no, name=a.name,
                type=a.type, normal_balance=a.normal_balance,
                is_active=a.is_active, created_at=a.created_at,
            ) for a in accounts
        ],
        "total": total,
    }


@router.post("/accounts", response_model=AccountResponse, status_code=201)
async def create_account(data: AccountCreate, db: AsyncSession = Depends(get_db)):
    existing = await svc.get_account_by_no(db, data.account_no)
    if existing:
        raise HTTPException(400, f"Account already exists: {data.account_no}")
    a = await svc.create_account(
        db, data.account_no, data.name, data.type,
        data.normal_balance, data.is_active,
    )
    return AccountResponse(
        id=str(a.id), account_no=a.account_no, name=a.name,
        type=a.type, normal_balance=a.normal_balance,
        is_active=a.is_active, created_at=a.created_at,
    )


# ─── Journal Entries ───────────────────────────────────────────────

@router.get("/entries", response_model=dict)
async def list_entries(
    period: Optional[str] = Query(None),
    posted: Optional[bool] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    entries, total = await svc.list_journal_entries(db, period, posted, skip, limit)
    result = []
    for e in entries:
        lines = []
        for line in e.lines:
            lines.append(JournalLineResponse(
                id=str(line.id),
                account_no=line.account.account_no if line.account else "",
                account_name=line.account.name if line.account else "",
                debit=float(line.debit),
                credit=float(line.credit),
                description=line.description,
            ))
        result.append(JournalEntryResponse(
            id=str(e.id), entry_no=e.entry_no, description=e.description,
            entry_date=e.entry_date, period=e.period,
            source_type=e.source_type, source_id=e.source_id,
            created_by=e.created_by, created_at=e.created_at,
            posted=e.posted, lines=lines,
        ))
    return {"entries": result, "total": total}


@router.post("/entries", status_code=201)
async def create_entry(data: JournalEntryCreate, db: AsyncSession = Depends(get_db)):
    lines = [
        {
            "account_no": l.account_no,
            "debit": l.debit,
            "credit": l.credit,
            "description": l.description,
        }
        for l in data.lines
    ]
    try:
        entry = await svc.create_journal_entry(
            db, data.description, data.entry_date, lines,
            created_by=data.created_by,
            source_type=data.source_type, source_id=data.source_id,
            actor_role="api",
        )
    except ConstraintBlocked as e:
        raise HTTPException(422, detail={
            "error": "business_rule_violation",
            "operation": e.operation,
            "verdicts": [
                {"code": v.code, "message": v.message, "alternatives": v.alternatives}
                for v in e.verdicts
            ],
        })
    except ValueError as e:
        raise HTTPException(400, detail=str(e))
    return {
        "message": f"Journal entry {entry.entry_no} created",
        "entry_no": entry.entry_no,
        "id": str(entry.id),
        "posted": entry.posted,
    }


@router.post("/entries/{entry_id}/post")
async def post_entry(entry_id: str, db: AsyncSession = Depends(get_db)):
    try:
        uid = uuid.UUID(entry_id)
    except ValueError:
        raise HTTPException(400, "Invalid entry ID")
    try:
        entry = await svc.post_entry(db, uid, actor_role="api")
    except ValueError as e:
        raise HTTPException(400, detail=str(e))
    if not entry:
        raise HTTPException(404, "Journal entry not found")
    return {
        "message": f"Entry {entry.entry_no} posted",
        "entry_no": entry.entry_no,
        "posted": entry.posted,
    }


# ─── Period Close ──────────────────────────────────────────────────

@router.post("/periods/close")
async def close_period(period: str, closed_by: str = "system",
                       db: AsyncSession = Depends(get_db)):
    try:
        close_rec = await svc.close_period(db, period, closed_by, actor_role="api")
    except ConstraintBlocked as e:
        raise HTTPException(422, detail={
            "error": "business_rule_violation",
            "operation": e.operation,
            "verdicts": [
                {"code": v.code, "message": v.message, "alternatives": v.alternatives}
                for v in e.verdicts
            ],
        })
    except ValueError as e:
        raise HTTPException(400, detail=str(e))
    return {
        "message": f"Period {period} closed",
        "period": close_rec.period,
        "closed_at": close_rec.closed_at,
        "closed_by": close_rec.closed_by,
    }


@router.get("/periods", response_model=dict)
async def list_periods(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    closes, total = await svc.list_period_closes(db, skip, limit)
    return {
        "periods": [
            {
                "id": str(c.id),
                "period": c.period,
                "closed_at": c.closed_at,
                "closed_by": c.closed_by,
                "is_closed": c.is_closed,
            }
            for c in closes
        ],
        "total": total,
    }


# ─── Accounts Receivable ───────────────────────────────────────────

@router.get("/ar", response_model=dict)
async def list_ar(
    status: Optional[str] = Query(None),
    customer_name: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    items, total = await svc.list_ar(db, status, customer_name, skip, limit)
    return {
        "items": [
            ARResponse(
                id=str(ar.id), customer_name=ar.customer_name,
                invoice_no=ar.invoice_no, amount=float(ar.amount),
                due_date=ar.due_date, paid_amount=float(ar.paid_amount or 0),
                status=ar.status, created_at=ar.created_at,
            ) for ar in items
        ],
        "total": total,
    }


@router.post("/ar", response_model=ARResponse, status_code=201)
async def create_ar(data: ARCreate, db: AsyncSession = Depends(get_db)):
    ar = await svc.create_ar(db, data.customer_name, data.invoice_no,
                             data.amount, data.due_date)
    return ARResponse(
        id=str(ar.id), customer_name=ar.customer_name,
        invoice_no=ar.invoice_no, amount=float(ar.amount),
        due_date=ar.due_date, paid_amount=float(ar.paid_amount or 0),
        status=ar.status, created_at=ar.created_at,
    )


@router.post("/ar/{ar_id}/payment")
async def record_ar_payment(ar_id: str, data: ARPaymentInput,
                            db: AsyncSession = Depends(get_db)):
    try:
        uid = uuid.UUID(ar_id)
    except ValueError:
        raise HTTPException(400, "Invalid AR ID")
    ar = await svc.update_ar_payment(db, uid, data.paid_amount)
    if not ar:
        raise HTTPException(404, "AR record not found")
    return {
        "message": f"Payment recorded for {ar.customer_name} — invoice {ar.invoice_no}",
        "status": ar.status,
        "paid_amount": float(ar.paid_amount),
        "balance": round(float(ar.amount) - float(ar.paid_amount), 2),
    }


@router.get("/ar/overdue-summary", response_model=ARSummaryResponse)
async def ar_overdue_summary(db: AsyncSession = Depends(get_db)):
    summary = await svc.get_ar_summary(db)
    return ARSummaryResponse(
        total_overdue=summary["total_overdue"],
        total_amount=summary["total_amount"],
        items=[
            ARSummaryItem(**i) for i in summary["items"]
        ],
    )
