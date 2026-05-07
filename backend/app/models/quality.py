import uuid
from datetime import datetime, date
from sqlalchemy import Column, String, Float, Date, DateTime, Text, ForeignKey, Uuid
from sqlalchemy.orm import relationship
from app.models.inventory import Base


class InspectionOrder(Base):
    __tablename__ = "inspection_orders"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    inspection_no = Column(String(50), unique=True, nullable=False, index=True)
    po_id = Column(Uuid, ForeignKey("purchase_orders.id"), nullable=True)
    part_id = Column(Uuid, ForeignKey("parts.id"), nullable=False)
    lot_no = Column(String(50), nullable=True)
    quantity = Column(Float, nullable=False)
    status = Column(String(20), default="pending")  # pending, approved, rejected, conditional
    inspection_date = Column(DateTime, nullable=True)
    inspected_by = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    part = relationship("Part")
    results = relationship("InspectionResult", back_populates="inspection")
    ncs = relationship("NonConformance", back_populates="inspection")


class InspectionResult(Base):
    __tablename__ = "inspection_results"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    inspection_id = Column(Uuid, ForeignKey("inspection_orders.id"), nullable=False)
    item_no = Column(String(50), nullable=True)          # 檢驗項目編號
    description = Column(Text, nullable=True)             # 檢驗項目描述
    spec_value = Column(String(200), nullable=True)       # 規格值
    measured_value = Column(String(200), nullable=True)   # 實測值
    result = Column(String(20), default="pass")           # pass, fail, conditional
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    inspection = relationship("InspectionOrder", back_populates="results")


class NonConformance(Base):
    __tablename__ = "non_conformances"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    nc_no = Column(String(50), unique=True, nullable=False, index=True)
    inspection_id = Column(Uuid, ForeignKey("inspection_orders.id"), nullable=True)
    part_id = Column(Uuid, ForeignKey("parts.id"), nullable=False)
    defect_code = Column(String(50), nullable=True)
    description = Column(Text, nullable=False)
    severity = Column(String(20), default="minor")        # minor, major, critical
    status = Column(String(20), default="open")           # open, investigating, closed
    created_by = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    resolved_at = Column(DateTime, nullable=True)

    part = relationship("Part")
    inspection = relationship("InspectionOrder", back_populates="ncs")
    capa_records = relationship("CAPARecord", back_populates="nc")


class CAPARecord(Base):
    __tablename__ = "capa_records"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    nc_id = Column(Uuid, ForeignKey("non_conformances.id"), nullable=False)
    root_cause = Column(Text, nullable=True)
    action = Column(Text, nullable=False)
    responsible = Column(String(100), nullable=True)
    deadline = Column(Date, nullable=True)
    status = Column(String(20), default="planned")        # planned, in_progress, closed
    closed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    nc = relationship("NonConformance", back_populates="capa_records")
