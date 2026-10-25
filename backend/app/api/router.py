from fastapi import APIRouter

from app.api.routes import fuelhh, health

api_router = APIRouter()
api_router.include_router(fuelhh.router)

root_router = APIRouter()
root_router.include_router(health.router)
