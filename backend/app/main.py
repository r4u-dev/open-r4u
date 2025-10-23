import logging

import uvicorn
from fastapi import FastAPI

from app.api.v1 import api_router
from app.config import get_settings

settings = get_settings()

logging.basicConfig(
    level=logging.DEBUG if settings.log_level == "DEBUG" else logging.INFO,
)

app = FastAPI(title="Open R4U Backend")
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
