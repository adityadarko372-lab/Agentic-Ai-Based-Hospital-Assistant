"""Nova Health FastAPI application entry point.

Run locally (from the `backend` folder):
    .venv\\Scripts\\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000

The server binds to 127.0.0.1 only, so it is not reachable from other
machines on the network. This is a local demonstration build.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session

from app.api.activity import router as activity_router
from app.api.appointments import router as appointments_router
from app.api.assistant import router as assistant_router
from app.api.auth import router as auth_router
from app.api.health import router as health_router
from app.api.hospital import router as hospital_router
from app.core.config import get_settings
from app.core.errors import register_error_handlers
from app.db.seed import seed_all
from app.db.session import create_tables, get_engine


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    # Create tables if missing and load the fictional demo data.
    create_tables()
    with Session(get_engine()) as session:
        seed_all(session)
    yield


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title=f"{settings.app_name} API",
        version=settings.app_version,
        description=(
            "Backend for the Nova Health agentic hospital assistant prototype. "
            "All data is synthetic demonstration data."
        ),
        lifespan=lifespan,
    )

    # Only the local Vite dev server may call the API from a browser.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "DELETE"],
        allow_headers=["Authorization", "Content-Type", "Idempotency-Key"],
    )

    register_error_handlers(app)
    app.include_router(health_router)
    app.include_router(auth_router)
    app.include_router(hospital_router)
    app.include_router(appointments_router)
    app.include_router(activity_router)
    app.include_router(assistant_router)
    return app


app = create_app()
