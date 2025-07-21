from config.celery import app
import logging
from database.database import SessionLocal
from PIL import Image
import base64
import io
from schema.diagnosis import DiagnosisResponse, box_to_schema, SimplifiedDiagnosisResponse, aggregate_and_normalize_diagnoses
import tempfile
import shutil
import os
from inference_sdk import InferenceHTTPClient

logger = logging.getLogger(__name__)

@app.task(name='tasks.diagnosis.process_diagnosis')
def process_diagnosis_task(user_id: int, image_base64: str):
    """
    비동기 진단 처리 태스크
    """
    try:
        # Base64를 이미지 파일로 변환
        image_data = base64.b64decode(image_base64)
        
        # 임시 파일로 저장
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
            tmp.write(image_data)
            tmp_path = tmp.name

        # Roboflow inference API 호출
        client = InferenceHTTPClient(
            api_url="https://serverless.roboflow.com",
            api_key=os.environ.get("ROBOFLOW_API_KEY")
        )
        result = client.run_workflow(
            workspace_name="skin-classification-tm1gk",
            workflow_id="detect-and-classify",
            images={"image": tmp_path},
            use_cache=True
        )

        # 임시 파일 삭제
        os.remove(tmp_path)

        # Roboflow 결과 파싱
        predictions = []
        if isinstance(result, list) and len(result) > 0:
            result = result[0]
        if isinstance(result, dict):
            output = result.get('output', {})
            predictions_dict = output.get('predictions', {})
            predictions = predictions_dict.get('predictions', [])

        # 간소화된 응답 생성
        simplified_data = aggregate_and_normalize_diagnoses(predictions, image_base64)
        
        # Pydantic 모델을 딕셔너리로 변환하여 JSON 직렬화 가능하게 만듦
        simplified_data_dict = [data.model_dump() for data in simplified_data]
        
        # SimplifiedDiagnosisResponse 형태로 반환
        return {
            "code": 200,
            "message": "진단정보 생성 성공",
            "data": simplified_data_dict
        }
            
    except Exception as e:
        logger.error(f"진단 처리 중 오류: {e}")
        return {
            "code": 500,
            "message": f"진단 처리 중 오류가 발생했습니다: {str(e)}",
            "data": []
        }
   
