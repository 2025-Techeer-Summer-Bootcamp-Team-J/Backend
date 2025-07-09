from fastapi import FastAPI, File, UploadFile
from database.database import engine
from api.router import api_router
from prometheus_fastapi_instrumentator import Instrumentator


# YOLOv8 skin disease detection 추가 import
from fastapi.responses import JSONResponse
from PIL import Image
from ultralytics import YOLO
import io

#서버가 실행되는 메인 공간

# models에 있는 객체들을 자동으로 db에 생성
#post.Base.metadata.create_all(bind=engine)

# 서버 실행
app = FastAPI()
# post/router/post_router.py에서 main으로 라우팅
# tags를 작성하면 docs에서 tag별로 분류되어 보기 편함
app.include_router(api_router)

yolo_model = YOLO("weights.pt")
CLASS_NAMES = ["Melanoma", "Psoriasis", "Seborrheic Keratoses", "Warts-Molluscum"]

# root url get 메서드
@app.get("/")
def read_root():
    return {"message": "Hello, World!"}

# Prometheus 메트릭을 위한 설정
Instrumentator().instrument(app).expose(app)
"""
# 피부 질병 탐지 엔드포인트, 테스트용 코드
@app.post("/predict")
async def predict(file: UploadFile = File(...)):
    image_bytes = await file.read()
    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    results = yolo_model(image)
    detections = results[0].boxes
    output = []
    for box in detections:
        cls_id = int(box.cls[0])
        label = CLASS_NAMES[cls_id]
        confidence = float(box.conf[0])
        bbox = [float(x) for x in box.xyxy[0].tolist()]
        output.append({
            "disease": label,
            "bbox": bbox,
            "confidence": confidence
        })
    return JSONResponse(content={"results": output})
 """
