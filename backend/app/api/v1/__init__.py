from fastapi import APIRouter

from app.api.v1 import executions, http_traces, implementations, projects, tasks, traces

api_router = APIRouter()
api_router.include_router(projects.router)
api_router.include_router(implementations.router)
api_router.include_router(tasks.router)
api_router.include_router(traces.router)
api_router.include_router(http_traces.router)
api_router.include_router(executions.router)
