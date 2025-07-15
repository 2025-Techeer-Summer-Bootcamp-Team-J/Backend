from fastapi import APIRouter, Depends, File, UploadFile, Form, HTTPException, Request, Path
from sqlalchemy.orm import Session
from config.celery import app
from models.diagnosis import Diagnosis
from database.database import get_db

from schema.Task import TaskStartResponse, TaskStatusResponse, TaskProgressInfo

import base64
from tasks.diagnosis import process_diagnosis_task

from PIL import Image  # ← Image import 추가
from schema.diagnosis import DiagnosisResponse, box_to_schema, BoundingBox, prediction_to_diagnosis_obj
import io  # ← io import 추가
from typing import List
from pydantic import BaseModel
from inference_sdk import InferenceHTTPClient
import tempfile
import shutil
import os
from services.diagnosis import delete_diagnosis



router = APIRouter(
    prefix="/diagnoses",
    tags=["diagnoses"]
)

# <<< 비동기 진단 요청 API >>>
@router.post("",
             response_model=TaskStartResponse, 
             summary="비동기 진단 요청",
             description="이미지를 업로드하여 비동기 진단을 요청합니다")
async def create_diagnosis_async(
    user_id: int = Form(...), 
    file: UploadFile = File(...), 
):
    """
    이미지를 업로드하여 비동기 진단을 요청합니다.
    태스크 ID를 반환하여 진행 상황을 추적할 수 있습니다.
    """
    # 파일이 이미지인지 간단히 확인
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=400, 
            detail={"code": 400, "detail": "지원하지 않는 파일 형식입니다"}
        )

    try:
        # 이미지 파일을 Base64로 인코딩
        contents = await file.read()
        image_base64 = base64.b64encode(contents).decode('utf-8')
        
        # Celery 태스크 실행 (Request와 db 객체 제거)
        task = process_diagnosis_task.delay(user_id, image_base64)
        
        return TaskStartResponse(
            code=200,
            message="진단 요청이 성공적으로 접수되었습니다",
            task_id=task.id,
            status="PENDING"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={"code": 500, "detail": f"진단 요청 처리 중 오류가 발생했습니다: {str(e)}"}
        )


# <<< 태스크 상태 조회 API >>>
@router.get("/tasks/{task_id}/status",
            response_model=TaskStatusResponse,
            summary="태스크 상태 조회",
            description="진단 태스크의 현재 상태를 조회합니다")
def get_task_status(task_id: str):
    """
    태스크 ID를 통해 진단 태스크의 현재 상태를 조회합니다.
    """
    
    try:
        # 태스크 ID 유효성 검사
        if not task_id or task_id.strip() == "":
            raise HTTPException(
                status_code=400,
                detail={"code": 400, "detail": "유효하지 않은 태스크 ID입니다"}
            )
            
        # Celery에서 태스크 상태 조회
        task = app.AsyncResult(task_id)
        
        # 태스크 상태 확인
        state = task.state
        
        if state == 'PENDING':
            return TaskStatusResponse(
                code=200,
                message="태스크가 대기 중입니다",
                task_id=task_id,
                state=state,
                progress=None,
                result=None,
                error=None
            )
        elif state == 'SUCCESS':
            # 태스크 성공 시 결과를 DiagnosisResponse로 변환
            try:
                result_data = task.result
                if result_data and isinstance(result_data, dict):
                    # dict 형태의 결과를 DiagnosisResponse로 변환
                    diagnosis_result = DiagnosisResponse(**result_data)
                    return TaskStatusResponse(
                        code=200,
                        message="태스크가 성공적으로 완료되었습니다",
                        task_id=task_id,
                        state=state,
                        progress=None,
                        result=diagnosis_result,
                        error=None
                    )
                else:
                    # 결과가 없거나 형식이 잘못된 경우
                    return TaskStatusResponse(
                        code=200,
                        message="태스크가 완료되었지만 결과가 없습니다",
                        task_id=task_id,
                        state=state,
                        progress=None,
                        result=None,
                        error=None
                    )
            except Exception as e:
                # 결과 파싱 실패
                return TaskStatusResponse(
                    code=500,
                    message="태스크 결과 처리 중 오류가 발생했습니다",
                    task_id=task_id,
                    state=state,
                    progress=None,
                    result=None,
                    error=f"결과 파싱 오류: {str(e)}"
                )
        elif state == 'FAILURE':
            error_info = str(task.info) if task.info else "알 수 없는 오류"
            return TaskStatusResponse(
                code=500,
                message="태스크 실행 중 오류가 발생했습니다",
                task_id=task_id,
                state=state,
                progress=None,
                result=None,
                error=error_info
            )
        elif state == 'RETRY':
            return TaskStatusResponse(
                code=200,
                message="태스크가 재시도 중입니다",
                task_id=task_id,
                state=state,
                progress=None,
                result=None,
                error=None
            )
        else:  # PROGRESS, STARTED 등
            return TaskStatusResponse(
                code=200,
                message=f"태스크가 진행 중입니다 (상태: {state})",
                task_id=task_id,
                state=state,
                progress=None,
                result=None,
                error=None
            )
            
    except ConnectionError as e:
        raise HTTPException(
            status_code=503,
            detail={"code": 503, "detail": f"Celery 브로커에 연결할 수 없습니다. Redis 또는 RabbitMQ 서비스를 확인해주세요: {str(e)}"}
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={"code": 500, "detail": f"태스크 상태 조회 중 오류가 발생했습니다: {str(e)}"}
        )

# <<< 기존 동기 진단 API (호환성을 위해 유지) >>>
@router.post("/sync",
             response_model=DiagnosisResponse, 
             summary="동기 진단 요청 (레거시)",
             description="이미지를 업로드하여 동기 진단을 요청합니다")
async def create_diagnosis_sync(
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

    if not user_id:
        raise HTTPException(status_code=500, detail="없는 사용자 입니다")

    diagnoses = db.query(Diagnosis).filter(Diagnosis.user_id == user_id).all()

    if not diagnoses:
        raise HTTPException(status_code=500, detail="진단 데이터가 없습니다")

    return {"code": 200, "message": "특정 사용자의 모든 진단 조회 성공", 
    "data": [box_to_schema(d) for d in diagnoses]
    }

@router.delete("/{diagnosis_id}", summary="진단 삭제", description="진단 정보를 삭제합니다")
def delete_user_diagnosis(user_id: int, diagnosis_id: int, db: Session = Depends(get_db)):

    deleted_diagnosis = delete_diagnosis(db, user_id, diagnosis_id)

    deleted_data_schema = box_to_schema(deleted_diagnosis)

    return DiagnosisResponse(
        code=200, 
        message="진단 정보 삭제 성공", 
        data=[deleted_data_schema]
    )