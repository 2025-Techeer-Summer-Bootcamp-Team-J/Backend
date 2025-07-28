from fastapi import APIRouter, Depends, File, UploadFile, Form, HTTPException, Request
from sqlalchemy.orm import Session
from config.celery import app
from models.diagnosis import Diagnosis
from database.database import get_db
import json
from schema.Task import TaskStartResponse, TaskStatusResponse
import base64
from tasks.diagnosis import process_diagnosis_task
from schema.diagnosis import DiagnosisResponse, box_to_schema, SimplifiedDiagnosisResponse, aggregate_and_normalize_diagnoses, UserDiagnosisResponse, diagnosis_to_simple_schema, UserDiagnosisBasicResponse, diagnosis_to_basic_schema, AdditionalInfoRequest, AdditionalInfoResponse, AdditionalInfoSuccessResponse
from inference_sdk import InferenceHTTPClient
import tempfile
import os
from services.diagnosis import delete_diagnosis, save_diagnosis_data, save_additional_info, get_additional_info
from fastapi.responses import StreamingResponse
from services.diagnosis import generate_disease_info_stream_service
from schema.diagnosis_save import SaveDiagnosisResponse, SavedDiagnosisResponse
from crud.storage import upload_image
from schema.ResultResponseModel import ResultResponseModel

router = APIRouter(
    prefix="/diagnoses",
    tags=["diagnoses"]
)

# <<< 진단 이미지 조회 API >>>
@router.get("/{diagnosis_id}/image", summary="진단 이미지 조회", description="진단 ID로 진단 시 사용한 이미지를 조회합니다.")
async def get_diagnosis_image(
    diagnosis_id: int,
    db: Session = Depends(get_db)
):
    """
    진단 ID로 진단 시 사용한 이미지를 조회합니다.
    """
    try:
        diagnosis = db.query(Diagnosis).filter(
            Diagnosis.diagnosis_id == diagnosis_id,
            Diagnosis.is_deleted == False
        ).first()

        if not diagnosis:
            raise HTTPException(status_code=404, detail="진단 정보를 찾을 수 없습니다")

        # image URL이 None이면 예외 처리
        if not diagnosis.image:
            raise HTTPException(status_code=404, detail="해당 진단에 저장된 이미지가 없습니다")

        return ResultResponseModel(status_code=200, message="이미지 조회 성공", data={"image_url": diagnosis.image})

    except HTTPException as e:
        # HTTPException은 그대로 전달
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"이미지 조회 중 오류가 발생했습니다: {str(e)}")

# <<< 비동기 진단 요청 API >>>
@router.post("",
             response_model=TaskStartResponse,
             summary="비동기 진단 요청",
             description="이미지를 업로드하여 비동기 진단을 요청합니다")
async def create_diagnosis_async(
    user_id: str = Form(...),
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
            # 태스크 성공 시 결과를 그대로 반환
            try:
                result_data = task.result
                if result_data and isinstance(result_data, dict):
                    # 태스크에서 이미 SimplifiedDiagnosisResponse 형태로 반환하므로 그대로 사용
                    return TaskStatusResponse(
                        code=200,
                        message="태스크가 성공적으로 완료되었습니다",
                        task_id=task_id,
                        state=state,
                        progress=None,
                        result=result_data,  # dict 형태 그대로 전달
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
    user_id: str = Form(...), 
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

@router.get("/users/{user_id}/diagnoses", response_model=UserDiagnosisBasicResponse, summary="유저 모든 진단 조회", description="유저 모든 진단 목록을 조회합니다")
def read_user_diagnoses(user_id: str, db: Session = Depends(get_db)):
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
            return UserDiagnosisBasicResponse(
                code=200,
                message="해당 사용자의 진단 데이터가 없습니다",
                data=[]
            )

        # 정상적인 경우 진단 데이터 반환
        diagnosis_data = []
        for d in diagnoses:
            try:
                diagnosis_data.append(diagnosis_to_basic_schema(d))
            except Exception as e:
                print(f"진단 데이터 변환 중 오류 발생 (ID: {getattr(d, 'id', 'Unknown')}): {e}")
                continue

        return UserDiagnosisBasicResponse(
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
def delete_user_diagnosis(user_id: str, diagnosis_id: int, db: Session = Depends(get_db)):

    deleted_diagnosis = delete_diagnosis(db, user_id, diagnosis_id)

    deleted_data_schema = box_to_schema(deleted_diagnosis)

    return DiagnosisResponse(
        code=200,
        message="진단 정보 삭제 성공",
        data=[deleted_data_schema]
    )

@router.get("/{diagnosis_id}", response_model=SavedDiagnosisResponse, summary="진단 세부 정보 조회", description="진단 ID를 통해 저장된 원본 진단 데이터와 연관된 질병 정보를 조회합니다.")
def get_diagnosis_details(diagnosis_id: int, db: Session = Depends(get_db)):
    """
    진단 ID를 통해 저장된 원본 진단 데이터와 연관된 질병 정보를 조회합니다.
    """
    diagnosis = db.query(Diagnosis).filter(Diagnosis.diagnosis_id == diagnosis_id, Diagnosis.is_deleted == False).first()

    if not diagnosis:
        raise HTTPException(
            status_code=404,
            detail={"code": 404, "message": "진단 정보를 찾을 수 없습니다."}
        )

    # 저장된 원본 데이터를 그대로 반환
    try:
        # detailed_info_json에서 원본 데이터 파싱
        detailed_info = {}
        if diagnosis.detailed_info_json:
            detailed_info = json.loads(diagnosis.detailed_info_json)
        
        # 연관된 질병 정보 조회
        diseases_data = [
            {
                "disease_id": disease.disease_id,
                "main_symptom": disease.main_symptom,
                "disease_name": disease.disease_name,
                "description": disease.description,
                "precautions": disease.precautions
            }
            for disease in diagnosis.diseases if not disease.is_deleted
        ]
        
        # 저장된 데이터와 동일한 구조로 반환 + 질병 정보 추가
        saved_data = {
            "diagnosis_id": diagnosis.diagnosis_id,
            "user_id": diagnosis.user_id,
            "image_base64": diagnosis.image or "",
            "disease_name": diagnosis.disease_name,
            "image_analysis": detailed_info.get("image_analysis", {}),
            "text_analysis": detailed_info.get("text_analysis", {}),
            "diseases": diseases_data
        }
        
        return SavedDiagnosisResponse(
            code=200,
            message="진단 세부 정보 및 질병 정보 조회 성공",
            data=saved_data
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={"code": 500, "message": f"진단 데이터 변환 중 오류가 발생했습니다: {str(e)}"}
        )

# <<< 질병 정보 스트리밍 생성 API >>>
@router.post("/generate-stream", summary="질병 정보 스트리밍 생성", description="사진과 질병명을 받아 SSE로 상세 정보를 스트리밍합니다. 스트리밍이 완료되면 자동으로 데이터베이스에 저장됩니다.")
async def generate_disease_info_stream(
    user_id: str = Form(...),
    disease_name: str = Form(...),
    image: UploadFile = File(...),
    symptoms: str | None = Form(None),
    db: Session = Depends(get_db)
):
    try:
        image_bytes = await image.read()
        
        # SSE를 위한 적절한 헤더 설정
        headers = {
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Cache-Control",
            "X-Accel-Buffering": "no"  # nginx 버퍼링 비활성화
        }
        
        return StreamingResponse(
            generate_disease_info_stream_service(image_bytes, disease_name, symptoms, user_id), 
            media_type="text/event-stream",
            headers=headers
        )
    except Exception as e:
        # 디버깅을 위해 예외 기록
        print(f"Error in generate_disease_info_stream: {e}")
        raise HTTPException(status_code=500, detail=f"스트리밍 생성 실패: {e}")


@router.post("/save",
             response_model=SaveDiagnosisResponse,
             summary="진단 결과 저장",
             description="스트리밍 완료 후 진단 결과 데이터를 데이터베이스에 저장합니다")
async def save_diagnosis_result(
    user_id: str,
    image: UploadFile = File(...),
    image_analysis: str = Form(...),
    text_analysis: str = Form(...),
    disease_name: str = Form(...),
    db: Session = Depends(get_db)
):
    """
    스트리밍 완료 후 진단 결과 데이터를 저장합니다.
    """
    try:
        image_analysis_dict = json.loads(image_analysis)
        text_analysis_dict = json.loads(text_analysis)
        image_file = image
        image_url = await upload_image(image_file)
        
        diagnosis = save_diagnosis_data(
            db=db,
            user_id=user_id,
            image=image_url,
            image_analysis_data=image_analysis_dict,
            text_analysis_data=text_analysis_dict,
            disease_name=disease_name
        )
        
        return SaveDiagnosisResponse(
            diagnosis_id=diagnosis.diagnosis_id,
            message="진단 결과가 성공적으로 저장되었습니다."
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"진단 결과 저장 중 오류가 발생했습니다: {str(e)}"
        )

# <<< 진단 보조 정보 저장 API >>>
@router.post("/{diagnosis_id}/additional",
             response_model=AdditionalInfoSuccessResponse,
             summary="진단 보조 정보 저장",
             description="진단의 보조 정보(주요 증상, 가려움 정도, 시작 시점, 보조 정보 텍스트)를 저장합니다")
async def save_diagnosis_additional_info(
    diagnosis_id: int,
    request: AdditionalInfoRequest,
    db: Session = Depends(get_db)
):
    """
    진단의 보조 정보를 저장합니다.
    """
    try:
        # 가려움 정도 유효성 검사
        if request.itching_level is not None and (request.itching_level < 1 or request.itching_level > 9):
            raise HTTPException(status_code=400, detail="가려움 정도는 1-9 사이의 값이어야 합니다")
        
        # 증상 지속 기간 유효성 검사
        valid_durations = ["오늘", "2-3일 전", "1주일 이상", "오래 전"]
        if request.symptom_duration and request.symptom_duration not in valid_durations:
            raise HTTPException(status_code=400, detail="올바른 증상 지속 기간을 선택해주세요")
        
        # 주요 증상 유효성 검사
        valid_symptoms = ["가려움", "따가움/동통", "붉은 반점", "각질/비듬", "진물/수포", "피부 간조", "부르지/이드름"]
        for symptom in request.main_symptoms:
            if symptom not in valid_symptoms:
                raise HTTPException(status_code=400, detail=f"올바르지 않은 증상입니다: {symptom}")
        
        # 먼저 해당 진단이 존재하는지 확인 (user_id는 요청에서 받거나 JWT에서 추출)
        diagnosis = db.query(Diagnosis).filter(
            Diagnosis.diagnosis_id == diagnosis_id,
            Diagnosis.is_deleted == False
        ).first()
        
        if not diagnosis:
            raise HTTPException(status_code=404, detail="진단 정보를 찾을 수 없습니다")
        
        # 보조 정보 저장
        updated_diagnosis = save_additional_info(
            db=db,
            user_id=diagnosis.user_id,  # 진단에서 user_id 가져오기
            diagnosis_id=diagnosis_id,
            main_symptoms=request.main_symptoms,
            itching_level=request.itching_level,
            symptom_duration=request.symptom_duration,
            additional_notes=request.additional_notes
        )
        
        # 저장된 정보 조회해서 응답 구성
        additional_info_data = get_additional_info(
            db=db,
            user_id=diagnosis.user_id,
            diagnosis_id=diagnosis_id
        )
        
        response_data = AdditionalInfoResponse(**additional_info_data)
        
        return AdditionalInfoSuccessResponse(
            code=200,
            message="보조 정보가 성공적으로 저장되었습니다",
            data=response_data
        )
        
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"보조 정보 저장 중 오류가 발생했습니다: {str(e)}"
        )

# <<< 진단 보조 정보 조회 API >>>
@router.get("/{diagnosis_id}/additional",
            response_model=AdditionalInfoSuccessResponse,
            summary="진단 보조 정보 조회",
            description="특정 진단의 보조 정보를 조회합니다")
async def get_diagnosis_additional_info(
    diagnosis_id: int,
    user_id: str,  # Query parameter로 받거나 JWT에서 추출
    db: Session = Depends(get_db)
):
    """
    특정 진단의 보조 정보를 조회합니다.
    """
    try:
        # 보조 정보 조회
        additional_info_data = get_additional_info(
            db=db,
            user_id=user_id,
            diagnosis_id=diagnosis_id
        )
        
        response_data = AdditionalInfoResponse(**additional_info_data)
        
        return AdditionalInfoSuccessResponse(
            code=200,
            message="보조 정보 조회 성공",
            data=response_data
        )
        
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"보조 정보 조회 중 오류가 발생했습니다: {str(e)}"
        )
