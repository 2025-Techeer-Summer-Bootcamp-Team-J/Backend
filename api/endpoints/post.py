from sqlalchemy.orm import Session
from database.database import get_db
from fastapi import Depends
from fastapi import APIRouter
from schema.post import PostCreate, PostRead
from crud.post import create, read_all, read_one, update as update_post_crud, delete as delete_post_crud

router = APIRouter(prefix="/posts", tags=["posts"])

@router.post("", summary="게시글 생성", description="게시글을 생성합니다")
def create_post(post: PostCreate, db: Session = Depends(get_db)):
    return create(db, post)

@router.get("", summary="게시글 목록 조회", description="게시글 목록을 조회합니다")
def read_posts(db: Session = Depends(get_db)) -> list[PostRead]:
    return read_all(db)

@router.get("/{post_id}", summary="게시글 상세 조회", description="게시글을 상세 조회합니다")
def read_post(post_id: int, db: Session = Depends(get_db)) -> PostRead:
    return read_one(db, post_id)

@router.put("/{post_id}", summary="게시글 수정", description="게시글을 수정합니다")
def update_post(post_id: int, post: PostCreate, db: Session = Depends(get_db)) -> PostRead:
    return update_post_crud(db, post_id, post)

@router.delete("/{post_id}", summary="게시글 삭제", description="게시글을 삭제합니다")
def delete_post(post_id: int, db: Session = Depends(get_db)) -> dict:
    return delete_post_crud(db, post_id)