from fastapi import APIRouter

router = APIRouter(prefix="/inventory", tags=["inventory"])


@router.get("/parts")
async def list_parts():
    """取得所有料號列表"""
    return {"parts": [], "total": 0}


@router.get("/stock")
async def query_stock(part_no: Optional[str] = None):
    """查詢庫存量"""
    return {"items": []}
