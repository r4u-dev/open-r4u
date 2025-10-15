from fastapi import APIRouter

from app.api.v1 import projects, tasks, traces

api_router = APIRouter()
api_router.include_router(projects.router)
api_router.include_router(tasks.router)
api_router.include_router(traces.router)
