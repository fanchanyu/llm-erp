"""
MPS Service — Master Production Schedule Calculation Engine

Core MPS logic following APICS / CPIM standards:
1. Determine Gross Requirement per time period
2. Calculate Projected Available Balance (PAB)
3. Determine if a new planned order is needed (lot sizing rules)
4. Calculate Available To Promise (ATP)
5. Apply Time Fence boundaries (DTF / PTF)
6. Generate exception messages

Lot sizing rules supported:
- Lot-for-lot (L4L): order exactly what is needed
- Fixed Quantity (FOQ): order in multiples of a fixed lot size
- Period Order (PO): accumulate demand across N periods
"""

import math
import uuid
from datetime import datetime, date, timedelta
from typing import Optional
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.mps import (
    MpsMaster, MpsEntry, TimeFence,
    MpsStatus, MpsEntryStatus, TimeFenceType, LotSizingRule,
)


def _u(val: str) -> uuid.UUID:
    """Convert string/UUID to UUID object for SQLAlchemy Uuid columns."""
    if isinstance(val, uuid.UUID):
        return val
    return uuid.UUID(val) if val else uuid.uuid4()


from app.models.bom import Product


# ═══════════════════════════════════════════════════════════
# Helper: 取得週的起始日 (星期一)
# ═══════════════════════════════════════════════════════════

def _week_start(d: date) -> date:
    """Return the Monday of the week containing date d."""
    return d - timedelta(days=d.weekday())


def _weeks_between(start: date, end: date) -> list[date]:
    """Generate list of Monday dates between start and end (inclusive)."""
    weeks = []
    current = _week_start(start)
    end_monday = _week_start(end)
    while current <= end_monday:
        weeks.append(current)
        current += timedelta(days=7)
    return weeks


# ═══════════════════════════════════════════════════════════
# MPS Master CRUD
# ═══════════════════════════════════════════════════════════

async def create_mps_master(db: AsyncSession, **kw) -> MpsMaster:
    """Create a new MPS master record."""
    master = MpsMaster(**kw)
    db.add(master)
    await db.flush()
    return master


async def get_mps_master(db: AsyncSession, mps_id: str = "") -> MpsMaster | None:
    """Get MPS master by ID, eagerly loaded with entries and time fences."""
    q = select(MpsMaster).options(
        selectinload(MpsMaster.entries),
        selectinload(MpsMaster.time_fences),
    )
    if mps_id:
        q = q.where(MpsMaster.id == _u(mps_id))
    r = await db.execute(q)
    return r.scalar_one_or_none()


async def list_mps_masters(db: AsyncSession, status: str = "", limit: int = 50) -> list[MpsMaster]:
    """List MPS masters, optionally filtered by status."""
    q = select(MpsMaster)
    if status:
        q = q.where(MpsMaster.status == status)
    r = await db.execute(q.order_by(MpsMaster.created_at.desc()).limit(limit))
    return list(r.scalars().all())


async def update_mps_master(db: AsyncSession, mps_id: str, **kw) -> MpsMaster | None:
    """Update MPS master fields."""
    master = await get_mps_master(db, mps_id=mps_id)
    if not master:
        return None
    for k, v in kw.items():
        if v is not None:
            setattr(master, k, v)
    await db.flush()
    return master


# ═══════════════════════════════════════════════════════════
# MPS Entry CRUD
# ═══════════════════════════════════════════════════════════

async def create_mps_entry(db: AsyncSession, **kw) -> MpsEntry:
    """Create a single MPS entry (one time period)."""
    entry = MpsEntry(**kw)
    db.add(entry)
    await db.flush()
    return entry


async def get_mps_entries(
    db: AsyncSession, mps_id: str, product_no: str = "",
) -> list[MpsEntry]:
    """Get all entries for an MPS master, optionally filtered by product."""
    q = select(MpsEntry).where(MpsEntry.mps_id == _u(mps_id))
    if product_no:
        q = q.where(MpsEntry.product_no == product_no)
    r = await db.execute(q.order_by(MpsEntry.period_week))
    return list(r.scalars().all())


async def bulk_create_entries(db: AsyncSession, entries: list[MpsEntry]) -> list[MpsEntry]:
    """Bulk insert MPS entries."""
    db.add_all(entries)
    await db.flush()
    return entries


# ═══════════════════════════════════════════════════════════
# Time Fence CRUD
# ═══════════════════════════════════════════════════════════

async def create_time_fence(db: AsyncSession, **kw) -> TimeFence:
    """Create a time fence."""
    tf = TimeFence(**kw)
    db.add(tf)
    await db.flush()
    return tf


async def get_time_fences(db: AsyncSession, mps_id: str) -> list[TimeFence]:
    """Get all time fences for an MPS master."""
    r = await db.execute(
        select(TimeFence)
        .where(TimeFence.mps_id == _u(mps_id))
        .order_by(TimeFence.fence_week)
    )
    return list(r.scalars().all())


# ═══════════════════════════════════════════════════════════
# MPS Calculation Engine (核心引擎)
# ═══════════════════════════════════════════════════════════

async def calculate_mps(
    db: AsyncSession,
    mps_id: str,
    starting_inventory: float,
    forecast_consume: bool = True,
    include_existing_orders: bool = True,
    recalculate_atp: bool = True,
) -> dict:
    """
    Execute full time-phased MPS calculation.

    Steps:
    1. Load MPS master + time fences
    2. Generate week periods from start_week to end_week
    3. Load or create MpsEntry records for each period
    4. Determine Gross Requirement per period
       - If forecast_consume: use FAS logic (forecast consumed by orders)
       - Else: GrossReq = max(forecast_qty, customer_orders_qty)
    5. Calculate PAB (Projected Available Balance) period by period
    6. Determine if a planned order is needed, apply lot sizing rule
    7. Calculate ATP (Available To Promise)
    8. Apply time fence boundaries and generate exception messages
    9. Persist results and return calculation result
    """
    # ── Step 1: Load MPS master with relations ──
    master = await get_mps_master(db, mps_id=mps_id)
    if not master:
        return {"error": f"MPS master {mps_id} not found"}

    # ── Step 1b: Load product info ──
    # (We'll infer product_no from existing entries or leave generic)

    # ── Step 2: Generate week periods ──
    week_mondays = _weeks_between(master.start_week, master.end_week)

    # ── Step 2b: Load time fences and build lookup ──
    time_fences = await get_time_fences(db, mps_id=mps_id)
    dtf_week: date | None = None
    ptf_week: date | None = None
    for tf in time_fences:
        if tf.fence_type == TimeFenceType.DEMAND_TIME_FENCE.value:
            dtf_week = tf.fence_week
        elif tf.fence_type == TimeFenceType.PLANNING_TIME_FENCE.value:
            ptf_week = tf.fence_week

    # ── Step 3: Load existing entries ──
    existing_entries = await get_mps_entries(db, mps_id=mps_id)
    entry_map: dict[str, MpsEntry] = {}
    for e in existing_entries:
        key = f"{e.product_no}|{e.period_week.isoformat()}"
        entry_map[key] = e

    # Group entries by product_no
    products_in_mps: set[str] = set()
    for e in existing_entries:
        products_in_mps.add(e.product_no)

    if not products_in_mps:
        return {"error": "No products found in MPS. Please add MpsEntry records first."}

    # ── Prepare result containers ──
    all_results = {}
    exception_count = 0
    below_safety_count = 0
    within_dtf_count = 0

    # Process each product
    for product_no in sorted(products_in_mps):
        product_entries = [e for e in existing_entries if e.product_no == product_no]
        product_name = product_entries[0].product_name if product_entries else ""

        # Sort entries by period
        product_entries.sort(key=lambda e: e.period_week)

        period_results = []
        running_pab = starting_inventory

        # ── Step 4 & 5 & 6: Main calculation loop ──
        for i, week_monday in enumerate(week_mondays):
            week_number = i + 1
            key = f"{product_no}|{week_monday.isoformat()}"
            entry = entry_map.get(key)

            if entry:
                forecast_qty = entry.forecast_qty or 0
                customer_orders_qty = entry.customer_orders_qty or 0
                scheduled_receipts = entry.scheduled_receipts or 0
                product_name = entry.product_name or product_name
            else:
                forecast_qty = 0
                customer_orders_qty = 0
                scheduled_receipts = 0

            # ── Step 4: Determine Gross Requirement ──
            if forecast_consume:
                # Forecast Consumption (FAS) logic:
                # Start with forecast, subtract customer orders up to forecast
                remaining_fcst = forecast_qty
                consumed = min(customer_orders_qty, remaining_fcst)
                gross_req = forecast_qty  # Always at least forecast
                # The remaining customer orders beyond forecast are additional demand
                extra_orders = max(0, customer_orders_qty - remaining_fcst)
                gross_req = forecast_qty + extra_orders
            else:
                # Simple method: GrossReq = max(forecast, customer orders)
                gross_req = max(forecast_qty, customer_orders_qty)

            # ── Determine time fence type for this period ──
            tf_type = None
            if dtf_week and week_monday <= dtf_week:
                tf_type = TimeFenceType.DEMAND_TIME_FENCE.value
                within_dtf_count += 1
            elif ptf_week and week_monday <= ptf_week:
                tf_type = TimeFenceType.PLANNING_TIME_FENCE.value

            # ── Step 5: Calculate PAB ──
            # PAB = previous PAB + scheduled_receipts - gross_requirement
            pab = running_pab + scheduled_receipts - gross_req

            # ── Step 6: Determine if planned order is needed ──
            planned_order_qty = 0
            planned_order_release = None
            exception_msg = None

            # Check if PAB would go below safety stock
            if pab < master.safety_stock and gross_req > 0:
                # Need a planned order
                if master.lot_sizing_rule == LotSizingRule.LOT_FOR_LOT.value:
                    # L4L: order exactly the shortage
                    planned_order_qty = (master.safety_stock - pab) + gross_req
                elif master.lot_sizing_rule == LotSizingRule.FIXED_QUANTITY.value:
                    # FOQ: order in multiples of fixed_lot_qty
                    lot_size = master.fixed_lot_qty or 100
                    shortage = (master.safety_stock - pab) + gross_req
                    planned_order_qty = math.ceil(shortage / lot_size) * lot_size
                elif master.lot_sizing_rule == LotSizingRule.PERIOD_ORDER.value:
                    # PO: accumulate demand for the next N periods (simplified: 1 period)
                    planned_order_qty = gross_req + max(0, master.safety_stock - pab)

                # Planned order release = offset by lead time (simplified: same period)
                planned_order_release = week_monday

                # Recalculate PAB with planned order included (in current period)
                pab = running_pab + scheduled_receipts + planned_order_qty - gross_req

            # Check safety stock exception
            if pab < master.safety_stock:
                exception_msg = (exception_msg or "") + f"PAB ({pab}) below safety stock ({master.safety_stock}); "
                below_safety_count += 1

            # Check DTF violation
            if tf_type == TimeFenceType.DEMAND_TIME_FENCE.value and planned_order_qty > 0:
                exception_msg = (exception_msg or "") + "Planned order inside DTF — requires confirmation; "
                exception_count += 1

            # ── Step 7: ATP will be calculated after all periods ──
            atp = 0  # Will be recalculated

            # ── Update or create entry ──
            if entry:
                entry.gross_requirement = gross_req
                entry.projected_balance = pab
                entry.planned_order_qty = planned_order_qty
                entry.planned_order_release = planned_order_release
                entry.available_to_promise = atp
                entry.time_fence_type = tf_type
                entry.status = MpsEntryStatus.PLANNED.value if planned_order_qty > 0 else MpsEntryStatus.FIRM.value
                entry.exception_message = exception_msg.strip() if exception_msg else None
            else:
                entry = MpsEntry(
                    id=uuid.uuid4(),
                    mps_id=mps_id,
                    product_no=product_no,
                    product_name=product_name,
                    period_week=week_monday,
                    week_number=week_number,
                    forecast_qty=forecast_qty,
                    customer_orders_qty=customer_orders_qty,
                    gross_requirement=gross_req,
                    scheduled_receipts=scheduled_receipts,
                    projected_balance=pab,
                    planned_order_qty=planned_order_qty,
                    planned_order_release=planned_order_release,
                    available_to_promise=atp,
                    time_fence_type=tf_type,
                    status=MpsEntryStatus.PLANNED.value if planned_order_qty > 0 else MpsEntryStatus.FIRM.value,
                    exception_message=exception_msg.strip() if exception_msg else None,
                )
                db.add(entry)

            running_pab = pab

            period_results.append({
                "period_week": week_monday,
                "week_number": week_number,
                "forecast_qty": forecast_qty,
                "customer_orders_qty": customer_orders_qty,
                "gross_requirement": gross_req,
                "scheduled_receipts": scheduled_receipts,
                "projected_balance": pab,
                "planned_order_qty": planned_order_qty,
                "planned_order_release": planned_order_release,
                "available_to_promise": 0,  # Updated in ATP pass
                "time_fence_type": tf_type,
                "exception_message": exception_msg.strip() if exception_msg else None,
            })

        # ── Step 7: Recalculate ATP (backward pass) ──
        if recalculate_atp:
            atp_results = _calculate_atp(
                period_results, starting_inventory, dtf_week
            )
            for idx, atp_val in enumerate(atp_results):
                period_results[idx]["available_to_promise"] = atp_val
                # Also update DB entry
                entry_key = f"{product_no}|{period_results[idx]['period_week'].isoformat()}"
                db_entry = entry_map.get(entry_key) or (
                    # Find the newly created entry by period_week
                    next((e for e in db.new if isinstance(e, MpsEntry)
                          and e.mps_id == _u(mps_id) and e.period_week == period_results[idx]['period_week']), None)
                )
                if db_entry:
                    db_entry.available_to_promise = atp_val

        # Check the key from existing entries first, then check db.new
        # Actually let's do a simpler approach: re-scan entries
        updated_entries = await get_mps_entries(db, mps_id=mps_id, product_no=product_no)
        for pr in period_results:
            for ue in updated_entries:
                if ue.period_week == pr["period_week"]:
                    ue.available_to_promise = pr["available_to_promise"]
                    break

        all_results[product_no] = {
            "product_no": product_no,
            "product_name": product_name,
            "periods": period_results,
            "summary": {
                "total_periods": len(period_results),
                "periods_with_exceptions": sum(1 for p in period_results if p["exception_message"]),
                "periods_below_safety_stock": sum(1 for p in period_results
                                                  if p["projected_balance"] < master.safety_stock),
                "periods_within_dtf": sum(1 for p in period_results
                                          if p["time_fence_type"] == TimeFenceType.DEMAND_TIME_FENCE.value),
                "final_projected_balance": period_results[-1]["projected_balance"] if period_results else 0,
                "has_exceptions": any(p["exception_message"] for p in period_results),
                "lot_sizing_rule": master.lot_sizing_rule,
            },
        }

    # ── Persist ──
    await db.flush()

    # Build overall response
    first_product = next(iter(all_results.values())) if all_results else {}
    periods = first_product.get("periods", []) if first_product else []
    summary = first_product.get("summary", {}) if first_product else {}

    return {
        "mps_id": str(mps_id),
        "mps_name": master.name,
        "product_no": list(products_in_mps)[0] if products_in_mps else "",
        "product_name": "",
        "starting_inventory": starting_inventory,
        "total_forecast": sum(p["forecast_qty"] for p in periods),
        "total_customer_orders": sum(p["customer_orders_qty"] for p in periods),
        "total_planned_orders": sum(p["planned_order_qty"] for p in periods),
        "periods": periods,
        "summary": summary,
        "products": {
            pno: info["summary"] for pno, info in all_results.items()
        },
    }


# ═══════════════════════════════════════════════════════════
# ATP Calculation (可供約量計算)
# ═══════════════════════════════════════════════════════════

def _calculate_atp(
    periods: list[dict],
    starting_inventory: float,
    dtf_week: date | None,
) -> list[float]:
    """
    Calculate Available To Promise (ATP) using standard discrete ATP logic.

    ATP is computed in a backward/forward pass:
    - In the first period (or first period inside DTF): ATP = on-hand + scheduled_receipts
      - cumulative customer orders up to (but not including) next scheduled receipt period
    - In subsequent periods with scheduled receipts:
      ATP = scheduled_receipts - customer orders up to next scheduled receipt period
    - Periods without scheduled receipts: ATP = 0 (they draw from previous ATP)
    """
    num_periods = len(periods)
    atp_values = [0.0] * num_periods

    if num_periods == 0:
        return atp_values

    # Find periods with scheduled receipts or planned orders
    # Standard ATP logic focuses on periods where supply arrives
    supply_periods = []
    for i, p in enumerate(periods):
        if p["scheduled_receipts"] > 0 or p["planned_order_qty"] > 0 or i == 0:
            supply_periods.append(i)

    # Calculate ATP for each supply period
    for idx, supply_idx in enumerate(supply_periods):
        # Determine the range of customer orders this ATP covers
        if idx + 1 < len(supply_periods):
            next_supply_idx = supply_periods[idx + 1]
        else:
            next_supply_idx = num_periods

        # Sum customer orders between this supply period and the next
        cum_orders = sum(
            periods[j]["customer_orders_qty"]
            for j in range(supply_idx, next_supply_idx)
        )

        if supply_idx == 0:
            # First period: ATP = starting_inventory + scheduled_receipts - cum_orders
            atp_values[supply_idx] = max(0, starting_inventory
                                         + periods[supply_idx]["scheduled_receipts"]
                                         - cum_orders)
        else:
            # Later periods: ATP = scheduled_receipts - cum_orders
            supply = (periods[supply_idx]["scheduled_receipts"]
                      + periods[supply_idx]["planned_order_qty"])
            atp_values[supply_idx] = max(0, supply - cum_orders)

    return atp_values


# ═══════════════════════════════════════════════════════════
# MPS Initialization — Generate empty time buckets
# ═══════════════════════════════════════════════════════════

async def initialize_mps_periods(
    db: AsyncSession,
    mps_id: str,
    product_no: str,
    product_name: str = "",
    forecast_qty_by_week: Optional[dict[str, float]] = None,
    customer_orders_by_week: Optional[dict[str, float]] = None,
) -> dict:
    """
    Initialize MPS entries with forecast and customer order data for a product.

    Creates MpsEntry rows for each week in the MPS period range, populated
    with provided forecast and customer order data (keyed by ISO week start date).
    """
    master = await get_mps_master(db, mps_id=mps_id)
    if not master:
        return {"error": f"MPS master {mps_id} not found"}

    forecast_qty_by_week = forecast_qty_by_week or {}
    customer_orders_by_week = customer_orders_by_week or {}

    week_mondays = _weeks_between(master.start_week, master.end_week)
    entries = []

    for i, week_monday in enumerate(week_mondays):
        wk = week_monday.isoformat()
        fcst = forecast_qty_by_week.get(wk, 0)
        cust = customer_orders_by_week.get(wk, 0)

        entry = MpsEntry(
            mps_id=mps_id,
            product_no=product_no,
            product_name=product_name,
            period_week=week_monday,
            week_number=i + 1,
            forecast_qty=fcst,
            customer_orders_qty=cust,
        )
        entries.append(entry)

    await bulk_create_entries(db, entries)

    return {
        "mps_id": str(mps_id),
        "product_no": product_no,
        "periods_created": len(entries),
        "start_week": master.start_week.isoformat(),
        "end_week": master.end_week.isoformat(),
    }


# ═══════════════════════════════════════════════════════════
# Planned Order → Work Order Conversion
# ═══════════════════════════════════════════════════════════

async def convert_planned_to_work_order(
    db: AsyncSession,
    mps_id: str,
    product_no: str,
    period_week: date,
    quantity: float,
) -> dict:
    """
    Convert an MPS planned order into a production work order.

    1. Find the MpsEntry for the given product + period
    2. Validate it has a planned order
    3. Create a ProductionOrder (dispatch module)
    4. Mark the entry as 'firm' (confirmed)
    5. Add the work order quantity to scheduled_receipts
    """
    from app.models.dispatch import ProductionOrder, OrderStatus

    # Find the MPS entry
    r = await db.execute(
        select(MpsEntry).where(
            and_(
                MpsEntry.mps_id == _u(mps_id),
                MpsEntry.product_no == product_no,
                MpsEntry.period_week == period_week,
            )
        )
    )
    entry = r.scalar_one_or_none()
    if not entry:
        return {"error": f"No MPS entry found for product {product_no} in week {period_week.isoformat()}"}

    if entry.planned_order_qty <= 0:
        return {"error": "No planned order exists for this period; run calculate_mps first"}

    # Create work order
    today_str = period_week.strftime("%Y%m%d")
    count_r = await db.execute(
        select(ProductionOrder)
        .where(ProductionOrder.order_no.like(f"MO-{today_str}-%"))
        .order_by(ProductionOrder.order_no.desc())
        .limit(1)
    )
    last = count_r.scalar_one_or_none()
    seq = 1
    if last:
        seq = int(last.order_no.split("-")[-1]) + 1

    work_order = ProductionOrder(
        order_no=f"MO-{today_str}-{seq:03d}",
        product_no=product_no,
        product_name=entry.product_name,
        quantity=quantity,
        due_date=period_week,
        priority=3,
        status=OrderStatus.DRAFT.value,
        notes=f"Auto-generated from MPS {mps_id}",
    )
    db.add(work_order)

    # Update MPS entry
    entry.status = MpsEntryStatus.FIRM.value
    entry.scheduled_receipts = (entry.scheduled_receipts or 0) + quantity
    entry.planned_order_qty = max(0, entry.planned_order_qty - quantity)
    await db.flush()

    return {
        "mps_id": str(mps_id),
        "product_no": product_no,
        "period_week": period_week.isoformat(),
        "quantity": quantity,
        "converted_to_work_order": True,
        "work_order_no": work_order.order_no,
        "message": f"Planned order for {quantity} x {product_no} converted to work order {work_order.order_no}",
    }
