from fastapi import APIRouter
from api.endpoints import post
from api.endpoints import skintype
from api.endpoints import diseases
from api.endpoints import diagnosis


api_router = APIRouter(
    prefix="/api"
)
api_router.include_router(post.router)
api_router.include_router(skintype.router)
api_router.include_router(diseases.router)
api_router.include_router(diagnosis.router)

