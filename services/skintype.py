from sqlalchemy.orm import Session
from fastapi import HTTPException

from models.skintype import SkinType
from schema.skintype import SkinTypeAllRead

def get_all_skintype(db:Session):
    skintype = db.query(SkinType).all()
    return skintype
