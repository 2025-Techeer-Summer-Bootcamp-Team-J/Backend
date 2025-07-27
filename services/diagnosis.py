from sqlalchemy.orm import Session
from models.diagnosis import Diagnosis
from fastapi import HTTPException
from models.diagnosis import Diagnosis as DiagnosisModel
from schema.diagnosis import DiagnosisData

import json
import base64
import logging
import asyncio
import re
from PIL import Image
import io
import google.generativeai as genai

# RAG 파이프라인
from services.rag import generate_disease_info
from dotenv import load_dotenv
import os
load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel("gemini-2.0-flash")

logger = logging.getLogger(__name__)

def delete_diagnosis(db: Session, user_id: str, diagnosis_id: int):
    diagnosis = db.query(Diagnosis).filter(Diagnosis.user_id == user_id, Diagnosis.diagnosis_id == diagnosis_id, Diagnosis.is_deleted == False).first()
    if not diagnosis:
        raise HTTPException(status_code=404, detail="진단 정보가 없습니다")

    # Soft delete: is_deleted를 True로 설정
    diagnosis.is_deleted = True
    db.commit()

    return diagnosis

def get_diagnosis_table(db: Session):
    diagnoses = db.query(Diagnosis).filter(Diagnosis.is_deleted == False).all()
    return [DiagnosisData.model_validate(diagnosis) for diagnosis in diagnoses]

def save_diagnosis_data(
    db: Session,
    user_id: str,
    image: str,
    image_analysis_data: dict,
    text_analysis_data: dict,
    disease_name: str = ""
) -> Diagnosis:
    """
    진단 결과 데이터를 데이터베이스에 저장합니다.
    """
    try:
        # disease_name 파라미터가 주어지지 않은 경우 text_analysis_data에서 추출하여 Fallback
        if not disease_name:
            disease_name = text_analysis_data.get("diagnosis_name", "")

        full_detailed_info = {
            "image_analysis": image_analysis_data,
            "text_analysis": text_analysis_data
        }
        

        diagnosis_data = Diagnosis(
            user_id=user_id,
            image=image,
            skinType_score=image_analysis_data.get("skin_score", 0),
            detailed_info_json=json.dumps(full_detailed_info, ensure_ascii=False),
            disease_name=disease_name
        )
        
        db.add(diagnosis_data)
        db.commit()
        db.refresh(diagnosis_data)
        
        logger.info(f"진단 데이터가 성공적으로 저장되었습니다. Diagnosis ID: {diagnosis_data.diagnosis_id}")
        return diagnosis_data

      
        
    except Exception as e:
        logger.error(f"데이터베이스 저장 중 오류: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"데이터베이스 저장 실패: {str(e)}")

def save_additional_info(
    db: Session, 
    user_id: str, 
    diagnosis_id: int, 
    main_symptoms: list, 
    itching_level: int = None,
    symptom_duration: str = None, 
    additional_notes: str = None
) -> Diagnosis:
    """
    진단의 보조 정보를 저장합니다.
    """
    try:
        # 해당 진단이 존재하고 사용자의 것인지 확인
        diagnosis = db.query(Diagnosis).filter(
            Diagnosis.diagnosis_id == diagnosis_id,
            Diagnosis.user_id == user_id,
            Diagnosis.is_deleted == False
        ).first()
        
        if not diagnosis:
            raise HTTPException(status_code=404, detail="진단 정보가 없습니다")
        
        # 보조 정보를 JSON 형태로 구성
        additional_info_data = {
            "main_symptoms": main_symptoms,
            "itching_level": itching_level,
            "symptom_duration": symptom_duration,
            "additional_notes": additional_notes
        }
        
        # JSON 문자열로 저장
        diagnosis.additional_info = json.dumps(additional_info_data, ensure_ascii=False)
        
        db.commit()
        db.refresh(diagnosis)
        
        logger.info(f"보조 정보가 성공적으로 저장되었습니다. Diagnosis ID: {diagnosis_id}")
        return diagnosis
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"보조 정보 저장 중 오류: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"보조 정보 저장 실패: {str(e)}")

def get_additional_info(db: Session, user_id: str, diagnosis_id: int) -> dict:
    """
    진단의 보조 정보를 조회합니다.
    """
    try:
        # 해당 진단이 존재하고 사용자의 것인지 확인
        diagnosis = db.query(Diagnosis).filter(
            Diagnosis.diagnosis_id == diagnosis_id,
            Diagnosis.user_id == user_id,
            Diagnosis.is_deleted == False
        ).first()
        
        if not diagnosis:
            raise HTTPException(status_code=404, detail="진단 정보가 없습니다")
        
        # additional_info가 없으면 빈 데이터 반환
        if not diagnosis.additional_info:
            return {
                "diagnosis_id": diagnosis_id,
                "user_id": user_id,
                "main_symptoms": [],
                "itching_level": None,
                "symptom_duration": None,
                "additional_notes": None,
                "created_at": diagnosis.created_at,
                "updated_at": diagnosis.updated_at
            }
        
        # JSON 파싱
        additional_info_data = json.loads(diagnosis.additional_info)
        
        return {
            "diagnosis_id": diagnosis_id,
            "user_id": user_id,
            "main_symptoms": additional_info_data.get("main_symptoms", []),
            "itching_level": additional_info_data.get("itching_level"),
            "symptom_duration": additional_info_data.get("symptom_duration"),
            "additional_notes": additional_info_data.get("additional_notes"),
            "created_at": diagnosis.created_at,
            "updated_at": diagnosis.updated_at
        }
        
    except HTTPException:
        raise
    except json.JSONDecodeError:
        logger.error(f"보조 정보 JSON 파싱 오류: diagnosis_id={diagnosis_id}")
        raise HTTPException(status_code=500, detail="보조 정보 형식 오류")
    except Exception as e:
        logger.error(f"보조 정보 조회 중 오류: {e}")
        raise HTTPException(status_code=500, detail=f"보조 정보 조회 실패: {str(e)}")

async def generate_disease_info_stream_service(image_bytes: bytes, disease_name: str, user_id: str):
    """
    이미지와 질병명을 처리하여 질병 정보를 생성하고 SSE를 통해 스트리밍합니다.
    """
    image_base64 = base64.b64encode(image_bytes).decode('utf-8')
    
    # 수집할 데이터
    image_analysis_data = {}
    text_analysis_data = {}
    
    try:
        # 1. 통합 RAG 호출 (이미지 + 텍스트)
        yield "data: " + json.dumps({"type": "status", "data": "세부 정보 생성 중..."}, ensure_ascii=False) + "\n\n"

        loop = asyncio.get_event_loop()
        combined_data = await loop.run_in_executor(None, generate_disease_info, image_bytes, disease_name)

        image_analysis_data = combined_data.get("image_analysis", {})
        # text_analysis_data는 image_analysis를 제외한 나머지 필드
        text_analysis_data = combined_data.copy()
        text_analysis_data.pop("image_analysis", None)

        # 이미지 분석 결과 전송
        yield "data: " + json.dumps({"type": "image_analysis", "data": image_analysis_data}, ensure_ascii=False) + "\n\n"

        # RAG 기반 정보 생성 (text_analysis_data 이미 준비됨)
        yield "data: " + json.dumps({"type": "status", "data": "이미지 분석 중..."}, ensure_ascii=False) + "\n\n"



        # 스트리밍으로 각 섹션 전송
        sections = [


            ("diagnosis_name", "disease_name"),
            ("ai_opinion", "ai_opinion"),
            ("detailed_description", "detailed_description"),
            ("precautions", "precautions"),
            ("management", "management")
        ]
        
        for section_key, section_type in sections:
            if section_key in text_analysis_data:
                yield "data: " + json.dumps({"type": f"{section_type}_start"}, ensure_ascii=False) + "\n\n"
                
                section_data = text_analysis_data[section_key]
                if isinstance(section_data, str):
                    # 문자열인 경우 청크로 나누어 전송
                    words = section_data.split()
                    for word in words:
                        yield "data: " + json.dumps({"type": f"{section_type}_chunk", "data": word}, ensure_ascii=False) + "\n\n"
                        await asyncio.sleep(0.05)
                        
                elif isinstance(section_data, list):
                    # 리스트인 경우 각 항목을 청크로 전송
                    for i, item in enumerate(section_data):
                        yield "data: " + json.dumps({"type": f"{section_type}_item_start", "data": i}, ensure_ascii=False) + "\n\n"
                        for word in item.split():
                            yield "data: " + json.dumps({"type": f"{section_type}_chunk", "data": word}, ensure_ascii=False) + "\n\n"
                            await asyncio.sleep(0.05)
                        yield "data: " + json.dumps({"type": f"{section_type}_item_end"}, ensure_ascii=False) + "\n\n"
                        
                elif isinstance(section_data, dict):
                    # 딕셔너리인 경우 키-값 쌍을 청크로 전송
                    for key, value in section_data.items():
                        yield "data: " + json.dumps({"type": f"{section_type}_item_start", "data": key}, ensure_ascii=False) + "\n\n"
                        for word in value.split():
                            yield "data: " + json.dumps({"type": f"{section_type}_chunk", "data": word}, ensure_ascii=False) + "\n\n"
                            await asyncio.sleep(0.05)
                        yield "data: " + json.dumps({"type": f"{section_type}_item_end"}, ensure_ascii=False) + "\n\n"
                
                yield "data: " + json.dumps({"type": f"{section_type}_end"}, ensure_ascii=False) + "\n\n"

        # 완료 이벤트와 함께 저장용 데이터 전송
        payload = json.dumps({
            "type": "done",
            "save_data": {
                "user_id": user_id,
                "image_base64": image_base64,
                "image_analysis": image_analysis_data,
                "text_analysis": text_analysis_data
            }
        }, ensure_ascii=False)
        yield f"data: {payload}\n\n"

    except Exception as e:
        logger.error(f"스트리밍 중 오류: {e}")
        yield "data: " + json.dumps({"type": "error", "data": str(e)}, ensure_ascii=False) + "\n\n"

