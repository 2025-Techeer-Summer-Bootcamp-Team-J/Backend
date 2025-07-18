from fastapi import APIRouter, File, UploadFile, Form, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from database.database import get_db
from services.diseases import (
    get_all_diseases_name, 
    get_disease_by_id, 
    generate_disease_info_stream_service
)
from schema.ResultResponseModel import ResultResponseModel

router = APIRouter(prefix="/diseases", tags=["Diseases"])

@router.post("/generate-stream", summary="질병 정보 스트리밍 생성", description="사진과 질병명을 받아 SSE로 상세 정보를 스트리밍합니다.")
async def generate_disease_info_stream(
    disease_name: str = Form(...),
    image: UploadFile = File(...)
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
            generate_disease_info_stream_service(image_bytes, disease_name), 
            media_type="text/event-stream",
            headers=headers
        )
    except Exception as e:
        # Log the exception for debugging
        print(f"Error in generate_disease_info_stream: {e}")
        raise HTTPException(status_code=500, detail=f"스트리밍 생성 실패: {e}")


# --- Existing Endpoints ---

@router.get("", summary="전체 질환 목록 조회", description="전체 질환 목록 조회합니다.")
def get_all_diseases_name_endpoint(db: Session = Depends(get_db)):
    try:
        diseases = get_all_diseases_name(db)  
        return ResultResponseModel(
            status_code=200,
            message="전체 질환 목록 조회 성공",
            data=diseases
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail="전체 질환 목록 조회 실패")

@router.get("/{disease_id}", summary="질환 상세 조회", description="질환 상세 조회합니다.")
def get_disease_by_id_endpoint(disease_id: int, db: Session = Depends(get_db)):
    try:
        disease = get_disease_by_id(db, disease_id)
        return ResultResponseModel(
            status_code=200,
            message="질환 상세 조회 성공",
            data=disease
        )
    except HTTPException as e:
        raise HTTPException(status_code=400, detail="찾을 수 없는 질환id 입니다.")
    except Exception as e:
        raise HTTPException(status_code=500, detail="등록되지 않은 질환입니다.")
