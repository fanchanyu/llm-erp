"""
LLM Tool Functions — Real DB implementation.
Each function creates its own DB session for LLM function calling.
"""

from app.database import async_session
from app.services import inventory_service, purchase_service, bom_service
from app.models.purchase import Supplier


async def query_inventory(part_no: str = None, name: str = None, category: str = None) -> list:
    """查詢零件庫存量。支援料號、品名關鍵字、分類查詢。"""
    async with async_session() as db:
        items = await inventory_service.query_stock(db, part_no, name, category)
    return items


async def create_purchase_order(supplier_name: str, items: list, notes: str = None) -> dict:
    """建立採購單。需要供應商名稱、品項列表(part_no/quantity/unit_price)。"""
    async with async_session() as db:
        # Find or create supplier
        suppliers, _ = await purchase_service.list_suppliers(db, supplier_name)
        supplier = suppliers[0] if suppliers else None
        if not supplier:
            supplier = await purchase_service.create_supplier(db, supplier_name)

        # Resolve part IDs
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


# Tool name → function mapping
TOOL_FUNCTIONS = {
    "query_inventory": query_inventory,
    "create_purchase_order": create_purchase_order,
    "query_bom": query_bom,
    "bom_explode": bom_explode,
    "check_stock_shortage": check_stock_shortage,
}
