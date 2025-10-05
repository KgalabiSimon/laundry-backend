from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.core.auth import auth_handler
from app.models import (
    User, UserRole, ServiceType, ServiceCategory,
    LoyaltyTierConfig, SubscriptionPlanConfig,
    MessageTemplate, NotificationType
)
import logging

logger = logging.getLogger(__name__)


def initialize_default_data():
    """Initialize default data for the application"""
    db = SessionLocal()
    try:
        # Create default admin user if none exists
        create_default_admin(db)

        # Create default service types
        create_default_services(db)

        # Create loyalty tier configurations
        create_loyalty_tiers(db)

        # Create subscription plan configurations
        create_subscription_plans(db)

        # Create default message templates
        create_default_message_templates(db)

        logger.info("Default data initialization completed")

    except Exception as e:
        logger.error(f"Error initializing default data: {e}")
        db.rollback()
    finally:
        db.close()


def create_default_admin(db: Session):
    """Create default admin user if none exists"""
    admin_exists = db.query(User).filter(User.role == UserRole.ADMIN).first()

    if not admin_exists:
        hashed_password = auth_handler.hash_password("admin123")
        admin_user = User(
            email="admin@laundrysystem.com",
            name="System Administrator",
            phone="+1234567890",
            hashed_password=hashed_password,
            role=UserRole.ADMIN,
            is_active=True,
            is_verified=True
        )
        db.add(admin_user)
        db.commit()
        logger.info("Default admin user created")


def create_default_services(db: Session):
    """Create default service types"""
    existing_services = db.query(ServiceType).count()

    if existing_services == 0:
        default_services = [
            {
                "name": "Shirt Wash",
                "category": ServiceCategory.WASH,
                "base_price": 40.00,
                "description": "Regular shirt washing",
                "estimated_duration_hours": 2
            },
            {
                "name": "Pant Wash",
                "category": ServiceCategory.WASH,
                "base_price": 50.00,
                "description": "Regular pant washing",
                "estimated_duration_hours": 2
            },
            {
                "name": "Suit Dry Clean",
                "category": ServiceCategory.DRY_CLEAN,
                "base_price": 200.00,
                "description": "Professional suit dry cleaning",
                "estimated_duration_hours": 24
            },
            {
                "name": "Dress Dry Clean",
                "category": ServiceCategory.DRY_CLEAN,
                "base_price": 150.00,
                "description": "Dress dry cleaning",
                "estimated_duration_hours": 24
            },
            {
                "name": "Shirt Iron",
                "category": ServiceCategory.IRON,
                "base_price": 20.00,
                "description": "Shirt pressing only",
                "estimated_duration_hours": 1
            },
            {
                "name": "Saree Wash",
                "category": ServiceCategory.SPECIAL,
                "base_price": 80.00,
                "description": "Delicate saree washing",
                "estimated_duration_hours": 4
            },
            {
                "name": "Curtain Cleaning",
                "category": ServiceCategory.SPECIAL,
                "base_price": 100.00,
                "description": "Large curtain cleaning",
                "estimated_duration_hours": 6
            },
            {
                "name": "Blanket Wash",
                "category": ServiceCategory.SPECIAL,
                "base_price": 120.00,
                "description": "Heavy blanket washing",
                "estimated_duration_hours": 4
            }
        ]

        for service_data in default_services:
            service = ServiceType(**service_data)
            db.add(service)

        db.commit()
        logger.info("Default service types created")


def create_loyalty_tiers(db: Session):
    """Create loyalty tier configurations"""
    existing_tiers = db.query(LoyaltyTierConfig).count()

    if existing_tiers == 0:
        loyalty_tiers = [
            {
                "tier_name": "bronze",
                "min_orders": 0,
                "discount_percentage": 0.00,
                "points_multiplier": 1.0,
                "color_code": "#CD7F32"
            },
            {
                "tier_name": "silver",
                "min_orders": 5,
                "discount_percentage": 5.00,
                "points_multiplier": 1.2,
                "color_code": "#C0C0C0"
            },
            {
                "tier_name": "gold",
                "min_orders": 15,
                "discount_percentage": 10.00,
                "points_multiplier": 1.5,
                "color_code": "#FFD700"
            },
            {
                "tier_name": "platinum",
                "min_orders": 30,
                "discount_percentage": 15.00,
                "points_multiplier": 2.0,
                "color_code": "#E5E4E2"
            }
        ]

        for tier_data in loyalty_tiers:
            tier = LoyaltyTierConfig(**tier_data)
            db.add(tier)

        db.commit()
        logger.info("Loyalty tier configurations created")


def create_subscription_plans(db: Session):
    """Create subscription plan configurations"""
    existing_plans = db.query(SubscriptionPlanConfig).count()

    if existing_plans == 0:
        subscription_plans = [
            {
                "plan_name": "basic",
                "discount_percentage": 0.00,
                "points_bonus_multiplier": 1.0,
                "monthly_fee": 0.00,
                "description": "Basic plan with standard benefits"
            },
            {
                "plan_name": "premium",
                "discount_percentage": 5.00,
                "points_bonus_multiplier": 1.5,
                "monthly_fee": 99.00,
                "description": "Premium plan with enhanced benefits"
            },
            {
                "plan_name": "family",
                "discount_percentage": 10.00,
                "points_bonus_multiplier": 2.0,
                "monthly_fee": 149.00,
                "description": "Family plan for multiple users"
            },
            {
                "plan_name": "business",
                "discount_percentage": 15.00,
                "points_bonus_multiplier": 2.5,
                "monthly_fee": 299.00,
                "description": "Business plan with maximum benefits"
            }
        ]

        for plan_data in subscription_plans:
            plan = SubscriptionPlanConfig(**plan_data)
            db.add(plan)

        db.commit()
        logger.info("Subscription plan configurations created")


def create_default_message_templates(db: Session):
    """Create default WhatsApp message templates"""
    existing_templates = db.query(MessageTemplate).count()

    if existing_templates == 0:
        default_templates = [
            {
                "name": "Order Confirmation",
                "notification_type": NotificationType.ORDER_CONFIRMATION,
                "template_name": "order_confirmation",
                "language_code": "en",
                "body_text": "Hi {{param1}}! 👋\n\nYour laundry order has been confirmed!\n\n🆔 Order ID: {{param2}}\n💰 Amount: ₹{{param3}}\n\nWe'll notify you when it's ready for pickup. Thank you for choosing LaundryPro! 🧺✨",
                "is_active": True,
                "is_approved": True
            },
            {
                "name": "Status Update",
                "notification_type": NotificationType.STATUS_UPDATE,
                "template_name": "status_update",
                "language_code": "en",
                "body_text": "Hi {{param1}}! 📋\n\nYour order {{param2}} status has been updated to: *{{param3}}*\n\nTrack your order anytime through our customer portal. Thank you! 🚀",
                "is_active": True,
                "is_approved": True
            },
            {
                "name": "Pickup Reminder",
                "notification_type": NotificationType.PICKUP_REMINDER,
                "template_name": "pickup_reminder",
                "language_code": "en",
                "body_text": "Hi {{param1}}! ⏰\n\nYour order {{param2}} is ready for pickup!\n\n📍 Please collect it at your convenience.\n🕒 Store hours: 9 AM - 8 PM\n\nThank you for choosing LaundryPro! 👕",
                "is_active": True,
                "is_approved": True
            },
            {
                "name": "Payment Confirmation",
                "notification_type": NotificationType.PAYMENT_CONFIRMATION,
                "template_name": "payment_confirmation",
                "language_code": "en",
                "body_text": "Hi {{param1}}! 💳\n\nPayment of ₹{{param2}} received for order {{param3}}\n\n✅ Payment Status: Confirmed\n🧾 Receipt will be provided at pickup\n\nThank you! 🙏",
                "is_active": True,
                "is_approved": True
            },
            {
                "name": "Loyalty Points Earned",
                "notification_type": NotificationType.LOYALTY_UPDATE,
                "template_name": "loyalty_points_earned",
                "language_code": "en",
                "body_text": "Congratulations {{param1}}! 🎉\n\nYou've earned {{param2}} loyalty points!\n\n⭐ Total Points: {{param3}}\n💡 Redeem points on your next order for discounts\n\nKeep using LaundryPro for more rewards! 🏆",
                "is_active": True,
                "is_approved": True
            },
            {
                "name": "Tier Upgrade",
                "notification_type": NotificationType.LOYALTY_UPDATE,
                "template_name": "loyalty_tier_upgrade",
                "language_code": "en",
                "body_text": "Amazing news {{param1}}! 🚀\n\nYou've been upgraded to *{{param4}} TIER*! 👑\n\n✨ You earned {{param2}} points\n⭐ Total Points: {{param3}}\n🎁 Enjoy enhanced benefits and bigger discounts!\n\nThank you for being a valued customer! 💎",
                "is_active": True,
                "is_approved": True
            },
            {
                "name": "Feedback Request",
                "notification_type": NotificationType.FEEDBACK_REQUEST,
                "template_name": "feedback_request",
                "language_code": "en",
                "body_text": "Hi {{param1}}! 📝\n\nWe hope you're happy with your order {{param2}}!\n\n⭐ Please rate our service and share your feedback\n💬 Your opinion helps us serve you better\n\nThank you for choosing LaundryPro! 🙏",
                "is_active": True,
                "is_approved": True
            },
            {
                "name": "Promotional Offer",
                "notification_type": NotificationType.PROMOTIONAL,
                "template_name": "promotional_offer",
                "language_code": "en",
                "body_text": "🎊 Special Offer for {{param1}}!\n\n🔥 Get {{param2}}% OFF on your next order\n⏰ Valid until {{param3}}\n\nUse code: *{{param4}}*\n\nDon't miss out - book your order now! 📱",
                "is_active": True,
                "is_approved": True
            }
        ]

        for template_data in default_templates:
            template = MessageTemplate(**template_data)
            db.add(template)

        db.commit()
        logger.info("Default message templates created")
