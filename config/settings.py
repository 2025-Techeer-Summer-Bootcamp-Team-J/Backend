# config/settings.py
from pydantic_settings import BaseSettings
import os

class Settings(BaseSettings):
    # Local development environment default settings (overridden by .env in Docker)
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/1"
    GEMINI_API_KEY: str = "" # Gemini API Key

    class Config:
        # If .env file exists, read environment variables from it
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "allow"  # Allow additional environment variables

# 설정 객체 인스턴스 생성
settings = Settings()