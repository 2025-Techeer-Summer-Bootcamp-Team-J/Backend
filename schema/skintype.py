from pydantic import BaseModel
from datetime import datetime

class SkinTypeBase(BaseModel):
    type_name: str
    type_description: str
    tip_title: str
    tip_content: str

class SkinTypeCreate(SkinTypeBase):
    pass

class SkinTypeRead(SkinTypeBase):
    skin_type_id: int
    created_at: datetime
    updated_at: datetime
    is_deleted: bool

    class Config:
        from_attributes = True

class SkinTypeUpdate(BaseModel):
    type_name: str
    tip_title: str
    tip_content: str

class SkinTypeDelete(BaseModel):
    skin_type_id: int