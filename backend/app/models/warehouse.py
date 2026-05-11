"""Warehouse & Supply Chain models — WMS, supplier evaluation, auto-replenishment."""

import uuid
from datetime import datetime, date
from sqlalchemy import (
    Column, String, Float, Integer, DateTime, Date, Boolean, Text,
    ForeignKey, Uuid,
)
from sqlalchemy.orm import relationship
from app.models.inventory import Base


# ─── Warehouse Zone (倉庫區域) ───────────────────────────────────

class WarehouseZone(Base):
    """Warehouse zone/area — e.g. 原料倉, 半成品倉, 成品倉, 不良品倉."""
    __tablename__ = "warehouse_zones"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    code = Column(String(20), unique=True, nullable=False, index=True)
    name = Column(String(200), nullable=False)
    zone_type = Column(String(30), default="raw")  # raw, semi, finished, defect, quarantine
    status = Column(String(20), default="active")
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


# ─── Bin Location (儲位) ─────────────────────────────────────────

class BinLocation(Base):
    """Physical storage location: aisle, rack, shelf, bin."""
    __tablename__ = "bin_locations"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    zone_id = Column(Uuid, ForeignKey("warehouse_zones.id"), nullable=False)
    code = Column(String(50), unique=True, nullable=False, index=True)
    aisle = Column(String(30), nullable=True)
    rack = Column(String(30), nullable=True)
    shelf = Column(String(30), nullable=True)
    bin = Column(String(30), nullable=True)
    max_capacity = Column(Float, nullable=True)       # max quantity this bin can hold
    current_qty = Column(Float, default=0)             # current occupied quantity
    part_id = Column(Uuid, ForeignKey("parts.id"), nullable=True)  # what part is stored here
    status = Column(String(20), default="active")       # active, full, maintenance, disabled
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    zone = relationship("WarehouseZone", foreign_keys=[zone_id])


# ─── Inventory Transfer (調撥單) ─────────────────────────────────

class InventoryTransfer(Base):
    """Stock transfer between locations/zones."""
    __tablename__ = "inventory_transfers"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    transfer_no = Column(String(50), unique=True, nullable=False, index=True)
    part_id = Column(Uuid, ForeignKey("parts.id"), nullable=False)
    quantity = Column(Float, nullable=False)
    from_bin_id = Column(Uuid, ForeignKey("bin_locations.id"), nullable=True)
    to_bin_id = Column(Uuid, ForeignKey("bin_locations.id"), nullable=False)
    from_zone_id = Column(Uuid, ForeignKey("warehouse_zones.id"), nullable=True)
    to_zone_id = Column(Uuid, ForeignKey("warehouse_zones.id"), nullable=False)
    reason = Column(String(100), default="transfer")  # transfer, adjustment, return
    status = Column(String(20), default="pending")     # pending, completed, cancelled
    created_by = Column(String(100), default="")
    completed_at = Column(DateTime, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


# ─── Pick Task (揀貨任務) ────────────────────────────────────────

class PickTask(Base):
    """Picking/packing task for outbound orders."""
    __tablename__ = "pick_tasks"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    task_no = Column(String(50), unique=True, nullable=False, index=True)
    reference_type = Column(String(30), nullable=False)  # sales_order, work_order, transfer
    reference_no = Column(String(100), nullable=False)
    part_id = Column(Uuid, ForeignKey("parts.id"), nullable=False)
    quantity_required = Column(Float, nullable=False)
    quantity_picked = Column(Float, default=0)
    from_bin_id = Column(Uuid, ForeignKey("bin_locations.id"), nullable=True)
    assigned_to = Column(String(100), nullable=True)
    status = Column(String(20), default="pending")  # pending, picking, packed, shipped, cancelled
    notes = Column(Text, nullable=True)
    picked_at = Column(DateTime, nullable=True)
    shipped_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


# ─── Cycle Count (盤點) ──────────────────────────────────────────

class CycleCount(Base):
    """Inventory cycle count / physical count record."""
    __tablename__ = "cycle_counts"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    count_no = Column(String(50), unique=True, nullable=False, index=True)
    part_id = Column(Uuid, ForeignKey("parts.id"), nullable=False)
    bin_id = Column(Uuid, ForeignKey("bin_locations.id"), nullable=True)
    expected_qty = Column(Float, nullable=False)
    actual_qty = Column(Float, nullable=False)
    variance = Column(Float, nullable=False)
    variance_pct = Column(Float, nullable=True)
    status = Column(String(20), default="pending")  # pending, counted, verified, resolved
    counted_by = Column(String(100), nullable=True)
    notes = Column(Text, nullable=True)
    counted_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


# ─── Supplier Evaluation (供應商評鑑) ────────────────────────────

class SupplierEvaluation(Base):
    """Periodic supplier performance evaluation."""
    __tablename__ = "supplier_evaluations"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    supplier_id = Column(Uuid, ForeignKey("suppliers.id"), nullable=False)
    eval_date = Column(Date, nullable=False)
    quality_score = Column(Float, default=0)    # 0-100
    delivery_score = Column(Float, default=0)   # 0-100
    price_score = Column(Float, default=0)      # 0-100
    service_score = Column(Float, default=0)    # 0-100
    total_score = Column(Float, default=0)
    grade = Column(String(10), nullable=True)   # A, B, C, D
    evaluator = Column(String(100), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    supplier = relationship("Supplier", foreign_keys=[supplier_id])


# ─── Supplier Price History (供應商報價) ─────────────────────────

class SupplierPrice(Base):
    """Historical pricing from suppliers for parts."""
    __tablename__ = "supplier_prices"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    supplier_id = Column(Uuid, ForeignKey("suppliers.id"), nullable=False)
    part_id = Column(Uuid, ForeignKey("parts.id"), nullable=False)
    unit_price = Column(Float, nullable=False)
    currency = Column(String(10), default="TWD")
    effective_date = Column(Date, nullable=False)
    expiry_date = Column(Date, nullable=True)
    moq = Column(Float, default=1)  # minimum order quantity
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    supplier = relationship("Supplier", foreign_keys=[supplier_id])


# ─── Reorder Rule (自動補貨規則) ─────────────────────────────────

class ReorderRule(Base):
    """Auto-replenishment rules triggered when stock falls below safety stock."""
    __tablename__ = "reorder_rules"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    part_id = Column(Uuid, ForeignKey("parts.id"), nullable=False, unique=True)
    preferred_supplier_id = Column(Uuid, ForeignKey("suppliers.id"), nullable=True)
    safety_stock = Column(Float, nullable=False)      # trigger level
    reorder_qty = Column(Float, nullable=False)        # how much to order
    lead_time_days = Column(Integer, default=7)
    auto_approve = Column(Boolean, default=False)      # auto-create PO or require approval
    is_active = Column(Boolean, default=True)
    last_triggered_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
