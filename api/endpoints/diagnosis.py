from fastapi import APIRouter, Depends, File, UploadFile, Form, HTTPException, Request
from sqlalchemy.orm import Session
from config.celery import app
from models.diagnosis import Diagnosis
from database.database import get_db

from schema.detailed_disease_info import DetailedDiseaseInfoRead, DetailedDiseaseInfoResponse
import json # For json.loads

from schema.Task import TaskStartResponse, TaskStatusResponse, TaskProgressInfo

import base64
from tasks.diagnosis import process_diagnosis_task

from PIL import Image  # ← Image import 추가
from schema.diagnosis import DiagnosisResponse, box_to_schema, BoundingBox, SimplifiedDiagnosisResponse, aggregate_and_normalize_diagnoses, SimplifiedDiagnosisData, DiagnosisData, UserDiagnosisResponse, diagnosis_to_simple_schema
import io  # ← io import 추가
from typing import List
from inference_sdk import InferenceHTTPClient
import tempfile
import shutil
import os
from services.diagnosis import delete_diagnosis, generate_and_save_detailed_disease_info
from schema.ResultResponseModel import ResultResponseModel



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
    태스크를 백그라운드에서 실행하고 즉시 태스크 ID를 반환합니다.
    태스크 상태는 /diagnoses/tasks/{task_id}/status 엔드포인트로 확인할 수 있습니다.
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

        # Celery 태스크를 백그라운드에서 실행 (결과를 기다리지 않음)
        task = process_diagnosis_task.delay(user_id, image_base64)

        # 즉시 태스크 ID와 상태 반환
        return TaskStartResponse(
            code=200,
            message="진단 태스크가 성공적으로 시작되었습니다",
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
            # 태스크 성공 시 결과를 SimplifiedDiagnosisResponse로 변환
            try:
                result_data = task.result
                if result_data and isinstance(result_data, dict):
                    # dict 형태의 결과를 SimplifiedDiagnosisResponse로 변환
                    diagnosis_result = SimplifiedDiagnosisResponse(**result_data)
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
             response_model=SimplifiedDiagnosisResponse,
             summary="동기 진단 요청 (간소화된 응답)",
             description="이미지를 업로드하여 동기 진단을 요청합니다. 같은 질환명의 신뢰도를 합쳐서 100분위로 정규화하여 반환합니다.")
async def create_diagnosis_sync(
    request: Request,
    user_id: int = Form(...), 
    file: UploadFile = File(...), 
    db: Session = Depends(get_db)
):
    # 파일이 이미지인지 간단히 확인
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail={"code": 400, "detail": "지원하지 않는 파일 형식입니다"})

    try:
        # 이미지를 base64로 인코딩
        contents = await file.read()
        image_base64 = base64.b64encode(contents).decode('utf-8')

        # Base64를 이미지 파일로 변환하여 임시 파일로 저장
        image_data = base64.b64decode(image_base64)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
            tmp.write(image_data)
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
        if isinstance(result, list) and len(result) > 0:
            result = result[0]
        if isinstance(result, dict):
            output = result.get('output', {})
            predictions_dict = output.get('predictions', {})
            predictions = predictions_dict.get('predictions', [])

        # 간소화된 응답 생성
        simplified_data = aggregate_and_normalize_diagnoses(predictions, image_base64)

        return SimplifiedDiagnosisResponse(
            code=200,
            message="진단정보 생성 성공",
            data=simplified_data
        )

    except Exception as e:
        print(f"동기 진단 처리 중 오류: {e}")
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail={"code": 500, "detail": f"진단 처리 중 오류가 발생했습니다: {str(e)}"}
        )

@router.get("/users/{user_id}", response_model=UserDiagnosisResponse, summary="유저 모든 진단 조회", description="유저 모든 진단 목록을 조회합니다")
def read_user_diagnoses(user_id: int, db: Session = Depends(get_db)):
    try:
        # user_id 유효성 검사 - 0보다 큰 양수여야 함
        if user_id <= 0:
            raise HTTPException(status_code=400, detail={"code": 400, "message": "유효하지 않은 사용자 ID입니다"})

        # 삭제되지 않은 진단 데이터만 조회 (diseases 관계도 함께 로드)
        diagnoses = db.query(Diagnosis).filter(
            Diagnosis.user_id == user_id,
            Diagnosis.is_deleted == False
        ).all()

        # 진단 데이터가 없는 경우 빈 배열로 응답 (404 대신 200으로 처리)
        if not diagnoses:
            return UserDiagnosisResponse(
                code=200,
                message="해당 사용자의 진단 데이터가 없습니다",
                data=[]
            )

        # 정상적인 경우 진단 데이터 반환
        diagnosis_data = []
        for d in diagnoses:
            try:
                diagnosis_data.append(diagnosis_to_simple_schema(d))
            except Exception as e:
                print(f"진단 데이터 변환 중 오류 발생 (ID: {getattr(d, 'id', 'Unknown')}): {e}")
                continue

        return UserDiagnosisResponse(
            code=200,
            message="특정 사용자의 모든 진단 조회 성공",
            data=diagnosis_data
        )

    except HTTPException:
        # HTTPException은 다시 발생시킴
        raise
    except Exception as e:
        print(f"사용자 진단 조회 중 예상치 못한 오류 발생: {e}")
        raise HTTPException(
            status_code=500,
            detail={"code": 500, "message": f"진단 데이터 조회 중 오류가 발생했습니다: {str(e)}"}
        )

@router.delete("/{diagnosis_id}", summary="진단 삭제", description="진단 정보를 삭제합니다")
def delete_user_diagnosis(user_id: int, diagnosis_id: int, db: Session = Depends(get_db)):

    deleted_diagnosis = delete_diagnosis(db, user_id, diagnosis_id)

    deleted_data_schema = box_to_schema(deleted_diagnosis)

    return DiagnosisResponse(
        code=200,
        message="진단 정보 삭제 성공",
        data=[deleted_data_schema]
    )

@router.get("/{diagnosis_id}", response_model=SimplifiedDiagnosisResponse, summary="진단 세부 정보 조회", description="진단 ID를 통해 진단 세부 정보를 조회합니다.")
def get_diagnosis_details(diagnosis_id: int, db: Session = Depends(get_db)):
    """
    진단 ID를 통해 진단 세부 정보를 조회합니다.
    """
    diagnosis = db.query(Diagnosis).filter(Diagnosis.diagnosis_id == diagnosis_id).first()

    if not diagnosis:
        raise HTTPException(
            status_code=404,
            detail={"code": 404, "message": "진단 정보를 찾을 수 없습니다."}
        )

    # SimplifiedDiagnosisResponse 스키마에 맞게 데이터 변환
    try:
        simplified_data = diagnosis_to_simple_schema(diagnosis)
        return SimplifiedDiagnosisResponse(
            code=200,
            message="진단 세부 정보 조회 성공",
            data=simplified_data
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={"code": 500, "message": f"진단 데이터 변환 중 오류가 발생했습니다: {str(e)}"}
        )

@router.post("/generate-and-save", summary="진단 정보 생성 및 저장", description="사진과 질병명을 받아 상세 진단 정보를 생성하고 DB에 저장합니다.")
async def generate_and_save_detailed_disease_info_endpoint(
    disease_name: str = Form(...),
    image: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    try:
        image_bytes = await image.read()
        record_id = await generate_and_save_detailed_disease_info(db, image_bytes, disease_name)
        return ResultResponseModel(
            status_code=200,
            message="질병 정보 생성 및 저장 성공",
            data={"id": record_id}
        )
    except Exception as e:
        print(f"Error in generate_and_save_detailed_disease_info_endpoint: {e}")
        raise HTTPException(status_code=500, detail=f"질병 정보 생성 및 저장 실패: {e}")

@router.get("/detailed/{diagnosis_id}", response_model=DetailedDiseaseInfoResponse, summary="저장된 질병 상세 정보 조회", description="저장된 질병 상세 정보를 ID로 조회합니다.")
def get_detailed_disease_info_by_id(
    diagnosis_id: int,
    db: Session = Depends(get_db)
):
    try:
        detailed_info = db.query(DetailedDiseaseInfo).filter(DetailedDiseaseInfo.id == diagnosis_id).first()
        if not detailed_info:
            raise HTTPException(status_code=404, detail={"code": 404, "message": "상세 질병 정보를 찾을 수 없습니다."})
        
        # Convert JSON strings back to Python objects for Pydantic model
        if detailed_info.precautions:
            detailed_info.precautions = json.loads(detailed_info.precautions)
        if detailed_info.management:
            detailed_info.management = json.loads(detailed_info.management)

        return DetailedDiseaseInfoResponse(
            code=200,
            message="상세 질병 정보 조회 성공",
            data=DetailedDiseaseInfoRead.model_validate(detailed_info)
        )
    except HTTPException as e:
        raise e
    except Exception as e:
        print(f"Error in get_detailed_disease_info_by_id: {e}")
        raise HTTPException(status_code=500, detail=f"상세 질병 정보 조회 실패: {e}")