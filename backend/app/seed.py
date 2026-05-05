"""
LLM-ERP Seed Data — 填入測試用的樣本資料
執行方式：python -m app.seed
"""

import asyncio
import uuid
from app.database import async_session, init_db
from app.models.inventory import Part, Inventory, InventoryTransaction
from app.models.purchase import Supplier, PurchaseOrder, PurchaseOrderItem
from app.models.bom import Product, BOMItem
from app.models.audit_log import AuditLog


async def seed():
    await init_db()
    async with async_session() as db:
        # ─── 料號 ─────────────────────────────────
        parts_data = [
            ("M6x20", "不鏽鋼螺絲 M6x20", "SUS304 M6x20 全牙", "pcs", "緊固件"),
            ("M8x30", "碳鋼螺絲 M8x30", "12.9級 碳鋼 M8x30", "pcs", "緊固件"),
            ("PLT-001", "底板 300x200mm", "Q235 雷切底板 300x200x5mm", "pcs", "鈑金件"),
            ("PLT-002", "側板 200x150mm", "Q235 雷切側板 200x150x3mm", "pcs", "鈑金件"),
            ("MTR-001", "馬達 400W", "交流伺服馬達 400W 220V", "pcs", "電機"),
            ("DRV-001", "驅動器 400W", "數位驅動器 400W 相容MTR-001", "pcs", "電機"),
            ("CBL-001", "電源線 1.5m", "3芯 2.0mm² 電源線 1.5米", "pcs", "線材"),
            ("CBL-002", "編碼器線 3m", "編碼器訊號線 3米", "pcs", "線材"),
            ("BRG-001", "軸承 6205", "深溝滾珠軸承 6205ZZ", "pcs", "傳動件"),
            ("SLR-001", "線性滑軌 500mm", "線性滑軌 HGH20 500mm", "pcs", "傳動件"),
            ("BLK-001", "滑塊 HGH20", "直線滑塊 HGH20-CA", "pcs", "傳動件"),
            ("TIM-001", "時規皮帶 600mm", "時規皮帶 HTD 5M 600mm", "pcs", "傳動件"),
        ]

        part_ids = {}
        for pno, pname, pspec, punit, pcat in parts_data:
            p = Part(part_no=pno, name=pname, spec=pspec, unit=punit, category=pcat)
            db.add(p)
            await db.flush()
            part_ids[pno] = p.id

        # ─── 庫存 ─────────────────────────────────
        stock_data = [
            ("M6x20", "A-01-01", 2000),
            ("M8x30", "A-01-02", 800),
            ("PLT-001", "B-01-01", 50),
            ("PLT-002", "B-01-02", 30),
            ("MTR-001", "C-01-01", 15),
            ("DRV-001", "C-01-02", 12),
            ("CBL-001", "D-01-01", 100),
            ("CBL-002", "D-01-02", 60),
            ("BRG-001", "E-01-01", 40),
            ("SLR-001", "F-01-01", 10),
            ("BLK-001", "F-01-02", 20),
            ("TIM-001", "G-01-01", 25),
        ]
        for pno, loc, qty in stock_data:
            inv = Inventory(part_id=part_ids[pno], location=loc, quantity=qty)
            db.add(inv)

        # ─── 供應商 ── ──────────────────────────────
        supplier = Supplier(name="大明螺絲", contact="王大明", phone="02-1234-5678")
        db.add(supplier)
        supplier2 = Supplier(name="電機王", contact="陳電機", phone="02-8765-4321")
        db.add(supplier2)
        await db.flush()

        # ─── 產品 & BOM ─────────────────────────
        # 產品A：自動鎖螺絲機基座
        prod_a = Product(product_no="ASM-001", name="自動鎖螺絲機基座", 
                         description="包含底板、側板、線性滑軌模組")
        db.add(prod_a)
        await db.flush()

        # BOM 結構（兩層）
        bom_a = [
            ("PLT-001", 1, 0, 1),
            ("PLT-002", 2, 1, 2),
            ("SLR-001", 2, 1, 3),
            ("BLK-001", 4, 1, 4),
            ("M6x20", 16, 2, 5),
            ("M8x30", 8, 2, 6),
        ]
        for pno, qty, lvl, seq in bom_a:
            b = BOMItem(product_id=prod_a.id, part_id=part_ids[pno], 
                       quantity=qty, level=lvl, sequence_no=seq)
            db.add(b)

        # 產品B：小型CNC
        prod_b = Product(product_no="CNC-001", name="小型CNC銑床", 
                         description="桌上型 CNC 銑床，含驅動與傳動系統")
        db.add(prod_b)
        await db.flush()

        bom_b = [
            ("PLT-001", 1, 0, 1),
            ("PLT-002", 2, 0, 2),
            ("MTR-001", 3, 1, 3),
            ("DRV-001", 3, 1, 4),
            ("SLR-001", 2, 1, 5),
            ("BLK-001", 4, 1, 6),
            ("BRG-001", 6, 2, 7),
            ("TIM-001", 2, 2, 8),
            ("CBL-001", 3, 2, 9),
            ("CBL-002", 3, 2, 10),
            ("M6x20", 24, 2, 11),
            ("M8x30", 12, 2, 12),
        ]
        for pno, qty, lvl, seq in bom_b:
            b = BOMItem(product_id=prod_b.id, part_id=part_ids[pno],
                       quantity=qty, level=lvl, sequence_no=seq)
            db.add(b)

        # ─── 採購單測試 ─────────────────────────
        po = PurchaseOrder(po_no="PO-20260505-001", supplier_id=supplier.id,
                          status="draft", ordered_by="seed", notes="測試採購單")
        db.add(po)
        await db.flush()

        po_items = [
            (part_ids["M6x20"], 500, 0.50),
            (part_ids["M8x30"], 300, 0.80),
        ]
        for pid, qty, price in po_items:
            item = PurchaseOrderItem(po_id=po.id, part_id=pid, quantity=qty, unit_price=price)
            db.add(item)

        await db.commit()

    print("✅ Seed data inserted!")
    print(f"   - {len(parts_data)} parts")
    print(f"   - {len(stock_data)} stock records")
    print(f"   - 2 suppliers")
    print(f"   - 2 products with BOM")
    print(f"   - 1 purchase order")


if __name__ == "__main__":
    asyncio.run(seed())
