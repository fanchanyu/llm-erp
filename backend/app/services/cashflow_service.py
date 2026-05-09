"""
Cash Flow Service — 現金流預測與可行性檢查

Provides functions to query current cash position, project future cash,
and check whether proposed purchases or rush orders are financially feasible
based on cash flow constraints.

現金流服務 — 查詢即時現金水位、預測未來現金流、判斷採購/急單的財務可行性。
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any, Optional

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.accounting import Account, JournalLine, AccountsReceivable
from app.models.purchase import PurchaseOrder, PurchaseOrderItem


# ═══════════════════════════════════════════════════════════════
# Cash Position — 即時現金水位
# ═══════════════════════════════════════════════════════════════

async def get_cash_position(db: AsyncSession) -> dict:
    """Query the current cash and bank account balance.

    查詢即時現金及銀行存款水位。

    Computes: sum(account 1101 [cash] + 1102 [bank]) debit balance - credit balance.
    For asset-type accounts (normal_balance='debit'), balance = sum(debits) - sum(credits).

    Returns:
        dict with keys:
        - cash_balance: float — balance of account 1101 (cash on hand)
        - bank_balance: float — balance of account 1102 (bank deposits)
        - total_cash: float — sum of cash + bank
        - currency: str — "TWD" (default display unit)
    """
    cash_accounts = {
        "1101": "cash",
        "1102": "bank",
    }

    balances = {}
    for acct_no, label in cash_accounts.items():
        # Find the account record
        acct_result = await db.execute(
            select(Account).where(Account.account_no == acct_no)
        )
        account = acct_result.scalar_one_or_none()

        if not account:
            balances[label] = 0.0
            continue

        # Sum debits and credits from journal lines for this account
        debit_result = await db.execute(
            select(func.coalesce(func.sum(JournalLine.debit), 0))
            .where(JournalLine.account_id == account.id)
        )
        total_debit = float(debit_result.scalar() or 0.0)

        credit_result = await db.execute(
            select(func.coalesce(func.sum(JournalLine.credit), 0))
            .where(JournalLine.account_id == account.id)
        )
        total_credit = float(credit_result.scalar() or 0.0)

        # Asset accounts have normal_balance='debit': balance = debits - credits
        if account.normal_balance == "debit":
            balance = total_debit - total_credit
        else:
            balance = total_credit - total_debit

        balances[label] = round(balance, 2)

    total_cash = round(balances.get("cash", 0.0) + balances.get("bank", 0.0), 2)

    return {
        "cash_balance": balances.get("cash", 0.0),
        "bank_balance": balances.get("bank", 0.0),
        "total_cash": total_cash,
        "currency": "TWD",
    }


# ═══════════════════════════════════════════════════════════════
# Projected Cash — 現金流預測
# ═══════════════════════════════════════════════════════════════

async def get_projected_cash(db: AsyncSession, days: int = 30) -> dict:
    """Project cash position over a given number of days.

    預測未來 N 天內的現金流變化。

    Projection formula:
      projected_balance = current_cash
                         + AR_expected_receipts (due within N days, excluding paid)
                         - AP_expected_payments (from PO items received but not fully paid)

    Args:
        db: Database session
        days: Number of days to project forward (default: 30)

    Returns:
        dict with keys:
        - current_cash: float
        - projected_balance: float
        - expected_inflows: list[dict] — AR receipts expected
        - expected_outflows: list[dict] — AP payments expected
        - days: int
        - projection_date: str (isoformat)
    """
    today = date.today()
    cutoff_date = today + timedelta(days=days)

    # ── 1. Current cash ────────────────────────────────────────────
    cash_pos = await get_cash_position(db)
    current_cash = cash_pos["total_cash"]

    # ── 2. Expected AR inflows (due within N days, excluding paid) ──
    ar_result = await db.execute(
        select(AccountsReceivable).where(
            and_(
                AccountsReceivable.status.in_(["open", "overdue"]),
                AccountsReceivable.due_date <= cutoff_date,
            )
        ).order_by(AccountsReceivable.due_date)
    )
    ar_records = list(ar_result.scalars().all())

    expected_inflows = []
    total_ar_inflow = 0.0
    for ar in ar_records:
        remaining = float(ar.amount) - float(ar.paid_amount or 0)
        if remaining > 0.01:
            total_ar_inflow += remaining
            expected_inflows.append({
                "customer_name": ar.customer_name,
                "invoice_no": ar.invoice_no,
                "amount": float(ar.amount),
                "paid_amount": float(ar.paid_amount or 0),
                "remaining": round(remaining, 2),
                "due_date": ar.due_date.isoformat(),
                "status": ar.status,
            })

    # ── 3. Expected AP outflows (from PO items received but not fully paid) ──
    # Simplified: find PurchaseOrders with status 'partial' or 'received',
    # and estimate pending payment as (quantity * unit_price) for items
    # that have been received but not yet fully accounted for.
    # We check JournalEntries with source_type='PO' to see what's been booked.
    po_result = await db.execute(
        select(PurchaseOrder).where(
            PurchaseOrder.status.in_(["partial", "received", "sent"])
        )
    )
    po_records = list(po_result.scalars().all())

    expected_outflows = []
    total_ap_outflow = 0.0

    for po in po_records:
        # Get items for this PO
        items_result = await db.execute(
            select(PurchaseOrderItem).where(
                PurchaseOrderItem.po_id == po.id
            )
        )
        items = list(items_result.scalars().all())

        for item in items:
            if float(item.received_qty or 0) <= 0:
                continue

            # Expected payment for received items
            unit_price = float(item.unit_price or 0)
            received_qty = float(item.received_qty or 0)
            total_value = unit_price * received_qty

            # Check if journal entries already recorded for this PO
            # (simplified: count any journal lines referencing the PO)
            je_count_result = await db.execute(
                select(func.count())
                .select_from(JournalLine)
                .join(Account, JournalLine.account_id == Account.id)
                .where(
                    and_(
                        Account.account_no.in_(["2101", "2102"]),  # AP accounts
                        JournalLine.entry_id.in_(
                            select(JournalLine.entry_id).where(
                                JournalLine.description.ilike(f"%{po.po_no}%")
                            )
                        ),
                    )
                )
            )
            booked_count = je_count_result.scalar() or 0

            if booked_count == 0:
                # No AP entry yet — add to expected outflows
                pending = round(total_value, 2)
                if pending > 0.01:
                    total_ap_outflow += pending
                    expected_outflows.append({
                        "po_no": po.po_no,
                        "item_part_id": str(item.part_id),
                        "received_qty": received_qty,
                        "unit_price": unit_price,
                        "estimated_payment": pending,
                        "status": po.status,
                    })

    # ── 4. Compute projection ──────────────────────────────────────
    projected_balance = round(current_cash + total_ar_inflow - total_ap_outflow, 2)

    return {
        "current_cash": current_cash,
        "projected_balance": projected_balance,
        "expected_inflow_total": round(total_ar_inflow, 2),
        "expected_outflow_total": round(total_ap_outflow, 2),
        "net_change": round(total_ar_inflow - total_ap_outflow, 2),
        "expected_inflows": expected_inflows,
        "expected_outflows": expected_outflows,
        "days": days,
        "projection_date": cutoff_date.isoformat(),
        "currency": "TWD",
    }


# ═══════════════════════════════════════════════════════════════
# Purchase Feasibility — 採購可行性檢查
# ═══════════════════════════════════════════════════════════════

async def check_purchase_feasibility(
    db: AsyncSession,
    po_amount: float,
    po_date: Optional[date] = None,
) -> dict:
    """Check whether a proposed purchase order is feasible given cash flow.

    檢查新的採購訂單是否在現金流可承擔範圍內。

    Evaluates whether the cash position (current + projected inflows before
    the PO's payment date) can cover the PO amount.

    Args:
        db: Database session
        po_amount: Total amount of the proposed purchase order
        po_date: Expected payment date for the PO (default: 30 days from now)

    Returns:
        dict with keys:
        - feasible: bool
        - projected_balance: float (projected cash at payment date)
        - current_cash: float
        - po_amount: float
        - warnings: list[str]
        - alternatives: list[str]
    """
    payment_date = po_date or (date.today() + timedelta(days=30))
    today = date.today()
    days_to_payment = max((payment_date - today).days, 0)

    # Get current cash
    cash_pos = await get_cash_position(db)
    current_cash = cash_pos["total_cash"]

    # Get AR inflows expected before payment date
    ar_result = await db.execute(
        select(AccountsReceivable).where(
            and_(
                AccountsReceivable.status.in_(["open", "overdue"]),
                AccountsReceivable.due_date <= payment_date,
            )
        )
    )
    ar_records = list(ar_result.scalars().all())
    expected_inflow = sum(
        float(ar.amount) - float(ar.paid_amount or 0)
        for ar in ar_records
    )

    # Simplified: no AP outflows before this PO's payment date
    projected_cash = round(current_cash + expected_inflow, 2)
    balance_after_po = round(projected_cash - po_amount, 2)

    # Evaluate feasibility
    warnings = []
    alternatives = []

    if balance_after_po < 0:
        feasible = False
        shortfall = round(-balance_after_po, 2)
        warnings.append(
            f"Insufficient cash: shortfall of {shortfall} TWD "
            f"after PO payment. "
            f"/ 現金不足：支付後短缺 {shortfall} 元。"
        )
        if days_to_payment > 7:
            alternatives.append(
                f"Delay PO payment by {days_to_payment + 15} days "
                f"to allow more AR collections. "
                f"/ 延後付款 {days_to_payment + 15} 天，增加應收回收時間。"
            )
        alternatives.append(
            "Request a supplier credit term extension. "
            "/ 請供應商延長信用期限。"
        )
        alternatives.append(
            "Split PO into smaller installments. "
            "/ 將採購單拆分為多期付款。"
        )
    elif balance_after_po < projected_cash * 0.1:
        feasible = True
        warnings.append(
            f"Cash ratio after PO is low ({balance_after_po} TWD). "
            f"Monitor closely. "
            f"/ 支付後現金水位偏低 ({balance_after_po} 元)，請密切關注。"
        )
        alternatives.append(
            "Consider partial payment to maintain higher cash buffer. "
            "/ 考慮部分付款以保持較高現金緩衝。"
        )
    else:
        feasible = True

    return {
        "feasible": feasible,
        "projected_balance": projected_cash,
        "balance_after_po": balance_after_po,
        "current_cash": current_cash,
        "expected_inflow_before_payment": round(expected_inflow, 2),
        "po_amount": round(po_amount, 2),
        "payment_date": payment_date.isoformat(),
        "days_to_payment": days_to_payment,
        "warnings": warnings,
        "alternatives": alternatives,
        "currency": "TWD",
    }


# ═══════════════════════════════════════════════════════════════
# Rush Order Cash Flow — 急單現金流影響
# ═══════════════════════════════════════════════════════════════

async def check_rush_order_cash_flow(
    db: AsyncSession,
    so_amount: float,
    premium_amount: float,
) -> dict:
    """Check whether accepting a rush order improves the cash position.

    檢查急單是否能夠改善現金流狀況。

    A rush order typically brings in premium revenue sooner than a regular
    order. This function evaluates:
    - Cash position before rush
    - Projected position with rush (so_amount + premium)
    - Whether the rush accelerates cash inflow vs. a regular order

    Args:
        db: Database session
        so_amount: Base order amount (without premium)
        premium_amount: Additional premium charged for rush

    Returns:
        dict with keys:
        - improves_cash: bool
        - current_cash: float
        - cash_with_rush: float
        - rush_inflow: float
        - cash_without_rush: float (regular order — no premium, slower payment)
        - advantage: float
        - details: str
    """
    cash_pos = await get_cash_position(db)
    current_cash = cash_pos["total_cash"]

    total_rush_inflow = round(so_amount + premium_amount, 2)

    # Without rush: regular order — typically no premium, payment slower
    # (simplified: assume regular order = base amount only)
    regular_inflow = round(so_amount, 2)

    # Rush premium typically means faster payment (customer pays premium
    # for speed, so payment terms may be shorter)
    # Simplified: rush brings in the premium component as additional cash
    cash_with_rush = round(current_cash + total_rush_inflow, 2)
    cash_without_rush = round(current_cash + regular_inflow, 2)

    advantage = round(total_rush_inflow - regular_inflow, 2)

    improves_cash = advantage > 0

    if improves_cash:
        details = (
            f"Rush order generates an additional {advantage} TWD in cash "
            f"vs. a regular order (premium of {premium_amount} TWD). "
            f"Cash position improves from {current_cash} to {cash_with_rush}. "
            f"/ 急單比常規訂單多產生 {advantage} 元現金（溢價 {premium_amount} 元），"
            f"現金水位從 {current_cash} 提升至 {cash_with_rush}。"
        )
    else:
        details = (
            f"Rush order would not improve cash position. "
            f"/ 急單不會改善現金水位。"
        )

    return {
        "improves_cash": improves_cash,
        "current_cash": current_cash,
        "cash_with_rush": cash_with_rush,
        "cash_without_rush": cash_without_rush,
        "rush_inflow": total_rush_inflow,
        "regular_inflow": regular_inflow,
        "premium_amount": round(premium_amount, 2),
        "advantage": advantage,
        "details": details,
        "currency": "TWD",
    }
