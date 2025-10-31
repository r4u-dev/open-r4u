from fastapi import APIRouter

from app.api.v1 import (
    executions,
    evaluations,
    grades,
    graders,
    http_traces,
    optimizations,
    implementations,
    projects,
    tasks,
    test_cases,
    traces,
)

api_router = APIRouter(prefix="/v1")
api_router.include_router(projects.router)
api_router.include_router(implementations.router)
api_router.include_router(tasks.router)
api_router.include_router(traces.router)
api_router.include_router(http_traces.router)
api_router.include_router(executions.router)
api_router.include_router(graders.router)
api_router.include_router(grades.router)
api_router.include_router(test_cases.router)
api_router.include_router(evaluations.router)
api_router.include_router(optimizations.router)
