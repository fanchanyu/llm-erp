import uuid
from datetime import datetime
from sqlalchemy import Column, String, Float, Integer, DateTime, Boolean, Text, ForeignKey, Enum as SAEnum, Uuid
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class Part(Base):
    __tablename__ = "parts"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    part_no = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(200), nullable=False)
    spec = Column(Text, nullable=True)
    unit = Column(String(10), nullable=False)  # pcs, kg, m, etc.
    category = Column(String(100), nullable=True)
    lead_time_days = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)


class Inventory(Base):
    __tablename__ = "inventory"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    part_id = Column(Uuid, ForeignKey("parts.id"), nullable=False)
    location = Column(String(50), nullable=True)
    quantity = Column(Float, nullable=False, default=0)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class InventoryTransaction(Base):
    __tablename__ = "inventory_transactions"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    part_id = Column(Uuid, ForeignKey("parts.id"), nullable=False)
    type = Column(String(20), nullable=False)  # inbound, outbound, adjustment
    quantity = Column(Float, nullable=False)
    reference_no = Column(String(100), nullable=True)  # PO no., work order no.
    notes = Column(Text, nullable=True)
    created_by = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
