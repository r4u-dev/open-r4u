from fastapi import APIRouter

from app.api.v1 import traces

api_router = APIRouter()
api_router.include_router(traces.router)
