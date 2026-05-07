"""
Production Scheduling & Dispatching Models

Core entities for factory floor control:
- WorkCenter: 工作站/機台 (e.g. CNC-01, 裝配線A)
- ProductionOrder: 工單 (from MRP or manual)
- Operation: 工序 (工單在特定機台上的作業)
- DispatchLog: 派工記錄

Flow: ProductionOrder → multiple Operations → dispatched to WorkCenters
"""

import uuid
from datetime import datetime, date
from sqlalchemy import (
    Column, String, Float, Integer, DateTime, Date, ForeignKey, Text, Enum as SAEnum,
)
from sqlalchemy.orm import declarative_base, relationship
import enum

Base = declarative_base()


class OrderStatus(str, enum.Enum):
    DRAFT = "draft"
    RELEASED = "released"
    DISPATCHED = "dispatched"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class OpStatus(str, enum.Enum):
    PENDING = "pending"
    READY = "ready"
    RUNNING = "running"
    COMPLETED = "completed"
    PAUSED = "paused"
    FAILED = "failed"


class WCStatus(str, enum.Enum):
    IDLE = "idle"
    RUNNING = "running"
    DOWN = "down"
    MAINTENANCE = "maintenance"


class WorkCenter(Base):
    __tablename__ = "work_centers"

    id = Column(String(32), primary_key=True, default=lambda: uuid.uuid4().hex)
    name = Column(String(100), nullable=False, unique=True)
    description = Column(Text, default="")
    status = Column(String(20), default=WCStatus.IDLE.value, index=True)
    capacity_hours = Column(Float, default=8.0)         # 每日可用工時
    efficiency = Column(Float, default=1.0)              # 效率係數
    location = Column(String(100), default="")
    # 可替代機台群組 (Route Changing 用)
    alternate_group = Column(String(50), default="")
    created_at = Column(DateTime, default=datetime.utcnow)

    operations = relationship("Operation", back_populates="work_center")


class ProductionOrder(Base):
    __tablename__ = "production_orders"

    id = Column(String(32), primary_key=True, default=lambda: uuid.uuid4().hex)
    order_no = Column(String(50), nullable=False, unique=True, index=True)
    product_no = Column(String(50), nullable=False)       # 對應 Product.product_no
    product_name = Column(String(200), default="")
    quantity = Column(Float, nullable=False)
    due_date = Column(Date, nullable=False, index=True)
    priority = Column(Integer, default=3)                 # 1=最急 ~ 5=最低
    status = Column(String(20), default=OrderStatus.DRAFT.value, index=True)
    notes = Column(Text, default="")
    created_by = Column(String(100), default="")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    operations = relationship("Operation", back_populates="order",
                              order_by="Operation.sequence_no")


class Operation(Base):
    """工單工序 — 一個工單可能需要在多個機台上加工"""

    __tablename__ = "operations"

    id = Column(String(32), primary_key=True, default=lambda: uuid.uuid4().hex)
    order_id = Column(String(32), ForeignKey("production_orders.id"), nullable=False)
    work_center_id = Column(String(32), ForeignKey("work_centers.id"), nullable=False)
    sequence_no = Column(Integer, nullable=False)         # 工序順序
    name = Column(String(200), default="")                # 工序名稱 (e.g. "銑削", "鑽孔")
    setup_time_min = Column(Float, default=0)             # 設定時間 (分鐘)
    cycle_time_min = Column(Float, default=0)             # 每件循環時間 (分鐘)
    total_time_min = Column(Float, default=0)             # 總工時 (setup + qty * cycle)
    status = Column(String(20), default=OpStatus.PENDING.value, index=True)

    scheduled_start = Column(DateTime, nullable=True)
    scheduled_end = Column(DateTime, nullable=True)
    actual_start = Column(DateTime, nullable=True)
    actual_end = Column(DateTime, nullable=True)
    delay_minutes = Column(Float, default=0)              # 累計延遲

    order = relationship("ProductionOrder", back_populates="operations")
    work_center = relationship("WorkCenter", back_populates="operations")


class DispatchLog(Base):
    """派工記錄 — 誰在什麼時候把工單派到哪個機台"""

    __tablename__ = "dispatch_logs"

    id = Column(String(32), primary_key=True, default=lambda: uuid.uuid4().hex)
    order_id = Column(String(32), ForeignKey("production_orders.id"), nullable=True)
    operation_id = Column(String(32), ForeignKey("operations.id"), nullable=True)
    work_center_id = Column(String(32), ForeignKey("work_centers.id"), nullable=True)
    action = Column(String(50), nullable=False)           # dispatch / reschedule / pause / resume
    dispatched_by = Column(String(100), default="system")
    notes = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.utcnow)
