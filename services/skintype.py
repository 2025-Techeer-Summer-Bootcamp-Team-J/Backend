from sqlalchemy.orm import Session
from fastapi import HTTPException

from models.skintype import SkinType
from models.diagnosis import Diagnosis
from schema.skintype import SkinTypeCreate, SkinTypeUpdate, SkinTypeDelete, SkinTypeRead

def get_all_skintype_name(db:Session):
    skintype_name = db.query(SkinType.type_name).filter(SkinType.is_deleted == False).all()
    return [result[0] for result in skintype_name]

def get_skintype_table(db: Session):
    skintype = db.query(SkinType).filter(SkinType.is_deleted == False).all()
    return [SkinTypeRead.model_validate(skin) for skin in skintype]

def create_skintype(db: Session, skintype: SkinTypeCreate):
    new_skintype = SkinType(
        type_name=skintype.type_name,
        type_description=skintype.type_description,
        tip_title=skintype.tip_title,
        tip_content=skintype.tip_content
    )
    db.add(new_skintype)
    db.commit()
    db.refresh(new_skintype)
    return SkinTypeRead.model_validate(new_skintype)

def delete_skintype(db: Session, skin_type_id: int):
    skintype = db.query(SkinType).filter(SkinType.skin_type_id == skin_type_id).first()
    if not skintype:
        raise HTTPException(status_code=404, detail="피부유형 정보가 없습니다")

    # 삭제 전에 Pydantic 스키마로 변환
    skintype_data = SkinTypeRead.model_validate(skintype)

    db.query(Diagnosis).filter(Diagnosis.skin_type_id == skin_type_id).update({"skin_type_id": None})
    
    skintype.diseases.clear()

    db.delete(skintype)
    db.commit()
    return skintype_data

def update_skintype(db: Session, skintype_id: int, skintype_update: SkinTypeUpdate):
    db_skintype = db.query(SkinType).filter(SkinType.skin_type_id == skintype_id).first()
    if not db_skintype:
        raise HTTPException(status_code=404, detail="피부유형 정보가 없습니다")
    
    update_data = skintype_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_skintype, key, value)

    db.commit()
    db.refresh(db_skintype)
    return SkinTypeRead.model_validate(db_skintype)

def get_type_description_by_id(db: Session, skintype_id: int):
    skintype = db.query(SkinType).filter(SkinType.skin_type_id == skintype_id).first()
    if not skintype:
        raise HTTPException(status_code=404, detail="피부유형 정보가 없습니다")
    return skintype.type_description