"""
LLM Tool Functions — 這些函數會被 LLM 調用來執行實際操作。
"""

from typing import Optional


async def query_inventory(part_no: Optional[str] = None, name: Optional[str] = None, category: Optional[str] = None) -> list:
    """查詢庫存 — TODO: 實作 SQLAlchemy 查詢"""
    return [
        {"part_no": "M6x20", "name": "不鏽鋼螺絲", "quantity": 1250, "location": "A-01-03"},
        {"part_no": "M8x30", "name": "碳鋼螺絲", "quantity": 800, "location": "A-01-05"},
    ]


async def create_purchase_order(supplier_name: str, items: list, notes: Optional[str] = None) -> dict:
    """建立採購單 — TODO: 實作 DB 寫入"""
    return {
        "po_no": "PO-20260001",
        "supplier": supplier_name,
        "status": "draft",
        "items_count": len(items),
        "message": f"採購單 PO-20260001 已建立（草稿狀態）"
    }


async def query_bom(product_no: Optional[str] = None, product_name: Optional[str] = None) -> list:
    """查詢 BOM — TODO: 實作 SQLAlchemy 查詢"""
    return [
        {"level": 0, "part_no": "PRD-001", "name": "A 產品", "qty": 1},
        {"level": 1, "part_no": "SUB-001", "name": "A 底座組件", "qty": 1},
        {"level": 2, "part_no": "M6x20", "name": "不鏽鋼螺絲", "qty": 4},
        {"level": 2, "part_no": "PLT-001", "name": "底板", "qty": 1},
    ]


async def bom_explode(product_no: str, quantity: float) -> dict:
    """BOM 多階展開 — 計算所有層級的物料需求"""
    bom = await query_bom(product_no=product_no)
    exploded = []
    for item in bom:
        exploded.append({
            **item,
            "required_qty": item["qty"] * quantity
        })
    return {
        "product_no": product_no,
        "demand_qty": quantity,
        "items": exploded
    }


async def check_stock_shortage(product_no: str, quantity: float) -> dict:
    """缺料檢查 — BOM 展開後比對庫存"""
    exploded = await bom_explode(product_no, quantity)
    shortages = []
    for item in exploded["items"]:
        if item["level"] == 0:
            continue
        stock = await query_inventory(part_no=item["part_no"])
        available = stock[0]["quantity"] if stock else 0
        needed = item["required_qty"]
        if available < needed:
            shortages.append({
                "part_no": item["part_no"],
                "name": item["name"],
                "need": needed,
                "have": available,
                "short": needed - available
            })
    return {
        "product_no": product_no,
        "demand_qty": quantity,
        "shortages": shortages,
        "has_shortage": len(shortages) > 0
    }
