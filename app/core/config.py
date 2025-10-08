from pydantic_settings import BaseSettings
from typing import List, Optional
import urllib.parse
import os

import urllib.parse

def get_azure_connection_uri():
    """Get Azure PostgreSQL connection URI from environment variables"""
    try:
        dbhost = os.environ.get('DBHOST', 'laundry-postpresql-db.postgres.database.azure.com')
        dbname = os.environ.get('DBNAME', 'postgres')
        dbuser = urllib.parse.quote(os.environ.get('DBUSER', 'azureuser'))
        dbpassword = os.environ.get('DBPASSWORD', '')
        sslmode = os.environ.get('SSLMODE', 'require')
        
        return f"postgresql://{dbuser}:{dbpassword}@{dbhost}:5432/{dbname}?sslmode={sslmode}"
    except Exception as e:
        print(f"Error constructing Azure connection URI: {e}")
        return None

class Settings(BaseSettings):
    # ------------------
    # Application
    # ------------------
    app_name: str = "LaundryPro API"
    app_version: str = "1.0.0"
    debug: bool = True
    environment: str = "development"  # dev / test / prod
    
    # Database Configuration
    database_url: str = None  # Will be set in get_database_url method
    
    def get_database_url(self) -> str:
        """Get database URL based on environment"""
        if self.environment == "production":
            # Use Azure PostgreSQL in production
            azure_url = get_azure_connection_uri()
            if azure_url:
                return azure_url
                
        # Fallback to local development database
        return "postgresql://laundry_user_2:2354@localhost:5432/laundry_db"

    # ------------------
    # Security
    # ------------------
    secret_key: str = "CHANGE_ME_IN_PROD"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # ------------------
    # CORS
    # ------------------
    allowed_origins: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "https://same-aej9qkmhge0-latest.netlify.app"
    ]

    # ------------------
    # Redis
    # ------------------
    redis_url: str = "redis://localhost:6379/0"

    # ------------------
    # Email
    # ------------------
    smtp_host: Optional[str] = None
    smtp_port: Optional[int] = None
    smtp_user: Optional[str] = None
    smtp_password: Optional[str] = None
    email_from: Optional[str] = None

    # ------------------
    # File Upload
    # ------------------
    max_file_size_mb: int = 10
    upload_folder: str = "uploads"

    # ------------------
    # WhatsApp Business API
    # ------------------
    whatsapp_api_url: str = "https://graph.facebook.com/v18.0"
    whatsapp_access_token: Optional[str] = None
    whatsapp_phone_number_id: Optional[str] = None
    whatsapp_business_account_id: Optional[str] = None
    whatsapp_webhook_verify_token: Optional[str] = None
    whatsapp_app_secret: Optional[str] = None
    whatsapp_enabled: bool = False

    class Config:
        env_file = ".env"
        case_sensitive = False

        @classmethod
        def parse_env_var(cls, field_name: str, raw_val: str) -> any:
            if field_name == 'allowed_origins':
                return [x.strip() for x in raw_val.split(',')]
            return cls.json_loads(raw_val)

    # ------------------
    # Database URI (Azure/Postgres-ready)
    # ------------------
    def get_connection_uri(self) -> str:
        """
        Returns a PostgreSQL connection URI.
        Priority:
        1. Use DATABASE_URL (common in cloud services like Azure)
        2. Fallback to individual environment variables
        """
        db_url = os.environ.get("DATABASE_URL")
        if db_url:
            # Ensure SSL is enforced for cloud Postgres
            if "?sslmode=" not in db_url.lower():
                db_url += "?sslmode=require"
            return db_url

        # Fallback: construct from individual env variables
        try:
            dbhost = os.environ['DBHOST']
            dbname = os.environ['DBNAME']
            dbuser = urllib.parse.quote(os.environ['DBUSER'])
            password = os.environ['DBPASSWORD']
            sslmode = os.environ.get('SSLMODE', 'require')
        except KeyError as e:
            raise KeyError(f"Missing required environment variable: {e}")

        return f"postgresql://{dbuser}:{password}@{dbhost}/{dbname}?sslmode={sslmode}"


# ------------------
# Global settings instance
# ------------------
settings = Settings()

# Ensure upload folder exists
os.makedirs(settings.upload_folder, exist_ok=True)
