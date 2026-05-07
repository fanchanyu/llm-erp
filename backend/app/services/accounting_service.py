"""Accounting service — accounts, journal entries, AR, and period close."""
from __future__ import annotations
import uuid
from datetime import datetime, date
from typing import Optional
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.models.accounting import (
    Account, JournalEntry, JournalLine, AccountsReceivable, MonthEndClose,
)
from app.event_engine.service_enforcer import enforce


# ─── Accounts ──────────────────────────────────────────────────────

async def list_accounts(
    db: AsyncSession, account_type: Optional[str] = None,
    skip: int = 0, limit: int = 50,
) -> tuple[list[Account], int]:
    q = select(Account)
    if account_type:
        q = q.where(Account.type == account_type)
    count_q = select(func.count()).select_from(q.subquery())
    total = (await db.execute(count_q)).scalar() or 0
    result = await db.execute(
        q.offset(skip).limit(limit).order_by(Account.account_no)
    )
    return list(result.scalars().all()), total


async def get_account(db: AsyncSession, account_id: uuid.UUID) -> Optional[Account]:
    return await db.get(Account, account_id)


async def get_account_by_no(db: AsyncSession, account_no: str) -> Optional[Account]:
    result = await db.execute(
        select(Account).where(Account.account_no == account_no)
    )
    return result.scalar_one_or_none()


async def create_account(
    db: AsyncSession, account_no: str, name: str,
    type: str, normal_balance: str, is_active: bool = True,
) -> Account:
    acc = Account(
        account_no=account_no, name=name, type=type,
        normal_balance=normal_balance, is_active=is_active,
    )
    db.add(acc)
    await db.flush()
    return acc


# ─── Journal Entries ───────────────────────────────────────────────

async def _next_entry_no(db: AsyncSession) -> str:
    """Generate next entry number: JE-YYYYMMDD-XXX."""
    today = datetime.utcnow().strftime("%Y%m%d")
    result = await db.execute(
        select(func.count()).select_from(
            select(JournalEntry).where(
                JournalEntry.entry_no.like(f"JE-{today}-%")
            ).subquery()
        )
    )
    count = result.scalar() or 0
    return f"JE-{today}-{count + 1:03d}"


async def create_journal_entry(
    db: AsyncSession, description: str, entry_date: date,
    lines: list[dict], created_by: str = "system",
    source_type: Optional[str] = None, source_id: Optional[str] = None,
    actor_role: str = "",
) -> JournalEntry:
    """Create a journal entry with double-entry validation.

    lines = [{account_no, debit, credit, description?}]
    Raises ConstraintBlocked if business rules are violated.
    """
    # Validate double-entry: total debits must equal total credits
    total_debit = sum(l.get("debit", 0) or 0 for l in lines)
    total_credit = sum(l.get("credit", 0) or 0 for l in lines)
    if abs(total_debit - total_credit) > 0.001:
        raise ValueError(
            f"Double-entry violation: debits ({total_debit}) != credits ({total_credit})"
        )

    # Resolve account references
    resolved_lines = []
    for l in lines:
        acc = await get_account_by_no(db, l["account_no"])
        if not acc:
            raise ValueError(f"Account not found: {l['account_no']}")
        if not acc.is_active:
            raise ValueError(f"Account is inactive: {l['account_no']}")
        resolved_lines.append({
            "account_id": acc.id,
            "debit": l.get("debit", 0) or 0,
            "credit": l.get("credit", 0) or 0,
            "description": l.get("description"),
        })

    period = entry_date.strftime("%Y-%m")

    # Run constraint enforcement for inventory-related entries
    if source_type and source_type.upper() in ("PO", "INV", "WO", "RECEIPT"):
        enforce("inventory_movement", {
            "source_type": source_type,
            "source_id": source_id,
            "amount": total_debit,
            "period": period,
        }, actor_role=actor_role)

    entry_no = await _next_entry_no(db)
    entry = JournalEntry(
        entry_no=entry_no, description=description, entry_date=entry_date,
        period=period, source_type=source_type, source_id=source_id,
        created_by=created_by,
    )
    db.add(entry)
    await db.flush()

    for rl in resolved_lines:
        line = JournalLine(
            entry_id=entry.id, account_id=rl["account_id"],
            debit=rl["debit"], credit=rl["credit"],
            description=rl["description"],
        )
        db.add(line)

    await db.flush()
    return entry


async def list_journal_entries(
    db: AsyncSession, period: Optional[str] = None,
    posted: Optional[bool] = None, skip: int = 0, limit: int = 50,
) -> tuple[list[JournalEntry], int]:
    q = select(JournalEntry).options(
        selectinload(JournalEntry.lines).selectinload(JournalLine.account)
    )
    if period:
        q = q.where(JournalEntry.period == period)
    if posted is not None:
        q = q.where(JournalEntry.posted == posted)
    count_q = select(func.count()).select_from(q.subquery())
    total = (await db.execute(count_q)).scalar() or 0
    result = await db.execute(
        q.offset(skip).limit(limit).order_by(JournalEntry.entry_date.desc(),
                                              JournalEntry.entry_no.desc())
    )
    return list(result.scalars().all()), total


async def get_journal_entry(
    db: AsyncSession, entry_id: uuid.UUID,
) -> Optional[JournalEntry]:
    result = await db.execute(
        select(JournalEntry)
        .options(selectinload(JournalEntry.lines).selectinload(JournalLine.account))
        .where(JournalEntry.id == entry_id)
    )
    return result.scalar_one_or_none()


async def post_entry(
    db: AsyncSession, entry_id: uuid.UUID,
    actor_role: str = "",
) -> Optional[JournalEntry]:
    """Post a journal entry (mark as posted)."""
    entry = await get_journal_entry(db, entry_id)
    if not entry:
        return None
    if entry.posted:
        raise ValueError(f"Entry {entry.entry_no} is already posted")
    entry.posted = True
    await db.flush()
    return entry


# ─── Period Close ──────────────────────────────────────────────────

async def close_period(
    db: AsyncSession, period: str, closed_by: str = "system",
    actor_role: str = "",
) -> MonthEndClose:
    """Close an accounting period. Runs constraint enforcement first."""
    # Check if period already closed
    existing = await db.execute(
        select(MonthEndClose).where(MonthEndClose.period == period)
    )
    if existing.scalar_one_or_none():
        raise ValueError(f"Period {period} is already closed")

    # Run constraint enforcement
    enforce("close_period", {"period": period}, actor_role=actor_role)

    close_rec = MonthEndClose(
        period=period, closed_at=datetime.utcnow(),
        closed_by=closed_by, is_closed=True,
    )
    db.add(close_rec)
    await db.flush()
    return close_rec


async def list_period_closes(
    db: AsyncSession, skip: int = 0, limit: int = 50,
) -> tuple[list[MonthEndClose], int]:
    q = select(MonthEndClose)
    count_q = select(func.count()).select_from(q.subquery())
    total = (await db.execute(count_q)).scalar() or 0
    result = await db.execute(
        q.offset(skip).limit(limit).order_by(MonthEndClose.period.desc())
    )
    return list(result.scalars().all()), total


# ─── Accounts Receivable ───────────────────────────────────────────

async def list_ar(
    db: AsyncSession, status: Optional[str] = None,
    customer_name: Optional[str] = None,
    skip: int = 0, limit: int = 50,
) -> tuple[list[AccountsReceivable], int]:
    q = select(AccountsReceivable)
    if status:
        q = q.where(AccountsReceivable.status == status)
    if customer_name:
        q = q.where(AccountsReceivable.customer_name.ilike(f"%{customer_name}%"))
    count_q = select(func.count()).select_from(q.subquery())
    total = (await db.execute(count_q)).scalar() or 0
    result = await db.execute(
        q.offset(skip).limit(limit).order_by(AccountsReceivable.due_date)
    )
    return list(result.scalars().all()), total


async def create_ar(
    db: AsyncSession, customer_name: str, invoice_no: str,
    amount: float, due_date: date,
) -> AccountsReceivable:
    ar = AccountsReceivable(
        customer_name=customer_name, invoice_no=invoice_no,
        amount=amount, due_date=due_date, paid_amount=0,
        status="open",
    )
    db.add(ar)
    await db.flush()
    return ar


async def update_ar_payment(
    db: AsyncSession, ar_id: uuid.UUID, paid_amount: float,
) -> Optional[AccountsReceivable]:
    ar = await db.get(AccountsReceivable, ar_id)
    if not ar:
        return None

    ar.paid_amount = float(ar.paid_amount or 0) + paid_amount
    if ar.paid_amount >= ar.amount - 0.001:
        ar.status = "paid"
        ar.paid_amount = ar.amount
    elif ar.due_date < date.today():
        ar.status = "overdue"
    else:
        ar.status = "open"
    await db.flush()
    return ar


async def get_ar_summary(db: AsyncSession) -> dict:
    """Return overdue AR summary for constraint enforcement callers."""
    today = date.today()
    result = await db.execute(
        select(AccountsReceivable).where(
            and_(
                AccountsReceivable.status.in_(["open", "overdue"]),
                AccountsReceivable.due_date < today,
            )
        ).order_by(AccountsReceivable.due_date)
    )
    items = list(result.scalars().all())

    summary_items = []
    total_amount = 0.0
    for ar in items:
        overdue_days = (today - ar.due_date).days
        total_amount += float(ar.amount) - float(ar.paid_amount or 0)
        summary_items.append({
            "customer_name": ar.customer_name,
            "invoice_no": ar.invoice_no,
            "amount": float(ar.amount),
            "paid_amount": float(ar.paid_amount or 0),
            "due_date": ar.due_date,
            "overdue_days": overdue_days,
        })

    return {
        "total_overdue": len(summary_items),
        "total_amount": round(total_amount, 2),
        "items": summary_items,
    }
