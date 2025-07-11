from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List
from schema.ResultResponseModel import ResultResponseModel
from services.diseases import create_disease as create_disease_service, delete_disease as delete_disease_service, update_disease as update_disease_service, get_disease_table as get_disease_table
from services.skintype import create_skintype as create_skintype_service, delete_skintype as delete_skintype_service, update_skintype as update_skintype_service, get_skintype_table as get_skintype_table
from schema.diseases import DiseaseCreate, DiseaseUpdate, DiseaseRead
from schema.skintype import SkinTypeCreate, SkinTypeUpdate, SkinTypeRead
from database.database import get_db

router = APIRouter(prefix="/admin", tags=["admin"])

@router.get("/disease", summary="질환정보 테이블 조회", description="질환정보 테이블을 조회합니다")
def get_disease(db: Session = Depends(get_db)):
    response=get_disease_table(db)
    return ResultResponseModel(status_code=200, message="질환 테이블 조회 성공", data=response)

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
    response=delete_disease_service(db, disease_id)
    return ResultResponseModel(status_code=200, message="질병 삭제 성공", data=response)

@router.get("/skintype", summary="피부유형정보 테이블 조회", description="피부유형정보 테이블을 조회합니다")
def get_skintype(db: Session = Depends(get_db)):
    response=get_skintype_table(db)
    return ResultResponseModel(status_code=200, message="피부유형 테이블 조회 성공", data=response)

@router.post("/skintype", summary="새로운 피부유형 추가", description="새로운 피부유형을 추가합니다")
def create_skintype(skin_type: SkinTypeCreate, db: Session = Depends(get_db)):
    if not skin_type:
        return ResultResponseModel(status_code=400, message="피부유형 정보가 없습니다")
    return create_skintype_service(db, skin_type)

@router.put("/skintype/{skin_type_id}", summary="피부유형정보 수정", description="피부유형정보를 수정합니다")
def update_skintype(skin_type_id: int, skintype: SkinTypeUpdate, db: Session = Depends(get_db)):
    if not skin_type_id:
        return ResultResponseModel(status_code=400, message="피부유형 정보가 없습니다")
    return update_skintype_service(db, skin_type_id, skintype)

@router.delete("/skintype/{skin_type_id}", summary="피부유형 삭제", description="피부유형정보를 삭제합니다")
def delete_skintype(skin_type_id: int, db: Session = Depends(get_db)):
    if not skin_type_id:
        return ResultResponseModel(status_code=400, message="피부유형 정보가 없습니다")
    response=delete_skintype_service(db, skin_type_id)
    return ResultResponseModel(status_code=200, message="피부유형 삭제 성공", data=response)
