"""MRP (Material Requirements Planning) Models.

Core entities for material requirements planning:
- MrpMaster: MRP plan header (名稱、描述、關聯 MPS、狀態)
- MrpItem: MRP 明細 (BOM 展開後的時段化淨需求、計畫訂單)
"""

import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, Float, Integer, DateTime, Text, ForeignKey, Uuid,
)
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


class MrpStatus(str):
    """MRP 主檔狀態"""
    DRAFT = "draft"
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class MrpOrderType(str):
    """MRP 訂單類型"""
    MAKE = "make"
    BUY = "buy"


# ─── MRP Master ──────────────────────────────────────────

class MrpMaster(Base):
    """MRP 計畫主檔 — 定義一個 MRP 運算計畫的標頭資訊"""
    __tablename__ = "mrp_masters"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    mps_id = Column(Uuid, ForeignKey("mps_masters.id"), nullable=False, index=True)
    status = Column(String(20), default=MrpStatus.DRAFT, index=True)
    created_by = Column(String(100), default="")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    items = relationship("MrpItem", back_populates="master",
                         order_by="MrpItem.bom_level, MrpItem.period_week")


# ─── MRP Item ───────────────────────────────────────────

class MrpItem(Base):
    """MRP 明細 — BOM 展開後的時段化淨需求與計畫訂單

    每筆記錄代表一個料件在某一時段（週）的 MRP 運算結果：
    - 毛需求 (Gross Requirement) = 上層 MPS 計畫 × BOM 用量
    - 在途量 (Scheduled Receipts) = 已確認採購單/工單
    - 預計庫存 (Projected Balance) = 上期庫存 + 在途 - 毛需求
    - 淨需求 (Net Requirement) = 當毛需求 > 庫存 + 在途時的差額
    - 計畫訂單 (Planned Order) = 滿足淨需求的批量建議
    - 計畫下達 (Planned Order Release) = 考慮提前期的訂單下達時間
    """
    __tablename__ = "mrp_items"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    mrp_id = Column(Uuid, ForeignKey("mrp_masters.id"), nullable=False)

    # 物料識別
    product_no = Column(String(50), nullable=False, index=True)
    part_no = Column(String(50), nullable=False, index=True)
    part_name = Column(String(200), default="")

    # BOM 階層
    bom_level = Column(Integer, nullable=False, default=0)

    # 時段 (週)
    period_week = Column(Integer, nullable=False, default=0)

    # ── MRP 運算結果 ──
    gross_requirement = Column(Float, default=0)            # 毛需求
    scheduled_receipts = Column(Float, default=0)           # 在途量 (已確認採購/工單)
    projected_balance = Column(Float, default=0)            # 預計庫存 (PAB)
    net_requirement = Column(Float, default=0)              # 淨需求
    planned_order_qty = Column(Float, default=0)            # 計畫訂單量
    planned_order_release = Column(Float, default=0)        # 計畫下達量 (提前期偏移後)

    # 訂單屬性
    order_type = Column(String(20), default=MrpOrderType.MAKE)  # make / buy
    lead_time_days = Column(Integer, default=0)             # 提前期 (天)
    source = Column(String(200), nullable=True)             # 來源 (如供應商、產線)
    exception_message = Column(Text, nullable=True)         # 例外訊息

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    master = relationship("MrpMaster", back_populates="items")
