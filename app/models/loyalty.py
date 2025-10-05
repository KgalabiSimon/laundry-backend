from sqlalchemy import Column, Integer, String, Text, Enum, DateTime, ForeignKey, Numeric, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base
import enum


class TransactionType(str, enum.Enum):
    EARNED = "earned"
    REDEEMED = "redeemed"
    EXPIRED = "expired"
    BONUS = "bonus"
    ADJUSTMENT = "adjustment"


class PointsTransaction(Base):
    __tablename__ = "points_transactions"

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=True)

    transaction_type = Column(Enum(TransactionType), nullable=False)
    points = Column(Integer, nullable=False)
    description = Column(Text, nullable=False)

    # Additional tracking
    processed_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    customer = relationship("Customer", back_populates="points_transactions")
    order = relationship("Order")
    processed_by = relationship("User")

    def __repr__(self):
        return f"<PointsTransaction(id={self.id}, customer_id={self.customer_id}, type='{self.transaction_type}', points={self.points})>"


class LoyaltyTierConfig(Base):
    __tablename__ = "loyalty_tier_configs"

    id = Column(Integer, primary_key=True, index=True)
    tier_name = Column(String, unique=True, nullable=False)
    min_orders = Column(Integer, nullable=False)
    discount_percentage = Column(Numeric(5, 2), nullable=False)
    points_multiplier = Column(Numeric(3, 2), nullable=False)
    color_code = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self):
        return f"<LoyaltyTierConfig(tier_name='{self.tier_name}', min_orders={self.min_orders})>"


class SubscriptionPlanConfig(Base):
    __tablename__ = "subscription_plan_configs"

    id = Column(Integer, primary_key=True, index=True)
    plan_name = Column(String, unique=True, nullable=False)
    discount_percentage = Column(Numeric(5, 2), nullable=False)
    points_bonus_multiplier = Column(Numeric(3, 2), nullable=False)
    monthly_fee = Column(Numeric(10, 2), default=0.00)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self):
        return f"<SubscriptionPlanConfig(plan_name='{self.plan_name}', discount={self.discount_percentage}%)>"
