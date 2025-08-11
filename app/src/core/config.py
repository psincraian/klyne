from pydantic_settings import BaseSettings
import secrets


class Settings(BaseSettings):
    PROJECT_NAME: str = "Klyne"
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5433/klyne"
    SECRET_KEY: str = "your-secret-key-change-in-production"
    RESEND_API_KEY: str = ""
    APP_DOMAIN: str = "http://localhost:8000"
    ENVIRONMENT: str = "development"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Generate a secure secret key if using the default in production
        if (self.ENVIRONMENT == "production" and 
            self.SECRET_KEY == "your-secret-key-change-in-production"):
            self.SECRET_KEY = secrets.token_urlsafe(32)

    class Config:
        case_sensitive = True
        env_file = ".env"


settings = Settings()
