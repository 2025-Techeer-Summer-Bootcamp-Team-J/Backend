from pydantic import BaseModel

from typing import Dict, Any
from fastapi import File, UploadFile

from typing import Dict, Any, List, Optional
from .diseases import DiseaseRead


class SaveDiagnosisRequest(BaseModel):
    user_id: str
    image_analysis: Dict[str, Any]
    text_analysis: Dict[str, Any]

class SaveDiagnosisResponse(BaseModel):
    diagnosis_id: int
    message: str 

# 조회용 스키마 추가 - 저장한 데이터와 동일한 구조
class SavedDiagnosisData(BaseModel):
    diagnosis_id: int
    user_id: str
    image_base64: str  # 이미지(Base64 또는 URL) 문자열
    image_analysis: Dict[str, Any]
    text_analysis: Dict[str, Any]
    disease_name: Optional[str] = None  # 질병명 필드(선택 사항)
    diseases: List[DiseaseRead] = []  # 연관된 질병 정보

class SavedDiagnosisResponse(BaseModel):
    code: int
    message: str
    data: SavedDiagnosisData 