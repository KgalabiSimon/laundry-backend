from sqlalchemy import Column, Integer, String, Numeric, Text, Enum, DateTime, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base
import enum


class ServiceCategory(str, enum.Enum):
    WASH = "wash"
    DRY_CLEAN = "dry-clean"
    IRON = "iron"
    SPECIAL = "special"


class ServiceType(Base):
    __tablename__ = "service_types"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    category = Column(Enum(ServiceCategory), nullable=False)
    base_price = Column(Numeric(10, 2), nullable=False)
    description = Column(Text, nullable=True)
    estimated_duration_hours = Column(Integer, default=2)  # Duration in hours
    is_active = Column(Boolean, default=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    order_items = relationship("OrderItem", back_populates="service_type")

    def __repr__(self):
        return f"<ServiceType(id={self.id}, name='{self.name}', category='{self.category}')>"
