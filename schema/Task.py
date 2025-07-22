from pydantic import BaseModel
from typing import Optional, Any
from schema.diagnosis import DiagnosisResponse, SimplifiedDiagnosisResponse


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
    result: Optional[Any] = None  # 다양한 형태의 결과를 받을 수 있도록 Any 타입 사용
    error: Optional[str] = None
