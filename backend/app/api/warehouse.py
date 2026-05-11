"""Warehouse & Supply Chain API — WMS, supplier evaluation, auto-replenishment."""

import uuid
from datetime import date, datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.services import warehouse_service as svc
from app.services import purchase_service as purchase_svc
from app.schemas.warehouse import *

router = APIRouter(prefix="/warehouse", tags=["warehouse"])

# ── BIN LOCATIONS ────────────────────────────────────────────────

@router.get("/zones", response_model=dict)
async def list_zones(db: AsyncSession = Depends(get_db)):
    zones = await svc.list_zones(db)
    return {"zones": [ZoneResponse(id=str(z.id), code=z.code, name=z.name,
              zone_type=z.zone_type, status=z.status, description=z.description) for z in zones]}

@router.post("/zones", status_code=201)
async def create_zone(data: ZoneCreate, db: AsyncSession = Depends(get_db)):
    existing = await svc.get_zone_by_code(db, data.code)
    if existing: raise HTTPException(400, f"Zone {data.code} exists")
    z = await svc.create_zone(db, data.code, data.name, zone_type=data.zone_type, description=data.description)
    return {"id": str(z.id), "code": z.code, "name": z.name}

@router.get("/bins", response_model=dict)
async def list_bins(zone_code: str = Query(""), db: AsyncSession = Depends(get_db)):
    bins = await svc.list_bins(db, zone_code)
    items = []
    for b in bins:
        part_no = ""
        if b.part_id:
            from app.models.inventory import Part
            r = await db.get(Part, b.part_id)
            part_no = r.part_no if r else ""
        items.append(BinResponse(id=str(b.id), zone_code=b.zone.code if b.zone else "",
            zone_name=b.zone.name if b.zone else "", code=b.code,
            aisle=b.aisle, rack=b.rack, shelf=b.shelf, bin=b.bin,
            max_capacity=b.max_capacity, current_qty=b.current_qty,
            part_no=part_no, status=b.status))
    return {"bins": items, "total": len(items)}

@router.post("/bins", status_code=201)
async def create_bin(data: BinCreate, db: AsyncSession = Depends(get_db)):
    z = await svc.get_zone_by_code(db, data.zone_code)
    if not z: raise HTTPException(404, f"Zone {data.zone_code} not found")
    bin_ = await svc.create_bin(db, z.id, data.code, aisle=data.aisle,
                rack=data.rack, shelf=data.shelf, bin=data.bin,
                max_capacity=data.max_capacity)
    return {"id": str(bin_.id), "code": bin_.code, "zone_code": data.zone_code}

# ── INVENTORY TRANSFER ───────────────────────────────────────────

@router.post("/transfers", response_model=dict, status_code=201)
async def create_transfer(data: TransferCreate, db: AsyncSession = Depends(get_db)):
    from app.models.inventory import Part
    from app.services.inventory_service import get_part_by_no
    part = await get_part_by_no(db, data.part_no)
    if not part: raise HTTPException(404, f"Part {data.part_no} not found")
    to_bin = await svc.get_bin_by_code(db, data.to_bin_code)
    if not to_bin: raise HTTPException(404, f"Bin {data.to_bin_code} not found")
    from_bin_id = None
    if data.from_bin_code:
        fb = await svc.get_bin_by_code(db, data.from_bin_code)
        if fb: from_bin_id = fb.id
    t = await svc.create_transfer(db, part.id, data.quantity, to_bin.id,
            from_bin_id=from_bin_id, reason=data.reason or "transfer",
            notes=data.notes)
    return {"id": str(t.id), "transfer_no": t.transfer_no, "status": t.status}

@router.post("/transfers/{transfer_id}/complete", response_model=dict)
async def complete_transfer(transfer_id: str, db: AsyncSession = Depends(get_db)):
    return await svc.complete_transfer(db, uuid.UUID(transfer_id))

@router.get("/transfers", response_model=dict)
async def list_transfers(status: str = Query(""), db: AsyncSession = Depends(get_db)):
    transfers = await svc.list_transfers(db, status)
    items = [{"id": str(t.id), "transfer_no": t.transfer_no, "quantity": t.quantity,
              "status": t.status, "reason": t.reason,
              "created_at": t.created_at} for t in transfers]
    return {"transfers": items, "total": len(items)}

# ── PICK TASKS ───────────────────────────────────────────────────

@router.post("/pick-tasks", response_model=dict, status_code=201)
async def create_pick_task(data: PickTaskCreate, db: AsyncSession = Depends(get_db)):
    from app.services.inventory_service import get_part_by_no
    part = await get_part_by_no(db, data.part_no)
    if not part: raise HTTPException(404, f"Part {data.part_no} not found")
    pt = await svc.create_pick_task(db, data.reference_type, data.reference_no,
            part.id, data.quantity_required, assigned_to=data.assigned_to, notes=data.notes)
    return {"id": str(pt.id), "task_no": pt.task_no, "status": pt.status}

@router.patch("/pick-tasks/{task_id}", response_model=dict)
async def update_pick_task(task_id: str, picked_qty: float = Query(...),
                            status: str = Query(""), db: AsyncSession = Depends(get_db)):
    kw = {}
    if status: kw["status"] = status
    pt = await svc.update_pick_task(db, uuid.UUID(task_id), picked_qty, **kw)
    if not pt: raise HTTPException(404, "Pick task not found")
    return {"id": str(pt.id), "task_no": pt.task_no, "status": pt.status, "picked_qty": pt.quantity_picked}

@router.get("/pick-tasks", response_model=dict)
async def list_pick_tasks(status: str = Query(""), db: AsyncSession = Depends(get_db)):
    pts = await svc.list_pick_tasks(db, status)
    items = [{"id": str(t.id), "task_no": t.task_no, "reference_type": t.reference_type,
              "reference_no": t.reference_no, "quantity_required": t.quantity_required,
              "quantity_picked": t.quantity_picked, "status": t.status,
              "assigned_to": t.assigned_to} for t in pts]
    return {"pick_tasks": items, "total": len(items)}

# ── CYCLE COUNTS ─────────────────────────────────────────────────

@router.post("/cycle-counts", response_model=dict, status_code=201)
async def create_cycle_count(data: CycleCountCreate, db: AsyncSession = Depends(get_db)):
    from app.services.inventory_service import get_part_by_no
    part = await get_part_by_no(db, data.part_no)
    if not part: raise HTTPException(404, f"Part {data.part_no} not found")
    cc = await svc.create_cycle_count(db, part.id, data.expected_qty, data.actual_qty,
            counted_by=data.counted_by, notes=data.notes)
    return {"id": str(cc.id), "count_no": cc.count_no, "variance": cc.variance,
            "variance_pct": cc.variance_pct, "status": cc.status}

@router.get("/cycle-counts", response_model=dict)
async def list_cycle_counts(db: AsyncSession = Depends(get_db)):
    ccs = await svc.list_cycle_counts(db)
    items = [{"id": str(c.id), "count_no": c.count_no, "expected_qty": c.expected_qty,
              "actual_qty": c.actual_qty, "variance": c.variance,
              "variance_pct": c.variance_pct, "status": c.status,
              "counted_by": c.counted_by} for c in ccs]
    return {"cycle_counts": items, "total": len(items)}

# ── SUPPLIER EVALUATION ──────────────────────────────────────────

@router.get("/eval/suppliers", response_model=dict)
async def list_suppliers_for_eval(search: str = Query(""), db: AsyncSession = Depends(get_db)):
    suppliers, total = await purchase_svc.list_suppliers(db, search)
    return {"suppliers": [{"id": str(s.id), "name": s.name, "score": s.score,
                           "contact": s.contact, "phone": s.phone} for s in suppliers], "total": total}

@router.post("/eval", status_code=201)
async def create_evaluation(data: EvalCreate, db: AsyncSession = Depends(get_db)):
    from app.services.purchase_service import get_supplier, list_suppliers
    s, _ = await list_suppliers(db, data.supplier_name)
    if not s: raise HTTPException(404, f"Supplier {data.supplier_name} not found")
    ev = await svc.create_evaluation(db, s[0].id, date.fromisoformat(data.eval_date),
            data.quality_score, data.delivery_score, data.price_score,
            data.service_score or 0, evaluator=data.evaluator, notes=data.notes)
    return {"id": str(ev.id), "total_score": ev.total_score, "grade": ev.grade}

@router.get("/eval", response_model=dict)
async def list_evaluations(supplier: str = Query(""), db: AsyncSession = Depends(get_db)):
    evals = await svc.list_evaluations(db, supplier)
    items = [EvalResponse(id=str(e.id),
              supplier_name=e.supplier.name if e.supplier else "",
              eval_date=e.eval_date.isoformat() if e.eval_date else "",
              quality_score=e.quality_score, delivery_score=e.delivery_score,
              price_score=e.price_score, total_score=e.total_score,
              grade=e.grade, evaluator=e.evaluator, notes=e.notes) for e in evals]
    return {"evaluations": items, "total": len(items)}

# ── SUPPLIER PRICING ─────────────────────────────────────────────

@router.post("/pricing", status_code=201)
async def set_price(data: PriceCreate, db: AsyncSession = Depends(get_db)):
    from app.services.purchase_service import list_suppliers
    from app.services.inventory_service import get_part_by_no
    s, _ = await list_suppliers(db, data.supplier_name)
    if not s: raise HTTPException(404, f"Supplier {data.supplier_name} not found")
    part = await get_part_by_no(db, data.part_no)
    if not part: raise HTTPException(404, f"Part {data.part_no} not found")
    sp = await svc.set_supplier_price(db, s[0].id, part.id, data.unit_price,
            date.fromisoformat(data.effective_date), currency=data.currency,
            expiry_date=date.fromisoformat(data.expiry_date) if data.expiry_date else None,
            moq=data.moq or 1)
    return {"id": str(sp.id), "supplier": data.supplier_name, "part_no": data.part_no,
            "unit_price": sp.unit_price, "currency": sp.currency}

@router.get("/pricing/best/{part_no}")
async def get_best_price(part_no: str, db: AsyncSession = Depends(get_db)):
    from app.services.inventory_service import get_part_by_no
    part = await get_part_by_no(db, part_no)
    if not part: raise HTTPException(404, f"Part {part_no} not found")
    best = await svc.get_best_price(db, part.id)
    if not best: return {"part_no": part_no, "best_price": None}
    return {"part_no": part_no, **best}

@router.get("/pricing", response_model=dict)
async def list_pricing(supplier: str = Query(""), part_no: str = Query(""),
                        db: AsyncSession = Depends(get_db)):
    prices = await svc.list_supplier_prices(db, supplier, part_no)
    items = []
    for p in prices:
        s = await db.get(__import__("app.models.purchase", fromlist=["Supplier"]).Supplier, p.supplier_id)
        items.append({"id": str(p.id), "supplier": s.name if s else "",
                       "unit_price": p.unit_price, "currency": p.currency,
                       "effective_date": p.effective_date.isoformat() if p.effective_date else None,
                       "expiry_date": p.expiry_date.isoformat() if p.expiry_date else None,
                       "moq": p.moq, "is_active": p.is_active})
    return {"prices": items, "total": len(items)}

# ── REORDER RULES ────────────────────────────────────────────────

@router.post("/reorder-rules", status_code=201)
async def set_reorder_rule(data: ReorderRuleCreate, db: AsyncSession = Depends(get_db)):
    from app.services.inventory_service import get_part_by_no
    part = await get_part_by_no(db, data.part_no)
    if not part: raise HTTPException(404, f"Part {data.part_no} not found")
    kw = {"lead_time_days": data.lead_time_days, "auto_approve": data.auto_approve}
    if data.preferred_supplier_name:
        from app.services.purchase_service import list_suppliers
        s, _ = await list_suppliers(db, data.preferred_supplier_name)
        if s: kw["preferred_supplier_id"] = s[0].id
    rule = await svc.set_reorder_rule(db, part.id, data.safety_stock, data.reorder_qty, **kw)
    return {"id": str(rule.id), "part_no": data.part_no, "safety_stock": rule.safety_stock,
            "reorder_qty": rule.reorder_qty, "auto_approve": rule.auto_approve}

@router.get("/reorder-rules", response_model=dict)
async def list_reorder_rules(db: AsyncSession = Depends(get_db)):
    r = await db.execute(
        __import__("sqlalchemy").select(
            __import__("app.models.warehouse", fromlist=["ReorderRule"]).ReorderRule
        )
    )
    rules = list(r.scalars().all())
    items = []
    for rule in rules:
        part_r = await db.execute(
            __import__("sqlalchemy").select(
                __import__("app.models.inventory", fromlist=["Part"]).Part
            ).where(__import__("app.models.inventory", fromlist=["Part"]).Part.id == rule.part_id)
        )
        part = part_r.scalar_one_or_none()
        supplier_name = ""
        if rule.preferred_supplier_id:
            s = await db.get(__import__("app.models.purchase", fromlist=["Supplier"]).Supplier, rule.preferred_supplier_id)
            supplier_name = s.name if s else ""
        items.append({"id": str(rule.id), "part_no": part.part_no if part else "",
                       "safety_stock": rule.safety_stock, "reorder_qty": rule.reorder_qty,
                       "preferred_supplier": supplier_name,
                       "lead_time_days": rule.lead_time_days, "auto_approve": rule.auto_approve,
                       "is_active": rule.is_active})
    return {"reorder_rules": items, "total": len(items)}

@router.post("/reorder/check", response_model=dict)
async def check_reorder(db: AsyncSession = Depends(get_db)):
    """Check all reorder rules and return items needing replenishment."""
    results = await svc.check_reorder_all(db)
    return {"items_needing_reorder": results, "total": len(results),
            "needs_action": len([r for r in results if r["action"] in ("alert", "auto_order")])}
