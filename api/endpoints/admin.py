from fastapi import APIRouter, Depends, HTTPException, responses
from sqlalchemy.orm import Session
from schema.ResultResponseModel import ResultResponseModel
from services.diseases import create_disease as create_disease_service, delete_disease as delete_disease_service, update_disease as update_disease_service, get_disease_table as get_disease_table
from services.firestore_example import firestore_demo
from services.picture_merge import overlay_image
from services.skintype import create_skintype as create_skintype_service, delete_skintype as delete_skintype_service, update_skintype as update_skintype_service, get_skintype_table as get_skintype_table
from schema.diseases import DiseaseCreate, DiseaseUpdate, DiseaseRead
from schema.skintype import SkinTypeCreate, SkinTypeUpdate, SkinTypeRead
from services.diagnosis import get_diagnosis_table as get_diagnosis_table
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

@router.get("/diagnosis", summary="진단정보 테이블 조회", description="진단정보 테이블을 조회합니다")
def get_diagnosis(db: Session = Depends(get_db)):
    response=get_diagnosis_table(db)
    return ResultResponseModel(status_code=200, message="진단 테이블 조회 성공", data=response)


@router.get("/merge_test")
def merge_test():
    try:
        overlay_image(
        base_path="input/original.jpg",
        overlay_paths=[
            "output/red_area.jpg",
            "output/water_area.jpg",
            "output/texture_enhanced_lines.jpg"
        ],
        save_path="output/skin_analysis_overlay.jpg",
        alpha=100  # 투명도 (0~255)
        )
        return
    except Exception as e:
        raise HTTPException(400,f"{e}")

@router.get("/skin_score_graph_test")
def skin_score_graph_test():
    from services.skin_score_graph import plot_score_radar
    import json
    try:
        with open("output/response_json.txt", "r", encoding="utf-8") as f:
            data = json.load(f)
        result = data["result"]
        score_info = result["score_info"]
        print("score_info: ",score_info)
        plot_score_radar(score_info)
        return {"message": "그래프가 성공적으로 출력되었습니다."}
    except Exception as e:
        raise  HTTPException(400,f"{e}")

@router.get("/fire_store_test")
def fire_store_test():
    try:
        firestore_demo()
    except Exception as e:
        raise HTTPException(400,f'{e}')
    return responses.Response(status_code=200)
