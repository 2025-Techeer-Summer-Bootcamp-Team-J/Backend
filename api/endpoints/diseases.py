from fastapi import APIRouter
from services.diseases import get_all_diseases_name

from schema.ResultResponseModel import ResultResponseModel
from sqlalchemy.orm import Session
from fastapi import Depends
from database.database import get_db

router = APIRouter(prefix="/diseases", tags=["Diseases"])

@router.get("", summary="전체 질환 목록 조회", description="전체 질환 목록 조회합니다.")
def get_all_diseases_name_endpoint(db: Session = Depends(get_db)):
    diseases = get_all_diseases_name(db)
    if not diseases:
        return ResultResponseModel(
        status_code=400,
        message="전체 질환 목록 조회 실패",
        data=None
    )   
    return ResultResponseModel(
        status_code=200,
        message="전체 질환 목록 조회 성공",
        data=diseases
    )

