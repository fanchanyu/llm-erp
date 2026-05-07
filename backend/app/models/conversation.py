import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime, Integer
from app.models.inventory import Base


class ConversationLog(Base):
    __tablename__ = "conversation_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(100), nullable=False, index=True)
    role = Column(String(20), nullable=False)  # 'user' or 'assistant'
    content = Column(Text, nullable=False)
    intent = Column(String(100), nullable=True)
    customer_id = Column(Integer, nullable=True, index=True)  # 關聯客戶 ID（CRM 整合用）
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    def to_dict(self):
        return {
            "id": self.id,
            "session_id": self.session_id,
            "role": self.role,
            "content": self.content,
            "intent": self.intent,
            "customer_id": self.customer_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
