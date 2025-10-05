import logging
from datetime import datetime
from typing import Dict, Any
from sqlalchemy.orm import Session

from app.core.celery_app import celery_app
from app.core.database import SessionLocal
from app.models.order import Order, OrderStatus
from app.tasks.notification_tasks import DatabaseTask, queue_order_notification

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, base=DatabaseTask)
def process_order_status_change(self, order_id: int, old_status: str, new_status: str) -> Dict[str, Any]:
    """Background task triggered when order status changes"""
    try:
        order = self.db.query(Order).filter(Order.id == order_id).first()
        if not order:
            return {"error": "Order not found"}

        # Map status changes to notification triggers
        notification_triggers = {
            ("pending", "in-progress"): "status_updated",
            ("in-progress", "ready"): "status_updated",
            ("ready", "completed"): "status_updated",
            ("pending", "cancelled"): "status_updated",
        }

        trigger = notification_triggers.get((old_status, new_status))
        if trigger:
            # Queue notification
            queue_order_notification(order_id, trigger)

            # Additional triggers based on new status
            if new_status == "ready":
                # Schedule pickup reminder for later
                queue_order_notification(order_id, "pickup_reminder")
            elif new_status == "completed":
                # Schedule feedback request
                queue_order_notification(order_id, "feedback_request")

        result = {
            "order_id": order_id,
            "status_change": f"{old_status} -> {new_status}",
            "notification_triggered": trigger is not None
        }

        logger.info(f"Order status change processed: {result}")
        return result

    except Exception as e:
        logger.error(f"Order status change processing failed for order {order_id}: {str(e)}")
        return {"error": str(e)}


@celery_app.task(bind=True, base=DatabaseTask)
def process_new_order(self, order_id: int) -> Dict[str, Any]:
    """Background task triggered when new order is created"""
    try:
        order = self.db.query(Order).filter(Order.id == order_id).first()
        if not order:
            return {"error": "Order not found"}

        # Send order confirmation notification
        queue_order_notification(order_id, "order_created")

        result = {
            "order_id": order_id,
            "confirmation_sent": True
        }

        logger.info(f"New order processed: {result}")
        return result

    except Exception as e:
        logger.error(f"New order processing failed for order {order_id}: {str(e)}")
        return {"error": str(e)}


# ===== CONVENIENCE FUNCTIONS =====

def trigger_order_created(order_id: int) -> None:
    """Trigger background processing for new order"""
    process_new_order.delay(order_id)


def trigger_status_change(order_id: int, old_status: str, new_status: str) -> None:
    """Trigger background processing for order status change"""
    process_order_status_change.delay(order_id, old_status, new_status)
