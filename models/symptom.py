from sqlalchemy import Column, Integer, String, VARCHAR, DateTime, Boolean, func
from sqlalchemy.orm import relationship
from database.database import Base

class Symptom(Base):
    __tablename__ = "SYMPTOM"

    symptom_id = Column(Integer, primary_key=True, index=True)
    symptom = Column(VARCHAR(255), nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    is_deleted = Column(Boolean, default=False) 

    diagnoses = relationship("Diagnosis", secondary="DIAGNOSIS_SYMPTOM", back_populates="symptoms")