"""FastAPI application factory and configuration."""

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from rakeback.api.routes import attributions, conversions, exports, partners, rakeback


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="Validator Rakeback Engine",
        version="0.1.0",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:5173",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(partners.router)
    app.include_router(attributions.router)
    app.include_router(conversions.router)
    app.include_router(rakeback.router)
    app.include_router(exports.router)

    @app.get("/health")
    def health_check():
        return {"status": "ok", "version": "0.1.0"}

    return app


app = create_app()


def start() -> None:
    """Entry point for the rakeback-api script."""
    import os
    # Disable reload on Windows to avoid multiprocessing PermissionError with WatchFiles
    reload = os.environ.get("RAKEBACK_RELOAD", "false").lower() in ("1", "true", "yes")
    uvicorn.run(
        "rakeback.api.app:app",
        host="0.0.0.0",
        port=8000,
        reload=reload,
    )
