from fastapi import APIRouter
from schema.ResultResponseModel import ResultResponseModel
from services.skintype import get_all_skintype
from sqlalchemy.orm import Session
from fastapi import Depends
from database.database import get_db

router = APIRouter(prefix="/skintype", tags=["skintype"])

@router.get("", summary="모든 skintype 조회", description="모든 skintype 목록을 조회합니다")
def get_skintype(db: Session = Depends(get_db)):
    response_data = get_all_skintype(db=db)
    return ResultResponseModel(status_code=200, message="success", data=response_data)