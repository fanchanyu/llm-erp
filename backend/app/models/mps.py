"""MPS (Master Production Schedule) Models.

Core entities for master production scheduling:
- MpsMaster: MPS plan header (周期、狀態、描述)
- MpsEntry: 時段化 MPS 明細 (每週的預測/訂單/PAB/ATP)
- TimeFence: 時間柵欄定義 (DTF / PTF)
"""

import uuid
from datetime import datetime, date
from sqlalchemy import (
    Column, String, Float, Integer, DateTime, Date, Text, ForeignKey,
    Enum as SAEnum, Uuid,
)
from sqlalchemy.orm import DeclarativeBase, relationship
import enum


class Base(DeclarativeBase):
    pass


class TimeFenceType(str, enum.Enum):
    """時間柵欄類型"""
    DEMAND_TIME_FENCE = "demand_time_fence"      # DTF — 凍結期，不允許變更
    PLANNING_TIME_FENCE = "planning_time_fence"   # PTF — 計畫期，可有限度變更


class MpsStatus(str, enum.Enum):
    """MPS 主檔狀態"""
    DRAFT = "draft"
    ACTIVE = "active"
    FROZEN = "frozen"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class MpsEntryStatus(str, enum.Enum):
    """MPS 明細狀態"""
    FIRM = "firm"               # 確認訂單
    PLANNED = "planned"         # 計畫訂單
    EXCEPTION = "exception"     # 例外訊息


class LotSizingRule(str, enum.Enum):
    """批量規則"""
    LOT_FOR_LOT = "lot_for_lot"           # 逐批法
    FIXED_QUANTITY = "fixed_quantity"     # 固定批量
    PERIOD_ORDER = "period_order"         # 期間訂貨法


# ─── MPS Master ──────────────────────────────────────────

class MpsMaster(Base):
    """MPS 計畫主檔 — 定義一個 MPS 計畫的標頭資訊"""
    __tablename__ = "mps_masters"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    start_week = Column(Date, nullable=False, index=True)           # 起始週
    end_week = Column(Date, nullable=False, index=True)             # 結束週
    status = Column(String(20), default=MpsStatus.DRAFT.value, index=True)
    lot_sizing_rule = Column(String(30), default=LotSizingRule.LOT_FOR_LOT.value)
    fixed_lot_qty = Column(Float, nullable=True)                    # 固定批量數量 (僅 fixed_quantity 使用)
    safety_stock = Column(Float, default=0)                         # 安全庫存
    created_by = Column(String(100), default="")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    entries = relationship("MpsEntry", back_populates="master",
                           order_by="MpsEntry.period_week")
    time_fences = relationship("TimeFence", back_populates="master")


# ─── MPS Entry ───────────────────────────────────────────

class MpsEntry(Base):
    """MPS 明細 — 單一時段的時段化展算結果

    依照 APICS 標準 MPS 邏輯，每個 period_week 包含：
    - 毛需求 (Gross Requirement) = max(預測, 客戶訂單) 或 預測耗用邏輯
    - 預計可用庫存 (PAB) = 前週PAB + 計畫接收量 - 毛需求
    - 可供約量 (ATP) = 確認訂單庫存 - 已承諾量
    """
    __tablename__ = "mps_entries"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    mps_id = Column(Uuid, ForeignKey("mps_masters.id"), nullable=False)
    product_no = Column(String(50), nullable=False, index=True)
    product_name = Column(String(200), default="")
    period_week = Column(Date, nullable=False, index=True)          # 該週起始日期 (星期一)
    week_number = Column(Integer, nullable=True)                    # 從 start_week 算起的第 N 週

    # ── 需求端 ──
    forecast_qty = Column(Float, default=0)                         # 預測需求量
    customer_orders_qty = Column(Float, default=0)                  # 客戶訂單量
    gross_requirement = Column(Float, default=0)                    # 毛需求 = max(fcst, cust_order) or consumed

    # ── 供給端 ──
    scheduled_receipts = Column(Float, default=0)                   # 計畫接收量 (已確認的工單/採購單)
    projected_balance = Column(Float, default=0)                    # PAB — 預計可用庫存
    planned_order_qty = Column(Float, default=0)                    # MPS 建議的計畫訂單量
    planned_order_release = Column(Date, nullable=True)             # 計畫訂單下達日期 (lead time offset)

    # ── ATP ──
    available_to_promise = Column(Float, default=0)                 # ATP — 可供約量

    # ── 時間柵欄 ──
    time_fence_type = Column(String(30), nullable=True)             # demand_time_fence / planning_time_fence / null

    # ── 狀態 ──
    status = Column(String(20), default=MpsEntryStatus.PLANNED.value, index=True)
    exception_message = Column(Text, nullable=True)                 # 例外訊息 (如: 低於安全庫存、落後 DTF)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    master = relationship("MpsMaster", back_populates="entries")


# ─── Time Fence ──────────────────────────────────────────

class TimeFence(Base):
    """時間柵欄 — 定義 MPS 計畫中各階段的時間邊界

    DTF (Demand Time Fence): 凍結期，已確認訂單不可變更
    PTF (Planning Time Fence): 計畫期，可有限度變更
    """
    __tablename__ = "time_fences"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    mps_id = Column(Uuid, ForeignKey("mps_masters.id"), nullable=False)
    fence_type = Column(String(30), nullable=False)                 # demand_time_fence / planning_time_fence
    fence_week = Column(Date, nullable=False)                       # 柵欄所在的週
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    master = relationship("MpsMaster", back_populates="time_fences")
