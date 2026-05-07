"""
Seed Dispatch Data — WorkCenters + Sample Production Order + Operations
"""

import asyncio
import uuid
from datetime import datetime, date, timedelta
from app.database import async_session, init_db
from app.services import dispatch_service as svc


async def seed_dispatch():
    await init_db()
    async with async_session() as db:
        # ── WorkCenters ──
        wcs = [
            {"name": "CNC-01", "description": "CNC 銑床 #1", "capacity_hours": 8.0, "alternate_group": "cnc"},
            {"name": "CNC-02", "description": "CNC 銑床 #2 (備援)", "capacity_hours": 8.0, "alternate_group": "cnc"},
            {"name": "鑽床-01", "description": "立式鑽床", "capacity_hours": 8.0, "alternate_group": "drill"},
            {"name": "裝配線A", "description": "產品組裝線 A", "capacity_hours": 8.0, "alternate_group": "assembly"},
            {"name": "裝配線B", "description": "產品組裝線 B (備援)", "capacity_hours": 8.0, "alternate_group": "assembly"},
            {"name": "QC-01", "description": "品檢站", "capacity_hours": 8.0, "alternate_group": ""},
        ]
        for wc_data in wcs:
            existing = await svc.get_work_center(db, name=wc_data["name"])
            if not existing:
                await svc.create_work_center(db, **wc_data)
                print(f"  ✅ WorkCenter: {wc_data['name']}")

        # ── Sample Production Order (CNC-001 × 3台) ──
        order = await svc.create_order(
            db,
            product_no="CNC-001",
            product_name="小型CNC銑床",
            quantity=3,
            due_date=date.today() + timedelta(days=14),
            priority=2,
            notes="客戶急單",
            created_by="seed",
        )

        # ── Operations ──
        # 工序1: 底板銑削 → CNC
        cnc = await svc.get_work_center(db, name="CNC-01")
        # 工序2: 鑽孔 → 鑽床
        drill = await svc.get_work_center(db, name="鑽床-01")
        # 工序3: 組裝 → 裝配線A
        assembly = await svc.get_work_center(db, name="裝配線A")
        # 工序4: 品檢 → QC
        qc = await svc.get_work_center(db, name="QC-01")

        ops_data = [
            (cnc.id, 1, "底板銑削加工", 15, 30),
            (drill.id, 2, "定位孔鑽孔", 10, 8),
            (assembly.id, 3, "馬達與驅動器組裝", 20, 45),
            (qc.id, 4, "功能測試與品檢", 5, 15),
        ]

        for wc_id, seq, name, setup, cycle in ops_data:
            await svc.add_operation(
                db, order.id, wc_id, seq, name, setup, cycle, quantity=3,
            )
            print(f"  ✅ Operation: {name}")

        await db.commit()
        print(f"\n✅ Dispatch seed complete!")
        print(f"   - {len(wcs)} work centers")
        print(f"   - 1 production order: {order.order_no}")
        print(f"   - 4 operations")


if __name__ == "__main__":
    asyncio.run(seed_dispatch())
