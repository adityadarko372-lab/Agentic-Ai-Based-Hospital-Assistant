"""Nova Health FastAPI application entry point.

Run locally (from the `backend` folder):
    .venv\\Scripts\\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000

The server binds to 127.0.0.1 only, so it is not reachable from other
machines on the network. This is a local demonstration build.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.health import router as health_router
from app.core.config import get_settings


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title=f"{settings.app_name} API",
        version=settings.app_version,
        description=(
            "Backend for the Nova Health agentic hospital assistant prototype. "
            "All data is synthetic demonstration data."
        ),
    )

    # Only the local Vite dev server may call the API from a browser.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "DELETE"],
        allow_headers=["Authorization", "Content-Type", "Idempotency-Key"],
    )

    app.include_router(health_router)
    return app


app = create_app()
