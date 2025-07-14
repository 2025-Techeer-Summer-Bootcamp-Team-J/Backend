from sqlalchemy.orm import Session
from fastapi import HTTPException, UploadFile
import requests
from dotenv import load_dotenv
import os
import json
import io
from typing import Dict, Any
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from models.skintype import SkinType
from models.diagnosis import Diagnosis
from models.user import User
from schema.skintype import SkinTypeCreate, SkinTypeUpdate, SkinTypeDelete, SkinTypeRead

load_dotenv()
api_key = os.environ.get("AILAB_API_KEY")

def create_session_with_retry():
    """재시도 로직이 포함된 requests 세션을 생성합니다."""
    session = requests.Session()
    
    retry_strategy = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["POST"]
    )
    
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    
    return session

def analyze_skin_with_ailab(image_file: UploadFile) -> Dict[str, Any]:
    """AILabAPI를 사용하여 피부 유형을 분석합니다."""
    if not api_key:
        raise HTTPException(status_code=500, detail="AILAB_API_KEY가 설정되지 않았습니다")
    
    url = "https://www.ailabapi.com/api/portrait/analysis/skin-analysis"
    
    try:
        if image_file.content_type not in ["image/jpeg", "image/jpg"]:
            raise HTTPException(status_code=400, detail="JPG 또는 JPEG 형식의 이미지만 지원됩니다")
        
        image_data = image_file.file.read()
        image_file.file.seek(0)
        
        if len(image_data) > 2 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="파일 크기는 2MB를 초과할 수 없습니다")
        
        files = {
            'image': (image_file.filename or 'image.jpg', io.BytesIO(image_data), image_file.content_type)
        }
        headers = {
            'ailabapi-api-key': api_key
        }
        
        session = create_session_with_retry()
        response = session.post(url, headers=headers, files=files, timeout=(10, 60))
        
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail="AILab API 호출 실패")
        
        return response.json()
        
    except requests.exceptions.Timeout:
        raise HTTPException(status_code=504, detail="API 호출 시간이 초과되었습니다")
    except requests.exceptions.ConnectionError:
        raise HTTPException(status_code=503, detail="외부 API 서버에 연결할 수 없습니다")
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=f"API 호출 중 오류가 발생했습니다: {str(e)}")
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="API 응답을 파싱할 수 없습니다")
    finally:
        if 'session' in locals():
            session.close()

def get_skintype_analysis(db: Session, user_id: int, image: UploadFile) -> Dict[str, Any]:
    """이미지를 분석하여 피부 유형 정보를 반환하고 사용자별로 결과를 저장합니다."""
    
    # 사용자 존재 여부 확인
    user = db.query(User).filter(User.user_id == user_id, User.is_deleted == False).first()
    if not user:
        raise HTTPException(status_code=404, detail="존재하지 않는 사용자입니다")
    
    # AILab API로 피부 분석 수행
    analysis_result = analyze_skin_with_ailab(image)
    
    # skin_type 값 추출 (result.skin_type.skin_type 경로)
    skin_type_code = None
    if 'result' in analysis_result and isinstance(analysis_result['result'], dict):
        result_data = analysis_result['result']
        if 'skin_type' in result_data and isinstance(result_data['skin_type'], dict):
            skin_type_obj = result_data['skin_type']
            if 'skin_type' in skin_type_obj:
                skin_type_code = skin_type_obj['skin_type']
    
    if skin_type_code is None:
        raise HTTPException(status_code=500, detail="피부 유형 분석 결과를 얻을 수 없습니다")
    
    # 값 범위 확인 (0-3)
    if skin_type_code < 0 or skin_type_code > 3:
        skin_type_code = 2  # 기본값: 중성
    
    # 데이터베이스 ID 매핑 (0->1, 1->2, 2->3, 3->4)
    db_skin_type_id = skin_type_code + 1
    skintype_info = db.query(SkinType).filter(SkinType.skin_type_id == db_skin_type_id).first()
    
    # 분석 결과를 Diagnosis 테이블에 저장
    try:
        new_diagnosis = Diagnosis(
            user_id=user_id,
            skin_type_id=db_skin_type_id,
            class_name="skin_analysis",
            confidence=1.0,
            x1=0, y1=0, x2=0, y2=0,
            image=image.filename if image.filename else "unknown"
        )
        db.add(new_diagnosis)
        db.commit()
        db.refresh(new_diagnosis)
    except Exception:
        db.rollback()
    
    # 응답 데이터 구성
    if not skintype_info:
        skin_type_names = {0: "지성 피부", 1: "건조 피부", 2: "중성 피부", 3: "복합성 피부"}
        return {
            "user_id": user_id,
            "skin_type_code": skin_type_code,
            "skin_type_name": skin_type_names.get(skin_type_code, "알 수 없음")
        }
    
    return {
        "user_id": user_id,
        "skin_type_code": skin_type_code,
        "skin_type_name": skintype_info.type_name
    }



def get_all_skintype_name(db:Session):
    skintype_name = db.query(SkinType.type_name).filter(SkinType.is_deleted == False).all()
    return [result[0] for result in skintype_name]

def get_skintype_table(db: Session):
    skintype = db.query(SkinType).filter(SkinType.is_deleted == False).all()
    return [SkinTypeRead.model_validate(skin) for skin in skintype]

def create_skintype(db: Session, skintype: SkinTypeCreate):
    new_skintype = SkinType(
        type_name=skintype.type_name,
        type_description=skintype.type_description,
        tip_title=skintype.tip_title,
        tip_content=skintype.tip_content
    )
    db.add(new_skintype)
    db.commit()
    db.refresh(new_skintype)
    return SkinTypeRead.model_validate(new_skintype)

def delete_skintype(db: Session, skin_type_id: int):
    skintype = db.query(SkinType).filter(SkinType.skin_type_id == skin_type_id).first()
    if not skintype:
        raise HTTPException(status_code=404, detail="피부유형 정보가 없습니다")

    # 삭제 전에 Pydantic 스키마로 변환
    skintype_data = SkinTypeRead.model_validate(skintype)

    db.query(Diagnosis).filter(Diagnosis.skin_type_id == skin_type_id).update({"skin_type_id": None})
    
    skintype.diseases.clear()

    db.delete(skintype)
    db.commit()
    return skintype_data

def update_skintype(db: Session, skin_type_id: int, skintype_update: SkinTypeUpdate):
    db_skintype = db.query(SkinType).filter(SkinType.skin_type_id == skin_type_id).first()
    if not db_skintype:
        raise HTTPException(status_code=404, detail="피부유형 정보가 없습니다")
    
    update_data = skintype_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_skintype, key, value)

    db.commit()
    db.refresh(db_skintype)
    return SkinTypeRead.model_validate(db_skintype)

def get_type_description_by_id(db: Session, skintype_id: int):
    skintype = db.query(SkinType).filter(SkinType.skin_type_id == skintype_id).first()
    if not skintype:
        raise HTTPException(status_code=404, detail="피부유형 정보가 없습니다")
    return skintype.type_description

def get_user_analysis_history(db: Session, user_id: int) -> Dict[str, Any]:
    """사용자의 피부 분석 히스토리를 조회합니다."""
    
    # 사용자 존재 여부 확인
    user = db.query(User).filter(User.user_id == user_id, User.is_deleted == False).first()
    if not user:
        raise HTTPException(status_code=404, detail="존재하지 않는 사용자입니다")
    
    # 해당 사용자의 피부 분석 기록 조회 (최신순)
    diagnoses = db.query(Diagnosis).filter(
        Diagnosis.user_id == user_id,
        Diagnosis.class_name == "skin_analysis",
        Diagnosis.is_deleted == False
    ).order_by(Diagnosis.created_at.desc()).all()
    
    history_list = []
    for diagnosis in diagnoses:
        # 피부 유형 정보 조회
        skintype_info = None
        if diagnosis.skin_type_id:
            skintype_info = db.query(SkinType).filter(SkinType.skin_type_id == diagnosis.skin_type_id).first()
        
        # 피부 유형 코드 계산 (DB ID에서 1을 빼서 API 코드로 변환)
        skin_type_code = diagnosis.skin_type_id - 1 if diagnosis.skin_type_id else None
        skin_type_names = {0: "지성 피부", 1: "건조 피부", 2: "중성 피부", 3: "복합성 피부"}
        
        history_item = {
            "diagnosis_id": diagnosis.diagnosis_id,
            "created_at": diagnosis.created_at.isoformat() if diagnosis.created_at else None,
            "skin_type_code": skin_type_code,
            "skin_type_name": skintype_info.type_name if skintype_info else skin_type_names.get(skin_type_code, "알 수 없음"),
            "type_description": skintype_info.type_description if skintype_info else None,
            "tip_title": skintype_info.tip_title if skintype_info else None,
            "tip_content": skintype_info.tip_content if skintype_info else None,
            "image_filename": diagnosis.image
        }
        history_list.append(history_item)
    
    return {
        "user_id": user_id,
        "user_name": user.name,
        "total_analyses": len(history_list),
        "history": history_list
    }
