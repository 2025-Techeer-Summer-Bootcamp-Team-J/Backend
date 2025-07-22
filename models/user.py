from sqlalchemy import Column, Integer, String, DateTime, Boolean, func, VARCHAR
from sqlalchemy.orm import relationship
from database.database import Base

class User(Base):
    __tablename__ = "USER"

    user_id = Column(Integer, primary_key=True, index=True)
    email = Column(VARCHAR(255), unique=True, index=True, nullable=True) # String으로 변경 및 nullable 허용
    name = Column(VARCHAR(255), nullable=True) # Changed to String and nullable
    first_name = Column(VARCHAR(255), nullable=True)
    last_name = Column(VARCHAR(255), nullable=True)
    profile_image_url = Column(VARCHAR(255), nullable=True)
    gender = Column(VARCHAR(255), nullable=True) # Changed to String and nullable
    birth_date = Column(DateTime, nullable=True) # Changed to nullable
    password = Column(VARCHAR(255), nullable=True) # Changed to String and nullable
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    is_deleted = Column(Boolean, default=False) 

    diagnoses = relationship("Diagnosis", back_populates="user") 