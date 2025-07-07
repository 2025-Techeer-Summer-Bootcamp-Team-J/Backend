from sqlalchemy import Column, Integer, VARCHAR, DateTime
from datetime import datetime

from database import Base

# 테스트용 모델
class Board(Base):
    __tablename__ = "Board"

    no = Column(Integer, primary_key= True, autoincrement=True)
    writer = Column(VARCHAR(30), nullable= False)
    title = Column(VARCHAR(30), nullable=False)
    content = Column(VARCHAR(100), nullable=False)
    date = Column(DateTime, nullable=False, default=datetime.now)
    isDel = Column(VARCHAR(1), nullable=False, default="f")