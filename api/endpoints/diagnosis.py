from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from schema.ResultResponseModel import ResultResponseModel
from services.diagnosis import get_user_diagnosis
from database.database import get_db

router = APIRouter(prefix="/diagnosis", tags=["diagnosis"])

@router.get("/{user_id}", summary="유저 진단 조회", description="유저 진단 목록을 조회합니다")
def get_user_diagnosis_endpoint(user_id: int, db: Session = Depends(get_db)):
    if not user_id:
        return ResultResponseModel(status_code=500, message="없는 사용자 입니다")
    
    diagnoses = get_user_diagnosis(db, user_id)
    if not diagnoses:
        return ResultResponseModel(status_code=500, message="진단 데이터가 없습니다")
    
    response_data = diagnoses
    return ResultResponseModel(status_code=200, message="특정 사용자의 모든 진단 조회 성공", data=response_data) 







