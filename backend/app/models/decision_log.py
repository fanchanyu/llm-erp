"""DecisionLog model — record and track every business decision."""

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text, JSON
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class DecisionLog(Base):
    __tablename__ = "decision_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    decision_type = Column(String(30), nullable=False)  # rush_order, supplier_change, schedule_change, price_change, other
    description = Column(Text, nullable=False)
    department = Column(String(50), nullable=False)
    actor = Column(String(100), nullable=False)
    role = Column(String(50), nullable=False)
    context_data = Column(JSON, nullable=True)  # snapshot of data at decision time
    alternatives = Column(JSON, nullable=True)  # list of explored alternatives
    outcome_summary = Column(Text, nullable=True)
    status = Column(String(20), default="pending")  # pending, in_review, completed
    created_at = Column(DateTime, default=datetime.utcnow)
