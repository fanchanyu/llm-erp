"""Report generation service — queries the DB and produces formatted markdown reports."""
from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Optional

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.inventory import Part, Inventory
from app.models.purchase import Supplier, PurchaseOrder, PurchaseOrderItem
from app.models.dispatch import ProductionOrder, Operation, WorkCenter
from app.models.accounting import Account, JournalEntry, JournalLine, AccountsReceivable


# ═══════════════════════════════════════════════════════════════
# 1. Inventory Report
# ═══════════════════════════════════════════════════════════════

async def generate_inventory_report(db: AsyncSession) -> dict:
    """List all inventory items with stock levels, valuation, and status."""
    q = select(
        Part.part_no, Part.name, Part.spec, Part.unit, Part.category,
        Inventory.location, Inventory.quantity, Inventory.updated_at,
    ).join(Inventory, Part.id == Inventory.part_id, isouter=True).order_by(Part.part_no)

    result = await db.execute(q)
    rows = result.all()

    # Build markdown table rows
    lines = []
    total_items = 0
    total_qty = 0
    low_stock = 0

    lines.append(f"# 📦 庫存報表 / Inventory Report")
    lines.append(f"**產生時間 / Generated**: {datetime.utcnow().strftime('%Y-%m-%d %H:%M')} UTC")
    lines.append("")
    lines.append("| 料號 / Part No | 品名 / Name | 單位 | 庫存量 / Qty | 儲位 / Location | 類別 / Category |")
    lines.append("|---|---|---|---|---|---|")

    for r in rows:
        qty = float(r.quantity or 0)
        total_qty += qty
        total_items += 1
        if 0 < qty <= 10:
            low_stock += 1
        location = r.location or "—"
        category = r.category or "—"
        lines.append(f"| {r.part_no} | {r.name} | {r.unit} | {qty:,.0f} | {location} | {category} |")

    lines.append("")
    lines.append(f"**摘要 / Summary**")
    lines.append(f"- 品項數 / Total SKUs: **{total_items}**")
    lines.append(f"- 總庫存量 / Total Quantity: **{total_qty:,.0f}**")
    lines.append(f"- 低庫存品項 / Low Stock (≤10): **{low_stock}**")

    return {
        "markdown": "\n".join(lines),
        "title": "庫存報表 / Inventory Report",
        "filename": f"inventory-report-{datetime.utcnow().strftime('%Y%m%d')}.md",
    }


# ═══════════════════════════════════════════════════════════════
# 2. AR Aging Report
# ═══════════════════════════════════════════════════════════════

async def generate_ar_aging_report(db: AsyncSession) -> dict:
    """AR aging report with overdue analysis."""
    today = date.today()

    result = await db.execute(
        select(AccountsReceivable)
        .where(AccountsReceivable.status.in_(["open", "overdue"]))
        .order_by(AccountsReceivable.due_date)
    )
    items = list(result.scalars().all())

    lines = []
    lines.append(f"# 💰 應收帳款帳齡報表 / AR Aging Report")
    lines.append(f"**產生時間 / Generated**: {datetime.utcnow().strftime('%Y-%m-%d %H:%M')} UTC")
    lines.append(f"**基準日 / As of**: {today.isoformat()}")
    lines.append("")

    # Summary buckets
    current_amount = 0.0
    aging_1_30 = 0.0
    aging_31_60 = 0.0
    aging_61_90 = 0.0
    aging_90_plus = 0.0
    total_open = 0.0

    for ar in items:
        balance = float(ar.amount) - float(ar.paid_amount or 0)
        total_open += balance
        overdue_days = (today - ar.due_date).days if ar.due_date < today else 0

        if overdue_days <= 0:
            current_amount += balance
        elif overdue_days <= 30:
            aging_1_30 += balance
        elif overdue_days <= 60:
            aging_31_60 += balance
        elif overdue_days <= 90:
            aging_61_90 += balance
        else:
            aging_90_plus += balance

    lines.append("## 📊 帳齡分析 / Aging Summary")
    lines.append("")
    lines.append("| 帳齡區間 / Bucket | 金額 / Amount |")
    lines.append("|---|---|")
    lines.append(f"| 未逾期 / Current (≤0 days) | ${current_amount:,.2f} |")
    lines.append(f"| 1–30 天逾期 | ${aging_1_30:,.2f} |")
    lines.append(f"| 31–60 天逾期 | ${aging_31_60:,.2f} |")
    lines.append(f"| 61–90 天逾期 | ${aging_61_90:,.2f} |")
    lines.append(f"| 90 天以上逾期 | ${aging_90_plus:,.2f} |")
    lines.append(f"| **合計 / Total** | **${total_open:,.2f}** |")
    lines.append("")

    # Detail table
    overdue_items = [ar for ar in items if ar.due_date < today]
    lines.append("## 📋 逾期明細 / Overdue Details")
    lines.append("")
    if overdue_items:
        lines.append("| 客戶 / Customer | 發票號 / Invoice | 應收金額 / Amount | 已收金額 / Paid | 到期日 / Due | 逾期天數 / Days |")
        lines.append("|---|---|---|---|---|---|")
        for ar in overdue_items:
            overdue_days = (today - ar.due_date).days
            lines.append(
                f"| {ar.customer_name} | {ar.invoice_no} | ${ar.amount:,.2f} | "
                f"${float(ar.paid_amount or 0):,.2f} | {ar.due_date} | {overdue_days} |"
            )
    else:
        lines.append("*無逾期項目 / No overdue items*")

    lines.append("")
    lines.append(f"**逾期總戶數 / Overdue Accounts**: {len(overdue_items)}")
    lines.append(f"**逾期總金額 / Overdue Total**: ${aging_1_30 + aging_31_60 + aging_61_90 + aging_90_plus:,.2f}")

    return {
        "markdown": "\n".join(lines),
        "title": "應收帳款帳齡報表 / AR Aging Report",
        "filename": f"ar-aging-report-{today.isoformat()}.md",
    }


# ═══════════════════════════════════════════════════════════════
# 3. Purchase Report
# ═══════════════════════════════════════════════════════════════

async def generate_purchase_report(db: AsyncSession) -> dict:
    """PO status summary with supplier info."""
    # All POs with their items and suppliers
    result = await db.execute(
        select(PurchaseOrder)
        .options(
            selectinload(PurchaseOrder.supplier),
            selectinload(PurchaseOrder.items).selectinload(PurchaseOrderItem.part),
        )
        .order_by(PurchaseOrder.created_at.desc())
    )
    pos = list(result.scalars().all())

    lines = []
    lines.append(f"# 📋 採購報表 / Purchase Order Report")
    lines.append(f"**產生時間 / Generated**: {datetime.utcnow().strftime('%Y-%m-%d %H:%M')} UTC")
    lines.append("")

    # Status summary
    status_counts = {}
    total_amount = 0.0
    for po in pos:
        status_counts[po.status] = status_counts.get(po.status, 0) + 1
        for item in (po.items or []):
            if item.unit_price:
                total_amount += float(item.unit_price) * float(item.quantity)

    lines.append("## 📊 狀態總覽 / Status Summary")
    lines.append("")
    lines.append("| 狀態 / Status | 數量 / Count |")
    lines.append("|---|---|")
    for status, count in sorted(status_counts.items()):
        lines.append(f"| {status} | {count} |")
    lines.append(f"| **合計 / Total** | **{len(pos)}** |")
    lines.append(f"**採購總金額 / Total PO Amount**: ${total_amount:,.2f}")
    lines.append("")

    # Detailed list
    lines.append("## 📄 採購單明細 / PO Details")
    lines.append("")
    if pos:
        lines.append("| 單號 / PO No | 供應商 / Supplier | 狀態 / Status | 金額 / Amount | 建立日期 / Created |")
        lines.append("|---|---|---|---|---|")
        for po in pos:
            po_amount = sum(
                float(item.unit_price or 0) * float(item.quantity)
                for item in (po.items or [])
            )
            supplier_name = po.supplier.name if po.supplier else "—"
            created = po.created_at.strftime("%Y-%m-%d") if po.created_at else "—"
            lines.append(
                f"| {po.po_no} | {supplier_name} | {po.status} | "
                f"${po_amount:,.2f} | {created} |"
            )
    else:
        lines.append("*無採購單 / No purchase orders*")

    return {
        "markdown": "\n".join(lines),
        "title": "採購報表 / Purchase Order Report",
        "filename": f"purchase-report-{datetime.utcnow().strftime('%Y%m%d')}.md",
    }


# ═══════════════════════════════════════════════════════════════
# 4. Production Report
# ═══════════════════════════════════════════════════════════════

async def generate_production_report(db: AsyncSession) -> dict:
    """Work order progress report."""
    result = await db.execute(
        select(ProductionOrder)
        .options(selectinload(ProductionOrder.operations))
        .order_by(ProductionOrder.created_at.desc())
    )
    orders = list(result.scalars().all())

    # Also get work centers for context
    wc_result = await db.execute(select(WorkCenter))
    work_centers = list(wc_result.scalars().all())

    lines = []
    lines.append(f"# 🔧 生產報表 / Production Report")
    lines.append(f"**產生時間 / Generated**: {datetime.utcnow().strftime('%Y-%m-%d %H:%M')} UTC")
    lines.append("")

    # Status summary
    status_counts = {}
    for o in orders:
        status_counts[o.status] = status_counts.get(o.status, 0) + 1

    lines.append("## 📊 工單狀態 / Order Status Overview")
    lines.append("")
    lines.append("| 狀態 / Status | 數量 / Count |")
    lines.append("|---|---|")
    for status in ["draft", "released", "dispatched", "in_progress", "completed", "cancelled"]:
        count = status_counts.get(status, 0)
        lines.append(f"| {status} | {count} |")
    lines.append(f"| **合計 / Total** | **{len(orders)}** |")
    lines.append("")

    # Work center status
    lines.append("## 🏭 工作站狀態 / Work Center Status")
    lines.append("")
    lines.append("| 名稱 / Name | 狀態 / Status | 每日工時 / Capacity | 替代群組 / Alt Group |")
    lines.append("|---|---|---|---|")
    for wc in work_centers:
        lines.append(f"| {wc.name} | {wc.status} | {wc.capacity_hours}h | {wc.alternate_group or '—'} |")
    lines.append("")

    # Detailed work orders
    lines.append("## 📋 工單明細 / Order Details")
    lines.append("")
    if orders:
        lines.append("| 單號 / Order No | 產品 / Product | 數量 / Qty | 交期 / Due | 優先級 / Pri | 狀態 / Status | 工序數 / Ops |")
        lines.append("|---|---|---|---|---|---|---|")
        for o in orders:
            op_count = len(o.operations or [])
            lines.append(
                f"| {o.order_no} | {o.product_no} | {o.quantity:,.0f} | "
                f"{o.due_date} | {o.priority} | {o.status} | {op_count} |"
            )
    else:
        lines.append("*無工單 / No work orders*")

    return {
        "markdown": "\n".join(lines),
        "title": "生產報表 / Production Report",
        "filename": f"production-report-{datetime.utcnow().strftime('%Y%m%d')}.md",
    }


# ═══════════════════════════════════════════════════════════════
# 5. Monthly P&L Report
# ═══════════════════════════════════════════════════════════════

async def generate_monthly_pl_report(db: AsyncSession, period: str) -> dict:
    """Simple monthly profit/loss report for a given period (YYYY-MM)."""
    # Get journal entries for the period
    result = await db.execute(
        select(JournalEntry)
        .options(
            selectinload(JournalEntry.lines).selectinload(JournalLine.account),
        )
        .where(JournalEntry.period == period)
        .order_by(JournalEntry.entry_date)
    )
    entries = list(result.scalars().all())

    # Also get accounts for categorization
    acc_result = await db.execute(
        select(Account).order_by(Account.account_no)
    )
    accounts = {a.id: a for a in list(acc_result.scalars().all())}

    lines = []
    lines.append(f"# 📊 損益表 / Profit & Loss Statement")
    lines.append(f"**期間 / Period**: {period}")
    lines.append(f"**產生時間 / Generated**: {datetime.utcnow().strftime('%Y-%m-%d %H:%M')} UTC")
    lines.append("")

    # Classify entries by account type
    revenue_total = 0.0
    expense_total = 0.0
    revenue_details = {}
    expense_details = {}

    for entry in entries:
        for jl in (entry.lines or []):
            acc = accounts.get(jl.account_id)
            if not acc:
                continue
            credit = float(jl.credit or 0)
            debit = float(jl.debit or 0)

            if acc.type == "revenue":
                amount = credit - debit
                if amount > 0:
                    revenue_total += amount
                    revenue_details[acc.name] = revenue_details.get(acc.name, 0) + amount
            elif acc.type == "expense":
                amount = debit - credit
                if amount > 0:
                    expense_total += amount
                    expense_details[acc.name] = expense_details.get(acc.name, 0) + amount

    # Revenue section
    lines.append("## 💵 收入 / Revenue")
    lines.append("")
    if revenue_details:
        lines.append("| 科目 / Account | 金額 / Amount |")
        lines.append("|---|---|")
        for name, amount in sorted(revenue_details.items()):
            lines.append(f"| {name} | ${amount:,.2f} |")
        lines.append(f"| **收入合計 / Total Revenue** | **${revenue_total:,.2f}** |")
    else:
        lines.append("*無收入資料 / No revenue data*")
    lines.append("")

    # Expense section
    lines.append("## 💸 費用 / Expenses")
    lines.append("")
    if expense_details:
        lines.append("| 科目 / Account | 金額 / Amount |")
        lines.append("|---|---|")
        for name, amount in sorted(expense_details.items()):
            lines.append(f"| {name} | ${amount:,.2f} |")
        lines.append(f"| **費用合計 / Total Expenses** | **${expense_total:,.2f}** |")
    else:
        lines.append("*無費用資料 / No expense data*")
    lines.append("")

    # Net profit/loss
    net = revenue_total - expense_total
    lines.append("## 📋 損益摘要 / P&L Summary")
    lines.append("")
    lines.append(f"| 項目 / Item | 金額 / Amount |")
    lines.append("|---|---|")
    lines.append(f"| 收入總額 / Total Revenue | ${revenue_total:,.2f} |")
    lines.append(f"| 費用總額 / Total Expenses | ${expense_total:,.2f} |")
    lines.append(f"| **淨利 / Net Profit** | **${net:,.2f}** |")
    lines.append("")
    lines.append(f"**記錄的交易筆數 / Journal Entries**: {len(entries)}")

    return {
        "markdown": "\n".join(lines),
        "title": f"損益表 / P&L Statement ({period})",
        "filename": f"pl-statement-{period}.md",
    }
