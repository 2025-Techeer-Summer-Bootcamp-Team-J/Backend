from fastapi import FastAPI, File, UploadFile, APIRouter, Depends, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from database.database import engine
from api.router import api_router
from prometheus_fastapi_instrumentator import Instrumentator
import os
import logging
#서버가 실행되는 메인 공간

# YOLOv8 skin disease detection 추가 import
from fastapi.responses import JSONResponse


# 로깅 설정 /app/logs/app.log 파일에 로깅

# 해당 경로가 없으면 자동으로 생성
os.makedirs("/app/logs", exist_ok=True)

logging.basicConfig(
    level=logging.INFO,  # DEBUG에서 INFO로 다시 변경
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.FileHandler("/app/logs/app.log"),
        logging.StreamHandler()
    ]
)

# Uvicorn access/error 로그도 파일로 남기기
uvicorn_access_logger = logging.getLogger("uvicorn.access")
uvicorn_error_logger = logging.getLogger("uvicorn.error")

file_handler = logging.FileHandler("/app/logs/app.log")
file_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))

uvicorn_access_logger.addHandler(file_handler)
uvicorn_error_logger.addHandler(file_handler)

# 필요하다면 중복 방지
uvicorn_access_logger.propagate = False
uvicorn_error_logger.propagate = False

# 모든 모델들을 import하여 순환참조 문제 해결
from models import *  # 이렇게 하면 models/__init__.py에서 정의한 순서대로 모든 모델이 로드됩니다
from database.database import engine, Base


# models에 있는 객체들을 자동으로 db에 생성
Base.metadata.create_all(bind=engine)

# 서버 실행
app = FastAPI()

# CORS 미들웨어 설정 - 프론트엔드에서 백엔드로 요청 허용
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 개발환경용 - 운영시에는 구체적인 도메인 지정
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# post/router/post_router.py에서 main으로 라우팅
# tags를 작성하면 docs에서 tag별로 분류되어 보기 편함
app.include_router(api_router)



# root url get 메서드
@app.get("/")
def read_root():
    return {"message": "Hello, World!"}

# Health check 엔드포인트 추가
@app.get("/health")
def health_check():
    return {"status": "healthy", "message": "Service is running"}

# Prometheus 메트릭을 위한 설정
Instrumentator().instrument(app).expose(app)

logging.info("FastAPI 서버가 시작됩니다!")
