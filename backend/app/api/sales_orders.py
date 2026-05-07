"""Sales Order API endpoints."""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.services import sales_order_service as svc
from app.services import customer_service as customer_svc
from app.schemas.sales_order import (
    SalesOrderCreate,
    SalesOrderResponse,
    SalesOrderItemResponse,
)

router = APIRouter(prefix="/so", tags=["sales_orders"])


def _order_to_response(order) -> SalesOrderResponse:
    """Convert a SalesOrder ORM object to SalesOrderResponse with customer name."""
    customer_name = ""
    if order.customer_id:
        # We don't eagerly load customer, but we can resolve via a separate query
        pass
    return SalesOrderResponse(
        id=order.id,
        so_no=order.so_no,
        customer_name="",  # will be filled below if available
        status=order.status,
        total_amount=float(order.total_amount or 0),
        notes=order.notes,
        created_at=order.created_at,
        items=[
            SalesOrderItemResponse(
                id=item.id,
                part_no=item.part_no,
                part_name=item.part_name,
                quantity=float(item.quantity),
                unit_price=float(item.unit_price or 0),
                line_total=float(item.line_total or 0),
                delivery_date=item.delivery_date,
            )
            for item in (order.items or [])
        ],
    )


@router.get("", response_model=dict)
async def list_orders(
    status: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    """List sales orders with optional status filter and pagination."""
    orders, total = await svc.list_orders(db, status, skip, limit)
    result = []
    for o in orders:
        resp = _order_to_response(o)
        # Resolve customer name
        customer = await customer_svc.get_customer(db, o.customer_id)
        if customer:
            resp.customer_name = customer.name
        result.append(resp)
    return {"orders": result, "total": total}


@router.post("", response_model=SalesOrderResponse, status_code=201)
async def create_order(data: SalesOrderCreate, db: AsyncSession = Depends(get_db)):
    """Create a new sales order with line items."""
    try:
        order = await svc.create_order(
            db,
            customer_no=data.customer_no,
            items_data=[item.model_dump() for item in data.items],
            notes=data.notes,
        )
    except ValueError as e:
        raise HTTPException(400, str(e))

    resp = _order_to_response(order)
    customer = await customer_svc.get_customer(db, order.customer_id)
    if customer:
        resp.customer_name = customer.name
    return resp


@router.get("/{order_id}", response_model=SalesOrderResponse)
async def get_order(order_id: int, db: AsyncSession = Depends(get_db)):
    """Get a sales order by ID with items."""
    order = await svc.get_order(db, order_id)
    if not order:
        raise HTTPException(404, f"Sales order {order_id} not found")
    resp = _order_to_response(order)
    customer = await customer_svc.get_customer(db, order.customer_id)
    if customer:
        resp.customer_name = customer.name
    return resp


@router.post("/{order_id}/confirm")
async def confirm_sales_order(order_id: int, db: AsyncSession = Depends(get_db)):
    """Confirm SO → auto-create production orders in dispatch."""
    try:
        order = await svc.confirm_order(db, order_id)
    except ValueError as e:
        raise HTTPException(400, str(e))
    resp = _order_to_response(order)
    customer = await customer_svc.get_customer(db, order.customer_id)
    if customer:
        resp.customer_name = customer.name
    return {"message": f"SO {order.so_no} confirmed → production", "order": resp.model_dump()}


@router.post("/{order_id}/ship")
async def ship_sales_order(order_id: int, db: AsyncSession = Depends(get_db)):
    """Ship SO → auto-outbound inventory."""
    try:
        order = await svc.ship_order(db, order_id)
    except ValueError as e:
        raise HTTPException(400, str(e))
    resp = _order_to_response(order)
    customer = await customer_svc.get_customer(db, order.customer_id)
    if customer:
        resp.customer_name = customer.name
    return {"message": f"SO {order.so_no} shipped", "order": resp.model_dump()}


@router.post("/{order_id}/deliver")
async def deliver_sales_order(order_id: int, db: AsyncSession = Depends(get_db)):
    """Mark SO as delivered."""
    try:
        order = await svc.deliver_order(db, order_id)
    except ValueError as e:
        raise HTTPException(400, str(e))
    resp = _order_to_response(order)
    customer = await customer_svc.get_customer(db, order.customer_id)
    if customer:
        resp.customer_name = customer.name
    return {"message": f"SO {order.so_no} delivered", "order": resp.model_dump()}
