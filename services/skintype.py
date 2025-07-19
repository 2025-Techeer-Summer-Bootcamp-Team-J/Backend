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
if not api_key:
    # Fail fast on startup if the key is missing.
    raise ValueError("AILAB_API_KEY environment variable is not set.")

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
    url = "https://www.ailabapi.com/api/portrait/analysis/skin-analysis"
    
    try:
        image_data = image_file.file.read()
        image_file.file.seek(0)
        
        files = {
            'image': (image_file.filename or 'image.jpg', io.BytesIO(image_data), image_file.content_type)
        }
        headers = {
            'ailabapi-api-key': api_key
        }
        
        with create_session_with_retry() as session:
            # files 딕셔너리의 value를 (filename, fileobj, content_type)에서 (filename, fileobj, content_type)로 전달하면
            # requests의 타입 검사에서 오류가 발생할 수 있으므로, content_type을 생략하거나 명시적으로 typing을 맞춰줍니다.
            # requests는 (filename, fileobj) 또는 (filename, fileobj, content_type) 튜플을 허용합니다.
            # 하지만 mypy 등에서 경고가 발생할 수 있으므로, 아래와 같이 content_type을 명시적으로 str로 지정합니다.
            files_for_requests = {
                'image': (image_file.filename or 'image.jpg', io.BytesIO(image_data), image_file.content_type or 'application/octet-stream')
            }
            response = session.post(url, headers=headers, files=files_for_requests, timeout=(10, 60))
            
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

def get_skintype_analysis(db: Session, user_id: int, image: UploadFile) -> Dict[str, Any]:
    """이미지를 분석하여 피부 유형 정보를 반환하고 사용자별로 결과를 저장합니다."""
    
    # 사용자 존재 여부 확인
    user = db.query(User).filter(User.user_id == user_id, User.is_deleted == False).first()
    if not user:
        raise HTTPException(status_code=404, detail="존재하지 않는 사용자입니다")
    
    # AILab API로 피부 분석 수행
    analysis_result = analyze_skin_with_ailab(image)
    
    # skin_type 값 추출 (result.skin_type.skin_type 경로)
    skin_type_code = analysis_result.get('result', {}).get('skin_type', {}).get('skin_type')
    
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
    skintype = db.query(SkinType).filter(SkinType.skin_type_id == skin_type_id, SkinType.is_deleted == False).first()
    if not skintype:
        raise HTTPException(status_code=404, detail="피부유형 정보가 없습니다")

    # 삭제 전에 Pydantic 스키마로 변환
    skintype_data = SkinTypeRead.model_validate(skintype)

    # Soft delete: is_deleted를 True로 설정
    skintype.is_deleted = True
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
    skintype = db.query(SkinType).filter(SkinType.skin_type_id == skintype_id, SkinType.is_deleted == False).first()
    if not skintype:
        raise HTTPException(status_code=404, detail="피부유형 정보가 없습니다")
    return skintype.type_description

