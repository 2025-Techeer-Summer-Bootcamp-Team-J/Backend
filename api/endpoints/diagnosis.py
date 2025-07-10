from fastapi import APIRouter, Depends, File, UploadFile, Form, HTTPException, Request
from sqlalchemy.orm import Session
from models.diagnosis import Diagnosis
from database.database import get_db
from PIL import Image  # ← Image import 추가
from schema.diagnosis import DiagnosisResponse, box_to_schema, boxes_to_diagnosis_objs
import io  # ← io import 추가
from typing import List
from pydantic import BaseModel

router = APIRouter(
    prefix="/diagnoses",
    tags=["diagnoses"]
)


# <<< 명세에 맞게 수정된 부분 (POST /diagnoses) >>>
@router.post("", response_model=DiagnosisResponse, summary="진단 요청")
async def create_diagnosis(
    request: Request,
    user_id: int = Form(...), 
    file: UploadFile = File(...), 
    db: Session = Depends(get_db)
):
    # 파일이 이미지인지 간단히 확인
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail={"code": 400, "detail": "지원하지 않는 파일 형식입니다"})

    contents = await file.read()
    pil_image = Image.open(io.BytesIO(contents))
    model = request.app.state.model  # ← main.py에서 등록한 모델 사용
    results = model.predict(pil_image)
    
    result = results[0]
    diagnosis_objs = boxes_to_diagnosis_objs(result, user_id)
    saved_diagnoses = []
    for db_diagnosis in diagnosis_objs:
        db.add(db_diagnosis)
        db.commit()
        db.refresh(db_diagnosis)
        saved_diagnoses.append(db_diagnosis)
    return DiagnosisResponse(
        code=200,
        message="진단정보 생성 성공",
        data=[box_to_schema(d) for d in saved_diagnoses]
    )

@router.get("/users/{user_id}", response_model=DiagnosisResponse, summary="특정 사용자의 모든 진단 목록 조회")
def read_user_diagnoses(user_id: int, db: Session = Depends(get_db)):
    diagnoses = db.query(Diagnosis).filter(Diagnosis.user_id == user_id).all()
    return DiagnosisResponse(
        code=200,
        message="특정 사용자의 모든 진단 조회 성공",
        data=[box_to_schema(d) for d in diagnoses]
    )