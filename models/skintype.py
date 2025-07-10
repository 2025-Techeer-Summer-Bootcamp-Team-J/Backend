from sqlalchemy import Column, Integer, String, Text, VARCHAR, DateTime, Boolean, func
from sqlalchemy.orm import relationship
from database.database import Base

class SkinType(Base):
    __tablename__ = "SKINTYPE"

    skin_type_id = Column(Integer, primary_key=True, index=True)
    type_name = Column(VARCHAR(255), nullable=False)
    type_description = Column(Text, nullable=False)
    tip_title = Column(VARCHAR(255), nullable=False)
    tip_content = Column(Text, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    is_deleted = Column(Boolean, default=False) 

    diagnoses = relationship("Diagnosis", back_populates="skin_type")
    diseases = relationship("Disease", secondary="SKINTYPE_DISEASE", back_populates="skintypes")
