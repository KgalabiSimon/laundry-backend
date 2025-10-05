from pydantic import BaseModel, validator
from typing import Optional, List
from datetime import datetime
from decimal import Decimal
from app.models import OrderStatus


class OrderItemBase(BaseModel):
    service_type_id: int
    quantity: int

    @validator('quantity')
    def validate_quantity(cls, v):
        if v <= 0:
            raise ValueError('Quantity must be greater than 0')
        return v


class OrderItemCreate(OrderItemBase):
    pass


class OrderItemResponse(OrderItemBase):
    id: int
    price_per_item: Decimal
    total_price: Decimal
    service_type_name: str
    service_type_category: str

    class Config:
        from_attributes = True


class OrderBase(BaseModel):
    notes: Optional[str] = None


class OrderCreate(OrderBase):
    customer_id: int
    items: List[OrderItemCreate]
    points_to_redeem: Optional[int] = 0

    @validator('items')
    def validate_items(cls, v):
        if not v:
            raise ValueError('Order must have at least one item')
        return v

    @validator('points_to_redeem')
    def validate_points(cls, v):
        if v < 0:
            raise ValueError('Points to redeem cannot be negative')
        return v


class OrderUpdate(BaseModel):
    status: Optional[OrderStatus] = None
    notes: Optional[str] = None
    assigned_to_id: Optional[int] = None


class OrderResponse(OrderBase):
    id: int
    tracking_id: str
    customer_id: int
    customer_name: str
    status: OrderStatus
    total_amount: Decimal
    discount_amount: Decimal
    final_amount: Decimal
    points_earned: int
    points_redeemed: int

    # Worker information
    captured_by_id: Optional[int] = None
    captured_by_name: Optional[str] = None
    assigned_to_id: Optional[int] = None
    assigned_to_name: Optional[str] = None

    # Items
    items: List[OrderItemResponse]

    # Timestamps
    created_at: datetime
    estimated_completion_time: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class OrderStatusUpdate(BaseModel):
    status: OrderStatus
    notes: Optional[str] = None


class OrderSearchParams(BaseModel):
    status: Optional[OrderStatus] = None
    customer_id: Optional[int] = None
    tracking_id: Optional[str] = None
    worker_id: Optional[int] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    limit: Optional[int] = 50
    offset: Optional[int] = 0


class OrderStats(BaseModel):
    total_orders: int
    pending_orders: int
    in_progress_orders: int
    ready_orders: int
    completed_orders: int
    cancelled_orders: int
    total_revenue: Decimal
    average_order_value: Decimal
    orders_today: int
    orders_this_week: int
    orders_this_month: int


class OrderTrackingResponse(BaseModel):
    tracking_id: str
    status: OrderStatus
    estimated_completion: Optional[datetime] = None
    status_history: List[dict]
    current_location: str
    next_update: str
