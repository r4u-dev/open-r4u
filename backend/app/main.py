import logging
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import api_router
from app.config import get_settings
from app.database import AsyncSessionMaker
from app.services.provider_service import load_providers_from_yaml
from app.services.task_grouping_queue import get_task_grouping_queue

settings = get_settings()

logging.basicConfig(
    level=logging.DEBUG if settings.log_level == "DEBUG" else logging.INFO,
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup/shutdown events."""
    # Startup: Load providers from YAML
    yaml_path = Path(__file__).parent.parent / "models.yaml"
    async with AsyncSessionMaker() as session:
        await load_providers_from_yaml(session, yaml_path)

    logger.info("Starting background workers...")
    queue_manager = get_task_grouping_queue()
    queue_manager.start_worker()
    logger.info("Background workers started")

    yield

    logger.info("Stopping background workers...")
    queue_manager = get_task_grouping_queue()
    queue_manager.stop_worker(timeout=10.0)
    logger.info("Background workers stopped")


app = FastAPI(title="Open R4U Backend", lifespan=lifespan)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8080",
        "http://localhost:3000",
        "http://127.0.0.1:8080",
        "http://127.0.0.1:3000",
        settings.app_url,
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.get("/health", tags=["health"])
async def health_check() -> dict[str, str]:
    """Simple health check endpoint."""
    return {"status": "ok"}


def main() -> None:
    """Entrypoint for running the app with uvicorn."""
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )


if __name__ == "__main__":
    main()
