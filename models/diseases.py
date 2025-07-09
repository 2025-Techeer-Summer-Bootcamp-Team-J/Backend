from sqlalchemy import Column, Integer, String, Text
from database import Base


class Diseases(Base):
    __tablename__ = "diseases"

    id = Column(Integer, primary_key=True)
    main_symptom = Column(Varchar(255), nullable=False)
    disease_name = Column(Varchar(255), nullable=False)
    description = Column(Text, nullable=False)
    precautions = Column(Text, nullable=False)