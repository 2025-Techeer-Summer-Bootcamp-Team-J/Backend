# services/uv_index.py

import httpx
from fastapi import HTTPException
from datetime import datetime
import json

from dotenv import load_dotenv
import os

load_dotenv()

KMA_API_KEY = os.getenv("KMA_API_KEY")
KMA_API_URL = "https://apis.data.go.kr/1360000/LivingWthrIdxServiceV4/getUVIdxV4"

if not KMA_API_KEY:
    raise ValueError("KMA_API_KEY가 설정되지 않았습니다. Backend 폴더의 .env 파일을 확인해주세요.")

# --- 이 부분의 경로가 바뀝니다! ---
# 이전: from .schemas.uv_index import UVIndexResponse
# 변경: from schemas.uv_index import UVIndexResponse
from schema.uv_index import UVIndexResponse

AREA_CODE_MAP = {
    "11B10101": "서울",
    "4215013700": "강릉",
    "28A00102": "인천",
    "26A00101": "부산",
    "11B20701": "수원"
}

async def fetch_uv_index_from_kma(area_code: str) -> UVIndexResponse:
    # 이 함수의 내용은 이전과 동일합니다.
    if area_code not in AREA_CODE_MAP:
        raise HTTPException(status_code=404, detail="지원하지 않는 지역 코드입니다.")
    params = {
        'serviceKey': KMA_API_KEY, 'pageNo': 1, 'numOfRows': 10,
        'dataType': 'JSON', 'areaNo': area_code, 'time': datetime.now().strftime('%Y%m%d%H')
    }
    
    async with httpx.AsyncClient() as client:
        response = None
        try:
            response = await client.get(KMA_API_URL, params=params)
            response.raise_for_status()
            data = response.json()
            
            items = data.get('response', {}).get('body', {}).get('items', {}).get('item')
            if not items:
                raise HTTPException(status_code=404, detail=f"'{AREA_CODE_MAP.get(area_code, area_code)}' 지역의 자외선 지수 정보가 없습니다.")

            item = items[0]
            return UVIndexResponse(area_name=AREA_CODE_MAP[area_code], **item)

        except httpx.RequestError as exc:
            print(f"An error occurred while requesting {exc.request.url!r}.")
            raise HTTPException(status_code=503, detail="기상청 API 서비스에 연결할 수 없습니다.")
        
        except httpx.HTTPStatusError as exc:
            # print(f"Error response {exc.response.status_code} while requesting {exc.request.url!r}.")
            raise HTTPException(status_code=502, detail="기상청 API로부터 잘못된 응답을 받았습니다.")

        except (json.JSONDecodeError, KeyError, IndexError, TypeError) as exc:
            # print(f"Data parsing error: {exc}")
            raise HTTPException(status_code=500, detail="기상청 API 응답을 처리하는 중 오류가 발생했습니다.")