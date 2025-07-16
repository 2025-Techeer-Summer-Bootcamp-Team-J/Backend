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
    try:
        diseases = get_all_diseases_name(db)  
        return ResultResponseModel(
            status_code=200,
            message="전체 질환 목록 조회 성공",
            data=diseases
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail="전체 질환 목록 조회 실패")

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
        raise HTTPException(
            status_code=400,
            detail="찾을 수 없는 질환id 입니다.")

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail="등록되지 않은 질환입니다.")