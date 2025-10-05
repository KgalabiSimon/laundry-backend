from sqlalchemy import Column, Integer, String, Numeric, DateTime, Enum, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base
from typing import Optional, List
import enum


class SubscriptionPlan(str, enum.Enum):
    BASIC = "basic"
    PREMIUM = "premium"
    FAMILY = "family"
    BUSINESS = "business"


class LoyaltyTier(str, enum.Enum):
    BRONZE = "bronze"
    SILVER = "silver"
    GOLD = "gold"
    PLATINUM = "platinum"


class Customer(Base):
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)

    # Contact Information
    address = Column(Text, nullable=True)

    # Loyalty Program
    loyalty_points = Column(Integer, default=0)
    loyalty_tier = Column(Enum(LoyaltyTier), default=LoyaltyTier.BRONZE)
    subscription_plan = Column(Enum(SubscriptionPlan), default=SubscriptionPlan.BASIC)

    # Statistics
    total_spent = Column(Numeric(10, 2), default=0.00)
    total_orders = Column(Integer, default=0)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="customer_profile")
    orders = relationship("Order", back_populates="customer")
    points_transactions = relationship("PointsTransaction", back_populates="customer")

    def __repr__(self):
        return f"<Customer(id={self.id}, user_id={self.user_id}, tier='{self.loyalty_tier}')>"

    @property
    def name(self):
        return self.user.name if self.user else None

    @property
    def email(self):
        return self.user.email if self.user else None

    @property
    def phone(self):
        return self.user.phone if self.user else None
