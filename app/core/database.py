from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool, StaticPool
from app.core.config import settings

# Create database engine
if settings.environment == "test":
    # Use in-memory SQLite for testing
    engine = create_engine(
        "sqlite:///./test.db",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
else:
    # Use PostgreSQL for development/production with better connection handling
    db_url = settings.database_url
    if not db_url:
        raise ValueError("DATABASE_URL environment variable is not set")
    
    # Add SSL mode if not already in URL
    if 'sslmode=' not in db_url.lower():
        db_url += "?sslmode=require"
    
    engine = create_engine(
        db_url,
        poolclass=QueuePool,
        pool_pre_ping=True,  # Verify connections before using them
        pool_size=5,         # Smaller initial pool size for Azure
        max_overflow=10,     # Allow up to 15 total connections (pool_size + max_overflow)
        pool_recycle=1800,   # Recycle connections every 30 minutes
        pool_timeout=30,     # Wait up to 30 seconds for a connection
    )

# Create SessionLocal class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create Base class for models
Base = declarative_base()


# Dependency to get database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Create all tables
def create_tables():
    Base.metadata.create_all(bind=engine)


# Drop all tables (for testing)
def drop_tables():
    Base.metadata.drop_all(bind=engine)
