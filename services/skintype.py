from sqlalchemy.orm import Session
from fastapi import HTTPException

from models.skintype import SkinType
from schema.skintype import SkinTypeCreate, SkinTypeUpdate, SkinTypeDelete

def get_all_skintype(db:Session):
    skintype = db.query(SkinType).filter(SkinType.is_deleted == False).all()
    return skintype

def create_skintype(db: Session, skintype: SkinTypeCreate):
    new_skintype = SkinType(
        type_name=skintype.type_name,
        tip_title=skintype.tip_title,
        tip_content=skintype.tip_content
    )
    db.add(new_skintype)
    db.commit()
    db.refresh(new_skintype)
    return new_skintype

def delete_skintype(db: Session, skintype_id: int):
    skintype = db.query(SkinType).filter(SkinType.skin_type_id == skintype_id).first()
    if not skintype:
        raise HTTPException(status_code=404, detail="피부유형 정보가 없습니다")
    skintype.is_deleted = True
    db.commit()
    return skintype

def update_skintype(db: Session, skintype_id: int, skintype_update: SkinTypeUpdate):
    db_skintype = db.query(SkinType).filter(SkinType.skin_type_id == skintype_id).first()
    if not db_skintype:
        raise HTTPException(status_code=404, detail="피부유형 정보가 없습니다")
    skintype.type_name = skintype.type_name
    skintype.tip_title = skintype.tip_title
    skintype.tip_content = skintype.tip_content
    db.commit()
    return skintype