from fastapi import APIRouter

router = APIRouter(prefix="/purchase", tags=["purchase"])


@router.get("/orders")
async def list_orders():
    """取得所有採購單"""
    return {"orders": [], "total": 0}


@router.get("/suppliers")
async def list_suppliers():
    """取得所有供應商"""
    return {"suppliers": [], "total": 0}
