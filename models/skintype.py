from sqlalchemy import Column, Integer, VARCHAR, DateTime, TEXT
from datetime import datetime

from database.database import Base

class SkinType(Base):
    __tablename__ = "skintype"

    id = Column(Integer, primary_key= True, autoincrement=True)
    name = Column(VARCHAR(30), nullable= False)
    tip_title = Column(VARCHAR(30), nullable= False)
    tip_content = Column(TEXT, nullable=False)
