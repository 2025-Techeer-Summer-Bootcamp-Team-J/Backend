from fastapi import APIRouter
from api.endpoints import skintype, diseases, diagnosis, admin


api_router = APIRouter(
    prefix="/api"
)
api_router.include_router(skintype.router)
api_router.include_router(diseases.router)
api_router.include_router(diagnosis.router)
api_router.include_router(admin.router)

