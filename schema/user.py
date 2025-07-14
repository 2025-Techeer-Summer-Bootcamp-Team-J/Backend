from typing import Optional
from pydantic import BaseModel
from datetime import datetime

class UserCreate(BaseModel):
    email: str
    password: str
    name: str
    gender: str
    birth_date: datetime

class UserRead(BaseModel):
    user_id: int
    name: str
    gender: str
    birth_date: datetime
    email: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    is_deleted: bool

    class Config:
        from_attributes = True

