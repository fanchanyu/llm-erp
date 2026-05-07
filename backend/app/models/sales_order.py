"""
Sales Order Model (銷售訂單).

Tracks customer sales orders with line items including part details,
pricing, and delivery schedule. Supports status workflow:
draft → confirmed → production → shipped → delivered → cancelled.
"""

from datetime import datetime
from sqlalchemy import Column, String, Float, Integer, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from app.models.inventory import Base


class SalesOrder(Base):
    __tablename__ = "sales_orders"

    id = Column(Integer, primary_key=True, autoincrement=True)
    so_no = Column(String(50), unique=True, nullable=False, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    order_date = Column(DateTime, default=datetime.utcnow)
    status = Column(String(20), default="draft")  # draft/confirmed/production/shipped/delivered/cancelled
    total_amount = Column(Float, default=0)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    items = relationship("SalesOrderItem", back_populates="sales_order",
                         order_by="SalesOrderItem.id")


class SalesOrderItem(Base):
    __tablename__ = "sales_order_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    so_id = Column(Integer, ForeignKey("sales_orders.id"), nullable=False)
    part_no = Column(String(50), nullable=False)
    part_name = Column(String(200), nullable=True)
    quantity = Column(Float, nullable=False)
    unit_price = Column(Float, default=0)
    line_total = Column(Float, default=0)
    delivery_date = Column(DateTime, nullable=True)

    sales_order = relationship("SalesOrder", back_populates="items")
