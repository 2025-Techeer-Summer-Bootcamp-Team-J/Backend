from sqlalchemy import Column, Integer, DateTime, Boolean, func
from database.database import Base

class UVIndex(Base):
    __tablename__ = "UV"

    uv_id = Column(Integer, primary_key=True, index=True)
    date = Column(DateTime, nullable=False)
    uv_Index = Column(Integer, nullable=True)
    create_at = Column(DateTime, server_default=func.now(), nullable=False)
    update_at = Column(DateTime, onupdate=func.now(), nullable=True)
    is_deleted = Column(Boolean, default=False, nullable=False)