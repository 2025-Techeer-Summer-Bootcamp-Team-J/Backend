from fastapi import APIRouter, HTTPException, File, UploadFile
from schema.ResultResponseModel import ResultResponseModel
from services.skintype import get_skintype_table, get_type_description_by_id, get_skintype_analysis
from sqlalchemy.orm import Session
from fastapi import Depends
from database.database import get_db

router = APIRouter(prefix="/skintypes", tags=["skintype"])

@router.get("", summary="모든 skintype 조회", description="모든 skintype 목록을 조회합니다")
def get_skintype(db: Session = Depends(get_db)):
    response_data = get_skintype_table(db=db)
    return ResultResponseModel(status_code=200, message="success", data=response_data)

@router.get("/{skintype_id}", summary="skintype 설명 조회", description="skintype 설명을 조회합니다")
def get_skintype_by_id(skintype_id: int, db: Session = Depends(get_db)):
    response_data = get_type_description_by_id(db=db, skintype_id=skintype_id)
    return ResultResponseModel(status_code=200, message="success", data=response_data)


@router.post("/users/{user_id}/image", summary="피부 유형 분석", description="얼굴 사진을 업로드하여 피부 유형을 분석합니다")
async def create_skintype_analysis(
    user_id: int,
    image: UploadFile = File(..., description="분석할 얼굴 사진 (JPG/JPEG, 최대 2MB)"),
    db: Session = Depends(get_db)
    ):
    # 파일 크기 확인 (2MB 제한)
    image.file.seek(0, 2)  # 파일 끝으로 이동
    file_size = image.file.tell()
    image.file.seek(0)  # 파일 시작으로 이동
    
    if file_size > 2 * 1024 * 1024:  # 2MB
        raise HTTPException(status_code=400, detail={"code": 400, "detail": "파일 크기는 2MB를 초과할 수 없습니다"})
    
    # 파일 형식 확인
    if not image.content_type or image.content_type not in ["image/jpeg", "image/jpg"]:
        raise HTTPException(status_code=400, detail={"code": 400, "detail": "JPG 또는 JPEG 형식의 이미지만 지원됩니다"})

    try:
        response_data = get_skintype_analysis(db=db, user_id=user_id, image=image)
        return ResultResponseModel(status_code=200, message="피부 유형 분석이 완료되었습니다", data=response_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail={"code": 500, "detail": f"분석 중 오류가 발생했습니다: {str(e)}"})