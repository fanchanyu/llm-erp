"""AfterActionReview model — post-decision analysis and lessons learned."""

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text, JSON
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class AfterActionReview(Base):
    __tablename__ = "after_action_reviews"

    id = Column(Integer, primary_key=True, autoincrement=True)
    decision_log_id = Column(Integer, nullable=True)
    title = Column(String(200), nullable=False)
    department = Column(String(50), nullable=False)
    expected_result = Column(Text, nullable=False)
    actual_result = Column(Text, nullable=False)
    variance_analysis = Column(Text, nullable=True)
    root_cause = Column(Text, nullable=True)
    corrective_action = Column(Text, nullable=True)
    preventive_action = Column(Text, nullable=True)
    lessons_learned = Column(Text, nullable=True)
    system_rule_updates = Column(JSON, nullable=True)
    status = Column(String(20), default="draft")  # draft, published, implemented
    reviewer = Column(String(100), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
