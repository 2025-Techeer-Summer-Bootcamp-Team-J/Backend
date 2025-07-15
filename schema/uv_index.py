# schemas/uv_index.py

from pydantic import BaseModel, Field
from typing import Optional

class UVIndexResponse(BaseModel):
    area_name: str = Field(..., description="지역 이름", example="서울")
    date: str = Field(..., description="측정 날짜 및 시간", example="2024052318")
    today_uv: Optional[str] = Field(None, alias="today", description="오늘의 자외선 지수 예측값", example="5")
    tomorrow_uv: Optional[str] = Field(None, alias="tomorrow", description="내일의 자외선 지수 예측값", example="6")
    the_day_after_tomorrow_uv: Optional[str] = Field(None, alias="theDayAfterTomorrow", description="모레의 자외선 지수 예측값", example="7")

    class Config:
        populate_by_name = True