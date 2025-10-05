from fastapi import APIRouter
from app.api.v1.endpoints import auth, notifications

api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(notifications.router, prefix="/notifications", tags=["Notifications"])

# Placeholder for other routers that will be created
# api_router.include_router(users.router, prefix="/users", tags=["Users"])
# api_router.include_router(customers.router, prefix="/customers", tags=["Customers"])
# api_router.include_router(orders.router, prefix="/orders", tags=["Orders"])
# api_router.include_router(workers.router, prefix="/workers", tags=["Workers"])
# api_router.include_router(services.router, prefix="/services", tags=["Services"])
# api_router.include_router(loyalty.router, prefix="/loyalty", tags=["Loyalty"])
# api_router.include_router(analytics.router, prefix="/analytics", tags=["Analytics"])
