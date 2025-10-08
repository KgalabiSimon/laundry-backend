from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool, StaticPool
from app.core.config import settings

# ------------------
# Database engine setup
# ------------------
if settings.environment == "test":
    # Use in-memory SQLite for testing
    engine = create_engine(
        "sqlite:///./test.db",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
else:
    # PostgreSQL for dev/prod (supports Azure DATABASE_URL)
    db_url = settings.get_connection_uri()
    engine = create_engine(
        db_url,
        poolclass=QueuePool,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
        pool_recycle=1800,
        pool_timeout=30,
    )

# ------------------
# Session and Base
# ------------------
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# ------------------
# Dependency to get DB session
# ------------------
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ------------------
# Helpers for table management
# ------------------
def create_tables():
    Base.metadata.create_all(bind=engine)

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
