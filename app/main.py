from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.utils import get_openapi
import time
import logging
from contextlib import asynccontextmanager

from app.core.config import settings
from app.core.database import create_tables
from app.api.v1.api import api_router
from app.core.logging_config import setup_logging

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    logger.info("Starting LaundryPro API...")
    create_tables()
    logger.info("Database tables created/verified")

    # Initialize default data if needed
    from app.utils.init_data import initialize_default_data
    initialize_default_data()

    yield

    # Shutdown
    logger.info("Shutting down LaundryPro API...")


# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="A comprehensive laundry service management API with loyalty program",
    openapi_url="/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    allow_headers=["*"],
)

# Trusted host middleware (security)
if settings.environment == "production":
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["*.herokuapp.com", "*.netlify.app", "localhost"]
    )


# Request timing middleware
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)

    # Log slow requests
    if process_time > 1.0:
        logger.warning(f"Slow request: {request.method} {request.url} took {process_time:.2f}s")

    return response


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Global exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error" if settings.environment == "production" else str(exc),
            "type": "internal_error"
        }
    )


# Include API router
app.include_router(api_router)

# Serve static files (for uploaded files)
app.mount("/static", StaticFiles(directory=settings.upload_folder), name="static")


# Root endpoint
@app.get("/")
async def root():
    return {
        "message": f"Welcome to {settings.app_name}",
        "version": settings.app_version,
        "environment": settings.environment,
        "docs_url": "/api/docs",
        "status": "healthy"
    }


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring"""
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "version": settings.app_version,
        "environment": settings.environment
    }


# API Info endpoint
@app.get("/api/v1/info")
async def api_info():
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
        "features": [
            "User Authentication (JWT)",
            "Role-based Access Control",
            "Customer Management",
            "Order Management",
            "Loyalty Program",
            "Worker Management",
            "Analytics Dashboard",
            "Order Tracking",
            "File Upload Support"
        ],
        "endpoints": {
            "authentication": "/api/v1/auth",
            "users": "/api/v1/users",
            "customers": "/api/v1/customers",
            "orders": "/api/v1/orders",
            "workers": "/api/v1/workers",
            "services": "/api/v1/services",
            "loyalty": "/api/v1/loyalty",
            "analytics": "/api/v1/analytics"
        }
    }
