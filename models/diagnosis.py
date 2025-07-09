from sqlalchemy import Column, Integer, VARCHAR, DateTime, TEXT, ForeignKey
from datetime import datetime

from database.database import Base

class Diagnosis(Base):
    __tablename__ = "diagnosis"

    id = Column(Integer, primary_key= True, autoincrement=True)
    user_id = Column(Integer, nullable= False)
    skin_type = Column(Integer, ForeignKey("skintype.id"), nullable= False)
    expected_treat = Column(Integer,  nullable= False)
    severity = Column(Integer, nullable= False)
    image = Column(VARCHAR(255), nullable= False)
    image_quality = Column(Integer, nullable= False)
    after = Column(VARCHAR(255), nullable= False)







