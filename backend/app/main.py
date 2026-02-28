"""FastAPI application — entry point."""

import logging
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.dependencies import get_api_key
from app.routes import attributions, completeness, conversions, exports, partners, rakeback
from app.routes.health import get_db_info
from config import Settings, get_settings
from migrations.migrate import migrate
from rakeback.services._types import DbInfoDict

logger: logging.Logger = logging.getLogger(__name__)


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings: Settings = get_settings()
    logger.info("DB: %s", settings.database.db_info_for_logging())

    migrate()
    yield


def create_app() -> FastAPI:
    app: FastAPI = FastAPI(
        title="Validator Rakeback Engine",
        version="0.2.0",
        lifespan=_lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["*"],
    )

    @app.exception_handler(Exception)
    async def _on_error(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled: %s", exc)
        return JSONResponse(
            status_code=500,
            content={"detail": str(exc), "type": type(exc).__name__},
        )

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/health/db", dependencies=[Depends(get_api_key)])
    def health_db() -> DbInfoDict:
        return get_db_info()

    app.include_router(partners.router)
    app.include_router(attributions.router)
    app.include_router(conversions.router)
    app.include_router(rakeback.router)
    app.include_router(exports.router)
    app.include_router(completeness.router)

    return app


app: FastAPI = create_app()


def start() -> None:
    """Entry point for rakeback-api."""
    backend_root: Path = Path(__file__).resolve().parent.parent
    os.chdir(backend_root)

    for candidate in (backend_root / ".env", backend_root.parent / ".env"):
        if candidate.exists():
            load_dotenv(candidate, override=False)

    reload: bool = os.environ.get("RAKEBACK_RELOAD", "false").lower() in ("1", "true", "yes")
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=reload,
    )
