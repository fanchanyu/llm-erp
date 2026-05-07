"""
Customer Master Model (客戶主檔).

Stores customer information including contact details, credit limit,
and customer level classification (A/B/C).
"""

from datetime import datetime
from sqlalchemy import Column, String, Float, Integer, DateTime, Boolean, Text
from app.models.inventory import Base


class Customer(Base):
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    customer_no = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(200), nullable=False)
    contact_person = Column(String(100), nullable=True)
    phone = Column(String(50), nullable=True)
    email = Column(String(200), nullable=True)
    credit_limit = Column(Float, default=0)
    level = Column(String(10), default="C")  # A / B / C
    notes = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
