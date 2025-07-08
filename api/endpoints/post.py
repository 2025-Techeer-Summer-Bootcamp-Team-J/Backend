from sqlalchemy.orm import Session
from database.database import get_db
from fastapi import Depends
from fastapi import APIRouter
from schema.post import PostCreate, PostRead
from crud.post import create, read_all, read_one, update as update_post_crud, delete as delete_post_crud

router = APIRouter(prefix="/posts", tags=["posts"])

@router.post("", response_model=PostRead)
def create_post(post: PostCreate, db: Session = Depends(get_db)):
    return create(db, post)

@router.get("", response_model=list[PostRead])
def read_posts(db: Session = Depends(get_db)) -> list[PostRead]:
    return read_all(db)

@router.get("/{post_id}", response_model=PostRead)
def read_post(post_id: int, db: Session = Depends(get_db)) -> PostRead:
    return read_one(db, post_id)

@router.put("/{post_id}", response_model=PostRead)
def update_post(post_id: int, post: PostCreate, db: Session = Depends(get_db)) -> PostRead:
    return update_post_crud(db, post_id, post)

@router.delete("/{post_id}")
def delete_post(post_id: int, db: Session = Depends(get_db)) -> dict:
    return delete_post_crud(db, post_id)