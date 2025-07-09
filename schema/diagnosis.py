from pydantic import BaseModel
from typing import List, Optional

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

# --- 성공 응답을 위한 스키마 ---
class DiagnosisResponse(BaseModel):
    code: int
    message: str
    data: Optional[List[Diagnosis]] = None