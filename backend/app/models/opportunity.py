"""
Opportunity Model (銷售機會).

Tracks sales opportunities through stages from qualification through
closed-won/lost, linked to leads and customers.
"""

from datetime import datetime
from sqlalchemy import Column, String, Float, Text, Integer, DateTime
from app.models.inventory import Base


class Opportunity(Base):
    __tablename__ = "opportunities"

    id = Column(Integer, primary_key=True, autoincrement=True)
    lead_id = Column(Integer, nullable=True, index=True)  # logical FK to leads.id
    customer_id = Column(Integer, nullable=False, index=True)  # logical FK to customers.id
    name = Column(String(200), nullable=False)
    amount = Column(Float, default=0)
    probability = Column(Integer, default=50)  # 0-100
    stage = Column(String(30), default="qualification")  # qualification / needs_analysis / proposal / negotiation / closed_won / closed_lost
    expected_close_date = Column(DateTime, nullable=True)
    win_reason = Column(Text, nullable=True)
    lost_reason = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
