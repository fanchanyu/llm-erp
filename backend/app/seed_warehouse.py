"""
Phase B Seed Data — WMS zones, bins, suppliers, evaluations, pricing, reorder rules.
Run: python -m app.seed_warehouse
"""
import asyncio
from datetime import date, datetime
from sqlalchemy import select
from app.database import async_session, init_db
from app.models.warehouse import WarehouseZone, BinLocation, SupplierEvaluation, SupplierPrice, ReorderRule
from app.models.purchase import Supplier
from app.models.inventory import Part


async def seed_warehouse():
    await init_db()
    async with async_session() as db:
        # ── Warehouse Zones ──
        zones_data = [
            ("RAW", "原料倉", "raw"), ("SEMI", "半成品倉", "semi"),
            ("FINISHED", "成品倉", "finished"), ("DEFECT", "不良品倉", "defect"),
            ("QUARANTINE", "待檢區", "quarantine"),
        ]
        for code, name, ztype in zones_data:
            existing = await db.execute(select(WarehouseZone).where(WarehouseZone.code == code))
            if not existing.scalar_one_or_none():
                db.add(WarehouseZone(code=code, name=name, zone_type=ztype))

        # ── Bin Locations ──
        zone_map = {}
        for code, _, _ in zones_data:
            r = await db.execute(select(WarehouseZone).where(WarehouseZone.code == code))
            z = r.scalar_one_or_none()
            if z: zone_map[code] = z.id

        bins_data = [
            ("RAW-A-01", "RAW", "A", "1", None, None, 1000),
            ("RAW-A-02", "RAW", "A", "2", None, None, 1000),
            ("RAW-B-01", "RAW", "B", "1", None, None, 800),
            ("SEMI-A-01", "SEMI", "A", "1", None, None, 500),
            ("FINISHED-A-01", "FINISHED", "A", "1", None, None, 500),
            ("FINISHED-A-02", "FINISHED", "A", "2", None, None, 500),
            ("DEFECT-A-01", "DEFECT", "A", "1", None, None, 200),
        ]
        for code, zcode, aisle, rack, shelf, bin_, cap in bins_data:
            existing = await db.execute(select(BinLocation).where(BinLocation.code == code))
            if not existing.scalar_one_or_none() and zcode in zone_map:
                db.add(BinLocation(zone_id=zone_map[zcode], code=code,
                        aisle=aisle, rack=rack, shelf=shelf, bin=bin_,
                        max_capacity=cap))

        # ── Suppliers (if not exist) ──
        existing_s = await db.execute(select(Supplier).where(Supplier.name == "大發鋼鐵"))
        if not existing_s.scalar_one_or_none():
            suppliers = [
                ("大發鋼鐵", "王先生", "02-1234-5678", "dafa@steel.com"),
                ("永裕五金", "李經理", "04-2345-6789", "yungyu@hardware.com"),
                ("日盛電子", "陳業務", "03-3456-7890", "risheng@elec.com"),
                ("長春化工", "林課長", "07-4567-8901", "changchun@chem.com"),
            ]
            for name, contact, phone, email in suppliers:
                db.add(Supplier(name=name, contact=contact, phone=phone, email=email, score=5.0))
            await db.flush()

        # ── Supplier Evaluations ──
        s_r = await db.execute(select(Supplier))
        all_suppliers = {s.name: s.id for s in s_r.scalars().all()}
        evals_data = [
            ("大發鋼鐵", 92, 88, 85, 90, "張總", "品質穩定，交期準時"),
            ("大發鋼鐵", 88, 85, 82, 87, "張總", "Q2評鑑"),
            ("永裕五金", 78, 82, 90, 80, "陳採購", "價格有競爭力"),
            ("日盛電子", 95, 90, 75, 88, "陳採購", "品質優但價格偏高"),
        ]
        for sname, qs, ds, ps, sv, ev, notes in evals_data:
            if sname in all_suppliers:
                existing_ev = await db.execute(
                    select(SupplierEvaluation).where(
                        SupplierEvaluation.supplier_id == all_suppliers[sname])
                )
                if not existing_ev.scalar_one_or_none():
                    from app.services.warehouse_service import create_evaluation
                    await create_evaluation(db, all_suppliers[sname], date.today(),
                            qs, ds, ps, sv, evaluator=ev, notes=notes)

        # ── Supplier Prices ──
        parts_r = await db.execute(select(Part).limit(5))
        parts = list(parts_r.scalars().all())
        if parts and "大發鋼鐵" in all_suppliers:
            for i, part in enumerate(parts):
                existing_price = await db.execute(
                    select(SupplierPrice).where(
                        SupplierPrice.supplier_id == all_suppliers["大發鋼鐵"],
                        SupplierPrice.part_id == part.id)
                )
                if not existing_price.scalar_one_or_none():
                    db.add(SupplierPrice(
                        supplier_id=all_suppliers["大發鋼鐵"],
                        part_id=part.id,
                        unit_price=50 + i * 10,
                        effective_date=date.today(),
                        currency="TWD",
                    ))

        # ── Reorder Rules ──
        if parts:
            for i, part in enumerate(parts):
                existing_rule = await db.execute(
                    select(ReorderRule).where(ReorderRule.part_id == part.id)
                )
                if not existing_rule.scalar_one_or_none():
                    db.add(ReorderRule(
                        part_id=part.id,
                        safety_stock=20 + i * 10,
                        reorder_qty=100 + i * 50,
                        lead_time_days=7,
                        preferred_supplier_id=all_suppliers.get("大發鋼鐵"),
                        auto_approve=(i == 0),
                    ))

        await db.commit()
        print("Phase B - Warehouse & Supply Chain seed data loaded!")
        print("  Zones: RAW, SEMI, FINISHED, DEFECT, QUARANTINE (5 zones)")
        print("  Bins: 7 locations with aisle/rack/shelf")
        print("  Suppliers: 大发钢铁, 永裕五金, 日盛电子, 长春化工")
        print("  Evaluations: 4 records with grade A-C")
        print("  Pricing: 5 parts priced from Supplier")
        print("  Reorder Rules: 5 rules with safety stock 20-60")

if __name__ == "__main__":
    asyncio.run(seed_warehouse())
