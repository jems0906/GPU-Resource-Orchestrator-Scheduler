from fastapi import APIRouter
from app.api.routes import jobs, metrics, providers, websocket

api_router = APIRouter()
api_router.include_router(jobs.router)
api_router.include_router(metrics.router)
api_router.include_router(providers.router)
api_router.include_router(websocket.router)
