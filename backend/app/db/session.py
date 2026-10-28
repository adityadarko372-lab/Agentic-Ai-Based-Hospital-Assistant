"""SQLite engine and request-scoped sessions."""

from collections.abc import Iterator

from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlmodel import Session, SQLModel, create_engine

from app.core.config import get_settings

_engine: Engine | None = None


def _configure_sqlite(dbapi_connection, _connection_record) -> None:
    cursor = dbapi_connection.cursor()
    # SQLite ignores FOREIGN KEY constraints unless this pragma is on.
    cursor.execute("PRAGMA foreign_keys=ON")
    # WAL lets readers continue while one request writes, and a writer waits
    # up to 15 s for another writer instead of failing at once with
    # "database is locked" (seen when two browser tests submitted together
    # while the assistant was busy with an optional model).
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA busy_timeout=15000")
    cursor.close()


def get_engine() -> Engine:
    """Create the engine lazily, so tests can point it at a temporary file."""
    global _engine
    if _engine is None:
        database_path = get_settings().database_path
        database_path.parent.mkdir(parents=True, exist_ok=True)
        _engine = create_engine(
            f"sqlite:///{database_path.as_posix()}",
            # FastAPI may use a different thread per request.
            connect_args={"check_same_thread": False, "timeout": 15},
        )
        event.listen(_engine, "connect", _configure_sqlite)
    return _engine


def reset_engine() -> None:
    """Close all connections and forget the engine (used by tests)."""
    global _engine
    if _engine is not None:
        _engine.dispose()
    _engine = None


def _add_missing_columns(engine: Engine) -> None:
    """Tiny forward-only migration for an existing demo database.

    `create_all` creates missing tables but never adds columns to a table
    that already exists. Columns added in later phases are nullable, so they
    can be added with ALTER TABLE without touching existing rows.
    """
    with engine.begin() as connection:
        for table in SQLModel.metadata.sorted_tables:
            existing = {row[1] for row in connection.exec_driver_sql(f'PRAGMA table_info("{table.name}")')}
            if not existing:
                continue  # table was just created with every column
            for column in table.columns:
                if column.name not in existing and column.nullable:
                    column_type = column.type.compile(dialect=engine.dialect)
                    connection.exec_driver_sql(f'ALTER TABLE "{table.name}" ADD COLUMN "{column.name}" {column_type}')


def create_tables() -> None:
    # Importing the models registers them with SQLModel.metadata.
    from app.db import models  # noqa: F401

    engine = get_engine()
    SQLModel.metadata.create_all(engine)
    _add_missing_columns(engine)


def get_session() -> Iterator[Session]:
    """FastAPI dependency: one database session per request."""
    with Session(get_engine()) as session:
        yield session
