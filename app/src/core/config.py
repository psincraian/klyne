from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    PROJECT_NAME: str = "Klyne"
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost/klyne"
    
    class Config:
        case_sensitive = True
        env_file = ".env"


settings = Settings()