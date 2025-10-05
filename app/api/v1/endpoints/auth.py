from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

from app.core.database import get_db
from app.core.auth import auth_handler, authenticate_user, get_current_user
from app.models import User, UserRole, Customer, Worker
from app.schemas.user import (
    UserLogin, UserCreate, TokenResponse, RefreshTokenRequest,
    PasswordChange, PasswordReset, UserResponse
)
from app.schemas.customer import CustomerCreate

router = APIRouter()
security = HTTPBearer()


@router.post("/login", response_model=TokenResponse)
async def login(
    user_credentials: UserLogin,
    db: Session = Depends(get_db)
):
    """Authenticate user and return JWT tokens"""
    user = authenticate_user(db, user_credentials.email, user_credentials.password)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User account is disabled"
        )

    # Check role if specified
    if user_credentials.role and user.role != user_credentials.role:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"User does not have {user_credentials.role.value} role"
        )

    # Update last login time
    user.last_login_at = datetime.utcnow()
    db.commit()

    # Create tokens
    access_token = auth_handler.create_access_token(data={"sub": str(user.id)})
    refresh_token = auth_handler.create_refresh_token(data={"sub": str(user.id)})

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=auth_handler.access_token_expire_minutes * 60,
        user=UserResponse.from_orm(user)
    )


@router.post("/register", response_model=UserResponse)
async def register(
    user_data: UserCreate,
    db: Session = Depends(get_db)
):
    """Register a new user"""
    # Check if user already exists
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # Hash password
    hashed_password = auth_handler.hash_password(user_data.password)

    # Create user
    db_user = User(
        email=user_data.email,
        name=user_data.name,
        phone=user_data.phone,
        hashed_password=hashed_password,
        role=user_data.role,
        is_active=True,
        is_verified=False
    )

    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    # Create customer profile if role is customer
    if user_data.role == UserRole.CUSTOMER:
        customer_profile = Customer(
            user_id=db_user.id,
            loyalty_points=0,
            total_spent=0,
            total_orders=0
        )
        db.add(customer_profile)
        db.commit()

    return UserResponse.from_orm(db_user)


@router.post("/register/customer", response_model=UserResponse)
async def register_customer(
    customer_data: CustomerCreate,
    db: Session = Depends(get_db)
):
    """Register a new customer with profile"""
    # Check if user already exists
    existing_user = db.query(User).filter(User.email == customer_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # Hash password
    hashed_password = auth_handler.hash_password(customer_data.password)

    # Create user
    db_user = User(
        email=customer_data.email,
        name=customer_data.name,
        phone=customer_data.phone,
        hashed_password=hashed_password,
        role=UserRole.CUSTOMER,
        is_active=True,
        is_verified=False
    )

    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    # Create customer profile
    customer_profile = Customer(
        user_id=db_user.id,
        address=customer_data.address,
        subscription_plan=customer_data.subscription_plan,
        loyalty_points=0,
        total_spent=0,
        total_orders=0
    )
    db.add(customer_profile)
    db.commit()

    return UserResponse.from_orm(db_user)


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    refresh_data: RefreshTokenRequest,
    db: Session = Depends(get_db)
):
    """Refresh access token using refresh token"""
    try:
        payload = auth_handler.decode_token(refresh_data.refresh_token)

        # Check if it's a refresh token
        if payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type"
            )

        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )

        user = db.query(User).filter(User.id == user_id).first()
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive"
            )

        # Create new tokens
        access_token = auth_handler.create_access_token(data={"sub": str(user.id)})
        refresh_token = auth_handler.create_refresh_token(data={"sub": str(user.id)})

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=auth_handler.access_token_expire_minutes * 60,
            user=UserResponse.from_orm(user)
        )

    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """Get current user information"""
    return UserResponse.from_orm(current_user)


@router.post("/change-password")
async def change_password(
    password_data: PasswordChange,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Change user password"""
    # Verify current password
    if not auth_handler.verify_password(password_data.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect current password"
        )

    # Hash new password
    new_hashed_password = auth_handler.hash_password(password_data.new_password)

    # Update password
    current_user.hashed_password = new_hashed_password
    db.commit()

    return {"message": "Password changed successfully"}


@router.post("/logout")
async def logout(
    current_user: User = Depends(get_current_user)
):
    """Logout user (client should discard tokens)"""
    return {"message": "Successfully logged out"}


@router.post("/reset-password")
async def reset_password(
    reset_data: PasswordReset,
    db: Session = Depends(get_db)
):
    """Request password reset (would typically send email)"""
    user = db.query(User).filter(User.email == reset_data.email).first()

    # Always return success for security (don't reveal if email exists)
    return {"message": "If the email exists, a reset link has been sent"}


# Admin endpoint to create worker accounts
@router.post("/register/worker", response_model=UserResponse)
async def register_worker(
    user_data: UserCreate,
    employee_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Register a new worker (admin only)"""
    # Check admin permission
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can create worker accounts"
        )

    # Check if user already exists
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # Check if employee ID is unique
    existing_worker = db.query(Worker).filter(Worker.employee_id == employee_id).first()
    if existing_worker:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Employee ID already exists"
        )

    # Hash password
    hashed_password = auth_handler.hash_password(user_data.password)

    # Create user
    db_user = User(
        email=user_data.email,
        name=user_data.name,
        phone=user_data.phone,
        hashed_password=hashed_password,
        role=UserRole.WORKER,
        is_active=True,
        is_verified=True
    )

    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    # Create worker profile
    worker_profile = Worker(
        user_id=db_user.id,
        employee_id=employee_id,
        created_by_id=current_user.id,
        total_orders_processed=0
    )
    db.add(worker_profile)
    db.commit()

    return UserResponse.from_orm(db_user)
