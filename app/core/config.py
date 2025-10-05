from pydantic_settings import BaseSettings
from typing import List, Optional
import os


class Settings(BaseSettings):
    # Application
    app_name: str = "LaundryPro API"
    app_version: str = "1.0.0"
    debug: bool = True
    environment: str = "development"

    # Database
    database_url: str = f"postgresql+psycopg2://{os.getenv('PGUSER')}:{os.getenv('PGPASSWORD')}@{os.getenv('PGHOST')}:{os.getenv('PGPORT', '5432')}/{os.getenv('PGDATABASE')}?sslmode=require"
    database_url_test: Optional[str] = None

    # Security
    secret_key: str ="jkbjjkbjhvvhvhjvhv"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # CORS
    allowed_origins: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "https://same-aej9qkmhge0-latest.netlify.app"
    ]

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Email
    smtp_host: Optional[str] = None
    smtp_port: Optional[int] = None
    smtp_user: Optional[str] = None
    smtp_password: Optional[str] = None
    email_from: Optional[str] = None

    # File Upload
    max_file_size_mb: int = 10
    upload_folder: str = "uploads"

    # WhatsApp Business API
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


# Global settings instance
settings = Settings()

# Ensure upload directory exists
os.makedirs(settings.upload_folder, exist_ok=True)
