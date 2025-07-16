from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from database.database import get_db
from models.uv_index import UVIndex
from schema.uv_index import UVIndexResponse
from schema.ResultResponseModel import ResultResponseModel
from services.uv_index import fetch_korea_uv_range # 추가: 실시간 조회를 위해 임포트
from datetime import datetime
import pytz
import re

router = APIRouter(
    prefix="/uv-index",
    tags=["UV Index"]
)

@router.get(
    "",
    response_model=ResultResponseModel, # ResultResponseModel로 감싸서 반환
    summary="가장 최근 자외선 지수 조회 (DB)",
    description="데이터베이스에 저장된 가장 최근의 자외선 지수 기록을 조회합니다."
)
async def get_latest_uv_index(db: Session = Depends(get_db)):
    """
    데이터베이스에 저장된 가장 최근의 자외선 지수 기록을 조회합니다.
    """
    try:
        latest_uv_record = db.query(UVIndex).order_by(UVIndex.create_at.desc()).first()

        if not latest_uv_record:
            # 데이터가 없는 경우 404 대신 성공 응답에 빈 데이터 또는 메시지 포함
            return ResultResponseModel(
                status_code=200,
                message="저장된 자외선 지수 데이터가 없습니다.",
                data=None
            )

        # UVIndexResponse 스키마를 사용하여 데이터 포맷팅
        uv_data = UVIndexResponse(
            location="대한민국",
            date=latest_uv_record.create_at.strftime("%Y년%m월%d일%H시"),
            now=str(latest_uv_record.uv_Index)
        )
        return ResultResponseModel(
            status_code=200,
            message="가장 최근 자외선 지수 조회 성공",
            data=uv_data
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"서버 내부 오류가 발생했습니다: {str(e)}")

# 새로 추가할 실시간 자외선 지수 조회 API 엔드포인트
@router.post(
    "",
    response_model=UVIndexResponse,
    summary="대한민국 자외선 지수 저장",
    description="대한민국 전체의 자외선 지수 최저~최고 범위를 실시간으로 조회하고 DB에 저장합니다."
)
async def save_korea_uv_range_live(db: Session = Depends(get_db)):
    """
    외부 API를 통해 대한민국 전체의 자외선 지수 범위를 실시간으로 조회하고 데이터베이스에 저장합니다.
    """
    try:
        try:
            uv_response = await fetch_korea_uv_range()
        except HTTPException as e:
            raise HTTPException(status_code=e.status_code, detail=f"자외선 지수 조회 실패: {e.detail}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"자외선 지수 조회 실패: {str(e)}")

        # uv_Index 값 추출 (예: "1~5"에서 1 또는 5, "3"에서 3)
        uv_index_value = None
        match = re.search(r'\d+', uv_response.now)
        if match:
            uv_index_value = int(match.group(0))

        try:
            # DB에 저장
            # uv_response.date는 'YYYY년 MM월 DD일 HH시' 형식으로 오므로, 파싱 형식 변경
            parsed_date = datetime.strptime(uv_response.date, "%Y년 %m월 %d일 %H시")
            new_uv_record = UVIndex(
                date=parsed_date.date(), # 날짜만 저장
                uv_Index=uv_index_value,
                create_at=datetime.now(pytz.timezone('Asia/Seoul'))
            )
            db.add(new_uv_record)
            db.commit()
            db.refresh(new_uv_record)
        except Exception as e:
            db.rollback()
            raise HTTPException(status_code=500, detail=f"자외선 지수 저장 실패: {str(e)}")

        return uv_response
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"서버 내부 오류가 발생했습니다: {str(e)}") 