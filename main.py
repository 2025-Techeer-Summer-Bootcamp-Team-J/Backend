from fastapi import FastAPI
from api.router import api_router
from prometheus_fastapi_instrumentator import Instrumentator

#서버가 실행되는 메인 공간

# YOLOv8 skin disease detection 추가 import
from fastapi.responses import JSONResponse
from PIL import Image
from ultralytics import YOLO
import io

# 모든 모델들을 import하여 순환참조 문제 해결
from models import *  # 이렇게 하면 models/__init__.py에서 정의한 순서대로 모든 모델이 로드됩니다
from database.database import engine, Base

# models에 있는 객체들을 자동으로 db에 생성
Base.metadata.create_all(bind=engine)

# 서버 실행
app = FastAPI()
# post/router/post_router.py에서 main으로 라우팅
# tags를 작성하면 docs에서 tag별로 분류되어 보기 편함
app.include_router(api_router)

# AI 모델 로드
app.state.model = YOLO("weights.pt")

# root url get 메서드
@app.get("/")
def read_root():
    return {"message": "Hello, World!"}

# Prometheus 메트릭을 위한 설정
Instrumentator().instrument(app).expose(app)
