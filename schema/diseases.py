from pydantic import BaseModel
from datetime import datetime

class DiseaseCreate(BaseModel):
    main_symptom: str
    disease_name: str
    description: str
    precautions: str

class DiseaseUpdate(BaseModel):
    main_symptom: str
    disease_name: str
    description: str
    precautions: str

class DiseaseDelete(BaseModel):
    disease_id: int

