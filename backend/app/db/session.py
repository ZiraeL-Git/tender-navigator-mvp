from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from backend.app.core.settings import Settings
from backend.app.db.base import Base


def create_engine_from_settings(settings: Settings) -> Engine:
    connect_args: dict[str, object] = {}
    if settings.database_url.startswith("sqlite"):
        connect_args["check_same_thread"] = False
        Path(settings.data_dir).mkdir(parents=True, exist_ok=True)

    return create_engine(settings.database_url, future=True, connect_args=connect_args)


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


def prepare_legacy_schema(engine: Engine) -> None:
    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())

    rename_map: dict[str, str] = {}

    if "company_profiles" in table_names:
        company_columns = {column["name"] for column in inspector.get_columns("company_profiles")}
        if "payload_json" in company_columns and "company_name" not in company_columns:
            rename_map["company_profiles"] = "legacy_company_profiles"

    if "analyses" in table_names:
        rename_map["analyses"] = "legacy_analyses"

    if not rename_map:
        return

    with engine.begin() as connection:
        for old_name, new_name in rename_map.items():
            existing_tables = set(inspect(connection).get_table_names())
            if old_name in existing_tables and new_name not in existing_tables:
                connection.execute(text(f"ALTER TABLE {old_name} RENAME TO {new_name}"))


def run_migrations(settings: Settings) -> None:
    config = Config(str(settings.backend_dir / "alembic.ini"))
    config.set_main_option("script_location", str(settings.backend_dir / "alembic"))
    config.set_main_option("sqlalchemy.url", settings.database_url)
    engine = create_engine_from_settings(settings)
    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())
    current_schema_tables = {
        "users",
        "company_profiles",
        "tender_analyses",
        "tender_documents",
        "analysis_results",
        "analysis_events",
    }

    if current_schema_tables.issubset(table_names):
        with engine.begin() as connection:
            if "alembic_version" not in table_names:
                connection.execute(text("CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL)"))
            row_count = connection.execute(text("SELECT COUNT(*) FROM alembic_version")).scalar_one()
            if row_count == 0:
                connection.execute(
                    text("INSERT INTO alembic_version (version_num) VALUES ('20260408_01')")
                )

    command.upgrade(config, "head")


def initialize_database(engine: Engine, settings: Settings) -> None:
    prepare_legacy_schema(engine)
    run_migrations(settings)
    Base.metadata.create_all(bind=engine)


@contextmanager
def session_scope(session_factory: sessionmaker[Session]) -> Iterator[Session]:
    session = session_factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
