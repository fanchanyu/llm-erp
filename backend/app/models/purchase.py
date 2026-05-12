import uuid
from datetime import datetime, date
from sqlalchemy import Column, String, Float, Date, DateTime, Text, ForeignKey, Uuid
from sqlalchemy.orm import relationship
from app.models.inventory import Base


class Supplier(Base):
    __tablename__ = "suppliers"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    name = Column(String(200), nullable=False, index=True)
    tier = Column(String(10), default="1")  # 1=一階, 2=二階, 3=三階
    parent_supplier_id = Column(Uuid, ForeignKey("suppliers.id"), nullable=True, index=True)
    contact = Column(String(100), nullable=True)
    phone = Column(String(50), nullable=True)
    email = Column(String(200), nullable=True)
    score = Column(Float, default=5.0)  # 0-5 supplier rating
    created_at = Column(DateTime, default=datetime.utcnow)

    # Self-referential relationship for tiered supply chain
    parent_supplier = relationship("Supplier", remote_side=[id], backref="sub_suppliers", foreign_keys=[parent_supplier_id])


class PurchaseOrder(Base):
    __tablename__ = "purchase_orders"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    po_no = Column(String(50), unique=True, nullable=False, index=True)
    supplier_id = Column(Uuid, ForeignKey("suppliers.id"), nullable=False)
    status = Column(String(20), default="draft")  # draft, sent, partial, received, cancelled
    ordered_by = Column(String(100), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    supplier = relationship("Supplier")
    items = relationship("PurchaseOrderItem", back_populates="po")


class PurchaseOrderItem(Base):
    __tablename__ = "purchase_order_items"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    po_id = Column(Uuid, ForeignKey("purchase_orders.id"), nullable=False)
    part_id = Column(Uuid, ForeignKey("parts.id"), nullable=False)
    quantity = Column(Float, nullable=False)
    unit_price = Column(Float, nullable=True)
    expected_delivery = Column(Date, nullable=True)
    received_qty = Column(Float, default=0)

    po = relationship("PurchaseOrder", back_populates="items")
    part = relationship("Part")
