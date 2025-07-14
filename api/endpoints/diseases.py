from fastapi import APIRouter
from services.diseases import get_all_diseases_name
from schema.ResultResponseModel import ResultResponseModel
from sqlalchemy.orm import Session
from fastapi import Depends, HTTPException
from database.database import get_db
from services.diseases import get_disease_by_id

router = APIRouter(prefix="/diseases", tags=["Diseases"])

# 전체 질환 목록 조회
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


# 특정 질환 상세 조회
@router.get("/{disease_id}", summary="질환 상세 조회", description="질환 상세 조회합니다.")
def get_disease_by_id_endpoint(disease_id: int, db: Session = Depends(get_db)):
    try:
        disease = get_disease_by_id(db, disease_id)
        return ResultResponseModel(
            status_code=200,
            message="질환 상세 조회 성공",
            data=disease
        )
    except HTTPException as e:
        return ResultResponseModel(
            status_code=400,
            message="찾을 수 없는 잘환id 입니다.",
            data=None)
    except Exception as e:
        return ResultResponseModel(
            status_code=500,
            message="등록되지 않은 질환입니다.",
            data=None)