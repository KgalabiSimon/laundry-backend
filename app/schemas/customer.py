from pydantic import BaseModel, EmailStr, validator
from typing import Optional
from datetime import datetime
from decimal import Decimal
from app.models import SubscriptionPlan, LoyaltyTier
from typing import List



class CustomerBase(BaseModel):
    address: Optional[str] = None
    subscription_plan: SubscriptionPlan = SubscriptionPlan.BASIC


class CustomerCreate(CustomerBase):
    # User information
    name: str
    email: EmailStr
    phone: Optional[str] = None
    password: str

    @validator('password')
    def validate_password(cls, v):
        if len(v) < 6:
            raise ValueError('Password must be at least 6 characters long')
        return v


class CustomerUpdate(BaseModel):
    address: Optional[str] = None
    subscription_plan: Optional[SubscriptionPlan] = None


class CustomerResponse(CustomerBase):
    id: int
    user_id: int

    # User information
    name: str
    email: str
    phone: Optional[str] = None
    is_active: bool

    # Loyalty information
    loyalty_points: int
    loyalty_tier: LoyaltyTier
    total_spent: Decimal
    total_orders: int

    # Timestamps
    created_at: datetime

    class Config:
        from_attributes = True


class CustomerStats(BaseModel):
    total_customers: int
    new_customers_this_month: int
    active_customers: int
    customers_by_tier: dict
    customers_by_plan: dict
    average_lifetime_value: Decimal
    top_customers: List[CustomerResponse]


class CustomerLoyaltyInfo(BaseModel):
    loyalty_points: int
    loyalty_tier: LoyaltyTier
    next_tier: Optional[LoyaltyTier] = None
    orders_to_next_tier: Optional[int] = None
    tier_benefits: dict
    total_points_earned: int
    total_points_redeemed: int
