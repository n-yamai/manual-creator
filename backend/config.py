import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str = ""
    GEMINI_API_KEY: str = ""
    SECRET_KEY: str = ""
    MEDIA_DIR: str = os.getenv("MEDIA_DIR", "/app/media")

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()

