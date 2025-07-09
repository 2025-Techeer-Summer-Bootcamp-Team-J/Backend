from sqlalchemy.orm import Session
from fastapi import HTTPException

from models.diseases import Diseases


def get_all_diseases(db: Session):
    return db.query(Diseases).all()

