from config.celery import app
import logging
from models.diagnosis import Diagnosis
from database.database import SessionLocal
from PIL import Image
import base64
import io
from schema.diagnosis import DiagnosisResponse, box_to_schema, boxes_to_diagnosis_objs
from ultralytics import YOLO

logger = logging.getLogger(__name__)

@app.task(name='tasks.diagnosis.process_diagnosis')
def process_diagnosis_task(user_id: int, image_base64: str):
    """
    진단 처리를 위한 Celery 태스크
    """
    try:
        # DB 세션 생성
        db = SessionLocal()
        
        # 모델 로드
        model = YOLO("weights.pt")
        
        # Base64를 PIL Image로 변환
        image_data = base64.b64decode(image_base64)
        pil_image = Image.open(io.BytesIO(image_data))
        
        # 모델 예측
        results = model.predict(pil_image)
        result = results[0]
        
        # 진단 객체 생성
        diagnosis_objs = boxes_to_diagnosis_objs(result, user_id)
        saved_diagnoses = []
        
        for db_diagnosis in diagnosis_objs:
            db.add(db_diagnosis)
            db.commit()
            db.refresh(db_diagnosis)
            saved_diagnoses.append(db_diagnosis)

        # 응답 데이터 생성
        response_data = DiagnosisResponse(
            code=200,
            message="진단정보 생성 성공",
            data=[box_to_schema(d) for d in saved_diagnoses]
        )
        
        return response_data.dict()
        
    except Exception as e:
        logger.error(f"진단 태스크 실행 중 오류: {str(e)}")
        # DiagnosisResponse 형태가 아닌 실패 정보 반환
        raise Exception(f"진단 처리 중 오류가 발생했습니다: {str(e)}")
    finally:
        # DB 세션 정리
        if 'db' in locals():
            db.close()