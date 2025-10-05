from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base
import enum


class UserRole(str, enum.Enum):
    ADMIN = "admin"
    WORKER = "worker"
    CUSTOMER = "customer"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    phone = Column(String, nullable=True)
    hashed_password = Column(String, nullable=False)
    role = Column(Enum(UserRole), nullable=False)
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_login_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    customer_profile = relationship("Customer", back_populates="user", uselist=False)
    worker_profile = relationship("Worker", back_populates="user", uselist=False, foreign_keys="[Worker.user_id]")

    # For tracking order activities
    captured_orders = relationship("Order", foreign_keys="Order.captured_by_id", back_populates="captured_by")
    assigned_orders = relationship("Order", foreign_keys="Order.assigned_to_id", back_populates="assigned_to")

    def __repr__(self):
        return f"<User(id={self.id}, email='{self.email}', role='{self.role}')>"
