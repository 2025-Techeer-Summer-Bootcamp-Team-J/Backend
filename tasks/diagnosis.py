
from config.celery import app
import logging
import base64
from schema.diagnosis import SimplifiedDiagnosisResponse, aggregate_and_normalize_diagnoses
from services.local_diagnosis import run_onnx_inference
import traceback

logger = logging.getLogger(__name__)

@app.task(name='tasks.diagnosis.process_diagnosis')
def process_diagnosis_task(user_id: str, image_base64: str):
    """
    비동기 진단 처리 태스크
    """
    try:
        logger.info(f"Starting diagnosis task for user: {user_id}")
        
        image_data = base64.b64decode(image_base64)
        logger.info("Image decoded successfully.")
        
        predictions = run_onnx_inference(image_data)
        logger.info(f"Inference result: {predictions}")
        
        if not predictions:
             logger.warning("Inference returned no predictions.")

        simplified_data = aggregate_and_normalize_diagnoses(predictions, image_base64)
        simplified_data_dict = [data.model_dump() for data in simplified_data]
        
        response = {
            "code": 200,
            "message": "진단정보 생성 성공",
            "data": simplified_data_dict,
            "image_base64": image_base64
        }
        logger.info("Task completed successfully.")
        return response
            
    except Exception as e:
        logger.error(f"Error during diagnosis task: {e}")
        logger.error(traceback.format_exc()) # This will give us the full traceback
        return {
            "code": 500,
            "message": f"진단 처리 중 오류가 발생했습니다: {str(e)}",
            "data": []
        }
