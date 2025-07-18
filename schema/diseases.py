from pydantic import BaseModel, ConfigDict
from typing import List, Optional

# --- Schemas for Database CRUD Operations ---

class DiseaseBase(BaseModel):
    main_symptom: Optional[str] = None
    disease_name: str
    description: Optional[str] = None
    precautions: Optional[str] = None

class DiseaseCreate(DiseaseBase):
    pass

class DiseaseUpdate(DiseaseBase):
    pass

class DiseaseRead(DiseaseBase):
    disease_id: int
    model_config = ConfigDict(from_attributes=True)

class DiseaseDelete(BaseModel):
    disease_id: int

# --- Schemas for Gemini API Response ---

class DiseaseSummary(BaseModel):
    suspected_disease: str
    skin_score: int
    severity: str
    estimated_treatment_period: str

class DiseaseInfoResponse(BaseModel):
    summary: DiseaseSummary
    ai_opinion: str
    detailed_description: str
    precautions: List[str]
    management: List[str]
