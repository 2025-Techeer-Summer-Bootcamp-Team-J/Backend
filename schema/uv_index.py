from pydantic import BaseModel
from typing import Optional

class UVIndexResponse(BaseModel):
    """UV 인덱스 API 응답 모델 - 대한민국 전체 범위"""
    location: str = "대한민국"
    date: str
<<<<<<< HEAD
    today: str  # "최저~최고" 형태 예: "1~5"
    
=======
    now: str  # "최저~최고" 형태 예: "1~5" 또는 단일 값

>>>>>>> develop
    class Config:
        json_encoders = {
            # 필요한 경우 인코더 추가
        } 