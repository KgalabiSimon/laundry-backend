from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, Enum, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base
import enum


class NotificationType(str, enum.Enum):
    ORDER_CONFIRMATION = "order_confirmation"
    STATUS_UPDATE = "status_update"
    PICKUP_REMINDER = "pickup_reminder"
    DELIVERY_REMINDER = "delivery_reminder"
    PAYMENT_CONFIRMATION = "payment_confirmation"
    LOYALTY_UPDATE = "loyalty_update"
    PROMOTIONAL = "promotional"
    FEEDBACK_REQUEST = "feedback_request"
    CUSTOM = "custom"


class MessageStatus(str, enum.Enum):
    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    READ = "read"
    FAILED = "failed"
    REJECTED = "rejected"


class MessageTemplate(Base):
    __tablename__ = "message_templates"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False, index=True)
    notification_type = Column(Enum(NotificationType), nullable=False)
    template_name = Column(String, nullable=False)  # WhatsApp template name
    language_code = Column(String, default="en", nullable=False)

    # Template content
    header_text = Column(Text, nullable=True)
    body_text = Column(Text, nullable=False)
    footer_text = Column(Text, nullable=True)

    # Template parameters and configuration
    parameters = Column(JSON, nullable=True)  # Parameter mappings
    has_buttons = Column(Boolean, default=False)
    button_config = Column(JSON, nullable=True)  # Button configurations

    # Media support
    has_media = Column(Boolean, default=False)
    media_type = Column(String, nullable=True)  # image, document, video

    # Status and management
    is_active = Column(Boolean, default=True)
    is_approved = Column(Boolean, default=False)  # WhatsApp template approval status

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    notifications = relationship("Notification", back_populates="template")

    def __repr__(self):
        return f"<MessageTemplate(name='{self.name}', type='{self.notification_type}')>"


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    template_id = Column(Integer, ForeignKey("message_templates.id"), nullable=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=True)

    # Message details
    notification_type = Column(Enum(NotificationType), nullable=False)
    recipient_phone = Column(String, nullable=False)
    message_text = Column(Text, nullable=False)

    # WhatsApp specific
    whatsapp_message_id = Column(String, nullable=True, index=True)
    template_name = Column(String, nullable=True)
    template_language = Column(String, default="en")
    template_parameters = Column(JSON, nullable=True)

    # Media attachment
    media_url = Column(String, nullable=True)
    media_type = Column(String, nullable=True)

    # Status tracking
    status = Column(Enum(MessageStatus), default=MessageStatus.PENDING)
    delivery_status = Column(String, nullable=True)
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0)

    # Scheduling
    scheduled_at = Column(DateTime(timezone=True), nullable=True)
    sent_at = Column(DateTime(timezone=True), nullable=True)
    delivered_at = Column(DateTime(timezone=True), nullable=True)
    read_at = Column(DateTime(timezone=True), nullable=True)

    # Metadata
    meta_data = Column(JSON, nullable=True)  # Additional data for tracking

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    customer = relationship("Customer")
    template = relationship("MessageTemplate", back_populates="notifications")
    order = relationship("Order")

    def __repr__(self):
        return f"<Notification(id={self.id}, type='{self.notification_type}', status='{self.status}')>"


class NotificationPreference(Base):
    __tablename__ = "notification_preferences"

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), unique=True, nullable=False)

    # WhatsApp preferences
    whatsapp_opted_in = Column(Boolean, default=True)
    whatsapp_phone = Column(String, nullable=True)

    # Notification type preferences
    order_updates = Column(Boolean, default=True)
    pickup_reminders = Column(Boolean, default=True)
    promotional_messages = Column(Boolean, default=True)
    loyalty_updates = Column(Boolean, default=True)
    feedback_requests = Column(Boolean, default=True)

    # Communication preferences
    preferred_language = Column(String, default="en")
    preferred_time_start = Column(String, default="09:00")  # HH:MM format
    preferred_time_end = Column(String, default="21:00")
    timezone = Column(String, default="UTC")

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    opted_out_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    customer = relationship("Customer")

    def __repr__(self):
        return f"<NotificationPreference(customer_id={self.customer_id}, whatsapp_opted_in={self.whatsapp_opted_in})>"


class WebhookEvent(Base):
    __tablename__ = "webhook_events"

    id = Column(Integer, primary_key=True, index=True)

    # Webhook details
    event_type = Column(String, nullable=False)
    whatsapp_message_id = Column(String, nullable=True, index=True)
    notification_id = Column(Integer, ForeignKey("notifications.id"), nullable=True)

    # Event data
    status = Column(String, nullable=True)
    timestamp = Column(DateTime(timezone=True), nullable=True)
    raw_data = Column(JSON, nullable=False)

    # Processing
    processed = Column(Boolean, default=False)
    processed_at = Column(DateTime(timezone=True), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    notification = relationship("Notification")

    def __repr__(self):
        return f"<WebhookEvent(id={self.id}, type='{self.event_type}', processed={self.processed})>"
