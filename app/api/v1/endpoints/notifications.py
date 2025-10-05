from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from fastapi.background import BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
import logging

from app.core.database import get_db
from app.core.auth import get_current_user, require_admin, require_worker_or_admin
from app.models import User, Customer, Notification, MessageTemplate, NotificationPreference
from app.schemas.notification import (
    NotificationCreate, NotificationResponse, NotificationUpdate,
    SendNotificationRequest, BulkNotificationRequest,
    MessageTemplateCreate, MessageTemplateResponse, MessageTemplateUpdate,
    NotificationPreferenceResponse, NotificationPreferenceUpdate,
    NotificationStats, NotificationSearchParams,
    WhatsAppWebhookEvent, OrderNotificationTrigger
)
from app.services.notification_service import notification_service
from app.services.whatsapp import whatsapp_service

router = APIRouter()
logger = logging.getLogger(__name__)


# ===== NOTIFICATION SENDING ENDPOINTS =====

@router.post("/send", response_model=Dict[str, Any])
async def send_notification(
    request: SendNotificationRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(require_worker_or_admin),
    db: Session = Depends(get_db)
):
    """Send a notification to a customer"""
    if request.scheduled_at:
        # For scheduled notifications, add to background tasks
        background_tasks.add_task(
            notification_service.send_notification, db, request
        )
        return {"success": True, "message": "Notification scheduled"}
    else:
        # Send immediately
        result = await notification_service.send_notification(db, request)
        return result


@router.post("/send-bulk", response_model=Dict[str, Any])
async def send_bulk_notifications(
    request: BulkNotificationRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Send notifications to multiple customers (admin only)"""
    background_tasks.add_task(
        notification_service.send_bulk_notifications, db, request
    )
    return {"success": True, "message": f"Bulk notification initiated for {len(request.customer_ids)} customers"}


@router.post("/order-trigger")
async def trigger_order_notification(
    request: OrderNotificationTrigger,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(require_worker_or_admin),
    db: Session = Depends(get_db)
):
    """Trigger order-related notification"""
    background_tasks.add_task(
        notification_service.send_order_notification,
        db, request.order_id, request.trigger_type, request.additional_data
    )
    return {"success": True, "message": f"Order notification triggered: {request.trigger_type}"}


@router.post("/loyalty")
async def send_loyalty_notification(
    customer_id: int,
    points_earned: int,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(require_worker_or_admin),
    db: Session = Depends(get_db),
    new_tier: Optional[str] = None
):
    """Send loyalty program notification"""
    background_tasks.add_task(
        notification_service.send_loyalty_notification,
        db, customer_id, points_earned, new_tier
    )
    return {"success": True, "message": "Loyalty notification sent"}



# ===== NOTIFICATION MANAGEMENT ENDPOINTS =====

@router.get("/", response_model=List[NotificationResponse])
def get_notifications(
    params: NotificationSearchParams = Depends(),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get notifications with filtering"""
    query = db.query(Notification)

    # Role-based filtering
    if current_user.role.value == "customer":
        # Customers can only see their own notifications
        customer = db.query(Customer).filter(Customer.user_id == current_user.id).first()
        if not customer:
            raise HTTPException(status_code=404, detail="Customer profile not found")
        query = query.filter(Notification.customer_id == customer.id)
    elif params.customer_id and current_user.role.value in ["admin", "worker"]:
        query = query.filter(Notification.customer_id == params.customer_id)

    # Apply filters
    if params.notification_type:
        query = query.filter(Notification.notification_type == params.notification_type)
    if params.status:
        query = query.filter(Notification.status == params.status)
    if params.order_id:
        query = query.filter(Notification.order_id == params.order_id)
    if params.date_from:
        query = query.filter(Notification.created_at >= params.date_from)
    if params.date_to:
        query = query.filter(Notification.created_at <= params.date_to)
    if params.template_name:
        query = query.filter(Notification.template_name == params.template_name)

    # Pagination and ordering
    notifications = query.order_by(Notification.created_at.desc())\
                        .offset(params.offset)\
                        .limit(params.limit)\
                        .all()

    return notifications


@router.get("/{notification_id}", response_model=NotificationResponse)
def get_notification(
    notification_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get specific notification"""
    notification = db.query(Notification).filter(Notification.id == notification_id).first()

    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")

    # Check permission
    if current_user.role.value == "customer":
        customer = db.query(Customer).filter(Customer.user_id == current_user.id).first()
        if not customer or notification.customer_id != customer.id:
            raise HTTPException(status_code=403, detail="Access denied")

    return notification


@router.patch("/{notification_id}", response_model=NotificationResponse)
def update_notification(
    notification_id: int,
    updates: NotificationUpdate,
    current_user: User = Depends(require_worker_or_admin),
    db: Session = Depends(get_db)
):
    """Update notification (admin/worker only)"""
    notification = db.query(Notification).filter(Notification.id == notification_id).first()

    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")

    # Update fields
    for field, value in updates.dict(exclude_unset=True).items():
        setattr(notification, field, value)

    db.commit()
    db.refresh(notification)
    return notification


@router.post("/retry-failed")
async def retry_failed_notifications(
    max_retries: int = Query(3, ge=1, le=5),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Retry failed notifications (admin only)"""
    result = await notification_service.retry_failed_notifications(db, max_retries)
    return result


# ===== STATISTICS ENDPOINTS =====

@router.get("/stats/summary", response_model=NotificationStats)
def get_notification_stats(
    days: int = Query(30, ge=1, le=365),
    customer_id: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get notification statistics"""
    # Role-based access
    if current_user.role.value == "customer":
        customer = db.query(Customer).filter(Customer.user_id == current_user.id).first()
        if not customer:
            raise HTTPException(status_code=404, detail="Customer profile not found")
        customer_id = customer.id
    elif customer_id and current_user.role.value not in ["admin", "worker"]:
        raise HTTPException(status_code=403, detail="Access denied")

    stats = notification_service.get_notification_stats(db, days, customer_id)
    return stats


# ===== TEMPLATE MANAGEMENT ENDPOINTS =====

@router.get("/templates/", response_model=List[MessageTemplateResponse])
def get_message_templates(
    active_only: bool = Query(True),
    notification_type: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get message templates"""
    query = db.query(MessageTemplate)

    if active_only:
        query = query.filter(MessageTemplate.is_active == True)

    if notification_type:
        query = query.filter(MessageTemplate.notification_type == notification_type)

    templates = query.order_by(MessageTemplate.name).all()
    return templates


@router.post("/templates/", response_model=MessageTemplateResponse)
def create_message_template(
    template: MessageTemplateCreate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Create message template (admin only)"""
    # Check for duplicate name
    existing = db.query(MessageTemplate).filter(MessageTemplate.name == template.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Template name already exists")

    db_template = MessageTemplate(**template.dict())
    db.add(db_template)
    db.commit()
    db.refresh(db_template)
    return db_template


@router.put("/templates/{template_id}", response_model=MessageTemplateResponse)
def update_message_template(
    template_id: int,
    updates: MessageTemplateUpdate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Update message template (admin only)"""
    template = db.query(MessageTemplate).filter(MessageTemplate.id == template_id).first()

    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    # Update fields
    for field, value in updates.dict(exclude_unset=True).items():
        setattr(template, field, value)

    db.commit()
    db.refresh(template)
    return template


@router.delete("/templates/{template_id}")
def delete_message_template(
    template_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Delete message template (admin only)"""
    template = db.query(MessageTemplate).filter(MessageTemplate.id == template_id).first()

    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    db.delete(template)
    db.commit()
    return {"message": "Template deleted successfully"}


# ===== NOTIFICATION PREFERENCES ENDPOINTS =====

@router.get("/preferences/", response_model=NotificationPreferenceResponse)
def get_notification_preferences(
    customer_id: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get notification preferences"""
    # Determine customer ID based on role
    if current_user.role.value == "customer":
        customer = db.query(Customer).filter(Customer.user_id == current_user.id).first()
        if not customer:
            raise HTTPException(status_code=404, detail="Customer profile not found")
        target_customer_id = customer.id
    elif customer_id and current_user.role.value in ["admin", "worker"]:
        target_customer_id = customer_id
    else:
        raise HTTPException(status_code=400, detail="Customer ID required")

    preferences = notification_service._get_notification_preferences(db, target_customer_id)
    return preferences


@router.put("/preferences/", response_model=NotificationPreferenceResponse)
def update_notification_preferences(
    updates: NotificationPreferenceUpdate,
    customer_id: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update notification preferences"""
    # Determine customer ID based on role
    if current_user.role.value == "customer":
        customer = db.query(Customer).filter(Customer.user_id == current_user.id).first()
        if not customer:
            raise HTTPException(status_code=404, detail="Customer profile not found")
        target_customer_id = customer.id
    elif customer_id and current_user.role.value in ["admin", "worker"]:
        target_customer_id = customer_id
    else:
        raise HTTPException(status_code=400, detail="Customer ID required")

    preferences = notification_service._get_notification_preferences(db, target_customer_id)

    # Update fields
    for field, value in updates.dict(exclude_unset=True).items():
        setattr(preferences, field, value)

    db.commit()
    db.refresh(preferences)
    return preferences


# ===== WHATSAPP WEBHOOK ENDPOINTS =====

@router.get("/webhook/whatsapp")
def verify_whatsapp_webhook(
    hub_mode: str = Query(alias="hub.mode"),
    hub_verify_token: str = Query(alias="hub.verify_token"),
    hub_challenge: str = Query(alias="hub.challenge")
):
    """Verify WhatsApp webhook subscription"""
    if hub_mode == "subscribe":
        challenge = whatsapp_service.verify_webhook(hub_verify_token, hub_challenge)
        if challenge:
            return int(challenge)

    raise HTTPException(status_code=403, detail="Webhook verification failed")


@router.post("/webhook/whatsapp")
async def handle_whatsapp_webhook(
    request: Request,
    db: Session = Depends(get_db)
):
    """Handle WhatsApp webhook events"""
    try:
        # Get raw body for signature verification
        body = await request.body()
        signature = request.headers.get("X-Hub-Signature-256", "")

        # Verify signature (if configured)
        if not whatsapp_service.verify_webhook_signature(body.decode(), signature):
            raise HTTPException(status_code=403, detail="Invalid signature")

        # Parse JSON payload
        import json
        payload = json.loads(body.decode())

        # Process webhook event
        success = await whatsapp_service.process_webhook_event(payload, db)

        if success:
            return {"status": "success"}
        else:
            raise HTTPException(status_code=500, detail="Failed to process webhook")

    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")
    except Exception as e:
        logger.error(f"Webhook processing error: {str(e)}")
        raise HTTPException(status_code=500, detail="Webhook processing failed")


# ===== ADMIN UTILITIES =====

@router.post("/test-whatsapp")
async def test_whatsapp_connection(
    phone: str,
    message: str = "Test message from LaundryPro API",
    current_user: User = Depends(require_admin),
):
    """Test WhatsApp connection (admin only)"""
    result = await whatsapp_service.send_text_message(phone, message)
    return result


@router.get("/health")
def notification_health_check():
    """Health check for notification service"""
    return {
        "service": "notifications",
        "status": "healthy",
        "whatsapp_enabled": whatsapp_service.enabled,
        "timestamp": "2024-01-01T00:00:00Z"
    }
