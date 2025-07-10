from pydantic import BaseModel
from typing import List, Optional
from models.diagnosis import Diagnosis as DiagnosisModel

# --- 기본 진단 정보 스키마 ---
class DiagnosisBase(BaseModel):
    class_name: str
    confidence: float
    bounding_box: List[int]

# --- DB에서 읽어올 때 사용할 스키마 (id 포함) ---
class Diagnosis(DiagnosisBase):
    id: int
    user_id: int

class Config:
    from_attributes = True # SQLAlchemy 모델을 Pydantic 모델로 변환

class BoundingBox(BaseModel):
    x1: int
    y1: int
    x2: int
    y2: int

class DiagnosisData(BaseModel):
    id: int
    user_id: int
    class_name: str
    confidence: float
    bounding_box: BoundingBox
# --- 성공 응답을 위한 스키마 ---
class DiagnosisResponse(BaseModel):
    code: int
    message: str
    data: List[DiagnosisData]  # ← 여기!

def box_to_schema(diagnosis_obj) -> DiagnosisData:
    return DiagnosisData(
        id=getattr(diagnosis_obj, 'id', 0),
        user_id=getattr(diagnosis_obj, 'user_id', 0),
        class_name=getattr(diagnosis_obj, 'class_name', ''),
        confidence=getattr(diagnosis_obj, 'confidence', 0.0),
        bounding_box=BoundingBox(
            x1=getattr(diagnosis_obj, 'x1', 0),
            y1=getattr(diagnosis_obj, 'y1', 0),
            x2=getattr(diagnosis_obj, 'x2', 0),
            y2=getattr(diagnosis_obj, 'y2', 0),
        )
    )

def boxes_to_diagnosis_objs(result, user_id: int) -> list:
    from models.diagnosis import Diagnosis as DiagnosisModel
    diagnosis_objs = []
    if result.boxes is not None:
        for box in result.boxes:
            diagnosis_objs.append(
                DiagnosisModel(
                    user_id=user_id,
                    class_name=result.names[int(box.cls)],
                    confidence=float(box.conf),
                    x1=int(box.xyxy[0][0]),
                    y1=int(box.xyxy[0][1]),
                    x2=int(box.xyxy[0][2]),
                    y2=int(box.xyxy[0][3]),
                )
            )
    return diagnosis_objs