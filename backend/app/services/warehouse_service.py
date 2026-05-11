"""
Warehouse & Supply Chain Service — WMS, supplier evaluation, auto-replenishment.
"""

from __future__ import annotations
import uuid
from datetime import datetime, date, timedelta
from typing import Optional
from sqlalchemy import select, or_, func, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.models.warehouse import (
    WarehouseZone, BinLocation, InventoryTransfer, PickTask,
    CycleCount, SupplierEvaluation, SupplierPrice, ReorderRule,
)
from app.models.purchase import Supplier, PurchaseOrder, PurchaseOrderItem
from app.models.inventory import Part, Inventory


# ═══════════════════════════════════════════════════════════════════
# ─── WAREHOUSE ZONE ──────────────────────────────────────────────
# ═══════════════════════════════════════════════════════════════════

async def list_zones(db: AsyncSession) -> list[WarehouseZone]:
    r = await db.execute(select(WarehouseZone).order_by(WarehouseZone.code))
    return list(r.scalars().all())

async def get_zone_by_code(db: AsyncSession, code: str) -> Optional[WarehouseZone]:
    r = await db.execute(select(WarehouseZone).where(WarehouseZone.code == code))
    return r.scalar_one_or_none()

async def create_zone(db: AsyncSession, code: str, name: str, **kw) -> WarehouseZone:
    z = WarehouseZone(code=code, name=name, **kw)
    db.add(z); await db.flush(); return z

# ═══════════════════════════════════════════════════════════════════
# ─── BIN LOCATION ────────────────────────────────────────────────
# ═══════════════════════════════════════════════════════════════════

async def list_bins(db: AsyncSession, zone_code: str = "") -> list[BinLocation]:
    q = select(BinLocation).options(selectinload(BinLocation.zone))
    if zone_code:
        z = await get_zone_by_code(db, zone_code)
        if z: q = q.where(BinLocation.zone_id == z.id)
    r = await db.execute(q.order_by(BinLocation.code))
    return list(r.scalars().all())

async def get_bin_by_code(db: AsyncSession, code: str) -> Optional[BinLocation]:
    q = select(BinLocation).options(selectinload(BinLocation.zone)).where(BinLocation.code == code)
    r = await db.execute(q); return r.scalar_one_or_none()

async def create_bin(db: AsyncSession, zone_id: uuid.UUID, code: str, **kw) -> BinLocation:
    b = BinLocation(zone_id=zone_id, code=code, **kw)
    db.add(b); await db.flush(); return b

async def update_bin_qty(db: AsyncSession, bin_id: uuid.UUID, delta: float,
                          part_id: Optional[uuid.UUID] = None) -> BinLocation:
    b = await db.get(BinLocation, bin_id)
    if not b: raise ValueError(f"Bin {bin_id} not found")
    b.current_qty = max(0, (b.current_qty or 0) + delta)
    if part_id: b.part_id = part_id
    await db.flush(); return b

# ═══════════════════════════════════════════════════════════════════
# ─── INVENTORY TRANSFER ──────────────────────────────────────────
# ═══════════════════════════════════════════════════════════════════

async def create_transfer(db: AsyncSession, part_id: uuid.UUID, quantity: float,
                           to_bin_id: uuid.UUID, **kw) -> InventoryTransfer:
    # Generate transfer number
    today = date.today().strftime("%Y%m%d")
    r = await db.execute(
        select(InventoryTransfer).where(
            InventoryTransfer.transfer_no.like(f"TF-{today}-%")
        ).order_by(desc(InventoryTransfer.transfer_no)).limit(1)
    )
    last = r.scalar_one_or_none()
    seq = (int(last.transfer_no.split("-")[-1]) + 1) if last and last.transfer_no else 1
    t = InventoryTransfer(
        transfer_no=f"TF-{today}-{seq:03d}", part_id=part_id,
        quantity=quantity, to_bin_id=to_bin_id, **kw
    )
    db.add(t); await db.flush()
    return t

async def complete_transfer(db: AsyncSession, transfer_id: uuid.UUID) -> dict:
    t = await db.get(InventoryTransfer, transfer_id)
    if not t: return {"error": "Transfer not found"}
    if t.status != "pending": return {"error": f"Transfer already {t.status}"}

    # Deduct from source
    if t.from_bin_id:
        await update_bin_qty(db, t.from_bin_id, -t.quantity)
    # Add to destination
    await update_bin_qty(db, t.to_bin_id, t.quantity, t.part_id)

    t.status = "completed"; t.completed_at = datetime.utcnow()
    await db.flush()
    return {"transfer_no": t.transfer_no, "status": "completed", "quantity": t.quantity}

async def list_transfers(db: AsyncSession, status: str = "", limit: int = 50) -> list[InventoryTransfer]:
    q = select(InventoryTransfer)
    if status: q = q.where(InventoryTransfer.status == status)
    r = await db.execute(q.order_by(desc(InventoryTransfer.created_at)).limit(limit))
    return list(r.scalars().all())

# ═══════════════════════════════════════════════════════════════════
# ─── PICK TASK ───────────────────────────────────────────────────
# ═══════════════════════════════════════════════════════════════════

async def create_pick_task(db: AsyncSession, ref_type: str, ref_no: str,
                            part_id: uuid.UUID, qty: float, **kw) -> PickTask:
    today = date.today().strftime("%Y%m%d")
    r = await db.execute(
        select(PickTask).where(PickTask.task_no.like(f"PK-{today}-%"))
        .order_by(desc(PickTask.task_no)).limit(1)
    )
    last = r.scalar_one_or_none()
    seq = (int(last.task_no.split("-")[-1]) + 1) if last and last.task_no else 1
    pt = PickTask(task_no=f"PK-{today}-{seq:03d}",
                   reference_type=ref_type, reference_no=ref_no,
                   part_id=part_id, quantity_required=qty, **kw)
    db.add(pt); await db.flush(); return pt

async def update_pick_task(db: AsyncSession, task_id: uuid.UUID,
                            picked_qty: float, **kw) -> Optional[PickTask]:
    pt = await db.get(PickTask, task_id)
    if not pt: return None
    pt.quantity_picked = picked_qty
    for k, v in kw.items():
        if v is not None: setattr(pt, k, v)
    if picked_qty >= pt.quantity_required:
        pt.status = "packed"; pt.picked_at = datetime.utcnow()
    elif picked_qty > 0:
        pt.status = "picking"
    await db.flush(); return pt

async def list_pick_tasks(db: AsyncSession, status: str = "", limit: int = 50) -> list[PickTask]:
    q = select(PickTask)
    if status: q = q.where(PickTask.status == status)
    r = await db.execute(q.order_by(desc(PickTask.created_at)).limit(limit))
    return list(r.scalars().all())

# ═══════════════════════════════════════════════════════════════════
# ─── CYCLE COUNT ─────────────────────────────────────────────────
# ═══════════════════════════════════════════════════════════════════

async def create_cycle_count(db: AsyncSession, part_id: uuid.UUID,
                              expected_qty: float, actual_qty: float, **kw) -> CycleCount:
    today = date.today().strftime("%Y%m%d")
    r = await db.execute(
        select(CycleCount).where(CycleCount.count_no.like(f"CC-{today}-%"))
        .order_by(desc(CycleCount.count_no)).limit(1)
    )
    last = r.scalar_one_or_none()
    seq = (int(last.count_no.split("-")[-1]) + 1) if last and last.count_no else 1
    variance = actual_qty - expected_qty
    var_pct = round(variance / expected_qty * 100, 2) if expected_qty > 0 else 0
    cc = CycleCount(count_no=f"CC-{today}-{seq:03d}",
                     part_id=part_id, expected_qty=expected_qty,
                     actual_qty=actual_qty, variance=variance,
                     variance_pct=var_pct, status="counted", **kw)
    db.add(cc); await db.flush(); return cc

async def list_cycle_counts(db: AsyncSession, limit: int = 50) -> list[CycleCount]:
    r = await db.execute(select(CycleCount).order_by(desc(CycleCount.created_at)).limit(limit))
    return list(r.scalars().all())

# ═══════════════════════════════════════════════════════════════════
# ─── SUPPLIER EVALUATION ─────────────────────────────────────────
# ═══════════════════════════════════════════════════════════════════

def _calc_grade(score: float) -> str:
    if score >= 90: return "A"
    elif score >= 75: return "B"
    elif score >= 60: return "C"
    return "D"

async def create_evaluation(db: AsyncSession, supplier_id: uuid.UUID,
                             eval_date: date, quality: float, delivery: float,
                             price: float, service: float = 0, **kw) -> SupplierEvaluation:
    total = round((quality + delivery + price + service) / 4, 1)
    grade = _calc_grade(total)
    ev = SupplierEvaluation(supplier_id=supplier_id, eval_date=eval_date,
                            quality_score=quality, delivery_score=delivery,
                            price_score=price, service_score=service,
                            total_score=total, grade=grade, **kw)
    db.add(ev)
    # Update supplier aggregate score
    s = await db.get(Supplier, supplier_id)
    if s: s.score = round(total / 20, 1)  # 0-100 to 0-5
    await db.flush(); return ev

async def list_evaluations(db: AsyncSession, supplier_name: str = "") -> list[SupplierEvaluation]:
    q = select(SupplierEvaluation).options(selectinload(SupplierEvaluation.supplier))
    if supplier_name:
        s_r = await db.execute(select(Supplier).where(Supplier.name.ilike(f"%{supplier_name}%")))
        s = s_r.scalar_one_or_none()
        if s: q = q.where(SupplierEvaluation.supplier_id == s.id)
    r = await db.execute(q.order_by(desc(SupplierEvaluation.created_at)))
    return list(r.scalars().all())

# ═══════════════════════════════════════════════════════════════════
# ─── SUPPLIER PRICE ──────────────────────────────────────────────
# ═══════════════════════════════════════════════════════════════════

async def set_supplier_price(db: AsyncSession, supplier_id: uuid.UUID,
                              part_id: uuid.UUID, unit_price: float,
                              effective_date: date, **kw) -> SupplierPrice:
    sp = SupplierPrice(supplier_id=supplier_id, part_id=part_id,
                        unit_price=unit_price, effective_date=effective_date, **kw)
    db.add(sp); await db.flush(); return sp

async def get_best_price(db: AsyncSession, part_id: uuid.UUID) -> Optional[dict]:
    """Get the lowest active price for a part across all suppliers."""
    r = await db.execute(
        select(SupplierPrice).options(selectinload(SupplierPrice.supplier)).where(
            SupplierPrice.part_id == part_id,
            SupplierPrice.is_active == True,
            or_(SupplierPrice.expiry_date.is_(None), SupplierPrice.expiry_date >= date.today()),
        ).order_by(SupplierPrice.unit_price).limit(1)
    )
    sp = r.scalar_one_or_none()
    if not sp: return None
    return {"supplier": sp.supplier.name, "unit_price": sp.unit_price,
            "currency": sp.currency, "moq": sp.moq}

async def list_supplier_prices(db: AsyncSession, supplier_name: str = "",
                                part_no: str = "") -> list[SupplierPrice]:
    q = select(SupplierPrice).options(
        selectinload(SupplierPrice.supplier))
    if supplier_name:
        s_r = await db.execute(select(Supplier).where(Supplier.name.ilike(f"%{supplier_name}%")))
        s = s_r.scalar_one_or_none()
        if s: q = q.where(SupplierPrice.supplier_id == s.id)
    r = await db.execute(q.order_by(desc(SupplierPrice.created_at)))
    return list(r.scalars().all())

# ═══════════════════════════════════════════════════════════════════
# ─── REORDER / AUTO-REPLENISHMENT ────────────────────────────────
# ═══════════════════════════════════════════════════════════════════

async def set_reorder_rule(db: AsyncSession, part_id: uuid.UUID,
                            safety_stock: float, reorder_qty: float, **kw) -> ReorderRule:
    # Upsert
    r = await db.execute(select(ReorderRule).where(ReorderRule.part_id == part_id))
    rule = r.scalar_one_or_none()
    if rule:
        rule.safety_stock = safety_stock; rule.reorder_qty = reorder_qty
        for k, v in kw.items():
            if v is not None: setattr(rule, k, v)
    else:
        rule = ReorderRule(part_id=part_id, safety_stock=safety_stock,
                           reorder_qty=reorder_qty, **kw)
        db.add(rule)
    await db.flush(); return rule

async def check_reorder_all(db: AsyncSession) -> list[dict]:
    """Check all active reorder rules against current stock levels."""
    r = await db.execute(select(ReorderRule).where(ReorderRule.is_active == True))
    rules = list(r.scalars().all())
    results = []
    for rule in rules:
        # Get current stock
        inv_r = await db.execute(
            select(func.coalesce(func.sum(Inventory.quantity), 0)).where(
                Inventory.part_id == rule.part_id)
        )
        stock = float(inv_r.scalar())
        part_r = await db.execute(select(Part).where(Part.id == rule.part_id))
        part = part_r.scalar_one_or_none()

        if stock < rule.safety_stock:
            shortage = rule.safety_stock - stock
            order_qty = max(rule.reorder_qty, shortage)
            supplier_name = ""
            if rule.preferred_supplier_id:
                s = await db.get(Supplier, rule.preferred_supplier_id)
                supplier_name = s.name if s else ""

            action = "auto_order" if rule.auto_approve else "alert"
            results.append({
                "part_no": part.part_no if part else str(rule.part_id),
                "part_name": part.name if part else "",
                "current_stock": stock,
                "safety_stock": rule.safety_stock,
                "shortage": round(shortage, 2),
                "suggested_order_qty": order_qty,
                "preferred_supplier": supplier_name,
                "action": action,
            })
            if rule.auto_approve:
                rule.last_triggered_at = datetime.utcnow()

    await db.flush()
    return results
