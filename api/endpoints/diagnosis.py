from fastapi import APIRouter, Depends, File, UploadFile, Form, HTTPException, Request
from sqlalchemy.orm import Session
from models.diagnosis import Diagnosis
from database.database import get_db
from PIL import Image  # ← Image import 추가
from schema.diagnosis import DiagnosisResponse, box_to_schema, BoundingBox, prediction_to_diagnosis_obj
import io  # ← io import 추가
from typing import List
from pydantic import BaseModel
from inference_sdk import InferenceHTTPClient
import tempfile
import shutil
import os



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

    # 업로드 파일을 임시 파일로 저장
    with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name

    # Roboflow inference API 호출
    client = InferenceHTTPClient(
        api_url="https://serverless.roboflow.com",
        api_key=os.environ.get("ROBOFLOW_API_KEY")
    )
    result = client.run_workflow(
        workspace_name="skin-classification-tm1gk",
        workflow_id="detect-and-classify",
        images={"image": tmp_path},
        use_cache=True
    )

    # 임시 파일 삭제
    os.remove(tmp_path)

    # Roboflow 결과 파싱
    predictions = []
    # result가 리스트라면 첫 번째 요소를 사용
    if isinstance(result, list) and len(result) > 0:
        result = result[0]
    if isinstance(result, dict):
        output = result.get('output', {})
        predictions_dict = output.get('predictions', {})
        predictions = predictions_dict.get('predictions', [])

    # DB 저장 및 응답 생성
    saved_diagnoses = []
    print("Roboflow result:", result)
    print("파싱된 predictions:", predictions)
    for pred in predictions:
        try:
            print("예측 결과 pred:", pred)
            db_diagnosis = prediction_to_diagnosis_obj(pred, user_id)
            db.add(db_diagnosis)
            db.commit()
            db.refresh(db_diagnosis)
            saved_diagnoses.append(db_diagnosis)
        except Exception as e:
            print("DB 저장 중 오류:", e)
    print("최종 saved_diagnoses:", saved_diagnoses)

    return DiagnosisResponse(
        code=200,
        message="진단정보 생성 성공",
        data=[box_to_schema(d) for d in saved_diagnoses]
    )

@router.get("/users/{user_id}", response_model=DiagnosisResponse, summary="유저 진단 조회", description="유저 진단 목록을 조회합니다")
def read_user_diagnoses(user_id: int, db: Session = Depends(get_db)):
    diagnoses = db.query(Diagnosis).filter(Diagnosis.user_id == user_id).all()
    print("diagnoses 타입:", type(diagnoses))
    if diagnoses:
        print("첫 번째 진단 객체 타입:", type(diagnoses[0]))
        print("첫 번째 진단 x1 값과 타입:", diagnoses[0].x1, type(diagnoses[0].x1))
    else:
        print("diagnoses가 비어있음")
    if not user_id:
        raise HTTPException(status_code=500, detail="없는 사용자 입니다")
    diagnoses = db.query(Diagnosis).filter(Diagnosis.user_id == user_id).all()
    if not diagnoses:
        raise HTTPException(status_code=500, detail="진단 데이터가 없습니다")
    return {"code": 200, "message": "특정 사용자의 모든 진단 조회 성공", 
    "data": [box_to_schema(d) for d in diagnoses]
    }




