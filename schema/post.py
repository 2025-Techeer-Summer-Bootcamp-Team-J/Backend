from pydantic import BaseModel

# dto request
class PostCreate(BaseModel):
    writer: str
    title: str
    content: str

# dto response
class PostRead(PostCreate):
    id: int
    class Config:
        orm_mode = True