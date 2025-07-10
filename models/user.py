from sqlalchemy import Column, Integer, String, DateTime, VARCHAR, Boolean, func
from sqlalchemy.orm import relationship
from database.database import Base

class User(Base):
    __tablename__ = "USER"

    user_id = Column(Integer, primary_key=True, index=True)
    name = Column(VARCHAR(255), nullable=False)
    gender = Column(VARCHAR(255), nullable=False)
    birth_date = Column(DateTime, nullable=False)
    email = Column(VARCHAR(255), nullable=False, unique=True)
    password = Column(VARCHAR(255), nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    is_deleted = Column(Boolean, default=False) 

    diagnoses = relationship("Diagnosis", back_populates="user") 