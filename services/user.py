from sqlalchemy.orm import Session
from models.user import User
from schema.user import UserRead

def signup_user(user: User, db: Session) -> User:
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

def get_user_table(db: Session):
    users = db.query(User).filter(User.is_deleted == False).all()
    return [UserRead.model_validate(user) for user in users]