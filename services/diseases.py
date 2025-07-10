from sqlalchemy.orm import Session
from fastapi import HTTPException

from models.diseases import Disease
from schema.diseases import DiseaseCreate, DiseaseUpdate, DiseaseDelete

def get_all_diseases(db: Session):
    return db.query(Disease).filter(Disease.is_deleted == False).all()

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
    return new_disease

def delete_disease(db: Session, disease_id: int):
    disease = db.query(Disease).filter(Disease.disease_id == disease_id).first()
    if not disease:
        raise HTTPException(status_code=404, detail="질병 정보가 없습니다")
    disease.is_deleted = True
    db.commit()
    return disease

def update_disease(db: Session, disease_id: int, disease_update: DiseaseUpdate):
    db_disease = db.query(Disease).filter(Disease.disease_id == disease_id).first()
    if not db_disease:
        raise HTTPException(status_code=404, detail="질병 정보가 없습니다")
    
    update_data = disease_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_disease, key, value)
        
    db.commit()
    db.refresh(db_disease)
    return db_disease