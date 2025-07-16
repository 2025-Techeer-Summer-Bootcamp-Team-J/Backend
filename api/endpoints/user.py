from fastapi import APIRouter, Depends, HTTPException, status
from schema.ResultResponseModel import ResultResponseModel
from services.user import signup_user, get_user_table
from sqlalchemy.orm import Session
from database.database import get_db
from sqlalchemy.exc import IntegrityError
from datetime import datetime
from models.user import User
from schema.user import UserCreate, UserRead
from services.dashboard import get_dashboard

router = APIRouter(prefix="/users", tags=["user"])

@router.get("", summary="user 테이블 조회", description="user 테이블 정보를 조회합니다")
def get_user(db: Session = Depends(get_db)):
    response_data = get_user_table(db)
    return ResultResponseModel(status_code=200, message="success", data=response_data)

@router.post("/signup", summary="회원 가입", description="새로운 유저의 회원가입")
def signup(req: UserCreate, db: Session = Depends(get_db)):
    # created_at은 DB에서 자동으로 설정되므로 제거
    new_user = User(
        email=req.email, 
        password=req.password, 
        name=req.name, 
        gender=req.gender, 
        birth_date=req.birth_date,
        is_deleted=False
    )
    try:
        saved_user = signup_user(new_user, db)
        # SQLAlchemy 객체를 Pydantic 모델로 변환하여 직렬화 문제 해결
        user_data = UserRead.model_validate(saved_user)
        return ResultResponseModel(status_code=200, message="회원가입 성공", data=user_data)
    except IntegrityError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="중복된 이메일입니다.")
    except Exception as e:
        # 기타 예외 처리 추가
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"서버 에러: {str(e)}")

@router.get("/{user_id}/dashboard", summary="유저 대시보드 조회", description="유저 대시보드를 조회합니다")
def get_user_dashboard(user_id: int, db: Session = Depends(get_db)):
    try:
        dashboard = get_dashboard(db, user_id)
        return ResultResponseModel(status_code=200, message="유저 대시보드 조회 성공", data=dashboard)
    except HTTPException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"dashboard 불러오기 실패: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"서버 에러: {str(e)}")