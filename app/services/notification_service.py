import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_

from app.models.notification import (
    Notification, MessageTemplate, NotificationPreference,
    MessageStatus, NotificationType
)
from app.models.customer import Customer
from app.models.order import Order, OrderStatus
from app.models.user import User
from app.services.whatsapp import whatsapp_service
from app.schemas.notification import (
    NotificationCreate, SendNotificationRequest,
    BulkNotificationRequest, NotificationStats
)

logger = logging.getLogger(__name__)


class NotificationService:
    def __init__(self):
        self.whatsapp = whatsapp_service

    async def send_notification(
        self,
        db: Session,
        request: SendNotificationRequest
    ) -> Dict[str, Any]:
        """Send a single notification to a customer"""
        try:
            # Get customer and check preferences
            customer = db.query(Customer).filter(Customer.id == request.customer_id).first()
            if not customer:
                return {"success": False, "error": "Customer not found"}

            preferences = self._get_notification_preferences(db, request.customer_id)

            # Check if customer opted in for this type of notification
            if not self._should_send_notification(preferences, request.notification_type):
                logger.info(f"Customer {request.customer_id} opted out of {request.notification_type}")
                return {"success": False, "error": "Customer opted out"}

            # Get phone number (prefer preference setting, fallback to user phone)
            recipient_phone = preferences.whatsapp_phone or customer.user.phone
            if not recipient_phone:
                return {"success": False, "error": "No phone number available"}

            # Create notification record
            notification_data = {
                "customer_id": request.customer_id,
                "order_id": request.order_id,
                "notification_type": request.notification_type,
                "recipient_phone": recipient_phone,
                "template_name": request.template_name,
                "template_language": preferences.preferred_language,
                "template_parameters": request.template_parameters,
                "scheduled_at": request.scheduled_at,
                "metadata": {"request_source": "api"}
            }

            # Handle template vs custom message
            if request.template_name:
                template = db.query(MessageTemplate).filter(
                    MessageTemplate.template_name == request.template_name,
                    MessageTemplate.is_active == True,
                    MessageTemplate.is_approved == True
                ).first()

                if not template:
                    return {"success": False, "error": "Template not found or not approved"}

                notification_data["template_id"] = template.id
                notification_data["message_text"] = self._build_message_from_template(
                    template, request.template_parameters or []
                )
            else:
                notification_data["message_text"] = request.custom_message or "Order update"

            # Create notification in database
            notification = Notification(**notification_data)
            db.add(notification)
            db.commit()
            db.refresh(notification)

            # Send immediately or schedule
            if request.scheduled_at and request.scheduled_at > datetime.utcnow():
                # Schedule for later (would use Celery in production)
                logger.info(f"Notification {notification.id} scheduled for {request.scheduled_at}")
                return {
                    "success": True,
                    "notification_id": notification.id,
                    "status": "scheduled"
                }
            else:
                # Send now
                result = await self._send_whatsapp_notification(notification)

                # Update notification with result
                notification.status = MessageStatus.SENT if result["success"] else MessageStatus.FAILED
                if result.get("message_id"):
                    notification.whatsapp_message_id = result["message_id"]
                if result.get("error"):
                    notification.error_message = result["error"]

                db.commit()

                return {
                    "success": result["success"],
                    "notification_id": notification.id,
                    "message_id": result.get("message_id"),
                    "error": result.get("error")
                }

        except Exception as e:
            logger.error(f"Error sending notification: {str(e)}")
            db.rollback()
            return {"success": False, "error": str(e)}

    async def send_bulk_notifications(
        self,
        db: Session,
        request: BulkNotificationRequest
    ) -> Dict[str, Any]:
        """Send notifications to multiple customers"""
        results = {"success": 0, "failed": 0, "errors": []}

        for customer_id in request.customer_ids:
            notification_request = SendNotificationRequest(
                customer_id=customer_id,
                notification_type=request.notification_type,
                template_name=request.template_name,
                template_parameters=request.template_parameters,
                header_parameters=request.header_parameters,
                scheduled_at=request.scheduled_at
            )

            result = await self.send_notification(db, notification_request)

            if result["success"]:
                results["success"] += 1
            else:
                results["failed"] += 1
                results["errors"].append({
                    "customer_id": customer_id,
                    "error": result["error"]
                })

            # Small delay to avoid rate limiting
            await asyncio.sleep(0.1)

        return results

    async def send_order_notification(
        self,
        db: Session,
        order_id: int,
        trigger_type: str,
        additional_data: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Send order-related notification based on trigger type"""
        try:
            order = db.query(Order).filter(Order.id == order_id).first()
            if not order:
                return {"success": False, "error": "Order not found"}

            customer = order.customer
            if not customer:
                return {"success": False, "error": "Customer not found"}

            # Map trigger types to notification types and templates
            notification_mapping = {
                "order_created": {
                    "type": NotificationType.ORDER_CONFIRMATION,
                    "template": "order_confirmation",
                    "parameters": [customer.user.name, order.tracking_id, str(order.final_amount)]
                },
                "status_updated": {
                    "type": NotificationType.STATUS_UPDATE,
                    "template": "status_update",
                    "parameters": [customer.user.name, order.tracking_id, order.status.value]
                },
                "pickup_reminder": {
                    "type": NotificationType.PICKUP_REMINDER,
                    "template": "pickup_reminder",
                    "parameters": [customer.user.name, order.tracking_id]
                },
                "delivery_reminder": {
                    "type": NotificationType.DELIVERY_REMINDER,
                    "template": "delivery_reminder",
                    "parameters": [customer.user.name, order.tracking_id]
                },
                "payment_confirmed": {
                    "type": NotificationType.PAYMENT_CONFIRMATION,
                    "template": "payment_confirmation",
                    "parameters": [customer.user.name, str(order.final_amount), order.tracking_id]
                },
                "feedback_request": {
                    "type": NotificationType.FEEDBACK_REQUEST,
                    "template": "feedback_request",
                    "parameters": [customer.user.name, order.tracking_id]
                }
            }

            mapping = notification_mapping.get(trigger_type)
            if not mapping:
                return {"success": False, "error": f"Unknown trigger type: {trigger_type}"}

            # Create notification request
            request = SendNotificationRequest(
                customer_id=customer.id,
                notification_type=mapping["type"],
                template_name=mapping["template"],
                template_parameters=mapping["parameters"],
                order_id=order_id
            )

            return await self.send_notification(db, request)

        except Exception as e:
            logger.error(f"Error sending order notification: {str(e)}")
            return {"success": False, "error": str(e)}

    async def send_loyalty_notification(
        self,
        db: Session,
        customer_id: int,
        points_earned: int,
        new_tier: Optional[str] = None
    ) -> Dict[str, Any]:
        """Send loyalty program related notification"""
        customer = db.query(Customer).filter(Customer.id == customer_id).first()
        if not customer:
            return {"success": False, "error": "Customer not found"}

        parameters = [customer.user.name, str(points_earned), str(customer.loyalty_points)]

        if new_tier:
            parameters.append(new_tier.upper())
            template_name = "loyalty_tier_upgrade"
        else:
            template_name = "loyalty_points_earned"

        request = SendNotificationRequest(
            customer_id=customer_id,
            notification_type=NotificationType.LOYALTY_UPDATE,
            template_name=template_name,
            template_parameters=parameters
        )

        return await self.send_notification(db, request)

    def get_notification_stats(
        self,
        db: Session,
        days: int = 30,
        customer_id: Optional[int] = None
    ) -> NotificationStats:
        """Get notification statistics"""
        base_query = db.query(Notification)

        if customer_id:
            base_query = base_query.filter(Notification.customer_id == customer_id)

        # Date range filter
        since_date = datetime.utcnow() - timedelta(days=days)
        base_query = base_query.filter(Notification.created_at >= since_date)

        # Basic counts
        total_sent = base_query.filter(Notification.status != MessageStatus.PENDING).count()
        total_delivered = base_query.filter(Notification.status == MessageStatus.DELIVERED).count()
        total_read = base_query.filter(Notification.status == MessageStatus.READ).count()
        total_failed = base_query.filter(Notification.status == MessageStatus.FAILED).count()

        # Calculate rates
        delivery_rate = (total_delivered / total_sent * 100) if total_sent > 0 else 0
        read_rate = (total_read / total_delivered * 100) if total_delivered > 0 else 0
        failure_rate = (total_failed / total_sent * 100) if total_sent > 0 else 0

        # Time-based counts
        last_24h = datetime.utcnow() - timedelta(hours=24)
        this_week = datetime.utcnow() - timedelta(days=7)
        this_month = datetime.utcnow() - timedelta(days=30)

        last_24h_sent = base_query.filter(Notification.created_at >= last_24h).count()
        this_week_sent = base_query.filter(Notification.created_at >= this_week).count()
        this_month_sent = base_query.filter(Notification.created_at >= this_month).count()

        return NotificationStats(
            total_sent=total_sent,
            total_delivered=total_delivered,
            total_read=total_read,
            total_failed=total_failed,
            delivery_rate=round(delivery_rate, 2),
            read_rate=round(read_rate, 2),
            failure_rate=round(failure_rate, 2),
            last_24h_sent=last_24h_sent,
            this_week_sent=this_week_sent,
            this_month_sent=this_month_sent
        )

    def _get_notification_preferences(self, db: Session, customer_id: int) -> NotificationPreference:
        """Get customer notification preferences, create default if not exists"""
        preferences = db.query(NotificationPreference).filter(
            NotificationPreference.customer_id == customer_id
        ).first()

        if not preferences:
            # Create default preferences
            preferences = NotificationPreference(
                customer_id=customer_id,
                whatsapp_opted_in=True,
                order_updates=True,
                pickup_reminders=True,
                promotional_messages=True,
                loyalty_updates=True,
                feedback_requests=True
            )
            db.add(preferences)
            db.commit()
            db.refresh(preferences)

        return preferences

    def _should_send_notification(
        self,
        preferences: NotificationPreference,
        notification_type: NotificationType
    ) -> bool:
        """Check if notification should be sent based on customer preferences"""
        if not preferences.whatsapp_opted_in:
            return False

        type_mapping = {
            NotificationType.ORDER_CONFIRMATION: preferences.order_updates,
            NotificationType.STATUS_UPDATE: preferences.order_updates,
            NotificationType.PICKUP_REMINDER: preferences.pickup_reminders,
            NotificationType.DELIVERY_REMINDER: preferences.pickup_reminders,
            NotificationType.PAYMENT_CONFIRMATION: preferences.order_updates,
            NotificationType.LOYALTY_UPDATE: preferences.loyalty_updates,
            NotificationType.PROMOTIONAL: preferences.promotional_messages,
            NotificationType.FEEDBACK_REQUEST: preferences.feedback_requests,
        }

        return type_mapping.get(notification_type, True)

    def _build_message_from_template(
        self,
        template: MessageTemplate,
        parameters: List[str]
    ) -> str:
        """Build message text from template and parameters"""
        message = template.body_text

        # Simple parameter substitution (in production, use proper templating)
        for i, param in enumerate(parameters):
            placeholder = f"{{{{param{i+1}}}}}"
            message = message.replace(placeholder, param)

        return message

    async def _send_whatsapp_notification(self, notification: Notification) -> Dict[str, Any]:
        """Send WhatsApp notification using the WhatsApp service"""
        if notification.template_name:
            # Send template message
            result = await self.whatsapp.send_template_message(
                recipient_phone=notification.recipient_phone,
                template_name=notification.template_name,
                language_code=notification.template_language,
                parameters=notification.template_parameters,
                notification_id=notification.id
            )
        else:
            # Send text message
            result = await self.whatsapp.send_text_message(
                recipient_phone=notification.recipient_phone,
                message_text=notification.message_text,
                notification_id=notification.id
            )

        return result

    async def retry_failed_notifications(self, db: Session, max_retries: int = 3) -> Dict[str, Any]:
        """Retry failed notifications"""
        failed_notifications = db.query(Notification).filter(
            Notification.status == MessageStatus.FAILED,
            Notification.retry_count < max_retries
        ).all()

        results = {"retried": 0, "success": 0, "failed": 0}

        for notification in failed_notifications:
            try:
                result = await self._send_whatsapp_notification(notification)

                notification.retry_count += 1
                notification.updated_at = datetime.utcnow()

                if result["success"]:
                    notification.status = MessageStatus.SENT
                    if result.get("message_id"):
                        notification.whatsapp_message_id = result["message_id"]
                    results["success"] += 1
                else:
                    notification.error_message = result.get("error")
                    results["failed"] += 1

                results["retried"] += 1

            except Exception as e:
                logger.error(f"Error retrying notification {notification.id}: {str(e)}")
                notification.retry_count += 1
                notification.error_message = str(e)
                results["failed"] += 1

            db.commit()

        return results


# Global notification service instance
notification_service = NotificationService()
