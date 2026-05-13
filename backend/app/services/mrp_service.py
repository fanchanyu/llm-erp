"""
MRP Service — Material Requirements Planning Calculation Engine

Core functions:
- BOM 展開 (遞迴 multi-level explosion)
- 淨需求計算 (Net Requirements = Gross - OnHand - InTransit + Allocated)
- 提前期偏移 (Lead Time Offset)
- 完整 MRP 運算 (run_mrp orchestrator)

MRP 邏輯流程:
  1. 從 MPS 讀取計畫訂單 (planned_order_qty > 0)
  2. 對每個 MPS 產品進行 BOM 展開 → 產生各階層毛需求
  3. 各時段淨需求 = 毛需求 - 可用庫存 - 在途量 + 已分配量
  4. 依 Part.lead_time_days 進行提前期偏移 → 產生計畫下達
"""

import uuid
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.mrp import MrpMaster, MrpItem
from app.models.mps import MpsEntry
from app.models.bom import BOMItem, Product
from app.models.inventory import Inventory, Part
from app.models.purchase import PurchaseOrderItem


# ═══════════════════════════════════════════════
# MRP Master CRUD
# ═══════════════════════════════════════════════

async def create_mrp_master(db: AsyncSession, **kw) -> MrpMaster:
    """建立 MRP 主檔"""
    master = MrpMaster(**kw)
    db.add(master)
    await db.flush()
    return master


async def get_mrp_master(db: AsyncSession, master_id: str = "") -> MrpMaster | None:
    """取得單一 MRP 主檔"""
    q = select(MrpMaster).options(selectinload(MrpMaster.items))
    if master_id:
        q = q.where(MrpMaster.id == master_id)
    r = await db.execute(q)
    return r.scalar_one_or_none()


async def list_mrp_masters(
    db: AsyncSession, status: str = "", limit: int = 50
) -> list[MrpMaster]:
    """列出 MRP 主檔"""
    q = select(MrpMaster)
    if status:
        q = q.where(MrpMaster.status == status)
    r = await db.execute(q.order_by(MrpMaster.created_at.desc()).limit(limit))
    return list(r.scalars().all())


async def update_mrp_master(
    db: AsyncSession, master_id: str, **kw
) -> MrpMaster | None:
    """更新 MRP 主檔"""
    master = await get_mrp_master(db, master_id=master_id)
    if not master:
        return None
    for k, v in kw.items():
        if v is not None:
            setattr(master, k, v)
    await db.flush()
    return master


# ═══════════════════════════════════════════════
# MRP Items CRUD
# ═══════════════════════════════════════════════

async def get_mrp_items(
    db: AsyncSession, mrp_id: str, part_no: str = "", bom_level: int = -1
) -> list[MrpItem]:
    """取得 MRP 明細清單"""
    q = select(MrpItem).where(MrpItem.mrp_id == mrp_id)
    if part_no:
        q = q.where(MrpItem.part_no == part_no)
    if bom_level >= 0:
        q = q.where(MrpItem.bom_level == bom_level)
    r = await db.execute(q.order_by(MrpItem.bom_level, MrpItem.period_week, MrpItem.part_no))
    return list(r.scalars().all())


async def create_mrp_items(db: AsyncSession, items: list[dict]) -> list[MrpItem]:
    """批量建立 MRP 明細"""
    objs = [MrpItem(**item) for item in items]
    db.add_all(objs)
    await db.flush()
    return objs


async def clear_mrp_items(db: AsyncSession, mrp_id: str) -> int:
    """清除指定 MRP 的所有明細（重新運算前呼叫）"""
    items = await get_mrp_items(db, mrp_id=mrp_id)
    count = len(items)
    for item in items:
        await db.delete(item)
    await db.flush()
    return count


# ═══════════════════════════════════════════════
# Step 1: 從 MPS 讀取計畫訂單
# ═══════════════════════════════════════════════

async def get_mps_planned_orders(
    db: AsyncSession, mps_id: str
) -> list[dict]:
    """讀取 MPS 計畫訂單 (planned_order_qty > 0)

    回傳: [{product_no, period_week (as int), quantity, ...}]
    """
    r = await db.execute(
        select(MpsEntry)
        .where(
            and_(
                MpsEntry.mps_id == mps_id,
                MpsEntry.planned_order_qty > 0,
            )
        )
        .order_by(MpsEntry.period_week)
    )
    entries = list(r.scalars().all())
    results = []
    for entry in entries:
        # Convert period_week (Date) to week integer if not already
        week_num = entry.week_number if entry.week_number else 0
        results.append({
            "product_no": entry.product_no,
            "product_name": entry.product_name,
            "period_week": week_num,
            "period_date": entry.period_week,
            "quantity": entry.planned_order_qty,
        })
    return results


# ═══════════════════════════════════════════════
# Step 2: BOM 展開 (遞迴多階層)
# ═══════════════════════════════════════════════

async def explode_bom(
    db: AsyncSession,
    product_no: str,
    quantity: float,
    level: int = 0,
    max_level: int = 3,
) -> list[dict]:
    """遞迴 BOM 展開

    查詢 BOMItem 找到該產品的所有子件，
    每個子件的毛需求 = parent_qty * bom_item.quantity，
    遞迴到 max_level 為止。

    回傳: [{level, product_no, part_no, part_name, required_qty, ...}]
    """
    if level > max_level:
        return []

    items = []

    # 查詢 BOMItem: 該產品的子件
    # product_no → Product.id → BOMItem.product_id
    prod_r = await db.execute(
        select(Product).where(Product.product_no == product_no)
    )
    product = prod_r.scalar_one_or_none()
    if not product:
        return items

    r = await db.execute(
        select(BOMItem)
        .where(BOMItem.product_id == product.id)
        .order_by(BOMItem.sequence_no, BOMItem.level)
    )
    bom_items = list(r.scalars().all())

    for bom in bom_items:
        # 查詢 Part 資訊
        part_r = await db.execute(
            select(Part).where(Part.id == bom.part_id)
        )
        part = part_r.scalar_one_or_none()
        if not part:
            continue

        # 查詢 BOMItem 關聯的 Part (via relationship) 取得名稱
        part_name = part.name
        lead_time = getattr(part, "lead_time_days", 7)  # fallback default
        unit = part.unit

        required_qty = quantity * bom.quantity

        # 判斷 order_type: 如果該 part 有子 BOM 則為 "make"，否則 "buy"
        # 檢查該 part 是否作為 product 出現在 BOMItem 中
        child_bom_r = await db.execute(
            select(BOMItem)
            .join(Product, BOMItem.product_id == Product.id)
            .where(Product.product_no == part.part_no)
            .limit(1)
        )
        has_child_bom = child_bom_r.scalar_one_or_none() is not None
        order_type = "make" if has_child_bom else "buy"

        items.append({
            "level": level + 1,
            "product_no": product_no,
            "part_no": part.part_no,
            "part_name": part_name,
            "required_qty": required_qty,
            "unit": unit,
            "order_type": order_type,
            "lead_time_days": lead_time,
        })

        # 遞迴: 如果該子件本身也有 BOM，繼續展開
        child_items = await explode_bom(
            db, product_no=part.part_no,
            quantity=required_qty,
            level=level + 1,
            max_level=max_level,
        )
        items.extend(child_items)

    return items


# Helper alias for explode_bom with part_no parameter name
async def explode_bom_by_product(
    db: AsyncSession,
    product_no: str,
    quantity: float,
    level: int = 0,
    max_level: int = 3,
) -> list[dict]:
    """BOM 展開對外介面 (product_no 入口)"""
    return await explode_bom(db, product_no, quantity, level, max_level)


# ═══════════════════════════════════════════════
# Step 3: 淨需求計算
# ═══════════════════════════════════════════════

async def calculate_net_requirements(
    db: AsyncSession,
    gross_items: list[dict],
) -> list[dict]:
    """淨需求計算

    對每個 BOM 展開後的料件，計算:
      net_requirement = gross_requirement - on_hand_qty - in_transit_qty + allocated_qty

    查詢來源:
      - Inventory: 現有庫存 (quantity)
      - Inventory: 已分配量 (allocated_qty, 如有此欄位)
      - PurchaseOrderItem: 在途量 (quantity - received_qty, 未交貨部分)

    回傳: 加入庫存資訊後的增強清單
    """
    results = []

    for item in gross_items:
        part_no = item["part_no"]
        gross_req = item["required_qty"]

        # 查詢庫存
        # Inventory 使用 part_id (UUID FK), 需透過 Part 查詢 part_no
        inv_r = await db.execute(
            select(Inventory)
            .join(Part, Inventory.part_id == Part.id)
            .where(Part.part_no == part_no)
        )
        inv = inv_r.scalar_one_or_none()

        on_hand_qty = 0.0
        allocated_qty = 0.0

        if inv:
            on_hand_qty = inv.quantity or 0.0
            # allocated_qty 可能不存在於 schema 中
            if hasattr(inv, "allocated_qty") and inv.allocated_qty is not None:
                allocated_qty = inv.allocated_qty

        # 查詢在途量 (Purchase Order Items, 尚未交貨)
        in_transit_qty = 0.0
        try:
            po_r = await db.execute(
                select(PurchaseOrderItem)
                .join(Part, PurchaseOrderItem.part_id == Part.id)
                .where(Part.part_no == part_no)
            )
            po_items = list(po_r.scalars().all())
            for po_item in po_items:
                # 已訂但未交 = quantity - received_qty
                outstanding = po_item.quantity - (po_item.received_qty or 0)
                if outstanding > 0:
                    in_transit_qty += outstanding
        except Exception:
            # 若 schema 不完整則忽略
            pass

        # 淨需求 = 毛需求 - 庫存 - 在途 + 已分配
        # 若為負值則設為 0 (無淨需求)
        available_qty = on_hand_qty + in_transit_qty - allocated_qty
        net_req = max(0, gross_req - available_qty)

        result_item = {**item}
        result_item.update({
            "gross_requirement": gross_req,
            "on_hand_qty": on_hand_qty,
            "allocated_qty": allocated_qty,
            "in_transit_qty": in_transit_qty,
            "available_qty": available_qty,
            "net_requirement": net_req,
            "planned_order_qty": net_req,  # 淨需求即為計畫訂單量 (lot-for-lot)
            "exception_message": "",
        })

        # 例外: 庫存不足以滿足毛需求
        if net_req > 0 and on_hand_qty < gross_req * 0.5:
            result_item["exception_message"] = (
                f"庫存不足: 毛需求 {gross_req}, "
                f"可用庫存 {on_hand_qty:.1f} + 在途 {in_transit_qty:.1f} "
                f"- 已分配 {allocated_qty:.1f}"
            )

        results.append(result_item)

    return results


# ═══════════════════════════════════════════════
# Step 4: 提前期偏移
# ═══════════════════════════════════════════════

async def apply_lead_time_offset(
    db: AsyncSession,
    net_items: list[dict],
    period_week: int = 0,
    week_days: int = 7,
) -> list[dict]:
    """提前期偏移

    根據 Part.lead_time_days 計算實際下單時間:
      - planned_order_release = period_week - ceil(lead_time_days / week_days)
      - 若偏移後 < 0，設為 0 (需要立即下單)

    參數:
      net_items: 淨需求計算後的料件清單
      period_week: 當前期數 (對應 MPS 的 week_number)
      week_days: 每週天數 (預設 7)

    回傳: 加入 planned_order_release 後的清單
    """
    results = []

    for item in net_items:
        lead_time_days = item.get("lead_time_days", 7)
        net_req = item.get("net_requirement", 0)

        # 計算偏移期數
        offset_weeks = max(1, (lead_time_days + week_days - 1) // week_days)
        release_week = max(0, period_week - offset_weeks)

        result_item = {**item}
        result_item["period_week"] = period_week
        result_item["planned_order_release"] = release_week

        # 例外: 需要立即下單 (提前期不足)
        if release_week == 0 and net_req > 0 and lead_time_days > 0:
            existing_msg = result_item.get("exception_message", "") or ""
            warning = f"需立即下單: 提前期 {lead_time_days} 天 > 可用時段"
            result_item["exception_message"] = (
                f"{existing_msg}; {warning}" if existing_msg else warning
            )

        results.append(result_item)

    return results


# ═══════════════════════════════════════════════
# Step 5: 完整 MRP 運算 (run_mrp)
# ═══════════════════════════════════════════════

async def run_mrp(
    db: AsyncSession,
    mrp_id: str,
    starting_inventory: float = 0,
    max_bom_level: int = 3,
    week_days: int = 7,
) -> dict:
    """執行完整的 MRP 運算

    整合流程:
      1. 清除舊有 MRP 明細
      2. 從 MPS 讀取計畫訂單 (get_mps_planned_orders)
      3. BOM 展開 (explode_bom)
      4. 淨需求計算 (calculate_net_requirements)
      5. 提前期偏移 (apply_lead_time_offset)
      6. 儲存結果至 MrpItem

    參數:
      db: AsyncSession
      mrp_id: MRP 主檔 ID
      starting_inventory: 期初庫存
      max_bom_level: BOM 最大展開階層 (預設 3)
      week_days: 每週天數 (預設 7)

    回傳: MRP 運算摘要 dict
    """
    # 1. 取得 MRP Master
    master = await get_mrp_master(db, master_id=mrp_id)
    if not master:
        return {"error": f"MRP master {mrp_id} not found"}

    # 2. 清除舊明細
    await clear_mrp_items(db, mrp_id=mrp_id)

    # 3. 從 MPS 讀取計畫訂單
    planned_orders = await get_mps_planned_orders(db, master.mps_id)
    if not planned_orders:
        # 更新狀態
        await update_mrp_master(db, mrp_id, status="completed")
        return {
            "mrp_id": mrp_id,
            "mrp_name": master.name,
            "status": "completed",
            "message": "MPS 無計畫訂單，MRP 無項目產出",
            "total_items": 0,
            "total_make_orders": 0,
            "total_buy_orders": 0,
        }

    all_mrp_items = []
    total_make = 0
    total_buy = 0
    exception_count = 0

    for order in planned_orders:
        product_no = order["product_no"]
        order_qty = order["quantity"]
        period_week = order["period_week"]

        # 4. BOM 展開
        bom_items = await explode_bom(
            db, product_no, order_qty, level=0, max_level=max_bom_level
        )

        if not bom_items:
            # 無 BOM 項目: 可能是採購件或未定義 BOM
            continue

        # 5. 淨需求計算
        net_items = await calculate_net_requirements(db, bom_items)

        # 6. 提前期偏移
        offset_items = await apply_lead_time_offset(
            db, net_items, period_week=period_week, week_days=week_days
        )

        # 7. 組裝 MrpItem 資料
        for item in offset_items:
            is_make = item.get("order_type", "buy") == "make"
            if is_make:
                total_make += 1
            else:
                total_buy += 1
            if item.get("exception_message"):
                exception_count += 1

            all_mrp_items.append({
                "mrp_id": mrp_id,
                "product_no": product_no,
                "part_no": item.get("part_no", ""),
                "part_name": item.get("part_name", ""),
                "bom_level": item.get("level", 0),
                "period_week": period_week,
                "gross_requirement": item.get("gross_requirement", 0),
                "scheduled_receipts": item.get("in_transit_qty", 0),
                "projected_balance": item.get("available_qty", 0),
                "net_requirement": item.get("net_requirement", 0),
                "planned_order_qty": item.get("planned_order_qty", 0),
                "planned_order_release": item.get("planned_order_release", 0),
                "order_type": item.get("order_type", "buy"),
                "lead_time_days": item.get("lead_time_days", 0),
                "source": item.get("source", ""),
                "exception_message": item.get("exception_message", ""),
            })

    # 8. 批量儲存
    if all_mrp_items:
        await create_mrp_items(db, all_mrp_items)

    # 9. 更新狀態
    await update_mrp_master(db, mrp_id, status="completed")

    return {
        "mrp_id": mrp_id,
        "mrp_name": master.name,
        "mps_id": master.mps_id,
        "status": "completed",
        "total_items": len(all_mrp_items),
        "total_make_orders": total_make,
        "total_buy_orders": total_buy,
        "exception_count": exception_count,
        "has_exceptions": exception_count > 0,
        "message": f"MRP 運算完成: {len(all_mrp_items)} 筆項目, "
                   f"{total_make} 筆自製, {total_buy} 筆採購, "
                   f"{exception_count} 筆例外",
    }
