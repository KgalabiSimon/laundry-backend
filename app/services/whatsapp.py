import aiohttp
import asyncio
import logging
import json
import hmac
import hashlib
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.models.notification import (
    Notification, MessageTemplate, NotificationPreference,
    WebhookEvent, MessageStatus, NotificationType
)
from app.models.customer import Customer
from app.models.order import Order

logger = logging.getLogger(__name__)


class WhatsAppService:
    def __init__(self):
        self.api_url = settings.whatsapp_api_url
        self.access_token = settings.whatsapp_access_token
        self.phone_number_id = settings.whatsapp_phone_number_id
        self.business_account_id = settings.whatsapp_business_account_id
        self.webhook_verify_token = settings.whatsapp_webhook_verify_token
        self.app_secret = settings.whatsapp_app_secret
        self.enabled = settings.whatsapp_enabled

        if not self.enabled:
            logger.warning("WhatsApp notifications are disabled")

    async def send_template_message(
        self,
        recipient_phone: str,
        template_name: str,
        language_code: str = "en",
        parameters: Optional[List[str]] = None,
        header_parameters: Optional[List[str]] = None,
        button_parameters: Optional[List[Dict]] = None,
        notification_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Send a WhatsApp template message"""

        if not self.enabled:
            logger.info(f"WhatsApp disabled - would send template {template_name} to {recipient_phone}")
            return {"success": False, "error": "WhatsApp notifications disabled"}

        # Clean phone number (remove non-digits, ensure country code)
        clean_phone = self._clean_phone_number(recipient_phone)

        # Prepare message payload
        payload = {
            "messaging_product": "whatsapp",
            "to": clean_phone,
            "type": "template",
            "template": {
                "name": template_name,
                "language": {"code": language_code}
            }
        }

        # Add components if parameters provided
        components = []

        # Header parameters
        if header_parameters:
            components.append({
                "type": "header",
                "parameters": [{"type": "text", "text": param} for param in header_parameters]
            })

        # Body parameters
        if parameters:
            components.append({
                "type": "body",
                "parameters": [{"type": "text", "text": param} for param in parameters]
            })

        # Button parameters
        if button_parameters:
            for button in button_parameters:
                components.append({
                    "type": "button",
                    "sub_type": button.get("sub_type", "quick_reply"),
                    "index": button.get("index", 0),
                    "parameters": button.get("parameters", [])
                })

        if components:
            payload["template"]["components"] = components

        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Authorization": f"Bearer {self.access_token}",
                    "Content-Type": "application/json"
                }

                url = f"{self.api_url}/{self.phone_number_id}/messages"

                async with session.post(url, json=payload, headers=headers) as response:
                    result = await response.json()

                    if response.status == 200 and "messages" in result:
                        message_id = result["messages"][0]["id"]
                        logger.info(f"WhatsApp message sent successfully: {message_id}")

                        # Update notification with message ID
                        if notification_id:
                            await self._update_notification_status(
                                notification_id, MessageStatus.SENT, message_id
                            )

                        return {
                            "success": True,
                            "message_id": message_id,
                            "data": result
                        }
                    else:
                        error_msg = result.get("error", {}).get("message", "Unknown error")
                        logger.error(f"WhatsApp API error: {error_msg}")

                        # Update notification with error
                        if notification_id:
                            await self._update_notification_status(
                                notification_id, MessageStatus.FAILED, error_message=error_msg
                            )

                        return {
                            "success": False,
                            "error": error_msg,
                            "data": result
                        }

        except Exception as e:
            logger.error(f"Error sending WhatsApp message: {str(e)}")

            # Update notification with error
            if notification_id:
                await self._update_notification_status(
                    notification_id, MessageStatus.FAILED, error_message=str(e)
                )

            return {
                "success": False,
                "error": str(e)
            }

    async def send_text_message(
        self,
        recipient_phone: str,
        message_text: str,
        notification_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Send a simple text message"""

        if not self.enabled:
            logger.info(f"WhatsApp disabled - would send text to {recipient_phone}: {message_text[:50]}...")
            return {"success": False, "error": "WhatsApp notifications disabled"}

        clean_phone = self._clean_phone_number(recipient_phone)

        payload = {
            "messaging_product": "whatsapp",
            "to": clean_phone,
            "type": "text",
            "text": {"body": message_text}
        }

        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Authorization": f"Bearer {self.access_token}",
                    "Content-Type": "application/json"
                }

                url = f"{self.api_url}/{self.phone_number_id}/messages"

                async with session.post(url, json=payload, headers=headers) as response:
                    result = await response.json()

                    if response.status == 200 and "messages" in result:
                        message_id = result["messages"][0]["id"]
                        logger.info(f"WhatsApp text message sent: {message_id}")

                        if notification_id:
                            await self._update_notification_status(
                                notification_id, MessageStatus.SENT, message_id
                            )

                        return {
                            "success": True,
                            "message_id": message_id,
                            "data": result
                        }
                    else:
                        error_msg = result.get("error", {}).get("message", "Unknown error")
                        logger.error(f"WhatsApp text message error: {error_msg}")

                        if notification_id:
                            await self._update_notification_status(
                                notification_id, MessageStatus.FAILED, error_message=error_msg
                            )

                        return {
                            "success": False,
                            "error": error_msg,
                            "data": result
                        }

        except Exception as e:
            logger.error(f"Error sending WhatsApp text message: {str(e)}")

            if notification_id:
                await self._update_notification_status(
                    notification_id, MessageStatus.FAILED, error_message=str(e)
                )

            return {
                "success": False,
                "error": str(e)
            }

    def _clean_phone_number(self, phone: str) -> str:
        """Clean and format phone number for WhatsApp API"""
        # Remove all non-digit characters
        clean = ''.join(filter(str.isdigit, phone))

        # If doesn't start with country code, assume India (+91)
        if not clean.startswith('91') and len(clean) == 10:
            clean = '91' + clean
        elif clean.startswith('0'):
            clean = '91' + clean[1:]

        return clean

    async def _update_notification_status(
        self,
        notification_id: int,
        status: MessageStatus,
        message_id: Optional[str] = None,
        error_message: Optional[str] = None
    ):
        """Update notification status in database"""
        try:
            # This would normally use dependency injection, but for async we'll create session
            from app.core.database import SessionLocal
            db = SessionLocal()

            notification = db.query(Notification).filter(Notification.id == notification_id).first()
            if notification:
                notification.status = status
                notification.updated_at = datetime.utcnow()

                if message_id:
                    notification.whatsapp_message_id = message_id
                    notification.sent_at = datetime.utcnow()

                if error_message:
                    notification.error_message = error_message
                    notification.retry_count += 1

                db.commit()

            db.close()

        except Exception as e:
            logger.error(f"Error updating notification status: {str(e)}")

    def verify_webhook(self, verify_token: str, challenge: str) -> Optional[str]:
        """Verify webhook subscription"""
        if verify_token == self.webhook_verify_token:
            return challenge
        return None

    def verify_webhook_signature(self, payload: str, signature: str) -> bool:
        """Verify webhook payload signature"""
        if not self.app_secret:
            return True  # Skip verification if no secret configured

        try:
            # Remove 'sha256=' prefix if present
            signature = signature.replace('sha256=', '')

            # Calculate expected signature
            expected = hmac.new(
                self.app_secret.encode(),
                payload.encode(),
                hashlib.sha256
            ).hexdigest()

            return hmac.compare_digest(signature, expected)

        except Exception as e:
            logger.error(f"Error verifying webhook signature: {str(e)}")
            return False

    async def process_webhook_event(self, payload: Dict[str, Any], db: Session) -> bool:
        """Process incoming webhook events"""
        try:
            # Log webhook event
            webhook_event = WebhookEvent(
                event_type="message_status",
                raw_data=payload,
                processed=False
            )
            db.add(webhook_event)
            db.commit()

            # Process status updates
            if "entry" in payload:
                for entry in payload["entry"]:
                    if "changes" in entry:
                        for change in entry["changes"]:
                            if change.get("field") == "messages":
                                value = change.get("value", {})

                                # Process message statuses
                                if "statuses" in value:
                                    for status in value["statuses"]:
                                        await self._process_status_update(status, db)

                                # Process incoming messages (for interactive responses)
                                if "messages" in value:
                                    for message in value["messages"]:
                                        await self._process_incoming_message(message, db)

            # Mark webhook as processed
            webhook_event.processed = True
            webhook_event.processed_at = datetime.utcnow()
            db.commit()

            return True

        except Exception as e:
            logger.error(f"Error processing webhook event: {str(e)}")
            return False

    async def _process_status_update(self, status: Dict[str, Any], db: Session):
        """Process message status updates"""
        message_id = status.get("id")
        status_type = status.get("status")
        timestamp = status.get("timestamp")

        if not message_id or not status_type:
            return

        # Find notification by WhatsApp message ID
        notification = db.query(Notification).filter(
            Notification.whatsapp_message_id == message_id
        ).first()

        if not notification:
            return

        # Convert timestamp
        status_time = datetime.fromtimestamp(int(timestamp)) if timestamp else datetime.utcnow()

        # Update notification based on status
        if status_type == "delivered":
            notification.status = MessageStatus.DELIVERED
            notification.delivered_at = status_time
        elif status_type == "read":
            notification.status = MessageStatus.READ
            notification.read_at = status_time
        elif status_type == "failed":
            notification.status = MessageStatus.FAILED
            error = status.get("errors", [{}])[0]
            notification.error_message = error.get("title", "Message failed")

        notification.delivery_status = status_type
        notification.updated_at = datetime.utcnow()

        db.commit()

        logger.info(f"Updated notification {notification.id} status to {status_type}")

    async def _process_incoming_message(self, message: Dict[str, Any], db: Session):
        """Process incoming messages (for interactive responses)"""
        # This could be used for handling customer responses to interactive messages
        # For now, just log the message
        from_phone = message.get("from")
        message_type = message.get("type")
        text = message.get("text", {}).get("body") if message_type == "text" else None

        logger.info(f"Received message from {from_phone}: {text}")

        # Could implement auto-responses or forward to customer service here


# Global WhatsApp service instance
whatsapp_service = WhatsAppService()
