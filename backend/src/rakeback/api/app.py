"""FastAPI application factory and configuration."""

import logging
import os
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from rakeback.api.routes import attributions, conversions, exports, health, partners, rakeback

logger = logging.getLogger(__name__)


@asynccontextmanager
async def _lifespan(app: FastAPI):
    """Ensure DB schema exists before handling requests."""
    from rakeback.config import get_settings
    from rakeback.database import init_database

    settings = get_settings()
    backend = "sqlite" if not settings.database._use_postgres() else "postgres"
    path_or_dsn = (
        settings.database._resolved_sqlite_path().as_posix()
        if not settings.database._use_postgres()
        else settings.database._redacted_postgres_dsn()
    )
    logger.info("DB: %s | %s", backend, path_or_dsn)

    init_database()
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title="Validator Rakeback Engine",
        version="0.1.0",
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
    async def _on_error(request: Request, exc: Exception):
        logger.exception("Unhandled: %s", exc)
        detail = str(exc)
        if "no such table" in detail.lower() or "operationalerror" in type(exc).__name__.lower():
            from rakeback.database import get_resolved_sqlite_path
            path = get_resolved_sqlite_path()
            hint = f" DB schema missing. Kill other backend processes, run: rakeback init-db, then restart." if path else " DB schema missing. Run: rakeback init-db."
            detail = f"{detail}{hint}"
        return JSONResponse(
            status_code=500,
            content={"detail": detail, "type": type(exc).__name__},
        )

    # Health routes - mount explicitly so /health and /health/db always exist
    @app.get("/health")
    def _health():
        return {"status": "ok"}

    @app.get("/health/db")
    def _health_db():
        return health._get_db_info()
    app.include_router(partners.router)
    app.include_router(attributions.router)
    app.include_router(conversions.router)
    app.include_router(rakeback.router)
    app.include_router(exports.router)

    return app


app = create_app()


def start() -> None:
    """Entry point for rakeback-api."""
    import os
    from pathlib import Path

    # app.py is backend/src/rakeback/api/app.py -> backend = 4 parents
    backend_root = Path(__file__).resolve().parent.parent.parent.parent
    os.chdir(backend_root)

    # Load .env from backend root, then project root (deterministic, cwd-independent)
    from dotenv import load_dotenv
    for candidate in (backend_root / ".env", backend_root.parent / ".env"):
        if candidate.exists():
            load_dotenv(candidate, override=False)

    reload = os.environ.get("RAKEBACK_RELOAD", "false").lower() in ("1", "true", "yes")
    uvicorn.run(
        "rakeback.api.app:app",
        host="0.0.0.0",
        port=8000,
        reload=reload,
    )
