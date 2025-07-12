from fastapi import APIRouter
from schema.ResultResponseModel import ResultResponseModel
from services.skintype import get_skintype_table, get_type_description_by_id
from sqlalchemy.orm import Session
from fastapi import Depends
from database.database import get_db

router = APIRouter(prefix="/skintype", tags=["skintype"])

@router.get("", summary="모든 skintype 조회", description="모든 skintype 목록을 조회합니다")
def get_skintype(db: Session = Depends(get_db)):
    response_data = get_skintype_table(db=db)
    return ResultResponseModel(status_code=200, message="success", data=response_data)

@router.get("/{skintype_id}", summary="skintype 설명 조회", description="skintype 설명을 조회합니다")
def get_skintype_by_id(skintype_id: int, db: Session = Depends(get_db)):
    response_data = get_type_description_by_id(db=db, skintype_id=skintype_id)
    return ResultResponseModel(status_code=200, message="success", data=response_data)