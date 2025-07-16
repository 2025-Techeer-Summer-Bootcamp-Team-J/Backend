from sqlalchemy.orm import Session
from models.diagnosis import Diagnosis
from fastapi import HTTPException
from models.diagnosis import Diagnosis as DiagnosisModel
from schema.diagnosis import DiagnosisData


def delete_diagnosis(db: Session, user_id: int, diagnosis_id: int):
    diagnosis = db.query(Diagnosis).filter(Diagnosis.user_id == user_id, Diagnosis.diagnosis_id == diagnosis_id).first()
    if not diagnosis:
        raise HTTPException(status_code=404, detail="진단 정보가 없습니다")

    diagnosis.diseases.clear()
    diagnosis.symptoms.clear()
    diagnosis.skin_type = None

    db.delete(diagnosis)
    db.commit()

    return diagnosis

def get_diagnosis_table(db: Session):
    diagnoses = db.query(Diagnosis).filter(Diagnosis.is_deleted == False).all()
    return [DiagnosisData.model_validate(diagnosis) for diagnosis in diagnoses]

