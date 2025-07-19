from typing import Optional
from sqlalchemy.orm import Session
from models.user import User
from schema.user import UserRead, UserCreate

def create_user(user_data: UserCreate, db: Session) -> User:
    db_user = User(
        email=user_data.email,
        password=user_data.password,
        name=user_data.name,
        first_name=user_data.first_name,
        last_name=user_data.last_name,
        profile_image_url=user_data.profile_image_url,
        gender=user_data.gender,
        birth_date=user_data.birth_date
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def get_user_by_email(email: str, db: Session) -> Optional[User]:
    return db.query(User).filter(User.email == email).first()

def get_user_table(db: Session):
    users = db.query(User).filter(User.is_deleted == False).all()
    return [UserRead.model_validate(user) for user in users]