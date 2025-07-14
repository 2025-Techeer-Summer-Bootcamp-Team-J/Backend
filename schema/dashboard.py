from pydantic import BaseModel
from typing import List
from schema.diagnosis import DiagnosisData
from schema.skintype import SkinTypeRead

class Dashboard(BaseModel):
    # 최근 30일 피부 상태 점수 변화
    recent_skinType_scores: List[int]
    # 최근 진단 기록
    recent_diagnosis_records: List[DiagnosisData]
    # 내 피부 프로필
    my_skin_profile: SkinTypeRead