from sqlalchemy import Column, Integer, String, DateTime, Enum, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base
import enum


class WorkerRole(str, enum.Enum):
    WORKER = "worker"
    SUPERVISOR = "supervisor"


class Worker(Base):
    __tablename__ = "workers"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)

    # Worker-specific information
    employee_id = Column(String, unique=True, nullable=False, index=True)
    worker_role = Column(Enum(WorkerRole), default=WorkerRole.WORKER)
    is_active = Column(Boolean, default=True)

    # Performance metrics
    total_orders_processed = Column(Integer, default=0)

    # Management
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="worker_profile", foreign_keys=[user_id])
    created_by = relationship("User", foreign_keys=[created_by_id])

    def __repr__(self):
        return f"<Worker(id={self.id}, employee_id='{self.employee_id}', role='{self.worker_role}')>"

    @property
    def name(self):
        return self.user.name if self.user else None

    @property
    def email(self):
        return self.user.email if self.user else None

    @property
    def phone(self):
        return self.user.phone if self.user else None
