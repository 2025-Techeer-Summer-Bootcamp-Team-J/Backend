from config.celery import app
import logging
from models.diagnosis import Diagnosis
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

def simplified_data_to_diagnosis_obj(simplified_data_list, user_id, image_base64):
    """
    간소화된 진단 데이터를 기반으로 DB 객체 생성
    하나의 진단 세션에 대해 하나의 diagnosis 레코드를 생성하고 여러 disease들을 연결
    """
    from models.diseases import Disease
    
    if not simplified_data_list:
        return None
    
    # 가장 높은 confidence 값을 confidence에 저장
    max_confidence = max(data.confidence for data in simplified_data_list)
    
    # Diagnosis 객체 생성
    diagnosis = Diagnosis(
        user_id=user_id,
        confidence=int(max_confidence),  # 가장 높은 confidence를 confidence에 저장
        image=image_base64
    )
    
    return diagnosis, simplified_data_list

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
        
        # DB 저장 - 간소화된 데이터를 기준으로 저장
        db = SessionLocal()
        try:
            if simplified_data:
                # 하나의 diagnosis 레코드 생성
                diagnosis, disease_data_list = simplified_data_to_diagnosis_obj(simplified_data, user_id, image_base64)
                
                if diagnosis:
                    db.add(diagnosis)
                    db.commit()
                    db.refresh(diagnosis)
                    
                    # 각 질환을 diagnosis와 연결
                    from models.diseases import Disease
                    for disease_data in disease_data_list:
                        # 질환이 DB에 존재하는지 확인
                        disease = db.query(Disease).filter(Disease.disease_name == disease_data.disease_name).first()
                        if disease:
                            # 이미 연결되어 있지 않다면 연결
                            if disease not in diagnosis.diseases:
                                diagnosis.diseases.append(disease)
                        else:
                            logger.warning(f"질환 '{disease_data.disease_name}'을 DB에서 찾을 수 없습니다.")
                    
                    # 질환 연결 정보 저장
                    db.commit()
                    
                    logger.info(f"진단 ID {diagnosis.diagnosis_id}로 {len(disease_data_list)}개 질환 저장 완료")
            
            return {
                "code": 200,
                "message": "진단정보 생성 성공",
                "data": [data.dict() for data in simplified_data]
            }
            
        except Exception as e:
            logger.error(f"DB 저장 중 오류: {e}")
            db.rollback()
            return {
                "code": 500,
                "message": f"DB 저장 중 오류가 발생했습니다: {str(e)}",
                "data": []
            }
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"진단 처리 중 오류: {e}")
        return {
            "code": 500,
            "message": f"진단 처리 중 오류가 발생했습니다: {str(e)}",
            "data": []
        }
   