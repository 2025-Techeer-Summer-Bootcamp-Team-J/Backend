from fastapi import APIRouter, Depends, HTTPException, status, Request
from schema.ResultResponseModel import ResultResponseModel
from services.user import create_user, get_user_table, get_user_by_email
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
    try:
        saved_user = create_user(req, db)
        user_data = UserRead.model_validate(saved_user)
        return ResultResponseModel(status_code=200, message="회원가입 성공", data=user_data)
    except IntegrityError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="중복된 이메일입니다.")
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"서버 에러: {str(e)}")

@router.post("/clerk-webhook", summary="Clerk Webhook", description="Clerk에서 유저 정보를 받아 처리합니다.")
async def clerk_webhook(request: Request, db: Session = Depends(get_db)):
    raw_payload = None # raw_payload 초기화
    try:
        raw_payload = await request.json()
        print(f"Received RAW Clerk webhook payload: {raw_payload}")

        clerk_event_data = raw_payload.get('data', {})
        event_type = raw_payload.get('type')
        print(f"Clerk Event Type: {event_type}")

        clerk_user_id = clerk_event_data.get('id')  # Clerk에서 전달되는 고유 ID
        mapped_data = {
            "email": clerk_event_data.get('email_addresses', [{}])[0].get('email_address') if clerk_event_data.get('email_addresses') else None,
            "first_name": clerk_event_data.get('first_name'),
            "last_name": clerk_event_data.get('last_name'),
            "profile_image_url": clerk_event_data.get('profile_image_url'),
            "user_id": clerk_user_id,
            "name": clerk_event_data.get('username') or clerk_event_data.get('first_name')
        }

        user_data_for_pydantic = {k: v for k, v in mapped_data.items() if v is not None}

        user_data = UserCreate(**user_data_for_pydantic)
        print(f"Successfully parsed user_data into UserCreate schema: {user_data.model_dump_json()}")

    except Exception as e:
        print(f"Error processing Clerk webhook payload: {e}")
        if raw_payload:
            print(f"Failed payload was: {raw_payload}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid payload from Clerk: {str(e)}")

    if not user_data.email:
        print("Error: email is missing in webhook payload.")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="email is required")

    existing_user = get_user_by_email(user_data.email, db)

    if existing_user:
        print(f"User with email {user_data.email} found. Attempting to update...")
        try:
            update_fields = user_data.model_dump(exclude_unset=True) # 명시적으로 설정된 필드만 포함
            for key, value in update_fields.items():
                if hasattr(existing_user, key) and value is not None:
                    setattr(existing_user, key, value)

            db.add(existing_user)
            db.commit()
            db.refresh(existing_user)
            print(f"User updated successfully in DB: {existing_user.email} (ID: {existing_user.user_id})")
            return ResultResponseModel(status_code=200, message="User updated successfully", data=UserRead.model_validate(existing_user))
        except Exception as e:
            db.rollback() # 업데이트 중 오류 발생 시 롤백
            print(f"Error updating user in DB: {e}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Server error during user update: {str(e)}")
    else:
        print(f"User with email {user_data.email} not found. Attempting to create new user...")
        try:
            new_user = create_user(user_data, db)
            # create_user already commits and refreshes
            print(f"New user created successfully in DB: {new_user.email} (ID: {new_user.user_id})")
            return ResultResponseModel(status_code=201, message="User created successfully", data=UserRead.model_validate(new_user))
        except IntegrityError as e:
            db.rollback() # 무결성 오류 발생 시 롤백
            print(f"IntegrityError during user creation: {e}")
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User with this email already exists.")
        except Exception as e:
            db.rollback() # 다른 오류 발생 시 롤백
            print(f"Server error during user creation: {e}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Server error during user creation: {str(e)}")
@router.get("/{user_id}/dashboard", summary="유저 대시보드 조회", description="유저 대시보드를 조회합니다")
def get_user_dashboard(user_id: str, db: Session = Depends(get_db)):
    try:
        dashboard = get_dashboard(db, user_id)
        return ResultResponseModel(status_code=200, message="유저 대시보드 조회 성공", data=dashboard)
    except HTTPException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"dashboard 불러오기 실패: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"서버 에러: {str(e)}")
