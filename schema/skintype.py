from pydantic import BaseModel

class SkinTypeCreate(BaseModel):
    name: str
    tip_title: str
    tip_content: str

class SkinTypeRead(SkinTypeCreate):
    id: int
    class Config:
        orm_mode = True

class SkinTypeAllRead(BaseModel):
    id: int
    name: str
    tip_title: str
    tip_content: str
    class Config:
        orm_mode = True