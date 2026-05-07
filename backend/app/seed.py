"""
LLM-ERP Seed Data — 填入測試用的樣本資料
執行方式：python -m app.seed
"""

import asyncio
import uuid
from datetime import datetime, date, timedelta
from app.database import async_session, init_db
from app.models.inventory import Part, Inventory, InventoryTransaction
from app.models.purchase import Supplier, PurchaseOrder, PurchaseOrderItem
from app.models.bom import Product, BOMItem
from app.models.audit_log import AuditLog
from app.models.quality import InspectionOrder, InspectionResult, NonConformance, CAPARecord
from app.models.accounting import Account, JournalEntry, JournalLine, AccountsReceivable, MonthEndClose
from sqlalchemy import select


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

    # ─── Seed Quality Data ──────────────────────────────────
    async with async_session() as db:
        # Create a sample inspection
        insp = InspectionOrder(
            inspection_no="IQC-20260505-001",
            part_id=part_ids["M6x20"],
            lot_no="LOT-A001",
            quantity=500,
            status="pending",
            inspected_by="QC-Team",
        )
        db.add(insp)
        await db.flush()

        # Create a sample NC
        nc = NonConformance(
            nc_no="NC-20260505-001",
            inspection_id=insp.id,
            part_id=part_ids["M8x30"],
            defect_code="DIM-OUT",
            description="M8x30 螺絲長度超差 0.5mm",
            severity="major",
            status="open",
            created_by="QC-Team",
        )
        db.add(nc)
        await db.flush()

        # Create a CAPA for the NC
        capa = CAPARecord(
            nc_id=nc.id,
            root_cause="模具磨損，需更換沖頭",
            action="更換沖頭模組，重新調教",
            responsible="生產-張三",
            status="planned",
        )
        db.add(capa)
        await db.commit()

    print("   - 1 inspection order")
    print("   - 1 non-conformance")
    print("   - 1 CAPA record")

    # ─── Seed Accounting Data ───────────────────────────────
    async with async_session() as db:
        # Chart of Accounts
        accounts_data = [
            ("1101", "現金", "asset", "debit"),
            ("1102", "銀行存款", "asset", "debit"),
            ("1201", "應收帳款", "asset", "debit"),
            ("1301", "庫存原料", "asset", "debit"),
            ("1302", "在製品", "asset", "debit"),
            ("1303", "庫存成品", "asset", "debit"),
            ("2101", "應付帳款", "liability", "credit"),
            ("2102", "暫估應付", "liability", "credit"),
            ("3101", "股本", "equity", "credit"),
            ("4101", "銷貨收入", "revenue", "credit"),
            ("5101", "原料成本", "expense", "debit"),
            ("5102", "製造費用", "expense", "debit"),
        ]
        for ano, aname, atype, abal in accounts_data:
            acc = Account(account_no=ano, name=aname, type=atype, normal_balance=abal)
            db.add(acc)
        await db.flush()

        # Sample journal entry (material received → PO收货)
        jentry = JournalEntry(
            entry_no="JV-20260505-001",
            description="PO-20260505-001 入庫-螺絲一批",
            entry_date=date(2026, 5, 5),
            period="2026-05",
            source_type="PO",
            source_id="PO-20260505-001",
            created_by="system",
        )
        db.add(jentry)
        await db.flush()

        # Debit inventory, Credit AP
        lines = [
            (jentry.id, "1301", 550.0, 0),   # 原料增加
            (jentry.id, "2101", 0, 550.0),   # 應付增加
        ]
        for eid, acct_no, dr, cr in lines:
            account = await db.execute(select(Account).where(Account.account_no == acct_no))
            acc = account.scalar_one()
            jl = JournalLine(entry_id=eid, account_id=acc.id, debit=dr, credit=cr)
            db.add(jl)

        # Sample AR
        ar = AccountsReceivable(
            customer_name="客戶A-精密機械",
            invoice_no="INV-20260505-001",
            amount=150000.0,
            due_date=date(2026, 6, 5),
            status="open",
        )
        db.add(ar)
        await db.commit()

    print("   - 12 accounts (chart of accounts)")
    print("   - 1 journal entry (2 lines)")
    print("   - 1 AR record")

    # ─── Seed Dispatch Data ──────────────────────────────────────
    async with async_session() as db:
        from app.models.dispatch import WorkCenter, ProductionOrder, Operation, DispatchLog, OrderStatus, OpStatus, WCStatus

        # Create WorkCenters
        wcs_data = [
            ("CNC-01", "CNC 加工中心", WCStatus.IDLE.value, 8.0, 0.95, "A區", "cnc_group"),
            ("銑床-01", "立式銑床", WCStatus.IDLE.value, 8.0, 0.90, "A區", "mill_group"),
            ("鑽床-01", "鑽孔機", WCStatus.IDLE.value, 8.0, 0.85, "B區", "drill_group"),
            ("裝配線A", "主裝配線", WCStatus.IDLE.value, 8.0, 1.0, "C區", "assembly"),
            ("QC-01", "品檢站", WCStatus.IDLE.value, 8.0, 1.0, "C區", "qc"),
        ]
        wc_ids = {}
        for wname, wdesc, wstat, wcap, weff, wloc, wgroup in wcs_data:
            wc = WorkCenter(name=wname, description=wdesc, status=wstat, capacity_hours=wcap, efficiency=weff, location=wloc, alternate_group=wgroup)
            db.add(wc)
            await db.flush()
            wc_ids[wname] = wc.id

        # Create Production Orders
        today = date.today()
        orders_data = [
            ("ASM-001", "自動鎖螺絲機基座", 10, today + timedelta(days=5), 2),
            ("CNC-001", "小型CNC銑床", 5, today + timedelta(days=10), 3),
            ("ASM-001", "自動鎖螺絲機基座", 8, today + timedelta(days=7), 1),
        ]
        order_ids = {}
        for pno, pname, qty, dd, pri in orders_data:
            po = ProductionOrder(
                order_no=f"WO-{today.strftime('%Y%m%d')}-{orders_data.index((pno,pname,qty,dd,pri))+1:03d}",
                product_no=pno, product_name=pname, quantity=qty,
                due_date=dd, priority=pri, status=OrderStatus.RELEASED.value,
                created_by="seed",
            )
            db.add(po)
            await db.flush()
            order_ids[po.order_no] = po.id

            # Add operations for each order
            ops_seq = [
                (wc_ids["CNC-01"], 1, "CNC加工", 15, 12, qty),
                (wc_ids["銑床-01"], 2, "銑面", 10, 8, qty),
                (wc_ids["鑽床-01"], 3, "鑽孔", 8, 5, qty),
                (wc_ids["裝配線A"], 4, "組裝", 20, 15, qty),
                (wc_ids["QC-01"], 5, "品檢", 5, 3, qty),
            ]
            for wcid, seq, opname, setup, cyc, q in ops_seq:
                total = setup + cyc * q
                op = Operation(
                    order_id=po.id, work_center_id=wcid,
                    sequence_no=seq, name=opname,
                    setup_time_min=setup, cycle_time_min=cyc,
                    total_time_min=total, status=OpStatus.PENDING.value,
                )
                db.add(op)

        await db.commit()

    print("   - 5 work centers")
    print("   - 3 production orders (with operations)")


if __name__ == "__main__":
    asyncio.run(seed())
