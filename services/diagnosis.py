from sqlalchemy.orm import Session
from models.diagnosis import Diagnosis
from fastapi import HTTPException
from models.diagnosis import Diagnosis as DiagnosisModel



def get_user_diagnosis(db: Session, user_id: int):
    get_user_diagnosis = db.query(Diagnosis).filter(Diagnosis.user_id == user_id).all()
    return get_user_diagnosis

def delete_diagnosis(db: Session, user_id: int, diagnosis_id: int):
    diagnosis = db.query(Diagnosis).filter(Diagnosis.user_id == user_id, Diagnosis.diagnosis_id == diagnosis_id).first()
    if not diagnosis:
        raise HTTPException(status_code=404, detail="진단 정보가 없습니다")

    #관계 필드의 연결을 끊음
    diagnosis.diseases.clear()
    diagnosis.symptoms.clear()
    diagnosis.skin_type.diagnoses.clear()

    db.delete(diagnosis)
    db.commit()

    return diagnosis