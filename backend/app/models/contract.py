"""Contract model — customer pricing agreements, auto-renew tracking."""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, JSON, Boolean, ForeignKey
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class Contract(Base):
    __tablename__ = "contracts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    contract_no = Column(String(50), unique=True, nullable=False, index=True)
    customer_id = Column(Integer, nullable=False)
    type = Column(String(20), nullable=False)  # annual, framework, project, one_time
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=True)
    pricing_json = Column(JSON, nullable=True)  # {part_no: {unit_price, min_qty, discount_pct}}
    payment_terms = Column(Text, nullable=True)
    status = Column(String(20), default="draft")  # draft, active, expired, terminated
    auto_renew = Column(Boolean, default=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ContractPricing(Base):
    __tablename__ = "contract_pricing"

    id = Column(Integer, primary_key=True, autoincrement=True)
    contract_id = Column(Integer, ForeignKey("contracts.id"), nullable=False)
    part_no = Column(String(100), nullable=False)
    unit_price = Column(Float, nullable=False)
    min_qty = Column(Float, default=0)
    discount_pct = Column(Float, default=0)

    contract = relationship("Contract", backref="pricing_lines")
