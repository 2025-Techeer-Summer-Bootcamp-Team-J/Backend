from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

class ImageAnalysisData(BaseModel):
    skin_score: Optional[int] = None
    severity: Optional[str] = None
    estimated_treatment_period: Optional[str] = None

class TextAnalysisData(BaseModel):
    ai_opinion: Optional[str] = None
    detailed_description: Optional[str] = None # 이것은 결합된 문자열이 될 것입니다
    precautions: Optional[List[str]] = None
    management: Optional[Dict[str, str]] = None # 프롬프트에 따라 dict로 가정

class DetailedDiseaseInfoBase(BaseModel):
    disease_name: str
    image_base64: Optional[str] = None

    skin_score: Optional[int] = None
    severity: Optional[str] = None
    estimated_treatment_period: Optional[str] = None

    ai_opinion: Optional[str] = None
    detailed_description: Optional[str] = None
    precautions: Optional[List[str]] = None
    management: Optional[Dict[str, str]] = None

class DetailedDiseaseInfoCreate(DetailedDiseaseInfoBase):
    pass

class DetailedDiseaseInfoRead(DetailedDiseaseInfoBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class DetailedDiseaseInfoResponse(BaseModel):
    code: int
    message: str
    data: DetailedDiseaseInfoRead

class DetailedDiseaseInfoListResponse(BaseModel):
    code: int
    message: str
    data: List[DetailedDiseaseInfoRead]
