"""
Factory Configuration Model (工廠設定).

Stores factory operating mode (MTO/MTS/ETO), pipeline stage definitions,
enabled form configurations, and cash flow rules.
"""

from datetime import datetime
from sqlalchemy import Column, String, Text, Integer, DateTime
from app.models.inventory import Base


class FactoryConfig(Base):
    __tablename__ = "factory_config"

    id = Column(Integer, primary_key=True, autoincrement=True)
    factory_type = Column(String(20), nullable=False, default="MTO")  # MTO / MTS / ETO
    name = Column(String(200), nullable=False, default="Default Factory")
    pipeline_stages = Column(Text, nullable=True)  # JSON string of pipeline stage definitions
    enabled_forms = Column(Text, nullable=True)  # JSON string of enabled form configurations
    cash_flow_rules = Column(Text, nullable=True)  # JSON string of cash flow rule definitions
    created_at = Column(DateTime, default=datetime.utcnow)
