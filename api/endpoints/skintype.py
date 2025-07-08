from fastapi import APIRouter
from schema.ResultResponseModel import ResultResponseModel
from services.skintype import get_all_skintype

router = APIRouter(prefix="/skintype", tags=["skintype"])

@router.get("", summary="모든 skintype 조회", description="모든 skintype 목록을 조회합니다")
def get_skintype():
    response_data = {get_all_skintype()}
    return ResultResponseModel(status_code=200, message="success", data=response_data)

