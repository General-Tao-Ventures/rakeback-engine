"""Application settings using Pydantic.

DB selection (deterministic, ONE place):
  - DATABASE_URL set and non-empty → PostgreSQL (use that URL).
  - DATABASE_URL absent/empty → ALWAYS SQLite (DB_SQLITE_PATH, default data/rakeback.db).
.env is loaded from backend root deterministically (not cwd-dependent).
"""

from functools import lru_cache
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def _backend_root() -> Path:
    """Backend package root (backend/). settings.py is in backend/src/rakeback/config/."""
    return Path(__file__).resolve().parent.parent.parent.parent


def _ensure_env_loaded() -> None:
    """Load .env from backend root (then project root) before any settings. Idempotent."""
    root = _backend_root()
    for candidate in (root / ".env", root.parent / ".env"):
        if candidate.exists():
            load_dotenv(candidate, override=False)


# Load .env as soon as config is imported
_ensure_env_loaded()


class DatabaseSettings(BaseSettings):
    """Database connection settings. Source of truth: DATABASE_URL or DB_SQLITE_PATH."""

    model_config = SettingsConfigDict(
        env_prefix="DB_",
        env_file=(str(_backend_root() / ".env"), ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Explicit Postgres: if set, use this URL. Otherwise ALWAYS use SQLite.
    database_url: Optional[str] = Field(
        default=None,
        description="PostgreSQL DSN; when set, uses Postgres. When absent, uses SQLite.",
        validation_alias="DATABASE_URL",
    )

    driver: str = Field(default="postgresql+psycopg2", description="SQLAlchemy driver (Postgres only)")
    host: str = Field(default="localhost", description="Database host")
    port: int = Field(default=5432, description="Database port")
    name: str = Field(default="rakeback", description="Database name")
    user: str = Field(default="rakeback", description="Database user")
    password: str = Field(default="", description="Database password")

    # SQLite: path relative to backend root. Default "data/rakeback.db".
    sqlite_path: Optional[str] = Field(
        default="data/rakeback.db",
        description="SQLite path (relative to backend root); used when DATABASE_URL is not set",
    )

    pool_size: int = Field(default=5, description="Connection pool size")
    pool_timeout: int = Field(default=30, description="Pool timeout in seconds")
    pool_recycle: int = Field(default=1800, description="Connection recycle time in seconds")

    def _use_postgres(self) -> bool:
        """True iff DATABASE_URL is explicitly set."""
        raw = (self.database_url or "").strip()
        return bool(raw)

    def _resolved_sqlite_path(self) -> Path:
        """Absolute path to SQLite file. Always relative to backend root."""
        raw = (self.sqlite_path or "data/rakeback.db").strip()
        path = Path(raw)
        if not path.is_absolute():
            path = (_backend_root() / path).resolve()
        return path

    def _redacted_postgres_dsn(self) -> str:
        """Postgres DSN with password redacted."""
        import re
        url = (self.database_url or "").strip()
        return re.sub(r":([^:@]+)@", r":***@", url) if url else ""

    @property
    def url(self) -> str:
        """Build database URL. Single source of truth for engine creation."""
        if self._use_postgres():
            return (self.database_url or "").strip()
        path = self._resolved_sqlite_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        return f"sqlite:///{path.as_posix()}"

    def db_info_for_logging(self) -> str:
        """Single line for startup log: backend type + absolute path or redacted DSN."""
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

    rpc_url: str = Field(
        default="wss://entrypoint-finney.opentensor.ai:443",
        description="Bittensor RPC URL (HTTP or WebSocket)",
    )
    rpc_timeout: int = Field(default=30, description="RPC request timeout in seconds")
    retry_attempts: int = Field(default=3, description="Number of retry attempts")
    retry_delay: float = Field(default=1.0, description="Delay between retries in seconds")
    finality_depth: int = Field(default=6, description="Blocks to consider final")


class ProcessingSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="PROCESSING_")

    batch_size: int = Field(default=100, description="Blocks per batch")
    max_parallel_blocks: int = Field(default=10, description="Max parallel block fetches")
    proportion_precision: int = Field(default=18, description="Decimal places for proportions")
    daily_aggregation_hour_utc: int = Field(default=0, description="Hour for daily aggregation")
    monthly_aggregation_day: int = Field(default=1, description="Day for monthly aggregation")


class AlertingSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="ALERT_")

    enabled: bool = Field(default=False, description="Enable alerting")
    slack_webhook_url: Optional[str] = Field(default=None, description="Slack webhook URL")
    email_recipients: Optional[str] = Field(default=None, description="Comma-separated emails")
    missing_block_threshold_pct: float = Field(default=5.0, description="Percent missing for critical alert")
    incomplete_entry_threshold_pct: float = Field(default=1.0, description="Percent for medium alert")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="RAKEBACK_",
        env_nested_delimiter="__",
        extra="ignore",
    )

    environment: str = Field(default="development", description="Environment name")
    debug: bool = Field(default=False, description="Debug mode")
    config_dir: Path = Field(default=Path("config"), description="Configuration directory")
    data_dir: Path = Field(default=Path("data"), description="Data directory")
    export_dir: Path = Field(default=Path("exports"), description="Export output directory")

    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    chain: ChainSettings = Field(default_factory=ChainSettings)
    processing: ProcessingSettings = Field(default_factory=ProcessingSettings)
    alerting: AlertingSettings = Field(default_factory=AlertingSettings)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.export_dir.mkdir(parents=True, exist_ok=True)


@lru_cache()
def get_settings() -> Settings:
    """Cached settings instance."""
    return Settings()
