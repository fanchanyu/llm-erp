"""
CRM Event Model (客戶互動事件模型).

記錄所有與客戶相關的互動事件，如來電、來訪、備註、電郵、會議等。
用於 CRM 整合與客戶 360 視圖。
"""

from datetime import datetime
from sqlalchemy import Column, String, Text, Integer, DateTime
from app.models.inventory import Base


class CrmEvent(Base):
    __tablename__ = "crm_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    customer_id = Column(Integer, nullable=False, index=True)  # 關聯客戶 ID
    event_type = Column(String(50), nullable=False)  # call / visit / note / email / meeting
    description = Column(Text, nullable=False)  # 事件描述
    reference_type = Column(String(50), nullable=True)  # 關聯單據類型（如 SO / PO / Invoice）
    reference_no = Column(String(100), nullable=True)  # 關聯單據號碼
    created_by = Column(String(100), nullable=True)  # 建立人員
    created_at = Column(DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "customer_id": self.customer_id,
            "event_type": self.event_type,
            "description": self.description,
            "reference_type": self.reference_type,
            "reference_no": self.reference_no,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
