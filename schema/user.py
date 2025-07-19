from typing import Optional
from pydantic import BaseModel
from datetime import datetime

class UserCreate(BaseModel):
    email: Optional[str] = None
    password: Optional[str] = None
    name: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    profile_image_url: Optional[str] = None
    gender: Optional[str] = None
    birth_date: Optional[datetime] = None

class UserRead(BaseModel):
    user_id: int
    name: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    profile_image_url: Optional[str] = None
    gender: Optional[str] = None
    birth_date: Optional[datetime] = None
    email: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    is_deleted: bool

    class Config:
        from_attributes = True