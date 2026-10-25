from fastapi import APIRouter

from app.api.routes import fuelhh, health, windfor

api_router = APIRouter()
api_router.include_router(fuelhh.router)
api_router.include_router(windfor.router)

root_router = APIRouter()
root_router.include_router(health.router)
