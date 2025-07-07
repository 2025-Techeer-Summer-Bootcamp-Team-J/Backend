from models.post import Post
from sqlalchemy.orm import Session
from schema.post import PostCreate
from fastapi import HTTPException

def create(db: Session, post: PostCreate):
    db_post = Post(
        writer=post.writer, 
        title=post.title, 
        content=post.content,
        # created_at, isdel은 default 값
        )
    db.add(db_post)
    db.commit()
    db.refresh(db_post)
    return db_post

def read_all(db: Session):
    return db.query(Post).all()

def read_one(db: Session, post_id: int):
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    return post

def update(db: Session, post_id: int, post: PostCreate):
    db_post = db.query(Post).filter(Post.id == post_id).first()
    if not db_post:
        raise HTTPException(status_code=404, detail="Post not found")
    db_post.title = post.title
    db_post.content = post.content
    db.commit()
    db.refresh(db_post)
    return db_post

def delete(db: Session, post_id: int):
    db_post = db.query(Post).filter(Post.id == post_id).first()
    if not db_post:
        raise HTTPException(status_code=404, detail="Post not found")
    db.delete(db_post)
    db.commit()
    return {"ok": True}