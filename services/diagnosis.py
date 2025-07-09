import sqlalchemy.orm import Session
from models.diagnosis import Diagnosis


 

def get_user_diagnosis(db: Session, user_id: int):
    get_user_diagnosis = db.query(Diagnosis).filter(Diagnosis.user_id == user_id).all()
    return get_user_diagnosis