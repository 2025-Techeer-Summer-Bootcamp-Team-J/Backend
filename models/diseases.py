from sqlalchemy import Column, Integer, String, Text, Table, ForeignKey, DateTime, Boolean, VARCHAR, func
from sqlalchemy.orm import relationship
from database.database import Base

skintype_disease_association = Table(
    'SKINTYPE_DISEASE', Base.metadata,
    Column('skin_type_id', Integer, ForeignKey('SKINTYPE.skin_type_id'), primary_key=True),
    Column('disease_id', Integer, ForeignKey('DISEASE.disease_id'), primary_key=True)
)

class Disease(Base):
    __tablename__ = "DISEASE"

    disease_id = Column(Integer, primary_key=True, index=True)
    main_symptom = Column(VARCHAR(255), nullable=False)
    disease_name = Column(VARCHAR(255), nullable=False)
    description = Column(Text, nullable=False)
    precautions = Column(Text, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    is_deleted = Column(Boolean, default=False) 

    diagnoses = relationship("Diagnosis", secondary="DIAGNOSIS_DISEASE", back_populates="diseases")
    skintypes = relationship("SkinType", secondary=skintype_disease_association, back_populates="diseases")