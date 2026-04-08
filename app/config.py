from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "StayEase API"
    app_env: str = "development"
    debug: bool = True
    api_prefix: str = "/api/v1"
    database_url: str = Field(
        default="postgresql+asyncpg://postgres:Kiran$1234@localhost:5432/stayease"
    )
    redis_url: str = "redis://localhost:6379/0"
    secret_key: str = "change-me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    refresh_token_expire_days: int = 30
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:5174", "http://localhost:3000"]

    # httpOnly refresh cookie settings
    refresh_cookie_name: str = "refresh_token"
    refresh_cookie_samesite: str = "lax"  # "lax" works well for same-site React apps
    refresh_cookie_path: str = "/"
    razorpay_key_id: str = ""
    razorpay_key_secret: str = ""
    razorpay_webhook_secret: str = ""
    otp_expiry_minutes: int = 10
    otp_max_attempts: int = 5
    
    # Email Configuration
    smtp_host: str = Field(default="smtp.gmail.com", description="SMTP server host")
    smtp_port: int = Field(default=587, description="SMTP server port")
    smtp_user: str = Field(default="", description="SMTP username")
    smtp_password: str = Field(default="", description="SMTP password")
    email_from: str = Field(default="noreply@stayease.com", description="From email address")
    
    # AWS S3 Configuration
    aws_access_key_id: str = Field(default="", description="AWS access key ID")
    aws_secret_access_key: str = Field(default="", description="AWS secret access key")
    aws_storage_bucket_name: str = Field(default="stayease-uploads", description="S3 bucket name")
    aws_region: str = Field(default="ap-south-1", description="AWS region")

    @field_validator("debug", mode="before")
    @classmethod
    def parse_debug_value(cls, value: object) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"1", "true", "yes", "on", "debug", "development"}:
                return True
            if normalized in {"0", "false", "no", "off", "release", "production"}:
                return False
        return bool(value)


@lru_cache
def get_settings() -> Settings:
    return Settings()
