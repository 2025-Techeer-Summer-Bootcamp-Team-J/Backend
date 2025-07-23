from models.user import User
from models.diagnosis import Diagnosis
from models.skintype import SkinType
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from schema.dashboard import Dashboard
from fastapi import HTTPException, status
from schema.diagnosis import box_to_schema

def get_dashboard(db: Session, user_id: str) -> Dashboard:
    # 최근 30일간 진단 기록 조회
    try:
        thirty_days_ago = datetime.now() - timedelta(days=30)
        recent_diagnoses = db.query(Diagnosis).filter(
            Diagnosis.user_id == user_id,
            Diagnosis.skinType_score != None,
            Diagnosis.created_at >= thirty_days_ago,
            Diagnosis.is_deleted == False
        ).order_by(Diagnosis.created_at.desc()).all()
        # int 또는 float 타입만 리스트에 포함
        recent_skinType_scores = [int(d.skinType_score) for d in recent_diagnoses if isinstance(d.skinType_score, (int, float))]

        # 최근 진단 기록 (최신 5개, SQLAlchemy 모델 객체 그대로 반환)
        recent_diagnosis_records = db.query(Diagnosis).filter(
            Diagnosis.user_id == user_id,
            Diagnosis.is_deleted == False
        ).order_by(Diagnosis.created_at.desc()).limit(5).all()

        # 내 피부 프로필 (가장 최근 진단의 skin_type_id 기준)
        latest_diagnosis = db.query(Diagnosis).filter(
            Diagnosis.user_id == user_id,
            Diagnosis.skin_type_id != None,
            Diagnosis.is_deleted == False
        ).order_by(Diagnosis.created_at.desc()).first()
        my_skin_profile = None
        if latest_diagnosis is not None and latest_diagnosis.skin_type_id is not None:
            my_skin_profile = db.query(SkinType).filter(SkinType.skin_type_id == latest_diagnosis.skin_type_id, SkinType.is_deleted == False).first()
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"dashboard 조회 실패: {str(e)}")
    
    try:
        return Dashboard(
            recent_skinType_scores=recent_skinType_scores,
            recent_diagnosis_records= [box_to_schema(d) for d in recent_diagnosis_records],
            my_skin_profile=my_skin_profile
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"dashboard return 실패: {str(e)}")