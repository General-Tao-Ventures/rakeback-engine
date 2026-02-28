"""Alembic environment configuration."""

from logging.config import fileConfig

from alembic import context
from alembic.config import Config
from sqlalchemy import MetaData, pool
from sqlalchemy.engine import Engine

from config import Settings, get_settings
from db.models import Base

config: Config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata: MetaData = Base.metadata


def get_url() -> str:
    settings: Settings = get_settings()
    return settings.database.url


def run_migrations_offline() -> None:
    url: str = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    from sqlalchemy import create_engine

    engine_options: dict[str, type] = {"poolclass": pool.NullPool}

    connectable: Engine = create_engine(get_url(), **engine_options)

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
