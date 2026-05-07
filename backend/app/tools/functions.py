"""
LLM Tool Functions -- Real DB implementation for all modules.
Each function creates its own DB session for LLM function calling.
"""

from app.database import async_session
from app.services import inventory_service, purchase_service, bom_service, dispatch_service, quality_service, accounting_service
from app.models.purchase import Supplier


async def query_inventory(part_no: str = None, name: str = None, category: str = None) -> list:
    """查詢零件庫存量。支援料號、品名關鍵字、分類查詢。"""
    async with async_session() as db:
        items = await inventory_service.query_stock(db, part_no, name, category)
    return items


async def create_purchase_order(supplier_name: str, items: list, notes: str = None) -> dict:
    """建立採購單。需要供應商名稱、品項列表(part_no/quantity/unit_price)。"""
    async with async_session() as db:
        suppliers, _ = await purchase_service.list_suppliers(db, supplier_name)
        supplier = suppliers[0] if suppliers else None
        if not supplier:
            supplier = await purchase_service.create_supplier(db, supplier_name)

        resolved = []
        for item in items:
            part = await inventory_service.get_part_by_no(db, item["part_no"])
            if not part:
                raise ValueError(f"Part not found: {item['part_no']}")
            resolved.append({
                "part_id": part.id,
                "quantity": item["quantity"],
                "unit_price": item.get("unit_price"),
            })

        po = await purchase_service.create_purchase_order(
            db, supplier.id, resolved, ordered_by="LLM", notes=notes,
        )

        return {
            "po_no": po.po_no,
            "supplier": supplier_name,
            "status": po.status,
            "items_count": len(items),
            "message": f"採購單 {po.po_no} 已建立（{po.status}）"
        }


async def query_bom(product_no: str = None, product_name: str = None) -> list:
    """查詢產品 BOM 結構。輸入產品料號或名稱，回傳物料清單。"""
    async with async_session() as db:
        products, _ = await bom_service.list_products(db, product_no or product_name)
        if not products:
            return []
        product = products[0]
        tree = await bom_service.get_bom_tree(db, product.id)
    return tree


async def bom_explode(product_no: str, quantity: float) -> dict:
    """BOM 多階展開。輸入成品料號和需求數量，展開所有層級的子件需求。"""
    async with async_session() as db:
        result = await bom_service.bom_explode(db, product_no, quantity)
    return result


async def check_stock_shortage(product_no: str, quantity: float) -> dict:
    """檢查缺料情況。輸入成品料號和需求數量，展開 BOM 後比對庫存，列出缺料項目。"""
    async with async_session() as db:
        result = await bom_service.check_shortage(db, product_no, quantity)
    return result


# ═══════════════════════════════════════════════
# Dispatch / Production Order Tools
# ═══════════════════════════════════════════════

async def create_work_center(name: str, description: str = "", capacity_hours: float = 8.0,
                             alternate_group: str = "") -> dict:
    """新增工作站/機台。需指定名稱、每日可用工時、可替代群組(用於Route Changing)。"""
    async with async_session() as db:
        wc = await dispatch_service.create_work_center(db, name=name, description=description,
                     capacity_hours=capacity_hours, alternate_group=alternate_group)
    return {"id": wc.id, "name": wc.name, "status": wc.status}


async def create_production_order(product_no: str, quantity: float, due_date: str,
                                   priority: int = 3, notes: str = "") -> dict:
    """建立生產工單。需指定產品料號、數量、交期(YYYY-MM-DD)、優先級(1-5)。"""
    async with async_session() as db:
        order = await dispatch_service.create_order(db,
            product_no=product_no, quantity=quantity, due_date=due_date,
            priority=priority, notes=notes, created_by="LLM")
    return {"order_no": order.order_no, "status": order.status, "product_no": product_no,
            "quantity": quantity, "due_date": str(due_date)}


async def release_order(order_no: str) -> dict:
    """釋出工單，變更狀態為 released（可派工）。"""
    async with async_session() as db:
        order = await dispatch_service.update_order(db, order_no, status="released")
        if not order:
            return {"error": f"Order {order_no} not found"}
    return {"order_no": order_no, "status": "released"}


async def dispatch_order(order_no: str) -> dict:
    """派工 — 將已釋出的工單分配到工作站。系統會依優先級和交期自動排程。"""
    async with async_session() as db:
        result = await dispatch_service.dispatch_order(db, order_no)
    return result


async def query_work_orders(status: str = "") -> list:
    """查詢工單列表。可過濾狀態：draft/released/dispatched/in_progress/completed。"""
    async with async_session() as db:
        orders = await dispatch_service.list_orders(db, status)
    return [
        {"order_no": o.order_no, "product_no": o.product_no, "quantity": o.quantity,
         "due_date": str(o.due_date), "priority": o.priority, "status": o.status}
        for o in orders
    ]


async def add_operation_to_order(order_no: str, work_center_name: str, sequence_no: int,
                                  name: str = "", setup_time_min: float = 0,
                                  cycle_time_min: float = 0) -> dict:
    """為工單新增工序。需指定工單號、工作站名稱、工序序號。"""
    async with async_session() as db:
        order = await dispatch_service.get_order(db, order_no=order_no)
        if not order:
            return {"error": f"Order {order_no} not found"}
        wc = await dispatch_service.get_work_center(db, name=work_center_name)
        if not wc:
            return {"error": f"WorkCenter '{work_center_name}' not found"}
        op = await dispatch_service.add_operation(db, order.id, wc.id, sequence_no,
                     name, setup_time_min, cycle_time_min, order.quantity)
    return {"operation_id": op.id, "order_no": order_no, "work_center": work_center_name,
            "sequence": sequence_no, "total_time_min": op.total_time_min}


async def right_shift_reschedule(work_center_name: str, delay_minutes: float = 30,
                                  reason: str = "") -> dict:
    """Right-Shift 重排程：機台故障或延誤時，將該機台上所有未完工序向後推移。"""
    async with async_session() as db:
        result = await dispatch_service.right_shift_reschedule(db, work_center_name,
                    delay_minutes, reason)
    return result


async def route_change_reschedule(work_center_name: str, reason: str = "") -> dict:
    """Route Changing：機台故障時，將工序轉到同一群組的替代機台。"""
    async with async_session() as db:
        result = await dispatch_service.route_change_reschedule(db, work_center_name, reason)
    return result


async def expedite_order(order_no: str, reason: str = "") -> dict:
    """急單插隊：將指定工單設為最高優先級，下次派工時優先排程。"""
    async with async_session() as db:
        result = await dispatch_service.expedite_reschedule(db, order_no, reason)
    return result


async def set_work_center_status(work_center_name: str, status: str) -> dict:
    """設定工作站狀態：idle / running / down / maintenance。"""
    async with async_session() as db:
        wc = await dispatch_service.get_work_center(db, name=work_center_name)
        if not wc:
            return {"error": f"WorkCenter '{work_center_name}' not found"}
        await dispatch_service.update_work_center(db, wc.id, status=status)
    return {"work_center": work_center_name, "status": status}


# ═══════════════════════════════════════════════
# Purchase Tools (list)
# ═══════════════════════════════════════════════

async def query_suppliers(name: str = "") -> list:
    """查詢供應商列表。可輸入名稱關鍵字過濾。"""
    async with async_session() as db:
        suppliers, total = await purchase_service.list_suppliers(db, name or None)
    return [
        {"id": str(s.id), "name": s.name, "contact": s.contact,
         "phone": s.phone, "email": s.email, "score": s.score}
        for s in suppliers
    ]


async def query_purchase_orders(po_no: str = "", status: str = "") -> list:
    """查詢採購單列表。可過濾狀態(draft/approved/shipped/received)或採購單號。"""
    async with async_session() as db:
        orders, total = await purchase_service.list_purchase_orders(db, status or None)
    # Filter by po_no if specified
    if po_no:
        orders = [o for o in orders if po_no.lower() in o.po_no.lower()]
    return [
        {
            "po_no": o.po_no, "supplier": o.supplier.name if o.supplier else "",
            "status": o.status, "ordered_by": o.ordered_by, "notes": o.notes,
            "created_at": str(o.created_at),
            "items": [
                {"part_no": i.part.part_no if i.part else "", "quantity": i.quantity,
                 "unit_price": i.unit_price, "received_qty": i.received_qty}
                for i in (o.items or [])
            ],
        }
        for o in orders
    ]


# ═══════════════════════════════════════════════
# Inventory Inbound / Outbound
# ═══════════════════════════════════════════════

async def inbound_material(part_no: str, quantity: float, location: str = "") -> dict:
    """入庫作業：將指定料號的物料入庫到指定儲位。"""
    async with async_session() as db:
        part = await inventory_service.get_part_by_no(db, part_no)
        if not part:
            return {"error": f"找不到料號 {part_no}"}
        inv = await inventory_service.inbound(db, part.id, quantity,
                    location=location or None, created_by="LLM",
                    reference_no=f"INBOUND-{part_no}")
    return {
        "part_no": part_no, "quantity": quantity, "location": location or "default",
        "message": f"{part_no} 已入庫 {quantity} 件",
    }


async def outbound_material(part_no: str, quantity: float, work_order: str = "") -> dict:
    """出庫作業：將指定料號的物料從庫存發出（例如發料至工單）。"""
    async with async_session() as db:
        part = await inventory_service.get_part_by_no(db, part_no)
        if not part:
            return {"error": f"找不到料號 {part_no}"}
        try:
            inv = await inventory_service.outbound(db, part.id, quantity,
                        reference_no=work_order or None, created_by="LLM",
                        actor_role="LLM")
        except ValueError as e:
            return {"error": str(e)}
    return {
        "part_no": part_no, "quantity": quantity, "work_order": work_order,
        "message": f"{part_no} 已出庫 {quantity} 件",
    }


# ═══════════════════════════════════════════════
# Quality / Inspection Tools
# ═══════════════════════════════════════════════

async def query_inspections(status: str = "") -> list:
    """查詢品檢單列表。可過濾狀態：pending/approved/rejected/conditional。"""
    async with async_session() as db:
        inspections, total = await quality_service.list_inspections(db, status or None)
    return [
        {
            "id": str(i.id), "inspection_no": i.inspection_no,
            "part_no": i.part.part_no if i.part else "",
            "quantity": i.quantity, "status": i.status,
            "lot_no": i.lot_no, "inspected_by": i.inspected_by,
            "inspection_date": str(i.inspection_date) if i.inspection_date else "",
        }
        for i in inspections
    ]


async def create_inspection(po_ref: str = "", part_no: str = "") -> dict:
    """新增品檢單。需指定採購單號和/或料號。"""
    async with async_session() as db:
        part = None
        if part_no:
            part = await inventory_service.get_part_by_no(db, part_no)
            if not part:
                return {"error": f"找不到料號 {part_no}"}
        insp = await quality_service.create_inspection(
            db, inspection_no="", part_id=part.id if part else None,
            quantity=0, po_id=None, actor_role="LLM",
        )
    return {
        "inspection_no": insp.inspection_no,
        "part_no": part_no, "status": insp.status,
        "message": f"品檢單 {insp.inspection_no} 已建立",
    }


async def query_ncs(status: str = "") -> list:
    """查詢不良品記錄（非符合項）。可過濾狀態：open/investigating/resolved/closed。"""
    async with async_session() as db:
        ncs, total = await quality_service.list_ncs(db, status or None)
    return [
        {
            "id": str(nc.id), "nc_no": nc.nc_no,
            "part_no": nc.part.part_no if nc.part else "",
            "defect_code": nc.defect_code, "severity": nc.severity,
            "description": nc.description[:100] if nc.description else "",
            "status": nc.status, "created_at": str(nc.created_at),
        }
        for nc in ncs
    ]


async def create_nc(part_no: str, defect_code: str, description: str,
                    severity: str = "major") -> dict:
    """建立不良品記錄(NC)。需指定料號、缺陷代碼、描述、嚴重程度(major/minor/critical)。"""
    async with async_session() as db:
        part = await inventory_service.get_part_by_no(db, part_no)
        if not part:
            return {"error": f"找不到料號 {part_no}"}
        nc = await quality_service.create_nc(
            db, nc_no="", part_id=part.id, description=description,
            defect_code=defect_code, severity=severity, created_by="LLM",
            actor_role="LLM",
        )
    return {
        "nc_no": nc.nc_no, "part_no": part_no, "severity": nc.severity,
        "status": nc.status,
        "message": f"不良品記錄 {nc.nc_no} 已建立（{severity}）",
    }


# ═══════════════════════════════════════════════
# Accounting Tools
# ═══════════════════════════════════════════════

async def query_accounts(type: str = "") -> list:
    """查詢會計科目列表。可依科目類型過濾(asset/liability/equity/revenue/expense)。"""
    async with async_session() as db:
        accounts, total = await accounting_service.list_accounts(db, type or None)
    return [
        {
            "account_no": a.account_no, "name": a.name, "type": a.type,
            "normal_balance": a.normal_balance, "is_active": a.is_active,
        }
        for a in accounts
    ]


async def query_ar(status: str = "") -> list:
    """查詢應收帳款(AR)列表。可過濾狀態：open/overdue/paid。"""
    async with async_session() as db:
        ar_list, total = await accounting_service.list_ar(db, status or None)
    return [
        {
            "id": str(ar.id), "customer_name": ar.customer_name,
            "invoice_no": ar.invoice_no, "amount": ar.amount,
            "paid_amount": ar.paid_amount, "due_date": str(ar.due_date),
            "status": ar.status,
        }
        for ar in ar_list
    ]


async def check_ar_overdue(days: int = 30) -> dict:
    """查詢逾期應收帳款。可設定逾期天數門檻（預設30天以上視為逾期）。"""
    async with async_session() as db:
        summary = await accounting_service.get_ar_summary(db)
    # Filter by overdue days threshold
    from datetime import date
    today = date.today()
    filtered_items = [
        item for item in summary.get("items", [])
        if item.get("overdue_days", 0) >= days
    ]
    return {
        "total_overdue": len(filtered_items),
        "total_amount": sum(
            item["amount"] - item.get("paid_amount", 0)
            for item in filtered_items
        ),
        "threshold_days": days,
        "items": filtered_items,
    }


async def create_journal_entry(description: str, lines: list) -> dict:
    """建立會計傳票/分錄。需提供摘要和明細行(每個明細包含account_no, debit, credit)。"""
    from datetime import date
    async with async_session() as db:
        try:
            entry = await accounting_service.create_journal_entry(
                db, description=description, entry_date=date.today(),
                lines=lines, created_by="LLM",
            )
        except ValueError as e:
            return {"error": str(e)}
    return {
        "entry_no": entry.entry_no, "description": entry.description,
        "entry_date": str(entry.entry_date), "posted": entry.posted,
        "message": f"傳票 {entry.entry_no} 已建立",
    }


# Tool name -> function mapping
TOOL_FUNCTIONS = {
    "query_inventory": query_inventory,
    "create_purchase_order": create_purchase_order,
    "query_bom": query_bom,
    "bom_explode": bom_explode,
    "check_stock_shortage": check_stock_shortage,
    # Purchase
    "query_suppliers": query_suppliers,
    "query_purchase_orders": query_purchase_orders,
    # Dispatch
    "create_work_center": create_work_center,
    "create_production_order": create_production_order,
    "release_order": release_order,
    "dispatch_order": dispatch_order,
    "query_work_orders": query_work_orders,
    "add_operation_to_order": add_operation_to_order,
    "right_shift_reschedule": right_shift_reschedule,
    "route_change_reschedule": route_change_reschedule,
    "expedite_order": expedite_order,
    "set_work_center_status": set_work_center_status,
    # Inventory
    "inbound_material": inbound_material,
    "outbound_material": outbound_material,
    # Quality
    "query_inspections": query_inspections,
    "create_inspection": create_inspection,
    "query_ncs": query_ncs,
    "create_nc": create_nc,
    # Accounting
    "query_accounts": query_accounts,
    "query_ar": query_ar,
    "check_ar_overdue": check_ar_overdue,
    "create_journal_entry": create_journal_entry,
}
