from pydantic import BaseModel
from typing import List, Optional
from models.diagnosis import Diagnosis as DiagnosisModel
from datetime import datetime
# --- 기본 진단 정보 스키마 ---
class DiagnosisBase(BaseModel):
    class_name: str
    confidence: float
    bounding_box: List[int]

# --- DB에서 읽어올 때 사용할 스키마 (id 포함) ---
class Diagnosis(DiagnosisBase):
    id: int
    user_id: int

class Config:
    from_attributes = True # SQLAlchemy 모델을 Pydantic 모델로 변환

class BoundingBox(BaseModel):
    x1: int
    y1: int
    x2: int
    y2: int

class DiagnosisData(BaseModel):
    id: int  # diagnosis_id의 별칭으로 사용
    user_id: int
    disease_name: Optional[str] = None  # 질환명 추가
    skin_type_id: Optional[int] = None
    confidence: Optional[int] = None  # 기존 expected_treat 대신 사용
    image: Optional[str] = None
    after: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    is_deleted: bool = False
    
    class Config:
        from_attributes = True
    


# --- 새로운 간소화된 진단 응답 스키마 ---
class SimplifiedDiagnosisData(BaseModel):
    disease_name: str  # 질환명
    confidence: float  # 신뢰도 (0.0 ~ 100.0, 소수 첫째자리)
    image: str  # 이미지 (base64)

class SimplifiedDiagnosisResponse(BaseModel):
    code: int
    message: str
    data: List[SimplifiedDiagnosisData]

# --- 성공 응답을 위한 스키마 ---
class DiagnosisResponse(BaseModel):
    code: int
    message: str
    data: List[DiagnosisData]  # ← 여기!

# --- 사용자 진단 조회를 위한 간단한 스키마 ---
class UserDiagnosisSimple(BaseModel):
    id: int
    user_id: int
    disease_name: str
    confidence: float
    
    class Config:
        from_attributes = True

# --- 사용자 진단 조회를 위한 기본 스키마 (질병명만) ---
class UserDiagnosisBasic(BaseModel):
    id: int
    user_id: int
    disease_name: str
    
    class Config:
        from_attributes = True

class UserDiagnosisResponse(BaseModel):
    code: int
    message: str
    data: List[UserDiagnosisSimple]

class UserDiagnosisBasicResponse(BaseModel):
    code: int
    message: str
    data: List[UserDiagnosisBasic]

def box_to_schema(diagnosis_obj) -> DiagnosisData:
    """Diagnosis 모델 객체를 DiagnosisData 스키마로 변환"""
    try:
        return DiagnosisData(
            id=getattr(diagnosis_obj, 'diagnosis_id', 0),
            user_id=getattr(diagnosis_obj, 'user_id', 0),
            skin_type_id=getattr(diagnosis_obj, 'skin_type_id', None),
            confidence=getattr(diagnosis_obj, 'confidence', None),
            image=getattr(diagnosis_obj, 'image', None),
            after=getattr(diagnosis_obj, 'after', None),
            created_at=getattr(diagnosis_obj, 'created_at', None),
            updated_at=getattr(diagnosis_obj, 'updated_at', None),
            is_deleted=getattr(diagnosis_obj, 'is_deleted', False)
        )
    except Exception as e:
        print(f"진단 데이터 변환 중 오류 발생: {e}")
        # 최소한의 기본값으로라도 반환
        return DiagnosisData(
            id=getattr(diagnosis_obj, 'diagnosis_id', 0),
            user_id=getattr(diagnosis_obj, 'user_id', 0),
            skin_type_id=None,
            confidence=None,
            image=None,
            after=None,
            created_at=None,
            updated_at=None,
            is_deleted=False
        )

def diagnosis_to_simple_schema(diagnosis_obj) -> SimplifiedDiagnosisData:
    """Diagnosis 모델 객체를 SimplifiedDiagnosisData 스키마로 변환"""
    try:
        # disease_name 가져오기 - 첫 번째 연관된 질병의 이름을 사용
        disease_name = "알 수 없음"
        if diagnosis_obj.diseases and len(diagnosis_obj.diseases) > 0:
            disease_name = diagnosis_obj.diseases[0].disease_name
            
        # confidence 값 가져오기
        confidence = getattr(diagnosis_obj, 'confidence', 0)
        if confidence is None:
            confidence = 0
            
        image_base64 = getattr(diagnosis_obj, 'image', None)
        if image_base64 is None:
            image_base64 = ""

        return SimplifiedDiagnosisData(
            disease_name=disease_name,
            confidence=float(confidence),
            image=image_base64
        )
    except Exception as e:
        print(f"간단한 진단 데이터 변환 중 오류 발생: {e}")
        # 최소한의 기본값으로라도 반환
        return SimplifiedDiagnosisData(
            disease_name="알 수 없음",
            confidence=0.0,
            image=""
        )

def diagnosis_to_basic_schema(diagnosis_obj) -> UserDiagnosisBasic:
    """Diagnosis 모델 객체를 UserDiagnosisBasic 스키마로 변환"""
    try:
        # disease_name 가져오기 - detailed_info_json에서 추출하거나 첫 번째 연관된 질병의 이름을 사용
        disease_name = "알 수 없음"
        
        # 1. detailed_info_json에서 질병명 추출 시도
        if hasattr(diagnosis_obj, 'detailed_info_json') and diagnosis_obj.detailed_info_json:
            try:
                import json
                detail_info = json.loads(diagnosis_obj.detailed_info_json)
                if isinstance(detail_info, dict):
                    # image_analysis에서 disease_name 찾기
                    image_analysis = detail_info.get('image_analysis', {})
                    if isinstance(image_analysis, dict) and 'disease_name' in image_analysis:
                        disease_name = image_analysis['disease_name']
            except (json.JSONDecodeError, KeyError, TypeError):
                pass
        
        # 2. 관계된 diseases 테이블에서 질병명 가져오기 (fallback)
        if disease_name == "알 수 없음" and hasattr(diagnosis_obj, 'diseases') and diagnosis_obj.diseases and len(diagnosis_obj.diseases) > 0:
            disease_name = diagnosis_obj.diseases[0].disease_name

        return UserDiagnosisBasic(
            id=getattr(diagnosis_obj, 'diagnosis_id', 0),
            user_id=getattr(diagnosis_obj, 'user_id', 0),
            disease_name=disease_name
        )
    except Exception as e:
        print(f"기본 진단 데이터 변환 중 오류 발생: {e}")
        # 최소한의 기본값으로라도 반환
        return UserDiagnosisBasic(
            id=getattr(diagnosis_obj, 'diagnosis_id', 0),
            user_id=getattr(diagnosis_obj, 'user_id', 0),
            disease_name="알 수 없음"
        )

def aggregate_and_normalize_diagnoses(predictions, image_base64: str) -> List[SimplifiedDiagnosisData]:
    """
    같은 질환명의 신뢰도를 합치고 100분위로 정규화하여 간소화된 진단 데이터로 변환
    """
    if not predictions:
        # 예측 결과가 없을 때 "정상입니다"로 응답
        return [SimplifiedDiagnosisData(
            disease_name="정상입니다",
            confidence=100.0,
            image=image_base64
        )]
    
    # 질환명별로 신뢰도 합산
    disease_confidence_map = {}
    for pred in predictions:
        class_name = pred.get('class', '')
        confidence = pred.get('confidence', 0.0)
        
        if class_name in disease_confidence_map:
            disease_confidence_map[class_name] += confidence
        else:
            disease_confidence_map[class_name] = confidence
    
    # 전체 신뢰도 합계 계산
    total_confidence = sum(disease_confidence_map.values())
    
    # 100분위로 정규화하고 소수 첫째 자리까지 반올림
    result = []
    for disease_name, confidence in disease_confidence_map.items():
        normalized_confidence = (confidence / total_confidence * 100) if total_confidence > 0 else 0.0
        normalized_confidence = round(normalized_confidence, 1)  # 소수 첫째 자리까지
        
        result.append(SimplifiedDiagnosisData(
            disease_name=disease_name,
            confidence=normalized_confidence,
            image=image_base64
        ))
    
    # 신뢰도 순으로 정렬 (높은 순)
    result.sort(key=lambda x: x.confidence, reverse=True)
    return result

# --- 진단 보조 정보 스키마 ---
class AdditionalInfoRequest(BaseModel):
    """보조 정보 입력 요청 스키마"""
    diagnosis_id: int
    main_symptoms: List[str] = []  # 주요 증상 (가려움, 따가움/동통, 붉은 반점, 각질/비듬, 진물/수포, 피부 간조, 부르지/이드름)
    itching_level: Optional[int] = None  # 가려움 정도 (1-9, 해당 시에만)
    symptom_duration: Optional[str] = None  # 언제부터 시작했나요 (오늘, 2-3일 전, 1주일 이상, 오래 전)
    additional_notes: Optional[str] = None  # 보조 정보 (텍스트)

class AdditionalInfoResponse(BaseModel):
    """보조 정보 조회 응답 스키마"""
    diagnosis_id: int
    user_id: int
    main_symptoms: List[str]
    itching_level: Optional[int]
    symptom_duration: Optional[str]
    additional_notes: Optional[str]
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class AdditionalInfoSuccessResponse(BaseModel):
    """보조 정보 API 성공 응답"""
    code: int
    message: str
    data: Optional[AdditionalInfoResponse] = None
    

