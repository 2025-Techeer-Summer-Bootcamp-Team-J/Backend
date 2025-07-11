from sqlalchemy.orm import Session
from fastapi import HTTPException

from models.diseases import Disease
from schema.diseases import DiseaseCreate, DiseaseUpdate, DiseaseDelete, DiseaseRead

def get_all_diseases_name(db: Session):
    diseases = db.query(Disease.disease_name).filter(Disease.is_deleted == False).all()
    return [result[0] for result in diseases]

def get_disease_table(db: Session):
    diseases = db.query(Disease).filter(Disease.is_deleted == False).all()
    return [DiseaseRead.model_validate(disease) for disease in diseases]

def create_disease(db: Session, disease: DiseaseCreate):
    new_disease = Disease(
        main_symptom=disease.main_symptom,
        disease_name=disease.disease_name,
        description=disease.description,
        precautions=disease.precautions
    )
    db.add(new_disease)
    db.commit()
    db.refresh(new_disease)
    return DiseaseRead.model_validate(new_disease)

def delete_disease(db: Session, disease_id: int):
    disease = db.query(Disease).filter(Disease.disease_id == disease_id).first()
    if not disease:
        raise HTTPException(status_code=404, detail="질병 정보가 없습니다")
    
    # 삭제 전에 Pydantic 스키마로 변환
    disease_data = DiseaseRead.model_validate(disease)
    
    disease.diagnoses.clear()
    disease.skintypes.clear()

    db.delete(disease)
    db.commit()
    return disease_data

def update_disease(db: Session, disease_id: int, disease_update: DiseaseUpdate):
    db_disease = db.query(Disease).filter(Disease.disease_id == disease_id).first()
    if not db_disease:
        raise HTTPException(status_code=404, detail="질병 정보가 없습니다")
    
    update_data = disease_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_disease, key, value)
        
    db.commit()
    db.refresh(db_disease)
    return DiseaseRead.model_validate(db_disease)