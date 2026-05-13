"""
LLM-ERP Seed Data — using SQLAlchemy models
"""
import sys, os, asyncio
sys.path.insert(0, "/mnt/d/Project/LLM_ERP/backend")

os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./llm_erp.db"
import app.models as models
from app.database import engine, get_db
from sqlalchemy import text
from datetime import datetime, date

async def seed():
    # Clear all data
    meta = models.Base.metadata
    async with engine.begin() as conn:
        for table in reversed(meta.sorted_tables):
            await conn.execute(text(f"DELETE FROM {table.name}"))
    
    now = datetime.utcnow()
    
    # Use raw SQL with proper UUID handling
    import uuid
    def uid():
        return uuid.uuid4().hex
    
    async with engine.begin() as conn:
        # ══ Parts & Inventory ══
        parts_data = {
            "M6x20": ("不鏽鋼螺絲 M6x20", "SUS304 M6x20 全牙", "pcs", "緊固件"),
            "BRG-001": ("軸承 6205", "深溝滾珠軸承 6205ZZ", "pcs", "傳動件"),
            "M8x30": ("不鏽鋼螺絲 M8x30", "SUS304 M8x30 全牙", "pcs", "緊固件"),
            "ASM-001": ("自動鎖螺絲機基座", "ASM-001 Base Assembly Unit", "pcs", "半成品"),
            "CNC-001": ("小型 CNC 銑床", "Desktop CNC Milling Machine", "pcs", "成品"),
            "MTR-001": ("步進馬達", "NEMA23 步進馬達 2.8A", "pcs", "傳動件"),
            "DRV-001": ("馬達驅動器", "DM542 步進驅動器", "pcs", "電子件"),
            "BLK-001": ("鋁擠型骨架", "2020鋁擠型 500mm", "pcs", "結構件"),
            "SLD-001": ("線性滑軌", "MGN12H 300mm", "pcs", "傳動件"),
            "PLA-001": ("壓克力面板", "透明壓克力 300x200mm", "pcs", "面板"),
            "BLT-001": ("皮帶", "2GT 同步皮帶 400mm", "pcs", "傳動件"),
            "CTL-001": ("控制器", "Arduino Mega 2560", "pcs", "電子件"),
        }
        pmap = {}
        for pn, (nm, sp, un, ct) in parts_data.items():
            pid = uid()
            await conn.execute(text(
                "INSERT INTO parts (id,part_no,name,spec,unit,category,created_at) VALUES (:id,:pn,:nm,:sp,:un,:ct,:now)"
            ), {"id":pid,"pn":pn,"nm":nm,"sp":sp,"un":un,"ct":ct,"now":now})
            pmap[pn] = pid
        
        inv_map = {"M6x20":2000,"BRG-001":40,"M8x30":1500,"ASM-001":3,"CNC-001":2,
                   "MTR-001":15,"DRV-001":8,"BLK-001":50,"SLD-001":12,"PLA-001":25,"BLT-001":20,"CTL-001":5}
        for pn, qty in inv_map.items():
            await conn.execute(text(
                "INSERT INTO inventory (id,part_id,location,quantity,updated_at) VALUES (:id,:pid,:loc,:qty,:now)"
            ), {"id":uid(),"pid":pmap[pn],"loc":"A-01","qty":qty,"now":now})
        
        # ══ Suppliers ══
        smap = {}
        supps = {"大明螺絲":("王大明","0912-345-678","daming@screws.com",85),
                 "傳動王":("李傳動","0923-456-789","drive@king.com",90),
                 "電子通":("張電子","0934-567-890","elec@tong.com",78)}
        for sn, (cp, ph, em, sc) in supps.items():
            sid = uid()
            await conn.execute(text(
                "INSERT INTO suppliers (id,name,contact,phone,email,score,created_at) VALUES (:id,:nm,:cp,:ph,:em,:sc,:now)"
            ), {"id":sid,"nm":sn,"cp":cp,"ph":ph,"em":em,"sc":sc,"now":now})
            smap[sn] = sid
        
        # ══ Products ══
        pdmap = {}
        for pn, nm, desc in [("ASM-001","自動鎖螺絲機基座","ASM-001 Base"),("CNC-001","小型 CNC 銑床","Desktop CNC")]:
            pdid = uid()
            await conn.execute(text(
                "INSERT INTO products (id,product_no,name,description,created_at) VALUES (:id,:pn,:nm,:desc,:now)"
            ), {"id":pdid,"pn":pn,"nm":nm,"desc":desc,"now":now})
            pdmap[pn] = pdid
        
        # ══ BOM ══
        boms = [("ASM-001","M6x20",12,1),("ASM-001","BRG-001",2,1),("ASM-001","BLK-001",2,1),
                ("ASM-001","SLD-001",1,1),("ASM-001","PLA-001",1,1),
                ("CNC-001","M8x30",20,1),("CNC-001","ASM-001",1,2),
                ("CNC-001","MTR-001",3,1),("CNC-001","DRV-001",3,1),
                ("CNC-001","BLT-001",2,1),("CNC-001","CTL-001",1,1)]
        for pn, cn, qty, lvl in boms:
            await conn.execute(text(
                "INSERT INTO bom_items (id,product_id,part_id,quantity,level) VALUES (:id,:pid,:cid,:qty,:lvl)"
            ), {"id":uid(),"pid":pdmap[pn],"cid":pmap[cn],"qty":qty,"lvl":lvl})
        
        # ══ Work Centers ══
        wmap = {}
        for nm, desc, st in [("CNC-01","CNC 加工中心","running"),("WELD-01","焊接工作站","idle"),
                              ("ASM-01","組裝工作站","idle"),("INS-01","檢驗站","idle")]:
            wid = uid()
            await conn.execute(text(
                "INSERT INTO work_centers (id,name,description,status) VALUES (:id,:nm,:desc,:st)"
            ), {"id":wid,"nm":nm,"desc":desc,"st":st})
            wmap[nm] = wid
        
        # ══ Production Orders ══
        for ono, pn, qty, dd, st in [("WO-20260506-001","CNC-001",3,"2026-05-06","released"),
                                      ("WO-20260505-001","ASM-001",5,"2026-05-05","released"),
                                      ("WO-20260504-001","CNC-001",2,"2026-05-04","dispatched")]:
            oid = uid()
            await conn.execute(text(
                "INSERT INTO production_orders (id,order_no,product_no,product_name,quantity,due_date,status,created_at) VALUES (:id,:ono,:pn,:pnm,:qty,:dd,:st,:now)"
            ), {"id":oid,"ono":ono,"pn":pn,"pnm":pn,"qty":qty,"dd":dd,"st":st,"now":now})
            if st == "dispatched":
                await conn.execute(text(
                    "INSERT INTO operations (id,order_id,work_center_id,sequence_no,name,total_time_min,status) VALUES (:id,:oid,:wid,1,'CNC加工',60,'in_progress')"
                ), {"id":uid(),"oid":oid,"wid":wmap["CNC-01"]})
        
        # ══ Purchase Orders ══
        poid = uid()
        await conn.execute(text(
            "INSERT INTO purchase_orders (id,po_no,supplier_id,status,created_at) VALUES (:id,:po,:sid,:st,:now)"
        ), {"id":poid,"po":"PO-20260505-001","sid":smap["大明螺絲"],"st":"received","now":now})
        for pn, qty, up, rq in [("M6x20",1000,0.50,1000),("M8x30",500,0.80,500)]:
            await conn.execute(text(
                "INSERT INTO purchase_order_items (id,po_id,part_id,quantity,unit_price,received_qty) VALUES (:id,:pid,:ptid,:qty,:up,:rq)"
            ), {"id":uid(),"pid":poid,"ptid":pmap[pn],"qty":qty,"up":up,"rq":rq})
        
        # ══ Accounts ══
        for ano, nm, tp, nb in [(1100,"原料庫存","asset","debit"),(2100,"應付帳款","liability","credit"),
                                (4100,"銷貨收入","revenue","credit"),(5100,"原料成本","expense","debit")]:
            await conn.execute(text(
                "INSERT INTO accounts (id,account_no,name,type,normal_balance,is_active,created_at) VALUES (:id,:ano,:nm,:tp,:nb,1,:now)"
            ), {"id":uid(),"ano":ano,"nm":nm,"tp":tp,"nb":nb,"now":now})
        
        # ══ AR ══
        for cn, inv, amt, ddate, st in [("大明機械","INV-001",50000,"2026-05-01","open"),
                                         ("台灣工具機","INV-002",120000,"2026-05-15","open"),
                                         ("先進精密","INV-003",30000,"2026-02-20","overdue")]:
            await conn.execute(text(
                "INSERT INTO accounts_receivable (id,customer_name,invoice_no,amount,due_date,paid_amount,status,created_at) VALUES (:id,:cn,:inv,:amt,:dd,0,:st,:now)"
            ), {"id":uid(),"cn":cn,"inv":inv,"amt":amt,"dd":ddate,"st":st,"now":now})
        
        # ══ Customers ══
        cumap = {}
        for cno, nm, cp, ph, em in [("C001","大明機械","王經理","0918-111-222","dm@mech.com"),
                                     ("C002","台灣工具機","李協理","0927-333-444","tw@mt.com"),
                                     ("C003","先進精密","陳副總","0936-555-666","adv@prec.com")]:
            cid = uid()
            await conn.execute(text(
                "INSERT INTO customers (id,customer_no,name,contact_person,phone,email,is_active,created_at) VALUES (:id,:cno,:nm,:cp,:ph,:em,1,:now)"
            ), {"id":cid,"cno":cno,"nm":nm,"cp":cp,"ph":ph,"em":em,"now":now})
            cumap[nm] = cid
        
        # ══ Sales Order ══
        soid = uid()
        await conn.execute(text(
            "INSERT INTO sales_orders (id,so_no,customer_id,order_date,status,total_amount,created_at) VALUES (:id,:so,:cid,:od,:st,:amt,:now)"
        ), {"id":soid,"so":"SO-20260501","cid":cumap["大明機械"],"od":"2026-05-01","st":"confirmed","amt":150000,"now":now})
        await conn.execute(text(
            "INSERT INTO sales_order_items (id,so_id,part_no,part_name,quantity,unit_price,line_total) VALUES (:id,:sid,:pn,:pnm,1,150000,150000)"
        ), {"id":uid(),"sid":soid,"pn":"CNC-001","pnm":"小型 CNC 銑床"})
        
        # ══ Inspection Order ══
        await conn.execute(text(
            "INSERT INTO inspection_orders (id,inspection_no,part_id,lot_no,quantity,status,created_at) VALUES (:id,:ino,:pid,:lot,:qty,:st,:now)"
        ), {"id":uid(),"ino":"INS-20260501","pid":pmap["M6x20"],"lot":"LOT-B001","qty":500,"st":"pending","now":now})
        
        print("Seed completed successfully!")

async def verify():
    async with engine.begin() as conn:
        for table in ["parts","inventory","suppliers","products","bom_items",
                      "production_orders","purchase_orders","work_centers",
                      "accounts","accounts_receivable","customers","sales_orders","inspection_orders"]:
            result = await conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
            cnt = result.scalar()
            print(f"  {table}: {cnt} rows")

if __name__ == "__main__":
    asyncio.run(seed())
    asyncio.run(verify())
