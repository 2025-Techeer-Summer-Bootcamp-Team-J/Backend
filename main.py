from fastapi import FastAPI, File, UploadFile, APIRouter, Depends, File, UploadFile, Form
import models.post as post
from database.database import engine
from api.router import api_router
from api.endpoints.diagnosis import router as diagnosis_router
from prometheus_fastapi_instrumentator import Instrumentator

#서버가 실행되는 메인 공간

# YOLOv8 skin disease detection 추가 import
from fastapi.responses import JSONResponse
from PIL import Image
from ultralytics import YOLO
import io


# models에 있는 객체들을 자동으로 db에 생성
post.Base.metadata.create_all(bind=engine)

# 서버 실행
app = FastAPI()
# post/router/post_router.py에서 main으로 라우팅
# tags를 작성하면 docs에서 tag별로 분류되어 보기 편함
app.include_router(api_router)
# AI 모델 로드
app.state.model = YOLO("weights2.pt")

# diagnosis 라우터 등록
app.include_router(diagnosis_router)

# root url get 메서드
@app.get("/")
def read_root():
    return {"message": "Hello, World!"}

# Prometheus 메트릭을 위한 설정
Instrumentator().instrument(app).expose(app)
