from fastapi import APIRouter
from api.endpoints import post
from api.endpoints import skintype

api_router = APIRouter(
    prefix="/api"
)
api_router.include_router(post.router)
api_router.include_router(skintype.router)