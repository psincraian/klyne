from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    PROJECT_NAME: str = "Klyne"
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5433/klyne"
    SECRET_KEY: str = "your-secret-key-change-in-production"
    RESEND_API_KEY: str = ""
    APP_DOMAIN: str = "http://localhost:8000"

    class Config:
        case_sensitive = True
        env_file = ".env"


settings = Settings()
