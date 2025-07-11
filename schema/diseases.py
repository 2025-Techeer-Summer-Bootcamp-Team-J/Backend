from pydantic import BaseModel
from datetime import datetime

class DiseaseCreate(BaseModel):
    main_symptom: str
    disease_name: str
    description: str
    precautions: str

class DiseaseRead(BaseModel):
    disease_id: int
    main_symptom: str
    disease_name: str
    description: str
    precautions: str
    created_at: datetime
    updated_at: datetime
    is_deleted: bool

    class Config:
        from_attributes = True

class DiseaseUpdate(BaseModel):
    main_symptom: str
    disease_name: str
    description: str
    precautions: str

class DiseaseDelete(BaseModel):
    disease_id: int

