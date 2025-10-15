from fastapi import APIRouter

from app.api.v1 import projects, traces

api_router = APIRouter()
api_router.include_router(projects.router)
api_router.include_router(traces.router)
