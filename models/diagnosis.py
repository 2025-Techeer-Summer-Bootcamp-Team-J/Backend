from sqlalchemy import Column, Integer, String, ForeignKey, Float, Table, VARCHAR, func, DateTime, Boolean, TEXT, BigInteger
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
    user_id = Column(VARCHAR(255), ForeignKey("USER.user_id"), nullable=False)
    skin_type_id = Column(Integer, ForeignKey("SKINTYPE.skin_type_id"), nullable=True)

    
    # 기존 컬럼들
    confidence = Column(Integer, nullable=True)
    image = Column(TEXT, nullable=True)
    after = Column(TEXT, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    is_deleted = Column(Boolean, default=False)

    skinType_score = Column(Float, nullable=True) # 이 줄을 추가합니다. 
    detailed_info_json = Column(TEXT, nullable=True) # 모든 상세 정보를 JSON 문자열로 저장
    additional_info = Column(TEXT, nullable=True) # 보조 정보를 JSON 문자열로 저장 (주요 증상, 가려움 정도, 시작 시점, 보조 정보 텍스트)
    disease_name = Column(String(255), nullable=True) # 질병명 저장

    # relationships - 문자열로 참조하여 순환참조 방지
    user = relationship("User", back_populates="diagnoses")
    skin_type = relationship("SkinType", back_populates="diagnoses")
    symptoms = relationship("Symptom", secondary=diagnosis_symptom_association, back_populates="diagnoses")
    diseases = relationship("Disease", secondary=diagnosis_disease_association, back_populates="diagnoses")
    
    # schema에서 사용하는 id 속성
    @property
    def id(self):
        return self.diagnosis_id