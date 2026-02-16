"""Application settings using Pydantic."""

from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseSettings(BaseSettings):
    """Database connection settings."""
    
    model_config = SettingsConfigDict(
        env_prefix="DB_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )
    
    driver: str = Field(default="postgresql+psycopg2", description="SQLAlchemy driver")
    host: str = Field(default="localhost", description="Database host")
    port: int = Field(default=5432, description="Database port")
    name: str = Field(default="rakeback", description="Database name")
    user: str = Field(default="rakeback", description="Database user")
    password: str = Field(default="", description="Database password")
    
    # SQLite override for development
    sqlite_path: Optional[str] = Field(default=None, description="SQLite file path (dev only)")
    
    # Connection pool settings
    pool_size: int = Field(default=5, description="Connection pool size")
    pool_timeout: int = Field(default=30, description="Pool timeout in seconds")
    pool_recycle: int = Field(default=1800, description="Connection recycle time in seconds")
    
    @property
    def url(self) -> str:
        """Build database URL."""
        if self.sqlite_path:
            return f"sqlite:///{self.sqlite_path}"
        return f"{self.driver}://{self.user}:{self.password}@{self.host}:{self.port}/{self.name}"


class ChainSettings(BaseSettings):
    """Chain RPC connection settings."""
    
    model_config = SettingsConfigDict(env_prefix="CHAIN_")
    
    rpc_url: str = Field(
        default="wss://entrypoint-finney.opentensor.ai:443",
        description="Bittensor RPC URL (HTTP or WebSocket)"
    )
    rpc_timeout: int = Field(default=30, description="RPC request timeout in seconds")
    retry_attempts: int = Field(default=3, description="Number of retry attempts")
    retry_delay: float = Field(default=1.0, description="Delay between retries in seconds")
    
    # Finality settings
    finality_depth: int = Field(default=6, description="Blocks to consider final")


class ProcessingSettings(BaseSettings):
    """Processing job settings."""
    
    model_config = SettingsConfigDict(env_prefix="PROCESSING_")
    
    batch_size: int = Field(default=100, description="Blocks per batch")
    max_parallel_blocks: int = Field(default=10, description="Max parallel block fetches")
    
    # Attribution settings
    proportion_precision: int = Field(default=18, description="Decimal places for proportions")
    
    # Aggregation settings
    daily_aggregation_hour_utc: int = Field(default=0, description="Hour to run daily aggregation")
    monthly_aggregation_day: int = Field(default=1, description="Day to run monthly aggregation")


class AlertingSettings(BaseSettings):
    """Alerting and notification settings."""
    
    model_config = SettingsConfigDict(env_prefix="ALERT_")
    
    enabled: bool = Field(default=False, description="Enable alerting")
    slack_webhook_url: Optional[str] = Field(default=None, description="Slack webhook URL")
    email_recipients: Optional[str] = Field(default=None, description="Comma-separated emails")
    
    # Thresholds
    missing_block_threshold_pct: float = Field(
        default=5.0,
        description="Percent missing blocks to trigger critical alert"
    )
    incomplete_entry_threshold_pct: float = Field(
        default=1.0,
        description="Percent incomplete entries to trigger medium alert"
    )


class Settings(BaseSettings):
    """Main application settings."""
    
    model_config = SettingsConfigDict(
        env_prefix="RAKEBACK_",
        env_nested_delimiter="__",
        extra="ignore"
    )
    
    # Environment
    environment: str = Field(default="development", description="Environment name")
    debug: bool = Field(default=False, description="Debug mode")
    
    # Paths
    config_dir: Path = Field(default=Path("config"), description="Configuration directory")
    data_dir: Path = Field(default=Path("data"), description="Data directory")
    export_dir: Path = Field(default=Path("exports"), description="Export output directory")
    
    # Nested settings
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    chain: ChainSettings = Field(default_factory=ChainSettings)
    processing: ProcessingSettings = Field(default_factory=ProcessingSettings)
    alerting: AlertingSettings = Field(default_factory=AlertingSettings)
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Ensure directories exist
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.export_dir.mkdir(parents=True, exist_ok=True)


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
