from fastapi import APIRouter

router = APIRouter(prefix="/bom", tags=["bom"])


@router.get("/products")
async def list_products():
    """取得所有產品"""
    return {"products": [], "total": 0}


@router.get("/explode/{product_no}")
async def explode_bom(product_no: str, quantity: float = 1):
    """BOM 多階展開"""
    return {"product_no": product_no, "quantity": quantity, "items": []}
