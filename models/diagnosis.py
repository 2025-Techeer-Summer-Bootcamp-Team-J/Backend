from sqlalchemy import Column, Integer, String, ForeignKey, Float, Table, VARCHAR, func, DateTime, Boolean
from sqlalchemy.orm import relationship
from database.database import Base

diagnosis_symptom_association = Table(
    'DIAGNOSIS_SYMPTOM', Base.metadata,
    Column('diagnosis_id', Integer, ForeignKey('DIAGNOSIS.diagnosis_id'), primary_key=True),
    Column('symptom_id', Integer, ForeignKey('SYMPTOM.symptom_id'), primary_key=True)
)

diagnosis_disease_association = Table(
    'DIAGNOSIS_DISEASE', Base.metadata,
    Column('diagnosis_id', Integer, ForeignKey('DIAGNOSIS.diagnosis_id'), primary_key=True),
    Column('disease_id', Integer, ForeignKey('DISEASE.disease_id'), primary_key=True)
)

class Diagnosis(Base):
    __tablename__ = "DIAGNOSIS"

    diagnosis_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("USER.user_id"), nullable=False)
    skin_type_id = Column(Integer, ForeignKey("SKINTYPE.skin_type_id"), nullable=True)
    
    # YOLO 결과를 위한 컬럼들 추가
    class_name = Column(VARCHAR(255), nullable=False)  # 질병 클래스명
    confidence = Column(Float, nullable=False)  # 신뢰도
    x1 = Column(Integer, nullable=False)  # bounding box 좌표
    y1 = Column(Integer, nullable=False)
    x2 = Column(Integer, nullable=False) 
    y2 = Column(Integer, nullable=False)
    
    # 기존 컬럼들
    expected_treat = Column(Integer, nullable=True)
    severity = Column(Float, nullable=True)
    image = Column(VARCHAR(255), nullable=True)
    image_quality = Column(Integer, nullable=True)
    after = Column(VARCHAR(255), nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    is_deleted = Column(Boolean, default=False) 

    # relationships - 문자열로 참조하여 순환참조 방지
    user = relationship("User", back_populates="diagnoses")
    skin_type = relationship("SkinType", back_populates="diagnoses")
    symptoms = relationship("Symptom", secondary=diagnosis_symptom_association, back_populates="diagnoses")
    diseases = relationship("Disease", secondary=diagnosis_disease_association, back_populates="diagnoses")
    
    # schema에서 사용하는 id 속성
    @property
    def id(self):
        return self.diagnosis_id


