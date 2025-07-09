from fastapi import APIRouter
from services.diseases import get_all_diseases

router = APIRouter(prefix="/diseases", tags=["Diseases"])

@router.get("/", summary="전체 질환 목록 조회", description="전체 질환 목록 조회합니다.")
def get_all_diseases_endpoint(db: Session = Depends(get_db)):
    return ResultResponseModel(
        status_code=200,
        message="전체 질환 목록 조회 성공",
        data=get_all_diseases(db)
    )
    if not get_all_diseases(db):
        return ResultResponseModel(
        status_code=400,
        message="전체 질환 목록 조회 실패",
        data=None
    )   
 