from fastapi import APIRouter, HTTPException
from services.uv_index import fetch_korea_uv_range
from schema.uv_index import UVIndexResponse

router = APIRouter(
    prefix="/uv-index",
    tags=["UV Index"]
)

@router.get(
    "/", 
    response_model=UVIndexResponse,
    summary="대한민국 자외선 지수 범위 조회",
    description="대한민국 전체의 자외선 지수 최저~최고 범위를 조회합니다."
)
async def get_korea_uv_range():
    """
    대한민국 전체의 자외선 지수 범위를 조회합니다.
    
    - 전국 주요 지역의 UV 지수를 실시간으로 조회
    - 최저~최고 범위로 표시
    - 어제와의 차이 제공
    """
    try:
        return await fetch_korea_uv_range()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="서버 내부 오류가 발생했습니다.") 