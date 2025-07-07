from fastapi import APIRouter
from api.endpoints import post

api_router = APIRouter()
api_router.include_router(post.router, tags=["posts"])