from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# local 실행
# SQLALCHEMY_DATABASE_URL = "mysql+pymysql://backend_user:backend_password@localhost:3306/db"
# docker 실행
SQLALCHEMY_DATABASE_URL = "mysql+pymysql://backend_user:backend_password@mysql:3306/db"
engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

