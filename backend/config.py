"""Application settings — single file, Pydantic-based.

DB selection:
  - DATABASE_URL set and non-empty -> PostgreSQL
  - DATABASE_URL absent/empty -> SQLite (DB_SQLITE_PATH, default data/rakeback.db)
"""

import re
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def _backend_root() -> Path:
    """Backend package root (backend/). config.py lives at backend/config.py."""
    return Path(__file__).resolve().parent


def _ensure_env_loaded() -> None:
    """Load .env from backend root (then project root). Idempotent."""
    root: Path = _backend_root()
    for candidate in (root / ".env", root.parent / ".env"):
        if candidate.exists():
            load_dotenv(candidate, override=False)


_ensure_env_loaded()


class DatabaseSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="DB_",
        env_file=(str(_backend_root() / ".env"), ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str | None = Field(
        default=None,
        description="PostgreSQL DSN; when set, uses Postgres.",
        validation_alias="DATABASE_URL",
    )
    driver: str = Field(default="postgresql+psycopg2")
    host: str = Field(default="localhost")
    port: int = Field(default=5432)
    name: str = Field(default="rakeback")
    user: str = Field(default="rakeback")
    password: str = Field(default="")
    sqlite_path: str | None = Field(default="data/rakeback.db")
    pool_size: int = Field(default=5)
    pool_timeout: int = Field(default=30)
    pool_recycle: int = Field(default=1800)

    def _use_postgres(self) -> bool:
        return bool((self.database_url or "").strip())

    def _resolved_sqlite_path(self) -> Path:
        raw: str = (self.sqlite_path or "data/rakeback.db").strip()
        path: Path = Path(raw)
        if not path.is_absolute():
            path = (_backend_root() / path).resolve()
        return path

    def _redacted_postgres_dsn(self) -> str:
        url: str = (self.database_url or "").strip()
        return re.sub(r":([^:@]+)@", r":***@", url) if url else ""

    @property
    def url(self) -> str:
        if self._use_postgres():
            return (self.database_url or "").strip()
        path = self._resolved_sqlite_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        return f"sqlite:///{path.as_posix()}"

    def db_info_for_logging(self) -> str:
        if self._use_postgres():
            return f"PostgreSQL @ {self._redacted_postgres_dsn()}"
        return f"SQLite @ {self._resolved_sqlite_path().as_posix()}"


class ChainSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="CHAIN_",
        env_file=(str(_backend_root() / ".env"), ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    rpc_url: str = Field(default="wss://entrypoint-finney.opentensor.ai:443")
    rpc_timeout: int = Field(default=30)
    retry_attempts: int = Field(default=3)
    retry_delay: float = Field(default=1.0)
    finality_depth: int = Field(default=6)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="RAKEBACK_",
        env_nested_delimiter="__",
        extra="ignore",
    )

    environment: str = Field(default="development")
    debug: bool = Field(default=False)
    api_key: str | None = Field(default=None, description="API key for mutation endpoints")
    config_dir: Path = Field(default=Path("config"))
    data_dir: Path = Field(default=Path("data"))
    export_dir: Path = Field(default=Path("exports"))

    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    chain: ChainSettings = Field(default_factory=ChainSettings)

    def model_post_init(self, _context: object) -> None:
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.export_dir.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    return Settings()
