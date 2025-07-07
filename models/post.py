from sqlalchemy import Column, Integer, VARCHAR, DateTime
from datetime import datetime

from database.database import Base

# example 모델
class Post(Base):
    __tablename__ = "post"

    id = Column(Integer, primary_key= True, autoincrement=True)
    writer = Column(VARCHAR(30), nullable= False)
    title = Column(VARCHAR(30), nullable=False)
    content = Column(VARCHAR(100), nullable=False)
    date = Column(DateTime, nullable=False, default=datetime.now)
    isDel = Column(VARCHAR(1), nullable=False, default="f")