"""
Rush Order Service — 急單評估與建議

Provides analytical functions to evaluate whether a rush (expedited) sales order
is financially beneficial, considering premium revenue, overtime costs, delay
penalties on existing orders, and opportunity costs.

急單評估服務 — 分析插單/急單的財務可行性，綜合考量溢價收入、
加班成本、延遲罰款與機會成本。
"""

from __future__ import annotations

from datetime import date, timedelta, datetime
from typing import Any, Optional

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.sales_order import SalesOrder, SalesOrderItem
from app.models.dispatch import ProductionOrder, Operation, OrderStatus


# ═══════════════════════════════════════════════════════════════
# Configuration — 急單評估預設參數
# ═══════════════════════════════════════════════════════════════

RUSH_ORDER_CONFIG: dict[str, Any] = {
    "premium_factor": 1.20,          # 溢價倍數 (加價 20%)
    "overtime_rate": 1.5,            # 加班費率 (1.5 倍正常工資)
    "delay_penalty_pct": 0.01,       # 延遲罰款比例 (每日 1% of order value)
    "max_acceptable_risk": 0.3,      # 可接受風險閾值 (佔 premium 的 30%)
}


# ═══════════════════════════════════════════════════════════════
# Helper — 估算工單總工時成本
# ═══════════════════════════════════════════════════════════════

async def _estimate_order_labor_cost(
    db: AsyncSession,
    order_id: str,
) -> float:
    """Estimate total labor cost for a production order based on its operations.

    根據工單工序估算總工時成本。

    Uses a simplified costing: total_time_min × (normal hourly rate).
    The normal hourly rate is derived from config (default ~50 units/hr).
    """
    result = await db.execute(
        select(Operation).where(Operation.order_id == order_id)
    )
    ops = list(result.scalars().all())
    total_minutes = sum(float(op.total_time_min or 0) for op in ops)
    # Assume normal labor rate of 50 cost-units per hour; configurable
    hourly_rate = 50.0
    return (total_minutes / 60.0) * hourly_rate


# ═══════════════════════════════════════════════════════════════
# Schedule Impact — 新訂單對現有排程的影響
# ═══════════════════════════════════════════════════════════════

async def get_schedule_impact(
    db: AsyncSession,
    so_data: dict,
) -> list[dict]:
    """Analyze how a new rush sales order would impact the existing production schedule.

    分析新急單對現有生產排程的影響：哪些工單會被延遲、延遲多久。

    Args:
        db: Database session
        so_data: Sales order data with keys:
            - items: list of {part_no, quantity, ...}
            - priority: int (1=highest, default 3)

    Returns:
        List of impacted orders with estimated delays:
        [{order_no, product_no, original_due_date, estimated_delay_days, delay_cost}]
    """
    # Get the priority from the SO data, default to urgent (2)
    rush_priority = so_data.get("priority", 2)

    # Get all active, uncompleted production orders — sorted by due_date then priority
    result = await db.execute(
        select(ProductionOrder)
        .where(ProductionOrder.status.in_([
            OrderStatus.RELEASED.value,
            OrderStatus.DISPATCHED.value,
            OrderStatus.IN_PROGRESS.value,
        ]))
        .order_by(ProductionOrder.due_date, ProductionOrder.priority)
    )
    active_orders = list(result.scalars().all())

    if not active_orders:
        return []

    # Calculate total rush work time based on matching items
    rush_total_time_min = 0.0
    for item in so_data.get("items", []):
        part_no = item.get("part_no", "")
        qty = float(item.get("quantity", 1))
        # Find any production order for this product that has operations defined
        # to estimate cycle time per unit
        po_result = await db.execute(
            select(Operation)
            .join(ProductionOrder, Operation.order_id == ProductionOrder.id)
            .where(ProductionOrder.product_no == part_no)
            .limit(10)
        )
        matching_ops = list(po_result.scalars().all())
        if matching_ops:
            for op in matching_ops:
                unit_time = float(op.cycle_time_min or 0) + (float(op.setup_time_min or 0) / max(qty, 1))
                rush_total_time_min += unit_time * qty
        else:
            # No historical data — assume 60 min per unit as default
            rush_total_time_min += 60.0 * qty

    # Simulate slot-in: the rush order (priority 1 or 2) jumps ahead of
    # existing orders with lower priority or later due dates.
    impacts = []
    accumulated_delay_min = 0.0
    inserted = False

    for po in active_orders:
        # Skip orders that are already in progress / partially done
        if po.status == OrderStatus.IN_PROGRESS.value and po.priority <= rush_priority:
            continue

        # The rush order inserts ahead of this order if:
        #   (a) rush priority is higher (lower number), OR
        #   (b) same priority but rush due is earlier
        if not inserted and (
            rush_priority < po.priority
        ):
            # Insert rush job — this pushes all subsequent orders
            accumulated_delay_min += rush_total_time_min
            inserted = True

        if accumulated_delay_min > 0:
            delay_days = round(accumulated_delay_min / (8 * 60), 1)  # convert to working days (8h shifts)
            delay_cost = delay_days * po.quantity * 10.0  # simplified: 10 cost-units per unit per day
            impacts.append({
                "order_no": po.order_no,
                "product_no": po.product_no,
                "original_due_date": po.due_date.isoformat() if po.due_date else "",
                "estimated_delay_days": delay_days,
                "delay_cost": round(delay_cost, 2),
            })

        # Add this order's time to accumulated delay for subsequent orders
        # Estimate its total operation time
        op_result = await db.execute(
            select(func.sum(Operation.total_time_min))
            .where(Operation.order_id == po.id)
        )
        po_time = float(op_result.scalar() or 120.0)  # default 2h if no ops
        accumulated_delay_min += po_time

    return impacts


# ═══════════════════════════════════════════════════════════════
# Alternatives — 替代方案建議
# ═══════════════════════════════════════════════════════════════

async def find_alternatives(
    db: AsyncSession,
    so_data: dict,
) -> list[dict]:
    """Suggest alternative approaches for handling a rush order.

    針對急單提出替代方案建議。

    Returns:
        List of alternative strategies with descriptions.
    """
    total_qty = sum(
        float(i.get("quantity", 0)) for i in so_data.get("items", [])
    )
    alternatives = []

    # Option 1: Full Rush — expedite entire order
    alternatives.append({
        "strategy": "full_rush",
        "label": "Full Rush / 全單急插",
        "description": (
            "Expedite the entire order at highest priority. "
            "Maximizes premium revenue but may cause significant delays "
            "to existing orders. Best for small, high-value orders."
            " / 整筆訂單以最高優先級插入，最大化溢價收入但可能嚴重影響既有訂單。"
        ),
        "estimated_overtime_pct": 1.5,
        "risk_level": "high",
    })

    # Option 2: Partial Outsourcing — rush in-house portion, outsource the rest
    alternatives.append({
        "strategy": "partial_outsource",
        "label": "Partial Outsourcing / 部分外包",
        "description": (
            "Produce a portion in-house with rush priority, outsource "
            "the remaining quantity to an external supplier. Balances "
            "speed with capacity constraints."
            " / 部分自製急單、其餘外包，平衡速度與產能限制。"
        ),
        "estimated_overtime_pct": 1.2,
        "risk_level": "medium",
        "outsource_quantity": round(total_qty * 0.4, 1) if total_qty else 0,
        "in_house_quantity": round(total_qty * 0.6, 1) if total_qty else 0,
    })

    # Option 3: Defer to regular schedule — no rush premium but no penalties
    alternatives.append({
        "strategy": "regular_schedule",
        "label": "Regular Schedule / 正常排程",
        "description": (
            "Place the order on the regular production schedule without "
            "expediting. No premium revenue, but no overtime costs or "
            "delay penalties either. Lowest risk."
            " / 按正常排程生產，無溢價也無加班/延遲成本。風險最低。"
        ),
        "estimated_overtime_pct": 1.0,
        "risk_level": "low",
    })

    return alternatives


# ═══════════════════════════════════════════════════════════════
# Main — 急單評估入口
# ═══════════════════════════════════════════════════════════════

async def evaluate_rush_order(
    db: AsyncSession,
    so_data: dict,
    production_schedule: Optional[list[dict]] = None,
) -> dict:
    """Evaluate whether a rush sales order is financially beneficial.

    評估急單的財務可行性，計算淨效益、風險等級與替代方案。

    The evaluation considers:
    - Premium revenue (default 1.15–1.30x multiplier)
    - Overtime costs from expedited production
    - Delay penalties on existing orders pushed back
    - Opportunity cost of capacity consumed

    Args:
        db: Database session
        so_data: Sales order data dict with keys:
            - items: list of {part_no, quantity, unit_price}
            - customer_info: optional dict with {name, priority}
        production_schedule: Optional pre-fetched schedule list.
            If None, queries the database.

    Returns:
        dict with keys:
        - recommended: bool — whether to accept the rush
        - net_benefit: float — estimated net financial gain
        - risk_level: str — "low" / "medium" / "high"
        - alternatives: list[dict] — alternative strategies
        - breakdown: dict — detailed cost/revenue breakdown
    """
    config = RUSH_ORDER_CONFIG
    premium_factor = config["premium_factor"]
    overtime_rate = config["overtime_rate"]
    delay_penalty_pct = config["delay_penalty_pct"]
    max_acceptable_risk = config["max_acceptable_risk"]

    # ── 1. Calculate base order value ────────────────────────────────
    items = so_data.get("items", [])
    base_amount = sum(
        float(i.get("quantity", 0)) * float(i.get("unit_price", 0))
        for i in items
    )
    if base_amount <= 0:
        return {
            "recommended": False,
            "net_benefit": 0,
            "risk_level": "low",
            "alternatives": [],
            "breakdown": {
                "premium_revenue": 0,
                "overtime_cost": 0,
                "delay_penalties": 0,
                "opportunity_cost": 0,
                "base_amount": 0,
            },
            "note": "Order has zero value — cannot evaluate.",
        }

    # ── 2. Premium revenue ──────────────────────────────────────────
    premium_revenue = round(base_amount * (premium_factor - 1), 2)

    # ── 3. Overtime cost estimate ────────────────────────────────────
    # Estimate total production minutes for this order
    estimated_total_min = 0.0
    for item in items:
        part_no = item.get("part_no", "")
        qty = float(item.get("quantity", 1))
        # Look for existing operations to estimate cycle time
        op_result = await db.execute(
            select(Operation)
            .join(ProductionOrder, Operation.order_id == ProductionOrder.id)
            .where(ProductionOrder.product_no == part_no)
            .limit(3)
        )
        ops = list(op_result.scalars().all())
        if ops:
            for op in ops:
                unit_time = (
                    float(op.setup_time_min or 0) / max(qty, 1)
                    + float(op.cycle_time_min or 0)
                )
                estimated_total_min += unit_time * qty
        else:
            # Default: 60 min per unit
            estimated_total_min += 60.0 * qty

    # Normal labor cost (50 units/hr)
    normal_hourly_rate = 50.0
    normal_labor_cost = (estimated_total_min / 60.0) * normal_hourly_rate
    overtime_cost = round(normal_labor_cost * (overtime_rate - 1), 2)

    # ── 4. Delay penalties on existing orders ───────────────────────
    schedule_impact = await get_schedule_impact(db, so_data)
    total_delay_penalties = 0.0
    for impact in schedule_impact:
        order_value = impact.get("delay_cost", 0)
        delay_days = impact.get("estimated_delay_days", 0)
        penalty = order_value * delay_penalty_pct * delay_days
        total_delay_penalties += penalty
    total_delay_penalties = round(total_delay_penalties, 2)

    # ── 5. Opportunity cost ─────────────────────────────────────────
    # Capacity consumed could have been used for other orders.
    # Simplified: 10% of base_amount as opportunity cost.
    opportunity_cost = round(base_amount * 0.10, 2)

    # ── 6. Net benefit ──────────────────────────────────────────────
    total_costs = overtime_cost + total_delay_penalties + opportunity_cost
    net_benefit = round(premium_revenue - total_costs, 2)

    # ── 7. Risk assessment ──────────────────────────────────────────
    if premium_revenue > 0:
        risk_ratio = abs(min(net_benefit, 0)) / premium_revenue
    else:
        risk_ratio = 0.0

    if risk_ratio <= max_acceptable_risk / 2:
        risk_level = "low"
    elif risk_ratio <= max_acceptable_risk:
        risk_level = "medium"
    else:
        risk_level = "high"

    recommended = net_benefit > 0 and risk_level != "high"

    # ── 8. Alternatives ─────────────────────────────────────────────
    alternatives = await find_alternatives(db, so_data)

    return {
        "recommended": recommended,
        "net_benefit": net_benefit,
        "risk_level": risk_level,
        "risk_ratio": round(risk_ratio, 4),
        "alternatives": alternatives,
        "schedule_impact": schedule_impact,
        "breakdown": {
            "base_amount": round(base_amount, 2),
            "premium_revenue": premium_revenue,
            "premium_factor": premium_factor,
            "overtime_cost": overtime_cost,
            "delay_penalties": total_delay_penalties,
            "opportunity_cost": opportunity_cost,
            "total_costs": round(total_costs, 2),
        },
    }
