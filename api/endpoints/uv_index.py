# api/endpoints/uv_index.py

from fastapi import APIRouter, HTTPException, Path

# 이 import 구문들이 절대 경로로 되어 있는지 확인!
from services import uv_index as uv_service
from schema.uv_index import UVIndexResponse

router = APIRouter(
    prefix="/uv-index",
    tags=["UV Index"]
)

@router.get("/{area_code}", response_model=UVIndexResponse, summary="특정 지역의 자외선 지수 조회")
async def get_uv_index(
    area_code: str = Path(..., min_length=8, max_length=10, description="조회할 지역의 코드", example="11B10101")
):
    try:
        uv_data = await uv_service.fetch_uv_index_from_kma(area_code)
        return uv_data
    except HTTPException as e:
        raise e