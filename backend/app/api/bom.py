"""BOM API endpoints with real DB integration."""

import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.services import bom_service as svc
from app.services.inventory_service import get_part_by_no
from app.schemas.bom import (
    ProductCreate, ProductResponse, BOMItemInput, BOMTreeItem,
    ExplosionRequest, ExplosionResponse, ExplosionItem,
    ShortageResponse, ShortageItem,
)

router = APIRouter(prefix="/bom", tags=["bom"])


@router.get("/products", response_model=dict)
async def list_products(
    search: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    products, total = await svc.list_products(db, search, skip, limit)
    return {
        "products": [
            ProductResponse(id=str(p.id), product_no=p.product_no,
                            name=p.name, description=p.description) for p in products
        ],
        "total": total,
    }


@router.post("/products", response_model=ProductResponse, status_code=201)
async def create_product(data: ProductCreate, db: AsyncSession = Depends(get_db)):
    existing = await svc.get_product_by_no(db, data.product_no)
    if existing:
        raise HTTPException(400, f"Product {data.product_no} already exists")
    p = await svc.create_product(db, data.product_no, data.name, data.description)
    return ProductResponse(id=str(p.id), product_no=p.product_no,
                           name=p.name, description=p.description)


@router.get("/products/{product_id}/bom", response_model=dict)
async def get_bom(product_id: str, db: AsyncSession = Depends(get_db)):
    try:
        uid = uuid.UUID(product_id)
    except ValueError:
        raise HTTPException(400, "Invalid product ID")
    product = await svc.get_product(db, uid)
    if not product:
        raise HTTPException(404, "Product not found")
    tree = await svc.get_bom_tree(db, uid)
    return {"product_no": product.product_no, "product_name": product.name, "items": tree}


@router.post("/products/{product_id}/bom", status_code=201)
async def add_bom_item(product_id: str, data: BOMItemInput,
                       db: AsyncSession = Depends(get_db)):
    try:
        uid = uuid.UUID(product_id)
    except ValueError:
        raise HTTPException(400, "Invalid product ID")
    product = await svc.get_product(db, uid)
    if not product:
        raise HTTPException(404, "Product not found")
    part = await get_part_by_no(db, data.part_no)
    if not part:
        raise HTTPException(404, f"Part not found: {data.part_no}")
    item = await svc.add_bom_item(db, uid, part.id, data.quantity, data.level, data.sequence_no)
    return {"message": "BOM item added", "id": str(item.id)}


@router.get("/explode/{product_no}", response_model=ExplosionResponse)
async def explode_bom(product_no: str, quantity: float = Query(1.0, gt=0),
                      db: AsyncSession = Depends(get_db)):
    try:
        result = await svc.bom_explode(db, product_no, quantity)
    except ValueError as e:
        raise HTTPException(404, str(e))
    return ExplosionResponse(
        product_no=result["product_no"],
        demand_quantity=result["demand_quantity"],
        items=[ExplosionItem(**i) for i in result["items"]],
    )


@router.post("/check-shortage", response_model=ShortageResponse)
async def check_shortage(data: ExplosionRequest, db: AsyncSession = Depends(get_db)):
    try:
        result = await svc.check_shortage(db, data.product_no, data.quantity)
    except ValueError as e:
        raise HTTPException(404, str(e))
    return ShortageResponse(
        product_no=result["product_no"],
        demand_quantity=result["demand_quantity"],
        has_shortage=result["has_shortage"],
        shortages=[ShortageItem(**s) for s in result["shortages"]],
        total_items=result["total_items"],
    )
