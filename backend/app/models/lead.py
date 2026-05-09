"""
Lead Model (潛在客戶).

Tracks inbound leads from various sources with scoring, status workflow
(new → contacted → qualified → converted/lost), and assignment tracking.
"""

from datetime import datetime
from sqlalchemy import Column, String, Text, Integer, DateTime
from app.models.inventory import Base


class Lead(Base):
    __tablename__ = "leads"

    id = Column(Integer, primary_key=True, autoincrement=True)
    company = Column(String(200), nullable=False)
    contact_person = Column(String(100), nullable=True)
    phone = Column(String(50), nullable=True)
    email = Column(String(200), nullable=True)
    source = Column(String(50), default="web")  # web / referral / cold_call / exhibition / other
    score = Column(Integer, default=0)
    status = Column(String(20), default="new")  # new / contacted / qualified / converted / lost
    assigned_to = Column(String(100), nullable=True)
    notes = Column(Text, nullable=True)
    lost_reason = Column(Text, nullable=True)
    converted_to_customer_id = Column(Integer, nullable=True, index=True)  # logical FK to customers.id
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
