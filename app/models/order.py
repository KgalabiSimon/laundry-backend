from sqlalchemy import Column, Integer, String, Numeric, Text, Enum, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base
import enum
import uuid


class OrderStatus(str, enum.Enum):
    PENDING = "pending"
    IN_PROGRESS = "in-progress"
    READY = "ready"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    tracking_id = Column(String, unique=True, nullable=False, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)

    # Order details
    status = Column(Enum(OrderStatus), default=OrderStatus.PENDING)
    total_amount = Column(Numeric(10, 2), nullable=False)
    discount_amount = Column(Numeric(10, 2), default=0.00)
    priority_fee = Column(Numeric(10, 2), default=0.00)
    final_amount = Column(Numeric(10, 2), nullable=False)

    # Loyalty program
    points_earned = Column(Integer, default=0)
    points_redeemed = Column(Integer, default=0)

    # Worker tracking
    captured_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    assigned_to_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    # Additional info
    notes = Column(Text, nullable=True)
    estimated_completion_time = Column(DateTime(timezone=True), nullable=True)
    actual_completion_time = Column(DateTime(timezone=True), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    customer = relationship("Customer", back_populates="orders")
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")
    captured_by = relationship("User", foreign_keys=[captured_by_id], back_populates="captured_orders")
    assigned_to = relationship("User", foreign_keys=[assigned_to_id], back_populates="assigned_orders")
    status_history = relationship("OrderStatusHistory", back_populates="order", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Order(id={self.id}, tracking_id='{self.tracking_id}', status='{self.status}')>"

    @staticmethod
    def generate_tracking_id():
        """Generate a unique tracking ID"""
        import time
        timestamp = str(int(time.time()))[-6:]  # Last 6 digits of timestamp
        random_part = str(uuid.uuid4())[:4].upper()
        return f"LP{timestamp}{random_part}"


class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    service_type_id = Column(Integer, ForeignKey("service_types.id"), nullable=False)

    quantity = Column(Integer, nullable=False)
    price_per_item = Column(Numeric(10, 2), nullable=False)
    total_price = Column(Numeric(10, 2), nullable=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    order = relationship("Order", back_populates="items")
    service_type = relationship("ServiceType", back_populates="order_items")

    def __repr__(self):
        return f"<OrderItem(id={self.id}, order_id={self.order_id}, quantity={self.quantity})>"


class OrderStatusHistory(Base):
    __tablename__ = "order_status_history"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    status = Column(Enum(OrderStatus), nullable=False)
    updated_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    notes = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    order = relationship("Order", back_populates="status_history")
    updated_by = relationship("User")

    def __repr__(self):
        return f"<OrderStatusHistory(id={self.id}, order_id={self.order_id}, status='{self.status}')>"
