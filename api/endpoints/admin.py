from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from schema.ResultResponseModel import ResultResponseModel
from services.diseases import create_disease as create_disease_service, delete_disease as delete_disease_service, update_disease as update_disease_service
from services.skintype import create_skintype as create_skintype_service, delete_skintype as delete_skintype_service, update_skintype as update_skintype_service
from schema.diseases import DiseaseCreate, DiseaseUpdate
from schema.skintype import SkinTypeCreate, SkinTypeUpdate
from database.database import get_db

router = APIRouter(prefix="/admin", tags=["admin"])

@router.post("/disease", summary="질환정보생성", description="질환정보를 생성합니다")
def create_disease(disease: DiseaseCreate, db: Session = Depends(get_db)):
    if not disease:
        return ResultResponseModel(status_code=400, message="질병 정보가 없습니다")
    return create_disease_service(db, disease)

@router.put("/disease/{disease_id}", summary="질환정보 수정", description="질환정보를 수정합니다")
def update_disease(disease_id: int, disease: DiseaseUpdate, db: Session = Depends(get_db)):
    if not disease_id:
        return ResultResponseModel(status_code=400, message="질병 정보가 없습니다")
    return update_disease_service(db, disease_id, disease)

@router.delete("/disease/{disease_id}", summary="질환 삭제", description="질환정보를 삭제합니다")
def delete_disease(disease_id: int, db: Session = Depends(get_db)):
    if not disease_id:
        return ResultResponseModel(status_code=400, message="질병 정보가 없습니다")
    return delete_disease_service(db, disease_id)

@router.post("/skintype", summary="새로운 피부유형 추가", description="새로운 피부유형을 추가합니다")
def create_skintype(skintype: SkinTypeCreate, db: Session = Depends(get_db)):
    if not skintype:
        return ResultResponseModel(status_code=400, message="피부유형 정보가 없습니다")
    return create_skintype_service(db, skintype)

@router.put("/skintype/{skintype_id}", summary="피부유형정보 수정", description="피부유형정보를 수정합니다")
def update_skintype(skintype_id: int, skintype: SkinTypeUpdate, db: Session = Depends(get_db)):
    if not skintype_id:
        return ResultResponseModel(status_code=400, message="피부유형 정보가 없습니다")
    return update_skintype_service(db, skintype_id, skintype)

@router.delete("/skintype/{skintype_id}", summary="피부유형 삭제", description="피부유형정보를 삭제합니다")
def delete_skintype(skintype_id: int, db: Session = Depends(get_db)):
    if not skintype_id:
        return ResultResponseModel(status_code=400, message="피부유형 정보가 없습니다")
    return delete_skintype_service(db, skintype_id)