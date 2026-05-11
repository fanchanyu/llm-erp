"""
LLM-ERP V2 - Phase A Seed Data (Production: Work Orders, MPS, Shop Floor)
Run: python -m app.seed_production
"""

import asyncio
from datetime import date, datetime, timedelta
from sqlalchemy import select
from app.database import async_session, init_db
from app.models.dispatch import (
    WorkCenter, ProductionOrder, Operation, OrderStatus, OpStatus,
)
from app.models.bom import Product, BOMItem


async def seed_production():
    await init_db()
    async with async_session() as db:
        # -- Work Centers --
        wc_data = [
            ("CNC-01", "CNC铣床#1", 16.0, 0.95, "A", "加工一区"),
            ("CNC-02", "CNC铣床#2", 16.0, 0.90, "A", "加工一区"),
            ("LATHE-01", "车床#1", 16.0, 0.92, "B", "加工二区"),
            ("DRILL-01", "钻床#1", 16.0, 0.88, "C", "加工二区"),
            ("GRIND-01", "研磨机#1", 16.0, 0.85, "D", "加工三区"),
            ("ASSY-01", "装配线A", 8.0, 1.0, "", "组装区"),
            ("ASSY-02", "装配线B", 8.0, 1.0, "", "组装区"),
            ("QC-01", "品检站", 8.0, 1.0, "", "检验区"),
        ]
        existing_wc = await db.execute(select(WorkCenter))
        existing_names = {w.name for w in existing_wc.scalars().all()}

        wc_ids = {}
        for name, desc, cap, eff, alt_grp, loc in wc_data:
            if name not in existing_names:
                wc = WorkCenter(name=name, description=desc,
                                capacity_hours=cap, efficiency=eff,
                                alternate_group=alt_grp, location=loc)
                db.add(wc)
                await db.flush()
                wc_ids[name] = wc.id
            else:
                r = await db.execute(select(WorkCenter).where(WorkCenter.name == name))
                wc_ids[name] = r.scalar_one().id

        # -- Products --
        existing_p = await db.execute(
            select(Product).where(Product.product_no == "GEAR-001")
        )
        if not existing_p.scalar_one_or_none():
            products = [
                ("GEAR-001", "精密齿轮A", "模块化传动齿轮"),
                ("SHAFT-002", "传动轴B", "硬化处理传动轴"),
                ("BRACKET-003", "支撑座C", "铸铁支撑座"),
            ]
            for pno, pname, pdesc in products:
                db.add(Product(product_no=pno, name=pname, description=pdesc))
            await db.flush()

        # -- BOM Items --
        existing_bom = await db.execute(select(BOMItem).limit(1))
        if not existing_bom.scalar_one_or_none():
            gear = await db.execute(
                select(Product).where(Product.product_no == "GEAR-001")
            )
            gear_p = gear.scalar_one_or_none()
            if gear_p:
                from app.models.inventory import Part
                parts_result = await db.execute(select(Part).limit(3))
                parts = list(parts_result.scalars().all())
                for p in parts:
                    db.add(BOMItem(product_id=gear_p.id, part_id=p.id, quantity=1, level=1))

        # -- Work Orders --
        today = date.today()
        existing_wo = await db.execute(select(ProductionOrder).limit(1))
        if not existing_wo.scalar_one_or_none():
            orders_data = [
                ("GEAR-001", "精密齿轮A", 100, today + timedelta(days=7), 2,
                 OrderStatus.IN_PROGRESS.value, "SO-20260501-001"),
                ("SHAFT-002", "传动轴B", 50, today + timedelta(days=14), 3,
                 OrderStatus.RELEASED.value, "SO-20260502-001"),
                ("BRACKET-003", "支撑座C", 200, today + timedelta(days=3), 4,
                 OrderStatus.DRAFT.value, "SO-20260503-001"),
                ("GEAR-001", "精密齿轮A", 80, today + timedelta(days=21), 1,
                 OrderStatus.DRAFT.value, "SO-20260505-001"),
            ]
            for pno, pname, qty, dd, prio, status, so_no in orders_data:
                today_str = today.strftime("%Y%m%d")
                existing_orders = await db.execute(
                    select(ProductionOrder).where(
                        ProductionOrder.order_no.like(f"WO-{today_str}-%")
                    ).order_by(ProductionOrder.order_no.desc()).limit(1)
                )
                last_wo = existing_orders.scalar_one_or_none()
                seq = 1
                if last_wo and last_wo.order_no:
                    seq = int(last_wo.order_no.split("-")[-1]) + 1
                order_no = f"WO-{today_str}-{seq:03d}"

                po = ProductionOrder(
                    order_no=order_no,
                    product_no=pno, product_name=pname,
                    quantity=qty, due_date=dd, priority=prio,
                    status=status, so_no=so_no, created_by="seed",
                    started_at=datetime.utcnow() if status == OrderStatus.IN_PROGRESS.value else None,
                )
                db.add(po)
                await db.flush()

                # Operations by product type
                if pno == "GEAR-001":
                    ops = [
                        (1, "CNC粗车", "CNC-01", 30, 3.0),
                        (2, "CNC精车", "CNC-02", 45, 2.5),
                        (3, "钻孔", "DRILL-01", 15, 1.0),
                        (4, "研磨", "GRIND-01", 20, 1.5),
                        (5, "品检", "QC-01", 5, 0.5),
                    ]
                elif pno == "SHAFT-002":
                    ops = [
                        (1, "车削", "LATHE-01", 25, 4.0),
                        (2, "研磨", "GRIND-01", 15, 2.0),
                        (3, "品检", "QC-01", 5, 0.5),
                    ]
                else:
                    ops = [
                        (1, "CNC加工", "CNC-01", 20, 2.0),
                        (2, "钻孔攻牙", "DRILL-01", 10, 1.0),
                        (3, "组装", "ASSY-01", 15, 0.5),
                        (4, "品检", "QC-01", 5, 0.3),
                    ]

                current_time = datetime.utcnow()
                for seq, op_name, wc_name, setup, cycle in ops:
                    if wc_name in wc_ids:
                        total = setup + cycle * qty
                        op = Operation(
                            order_id=po.id, work_center_id=wc_ids[wc_name],
                            sequence_no=seq, name=op_name,
                            setup_time_min=setup, cycle_time_min=cycle,
                            total_time_min=total,
                            scheduled_start=current_time,
                            scheduled_end=current_time + timedelta(minutes=total),
                            status=OpStatus.READY.value if status != OrderStatus.DRAFT.value else OpStatus.PENDING.value,
                        )
                        db.add(op)
                        current_time += timedelta(minutes=total)

        await db.commit()
        print("Phase A - Production seed data loaded!")
        print("  Work Centers: CNC-01/02, LATHE-01, DRILL-01, GRIND-01, ASSY-01/02, QC-01")
        print("  Products: GEAR-001, SHAFT-002, BRACKET-003")
        print("  Work Orders: 4 orders (1 in_progress, 1 released, 2 draft)")
        print("  Operations: Full routing with 3-5 ops per order")


if __name__ == "__main__":
    asyncio.run(seed_production())
