import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://manual_user:manual_password@db:5432/manual_db")
    GEMINI_API_KEY: str = ""
    SECRET_KEY: str = ""
    MEDIA_DIR: str = os.getenv("MEDIA_DIR", "/app/media")
    CORS_ORIGINS: str = os.getenv("CORS_ORIGINS", "")

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()

