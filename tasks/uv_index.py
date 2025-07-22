from config.celery import app
from sqlalchemy.orm import Session
from database.database import get_db
from models.uv_index import UVIndex
from services.uv_index import fetch_korea_uv_range
from datetime import datetime
import pytz
import re
import logging
import asyncio

logger = logging.getLogger(__name__)

@app.task
def update_uv_index_task():
    """매시간 자외선 지수를 조회하여 데이터베이스에 저장하는 Celery 태스크"""
    logger.info("Celery 태스크: 자외선 지수 업데이트 시작")
    db: Session = next(get_db())
    try:
        # async 함수를 동기 환경에서 실행
        uv_response = asyncio.run(fetch_korea_uv_range())

        uv_index_value = None
        match = re.search(r'\d+', uv_response.now)
        if match:
            uv_index_value = int(match.group(0))

        parsed_date = datetime.strptime(uv_response.date, "%Y년 %m월 %d일 %H시")
        seoul_tz = pytz.timezone('Asia/Seoul')
        new_uv_record = UVIndex(
            date=parsed_date.date(),
            uv_Index=uv_index_value,
            create_at=datetime.now(seoul_tz)
        )
        db.add(new_uv_record)
        db.commit()
        db.refresh(new_uv_record)
        logger.info(f"자외선 지수 성공적으로 저장: {uv_response.now} (날짜: {uv_response.date})")

    except Exception as e:
        db.rollback()
        logger.error(f"자외선 지수 업데이트 중 오류 발생: {e}")
    finally:
        db.close()