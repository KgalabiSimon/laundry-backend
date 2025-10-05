import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List
from celery import Task
from sqlalchemy.orm import Session

from app.core.celery_app import celery_app
from app.core.database import SessionLocal
from app.models.notification import Notification, MessageStatus, NotificationType
from app.models.order import Order
from app.models.customer import Customer
from app.services.notification_service import notification_service
from app.schemas.notification import SendNotificationRequest, BulkNotificationRequest

logger = logging.getLogger(__name__)


class DatabaseTask(Task):
    """Base task with database session management"""
    _db = None

    @property
    def db(self):
        if self._db is None:
            self._db = SessionLocal()
        return self._db

    def after_return(self, status, retval, task_id, args, kwargs, einfo):
        if self._db is not None:
            self._db.close()
            self._db = None


@celery_app.task(bind=True, base=DatabaseTask)
def send_notification_task(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
    """Background task to send a single notification"""
    try:
        request = SendNotificationRequest(**request_data)

        # Run async function in sync context
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        result = loop.run_until_complete(
            notification_service.send_notification(self.db, request)
        )

        loop.close()

        logger.info(f"Notification task completed: {result}")
        return result

    except Exception as e:
        logger.error(f"Notification task failed: {str(e)}")
        raise self.retry(exc=e, countdown=60, max_retries=3)


@celery_app.task(bind=True, base=DatabaseTask)
def send_bulk_notifications_task(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
    """Background task to send bulk notifications"""
    try:
        request = BulkNotificationRequest(**request_data)

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        result = loop.run_until_complete(
            notification_service.send_bulk_notifications(self.db, request)
        )

        loop.close()

        logger.info(f"Bulk notification task completed: {result}")
        return result

    except Exception as e:
        logger.error(f"Bulk notification task failed: {str(e)}")
        raise self.retry(exc=e, countdown=60, max_retries=3)


@celery_app.task(bind=True, base=DatabaseTask)
def send_order_notification_task(
    self,
    order_id: int,
    trigger_type: str,
    additional_data: Dict[str, Any] = None
) -> Dict[str, Any]:
    """Background task to send order-related notification"""
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        result = loop.run_until_complete(
            notification_service.send_order_notification(
                self.db, order_id, trigger_type, additional_data
            )
        )

        loop.close()

        logger.info(f"Order notification task completed for order {order_id}: {result}")
        return result

    except Exception as e:
        logger.error(f"Order notification task failed for order {order_id}: {str(e)}")
        raise self.retry(exc=e, countdown=60, max_retries=3)


@celery_app.task(bind=True, base=DatabaseTask)
def send_loyalty_notification_task(
    self,
    customer_id: int,
    points_earned: int,
    new_tier: str = None
) -> Dict[str, Any]:
    """Background task to send loyalty notification"""
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        result = loop.run_until_complete(
            notification_service.send_loyalty_notification(
                self.db, customer_id, points_earned, new_tier
            )
        )

        loop.close()

        logger.info(f"Loyalty notification task completed for customer {customer_id}: {result}")
        return result

    except Exception as e:
        logger.error(f"Loyalty notification task failed for customer {customer_id}: {str(e)}")
        raise self.retry(exc=e, countdown=60, max_retries=3)


@celery_app.task(bind=True, base=DatabaseTask)
def retry_failed_notifications(self) -> Dict[str, Any]:
    """Periodic task to retry failed notifications"""
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        result = loop.run_until_complete(
            notification_service.retry_failed_notifications(self.db, max_retries=3)
        )

        loop.close()

        logger.info(f"Retry failed notifications completed: {result}")
        return result

    except Exception as e:
        logger.error(f"Retry failed notifications task failed: {str(e)}")
        return {"error": str(e)}


@celery_app.task(bind=True, base=DatabaseTask)
def send_scheduled_notifications(self) -> Dict[str, Any]:
    """Periodic task to send scheduled notifications"""
    try:
        # Find notifications scheduled for now or past
        now = datetime.utcnow()
        scheduled_notifications = self.db.query(Notification).filter(
            Notification.status == MessageStatus.PENDING,
            Notification.scheduled_at <= now
        ).all()

        results = {"sent": 0, "failed": 0}

        for notification in scheduled_notifications:
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

                result = loop.run_until_complete(
                    notification_service._send_whatsapp_notification(notification)
                )

                loop.close()

                # Update notification status
                if result["success"]:
                    notification.status = MessageStatus.SENT
                    if result.get("message_id"):
                        notification.whatsapp_message_id = result["message_id"]
                    results["sent"] += 1
                else:
                    notification.status = MessageStatus.FAILED
                    notification.error_message = result.get("error")
                    results["failed"] += 1

                notification.sent_at = datetime.utcnow()
                self.db.commit()

            except Exception as e:
                logger.error(f"Failed to send scheduled notification {notification.id}: {str(e)}")
                notification.status = MessageStatus.FAILED
                notification.error_message = str(e)
                results["failed"] += 1
                self.db.commit()

        logger.info(f"Scheduled notifications processed: {results}")
        return results

    except Exception as e:
        logger.error(f"Send scheduled notifications task failed: {str(e)}")
        return {"error": str(e)}


@celery_app.task(bind=True, base=DatabaseTask)
def cleanup_old_notifications(self, days: int = 90) -> Dict[str, Any]:
    """Periodic task to cleanup old notifications"""
    try:
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        # Delete old notifications (keep only recent ones)
        deleted_count = self.db.query(Notification).filter(
            Notification.created_at < cutoff_date
        ).count()

        self.db.query(Notification).filter(
            Notification.created_at < cutoff_date
        ).delete()

        self.db.commit()

        result = {"deleted_count": deleted_count, "cutoff_date": cutoff_date.isoformat()}
        logger.info(f"Cleanup old notifications completed: {result}")
        return result

    except Exception as e:
        logger.error(f"Cleanup old notifications task failed: {str(e)}")
        return {"error": str(e)}


@celery_app.task(bind=True, base=DatabaseTask)
def send_order_reminders(self) -> Dict[str, Any]:
    """Periodic task to send pickup/delivery reminders"""
    try:
        # Find orders that need reminders
        reminder_time = datetime.utcnow() + timedelta(hours=2)  # 2 hours before estimated completion

        orders_ready = self.db.query(Order).filter(
            Order.status == "ready",
            Order.estimated_completion_time <= reminder_time
        ).all()

        results = {"pickup_reminders_sent": 0, "failed": 0}

        for order in orders_ready:
            try:
                # Check if reminder already sent (you'd add a flag to track this)
                request_data = {
                    "order_id": order.id,
                    "trigger_type": "pickup_reminder"
                }

                send_order_notification_task.delay(order.id, "pickup_reminder")
                results["pickup_reminders_sent"] += 1

            except Exception as e:
                logger.error(f"Failed to send pickup reminder for order {order.id}: {str(e)}")
                results["failed"] += 1

        logger.info(f"Order reminders processed: {results}")
        return results

    except Exception as e:
        logger.error(f"Send order reminders task failed: {str(e)}")
        return {"error": str(e)}


# ===== CONVENIENCE FUNCTIONS FOR IMMEDIATE USE =====

def queue_notification(request_data: Dict[str, Any]) -> None:
    """Queue a notification for background processing"""
    send_notification_task.delay(request_data)


def queue_bulk_notifications(request_data: Dict[str, Any]) -> None:
    """Queue bulk notifications for background processing"""
    send_bulk_notifications_task.delay(request_data)


def queue_order_notification(order_id: int, trigger_type: str, additional_data: Dict = None) -> None:
    """Queue an order notification for background processing"""
    send_order_notification_task.delay(order_id, trigger_type, additional_data or {})


def queue_loyalty_notification(customer_id: int, points_earned: int, new_tier: str = None) -> None:
    """Queue a loyalty notification for background processing"""
    send_loyalty_notification_task.delay(customer_id, points_earned, new_tier)
