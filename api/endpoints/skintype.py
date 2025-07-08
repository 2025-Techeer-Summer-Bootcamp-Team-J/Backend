from fastapi import APIRouter

router = APIRouter(prefix="/skintype", tags=["skintype"])

@router.get("")
def get_skintype():
    return {"message": "Hello, World!"}

