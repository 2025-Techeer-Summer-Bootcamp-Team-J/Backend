import requests
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
from fastapi import HTTPException
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import os
from dotenv import load_dotenv
import urllib3
import asyncio

# SSL 경고 비활성화
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

from schema.uv_index import UVIndexResponse

load_dotenv()

# 로거 설정
logger = logging.getLogger(__name__)

# Current UV Index API URL (무료, API 키 불필요)
CURRENT_UV_API_URL = "https://currentuvindex.com/api/v1/uvi"

# 지역 코드와 위도/경도 매핑
AREA_CODE_MAP = {
    "11B10101": {"name": "서울", "lat": 37.5665, "lon": 126.9780},
    "4215013700": {"name": "강릉", "lat": 37.7519, "lon": 128.8761},
    "28A00102": {"name": "인천", "lat": 37.4563, "lon": 126.7052}, 
    "26A00101": {"name": "부산", "lat": 35.1796, "lon": 129.0756},
    "11B20701": {"name": "수원", "lat": 37.2636, "lon": 127.0286}
}

def create_session() -> requests.Session:
    """안정적인 requests 세션을 생성합니다."""
    session = requests.Session()
    
    # 재시도 설정
    retry_strategy = Retry(
        total=3,
        backoff_factor=0.5,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"]
    )
    
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    
    # 기본 헤더 설정
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'application/json',
        'Accept-Language': 'ko-KR,ko;q=0.9,en;q=0.8',
        'Connection': 'keep-alive'
    })
    
    return session

async def fetch_single_area_uv(area_info: Dict[str, Any]) -> Optional[float]:
    """단일 지역의 UV 지수를 조회합니다."""
    params = {
        'latitude': area_info["lat"],
        'longitude': area_info["lon"]
    }
    
    session = create_session()
    
    try:
        response = session.get(
            CURRENT_UV_API_URL,
            params=params,
            timeout=(10, 30)
        )
        
        response.raise_for_status()
        data = response.json()
        
        if not data.get('ok', False):
            logger.warning(f"{area_info['name']} UV 데이터 조회 실패")
            return None  # None을 반환하여 실제 실패를 표시
        
        current_uv = data.get('now', {}).get('uvi', None)
        return float(current_uv) if current_uv is not None else None
        
    except Exception as e:
        logger.warning(f"{area_info['name']} UV 데이터 조회 중 오류: {e}")
        return None  # None을 반환하여 실제 실패를 표시
        
    finally:
        session.close()

async def fetch_korea_uv_range() -> UVIndexResponse:
    """대한민국 전체의 UV 지수 범위를 조회합니다."""
    current_time = datetime.now(timezone(timedelta(hours=9))).strftime('%Y년 %m월 %d일 %H시')
    
    logger.info("대한민국 전체 UV 지수 범위 조회 시작")
    
    try:
        # 모든 지역의 UV 지수를 병렬로 조회
        tasks = []
        for area_code, area_info in AREA_CODE_MAP.items():
            tasks.append(fetch_single_area_uv(area_info))
        
        # 현재 UV 지수들
        uv_values = await asyncio.gather(*tasks)
        
        # 유효한 값들만 필터링 (None이 아닌 값들, 0 포함)
        valid_uv_values = [uv for uv in uv_values if uv is not None]
        
        if not valid_uv_values:
            raise HTTPException(status_code=503, detail="UV 지수 데이터를 가져올 수 없습니다.")
        
        # 최저, 최고 계산
        min_uv = int(min(valid_uv_values))
        max_uv = int(max(valid_uv_values))
        
        logger.info(f"대한민국 UV 지수 범위: {min_uv}~{max_uv}")
        
        return UVIndexResponse(
            location="대한민국",
            date=current_time,
            now=f"{min_uv}~{max_uv}" if min_uv != max_uv else str(min_uv) # today 대신 now 사용
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"대한민국 UV 지수 범위 조회 중 오류: {e}")
        raise HTTPException(status_code=500, detail="서버 내부 오류가 발생했습니다.")

# 기존 함수는 호환성을 위해 유지
async def fetch_uv_index_from_kma(area_code: str) -> UVIndexResponse:
    """Current UV Index API에서 실제 UV 인덱스 데이터를 가져옵니다."""
    
    # 새로운 API로 리다이렉트
    return await fetch_korea_uv_range() 