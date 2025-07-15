from pydantic import BaseModel
from typing import Optional
from schema.diagnosis import DiagnosisResponse


# --- 비동기 태스크 관련 스키마 ---
class TaskStartResponse(BaseModel):
    """태스크 시작 응답"""
    code: int
    message: str
    task_id: str
    status: str

class TaskProgressInfo(BaseModel):
    """태스크 진행 상태 정보"""
    current: int
    total: int
    status: str

class TaskStatusResponse(BaseModel):
    """태스크 상태 조회 응답"""
    code: int
    message: str
    task_id: str
    state: str
    progress: Optional[TaskProgressInfo] = None
    result: Optional[DiagnosisResponse] = None
    error: Optional[str] = None
