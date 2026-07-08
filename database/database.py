from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
<<<<<<< HEAD
from os import getenv
# local 실행
# SQLALCHEMY_DATABASE_URL = "mysql+pymysql://backend_user:backend_password@localhost:3306/db"
# docker 실행
SQLALCHEMY_DATABASE_URL = getenv("MYSQL_URL")
=======
from dotenv import load_dotenv
import os
load_dotenv()

# mysql db 연결
# docker 실행
SQLALCHEMY_DATABASE_URL = os.getenv("MYSQL_URL")
>>>>>>> 02cd5b70ba7d48699f1ad3370fc8a846425868ee
engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()