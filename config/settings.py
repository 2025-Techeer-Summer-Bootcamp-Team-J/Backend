# config/settings.py
from pydantic_settings import BaseSettings
import os

class Settings(BaseSettings):
    # 로컬 개발환경용 기본 설정 (Docker에서는 .env로 오버라이드)
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/1"

    class Config:
        # .env 파일이 있다면 해당 파일에서 환경 변수를 읽어옴
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "allow"  # 추가적인 환경 변수들을 허용

# 설정 객체 인스턴스 생성
settings = Settings()