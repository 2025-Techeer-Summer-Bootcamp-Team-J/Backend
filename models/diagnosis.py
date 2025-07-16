from sqlalchemy import Column, Integer, String, ForeignKey, Float, Table, VARCHAR, func, DateTime, Boolean, Text
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

    
    # 기존 컬럼들
    confidence = Column(Integer, nullable=True)
    image = Column(Text, nullable=True)
    after = Column(Text, nullable=True)
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