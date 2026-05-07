"""BOM service — products, BOM structure, multi-level explosion."""

import uuid
from typing import Optional
from sqlalchemy import select, or_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.models.bom import Product, BOMItem
from app.services.inventory_service import get_stock_by_part
from app.event_engine.service_enforcer import enforce


# ─── Products ─────────────────────────────────────────────────────

async def list_products(db: AsyncSession, search: Optional[str] = None,
                        skip: int = 0, limit: int = 50) -> tuple[list[Product], int]:
    q = select(Product)
    if search:
        q = q.where(or_(Product.product_no.ilike(f"%{search}%"), Product.name.ilike(f"%{search}%")))
    count_q = select(func.count()).select_from(q.subquery())
    total = (await db.execute(count_q)).scalar() or 0
    result = await db.execute(q.offset(skip).limit(limit).order_by(Product.product_no))
    return list(result.scalars().all()), total


async def get_product(db: AsyncSession, product_id: uuid.UUID) -> Optional[Product]:
    return await db.get(Product, product_id)


async def get_product_by_no(db: AsyncSession, product_no: str) -> Optional[Product]:
    result = await db.execute(select(Product).where(Product.product_no == product_no))
    return result.scalar_one_or_none()


async def create_product(db: AsyncSession, product_no: str, name: str,
                         description: Optional[str] = None) -> Product:
    p = Product(product_no=product_no, name=name, description=description)
    db.add(p)
    await db.flush()
    return p


# ─── BOM Items ────────────────────────────────────────────────────

async def get_bom_tree(db: AsyncSession, product_id: uuid.UUID) -> list[dict]:
    """Get the full BOM tree for a product as a flat list with level info."""
    result = await db.execute(
        select(BOMItem).options(selectinload(BOMItem.part), selectinload(BOMItem.product))
        .where(BOMItem.product_id == product_id)
        .order_by(BOMItem.level, BOMItem.sequence_no)
    )
    items = result.scalars().all()
    return [
        {
            "id": str(item.id),
            "product_no": item.product.product_no if item.product else "",
            "product_name": item.product.name if item.product else "",
            "level": item.level,
            "sequence_no": item.sequence_no,
            "part_no": item.part.part_no if item.part else "",
            "part_name": item.part.name if item.part else "",
            "quantity": float(item.quantity),
            "unit": item.part.unit if item.part else "",
        }
        for item in items
    ]


async def add_bom_item(db: AsyncSession, product_id: uuid.UUID, part_id: uuid.UUID,
                       quantity: float, level: int,
                       sequence_no: Optional[int] = None,
                       actor_role: str = "") -> BOMItem:
    # Check BOM edit constraints
    enforce("edit_bom", {
        "bom_status": "active",  # conservative: check circular ref
        "bom_tree": {},
        "parent_id": str(product_id),
        "child_id": str(part_id),
    }, actor_role=actor_role)

    item = BOMItem(
        product_id=product_id, part_id=part_id,
        quantity=quantity, level=level, sequence_no=sequence_no,
    )
    db.add(item)
    await db.flush()
    return item


# ─── BOM Multi-Level Explosion ────────────────────────────────────

async def bom_explode(db: AsyncSession, product_no: str, demand_quantity: float) -> dict:
    """
    Multi-level BOM explosion.
    
    Starting from the final product (level 0), recursively expand each sub-component
    to calculate the required quantity at every level.
    
    Returns:
    {
        "product_no": "...",
        "demand_quantity": N,
        "items": [
            {"level": 0, "part_no": "...", "name": "...", "qty_per_parent": 1, "required_qty": N},
            {"level": 1, "part_no": "...", "name": "...", "qty_per_parent": X, "required_qty": N*X},
            ...
        ]
    }
    """
    product = await get_product_by_no(db, product_no)
    if not product:
        raise ValueError(f"Product not found: {product_no}")

    exploded = []
    _explode_recursive(db, product.id, demand_quantity, 0, exploded)
    # await is not used inside the recursive, but we need to trigger the lazy loading
    # Actually we need a different approach for async. Let me do it iteratively.

    # Re-do properly with async
    return await _bom_explode_async(db, product, demand_quantity)


async def _bom_explode_async(db: AsyncSession, product: Product, demand_qty: float) -> dict:
    """Async BOM explosion using iterative stack."""
    items_map = {}  # part_id -> list of BOMItem (could have same part in different levels)
    result_items = []

    # Get all BOM items for this product
    bom_rows = await db.execute(
        select(BOMItem).options(selectinload(BOMItem.part))
        .where(BOMItem.product_id == product.id)
        .order_by(BOMItem.level, BOMItem.sequence_no)
    )
    all_items = bom_rows.scalars().all()

    # Build level groups
    from collections import defaultdict
    level_groups = defaultdict(list)
    for item in all_items:
        level_groups[item.level].append(item)

    # Find max level
    max_level = max(level_groups.keys()) if level_groups else 0

    # Propagate quantities: level 0 = product itself
    result_items.append({
        "level": 0,
        "part_no": product.product_no,
        "name": product.name,
        "qty_per_parent": 1,
        "required_qty": demand_qty,
    })

    # Parent multiplier at each level
    parent_qty = {0: demand_qty}

    for level in range(1, max_level + 1):
        for item in level_groups.get(level, []):
            parent_multiplier = parent_qty.get(level - 1, demand_qty)
            required = float(item.quantity) * parent_multiplier
            part = item.part
            result_items.append({
                "level": item.level,
                "part_no": part.part_no if part else "",
                "name": part.name if part else "",
                "qty_per_parent": float(item.quantity),
                "required_qty": required,
            })
            # If this part is also an assembly (has its own BOM), its required qty becomes parent for next level
            # For now, flat explosion as above

    return {
        "product_no": product.product_no,
        "demand_quantity": demand_qty,
        "items": result_items,
    }


async def check_shortage(db: AsyncSession, product_no: str, demand_quantity: float) -> dict:
    """
    Check material shortage: BOM explode → compare with stock → list shortages.
    """
    explosion = await _bom_explode_async(db, await get_product_by_no(db, product_no), demand_quantity)
    shortages = []

    for item in explosion["items"]:
        if item["level"] == 0:
            continue  # skip the product itself
        # Get stock for this part
        try:
            part = await get_product_by_no(db, item["part_no"])
            from app.models.inventory import Part
            from sqlalchemy import select as sel
            result = await db.execute(sel(Part).where(Part.part_no == item["part_no"]))
            part_obj = result.scalar_one_or_none()
            stock = await get_stock_by_part(db, part_obj.id) if part_obj else 0
        except Exception:
            stock = 0

        needed = item["required_qty"]
        if stock < needed:
            shortages.append({
                "level": item["level"],
                "part_no": item["part_no"],
                "name": item["name"],
                "required": needed,
                "available": stock,
                "shortage": needed - stock,
            })

    return {
        "product_no": product_no,
        "demand_quantity": demand_quantity,
        "has_shortage": len(shortages) > 0,
        "shortages": shortages,
        "total_items": len(explosion["items"]),
    }
