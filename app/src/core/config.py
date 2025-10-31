from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    PROJECT_NAME: str = "Klyne"
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5433/klyne"
    SECRET_KEY: str = "your-secret-key-change-in-production"
    RESEND_API_KEY: str = ""
    APP_DOMAIN: str = "http://localhost:8000"
    ENVIRONMENT: str = "development"

    # Polar Settings
    POLAR_ACCESS_TOKEN: str = ""
    POLAR_WEBHOOK_SECRET: str = ""
    POLAR_STARTER_MONTHLY_PRODUCT_ID: str = ""
    POLAR_STARTER_YEARLY_PRODUCT_ID: str = ""
    POLAR_PRO_MONTHLY_PRODUCT_ID: str = ""
    POLAR_PRO_YEARLY_PRODUCT_ID: str = ""
    POLAR_ENVIRONMENT: str = ""

    # Scheduler Settings
    POLAR_SYNC_ENABLED: bool = True
    POLAR_SYNC_HOUR: int = 2  # UTC hour (2 AM UTC by default)
    POLAR_SYNC_MINUTE: int = 0  # Minute within the hour
    
    # Free Plan Settings
    FREE_PLAN_DATA_RETENTION_DAYS: int = 7
    FREE_PLAN_RATE_LIMIT_PER_HOUR: int = 100
    PAID_PLAN_RATE_LIMIT_PER_HOUR: int = 1000
    DATA_CLEANUP_HOUR: int = 3  # UTC hour for daily cleanup (3 AM UTC)
    DATA_CLEANUP_MINUTE: int = 0

    CF_TURNSTILE_SECRET: str = ""
    CF_TURNSTILE_SITE_KEY: str = "1x00000000000000000000AA"

    LOGFIRE_TOKEN: str = ""
    SENTRY_DSN: str = ""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Validate that required secrets are set in production
        if self.ENVIRONMENT == "production":
            if self.SECRET_KEY == "your-secret-key-change-in-production":
                raise ValueError(
                    "SECRET_KEY must be set in production environment. "
                    "Generate one with: python -c 'import secrets; print(secrets.token_urlsafe(32))'"
                )

    class Config:
        case_sensitive = True
        env_file = ".env"


settings = Settings()
