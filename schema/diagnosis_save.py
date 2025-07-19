from pydantic import BaseModel
from typing import Dict, Any

class SaveDiagnosisRequest(BaseModel):
    user_id: int
    image_base64: str
    image_analysis: Dict[str, Any]
    text_analysis: Dict[str, Any]

class SaveDiagnosisResponse(BaseModel):
    diagnosis_id: int
    message: str 

# 조회용 스키마 추가 - 저장한 데이터와 동일한 구조
class SavedDiagnosisData(BaseModel):
    diagnosis_id: int
    user_id: int
    image_base64: str
    image_analysis: Dict[str, Any]
    text_analysis: Dict[str, Any]

class SavedDiagnosisResponse(BaseModel):
    code: int
    message: str
    data: SavedDiagnosisData 