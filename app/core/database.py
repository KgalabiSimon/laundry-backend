from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool, StaticPool
from app.core.config import settings

# ------------------
# Database connection testing
# ------------------
def test_database_connection(url: str) -> tuple[bool, str]:
    """Test database connection and return status and message."""
    try:
        # Create a test engine without pooling
        test_engine = create_engine(url, poolclass=None)
        with test_engine.connect() as conn:
            conn.execute("SELECT 1")  # Simple test query
        return True, "Database connection successful"
    except Exception as e:
        return False, f"Database connection failed: {str(e)}"

# ------------------
# Database engine setup with connection testing
# ------------------
def setup_database_engine():
    """Setup database engine with connection testing and proper error handling."""
    if settings.environment == "test":
        # Use in-memory SQLite for testing
        return create_engine(
            "sqlite:///./test.db",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
    
    # Get database URL for production/development
    db_url = settings.get_connection_uri()
    if not db_url:
        raise ValueError("Database URL is not configured")

    # Test the connection before setting up the engine
    is_connected, message = test_database_connection(db_url)
    print(f"Database Connection Status: {message}")
    
    if not is_connected and settings.environment == "production":
        raise ConnectionError(f"Production database connection failed: {message}")
    
    # Create the engine with production-ready settings
    return create_engine(
        db_url,
        poolclass=QueuePool,
        pool_pre_ping=True,         # Verify connections before using
        pool_size=5,                # Start with 5 connections
        max_overflow=10,            # Allow up to 10 additional connections
        pool_recycle=1800,          # Recycle connections every 30 minutes
        pool_timeout=30,            # Wait up to 30 seconds for a connection
        pool_use_lifo=True,         # Last In First Out for better performance
        echo_pool=True             # Log pool events for monitoring
    )

# Initialize the engine
try:
    engine = setup_database_engine()
except Exception as e:
    print(f"Failed to initialize database engine: {e}")
    if settings.environment == "production":
        raise  # Re-raise in production
    # In development, fall back to SQLite
    print("Falling back to SQLite for development...")
    engine = create_engine(
        "sqlite:///./fallback.db",
        connect_args={"check_same_thread": False},
    )

# ------------------
# Session and Base
# ------------------
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# ------------------
# Dependency to get DB session with connection testing
# ------------------
def get_db():
    """Get database session with connection testing and error handling."""
    db = SessionLocal()
    try:
        # Test the connection before yielding
        db.execute("SELECT 1")
        yield db
    except Exception as e:
        print(f"Database session error: {e}")
        db.rollback()  # Rollback any pending transactions
        raise
    finally:
        db.close()

# ------------------
# Helpers for table management
# ------------------
def create_tables():
    """Create database tables with connection verification."""
    try:
        # Test connection before creating tables
        with engine.connect() as conn:
            conn.execute("SELECT 1")
        
        Base.metadata.create_all(bind=engine)
        print("Database tables created successfully")
    except Exception as e:
        print(f"Error creating database tables: {e}")
        if settings.environment == "production":
            raise  # Re-raise in production
        print("Failed to create tables - check database connection")

def drop_tables():
    Base.metadata.drop_all(bind=engine)

# ------------------
# Optional: Test connection
# ------------------
def test_connection():
    try:
        with engine.connect() as conn:
            print(f"✅ Database connection successful: {conn.engine.url}")
    except Exception as e:
        print(f"❌ Database connection failed: {e}")

# Uncomment to test connection on startup
# test_connection()
