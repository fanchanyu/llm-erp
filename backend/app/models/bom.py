import uuid
from datetime import datetime
from sqlalchemy import Column, String, Float, Integer, DateTime, Text, ForeignKey, Uuid
from sqlalchemy.orm import relationship
from app.models.inventory import Base


class Product(Base):
    __tablename__ = "products"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    product_no = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class BOMItem(Base):
    __tablename__ = "bom_items"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    product_id = Column(Uuid, ForeignKey("products.id"), nullable=False)
    part_id = Column(Uuid, ForeignKey("parts.id"), nullable=False)
    quantity = Column(Float, nullable=False)
    level = Column(Integer, nullable=False)  # BOM 階層: 0=成品, 1=子組件, 2=零件...
    sequence_no = Column(Integer, nullable=True)  # 工序順序

    product = relationship("Product")
    part = relationship("Part")
