from pydantic import BaseModel, validator, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from app.models.notification import NotificationType, MessageStatus


class NotificationPreferenceBase(BaseModel):
    whatsapp_opted_in: bool = True
    whatsapp_phone: Optional[str] = None
    order_updates: bool = True
    pickup_reminders: bool = True
    promotional_messages: bool = True
    loyalty_updates: bool = True
    feedback_requests: bool = True
    preferred_language: str = "en"
    preferred_time_start: str = "09:00"
    preferred_time_end: str = "21:00"
    timezone: str = "UTC"


class NotificationPreferenceUpdate(NotificationPreferenceBase):
    pass


class NotificationPreferenceResponse(NotificationPreferenceBase):
    id: int
    customer_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    opted_out_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class MessageTemplateBase(BaseModel):
    name: str
    notification_type: NotificationType
    template_name: str
    language_code: str = "en"
    header_text: Optional[str] = None
    body_text: str
    footer_text: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None
    has_buttons: bool = False
    button_config: Optional[Dict[str, Any]] = None
    has_media: bool = False
    media_type: Optional[str] = None


class MessageTemplateCreate(MessageTemplateBase):
    pass


class MessageTemplateUpdate(BaseModel):
    name: Optional[str] = None
    template_name: Optional[str] = None
    language_code: Optional[str] = None
    header_text: Optional[str] = None
    body_text: Optional[str] = None
    footer_text: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None
    has_buttons: Optional[bool] = None
    button_config: Optional[Dict[str, Any]] = None
    has_media: Optional[bool] = None
    media_type: Optional[str] = None
    is_active: Optional[bool] = None


class MessageTemplateResponse(MessageTemplateBase):
    id: int
    is_active: bool
    is_approved: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class NotificationBase(BaseModel):
    notification_type: NotificationType
    recipient_phone: str
    message_text: str
    template_name: Optional[str] = None
    template_language: str = "en"
    template_parameters: Optional[Dict[str, Any]] = None
    media_url: Optional[str] = None
    media_type: Optional[str] = None
    scheduled_at: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None


class NotificationCreate(NotificationBase):
    customer_id: int
    template_id: Optional[int] = None
    order_id: Optional[int] = None


class NotificationUpdate(BaseModel):
    status: Optional[MessageStatus] = None
    error_message: Optional[str] = None
    scheduled_at: Optional[datetime] = None


class NotificationResponse(NotificationBase):
    id: int
    customer_id: int
    template_id: Optional[int] = None
    order_id: Optional[int] = None
    whatsapp_message_id: Optional[str] = None
    status: MessageStatus
    delivery_status: Optional[str] = None
    error_message: Optional[str] = None
    retry_count: int
    sent_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    read_at: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class SendNotificationRequest(BaseModel):
    customer_id: int
    notification_type: NotificationType
    template_name: Optional[str] = None
    template_parameters: Optional[List[str]] = None
    header_parameters: Optional[List[str]] = None
    button_parameters: Optional[List[Dict]] = None
    custom_message: Optional[str] = None
    order_id: Optional[int] = None
    scheduled_at: Optional[datetime] = None

    @validator('template_parameters', 'header_parameters')
    def validate_parameters(cls, v):
        if v is not None and len(v) > 10:  # WhatsApp limit
            raise ValueError('Too many parameters (max 10)')
        return v


class BulkNotificationRequest(BaseModel):
    customer_ids: List[int]
    notification_type: NotificationType
    template_name: str
    template_parameters: Optional[List[str]] = None
    header_parameters: Optional[List[str]] = None
    scheduled_at: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None

    @validator('customer_ids')
    def validate_customer_ids(cls, v):
        if len(v) > 100:  # Batch limit
            raise ValueError('Too many customers in batch (max 100)')
        return v


class NotificationStats(BaseModel):
    total_sent: int
    total_delivered: int
    total_read: int
    total_failed: int
    delivery_rate: float
    read_rate: float
    failure_rate: float
    avg_delivery_time: Optional[float] = None
    last_24h_sent: int
    this_week_sent: int
    this_month_sent: int


class WhatsAppWebhookEvent(BaseModel):
    verify_token: Optional[str] = None
    challenge: Optional[str] = None
    entry: Optional[List[Dict[str, Any]]] = None


class WhatsAppStatusUpdate(BaseModel):
    message_id: str
    status: str
    timestamp: Optional[str] = None
    error: Optional[Dict[str, Any]] = None


class OrderNotificationTrigger(BaseModel):
    order_id: int
    trigger_type: str = Field(..., description="Type of notification trigger")
    additional_data: Optional[Dict[str, Any]] = None

    @validator('trigger_type')
    def validate_trigger_type(cls, v):
        valid_triggers = [
            'order_created', 'status_updated', 'pickup_reminder',
            'delivery_reminder', 'payment_confirmed', 'feedback_request'
        ]
        if v not in valid_triggers:
            raise ValueError(f'Invalid trigger type. Must be one of: {valid_triggers}')
        return v


class NotificationSearchParams(BaseModel):
    customer_id: Optional[int] = None
    notification_type: Optional[NotificationType] = None
    status: Optional[MessageStatus] = None
    order_id: Optional[int] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    template_name: Optional[str] = None
    limit: int = 50
    offset: int = 0

    @validator('limit')
    def validate_limit(cls, v):
        if v > 100:
            raise ValueError('Limit cannot exceed 100')
        return v
