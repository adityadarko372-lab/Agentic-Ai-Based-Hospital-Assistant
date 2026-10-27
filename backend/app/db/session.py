"""SQLite engine and request-scoped sessions."""

from collections.abc import Iterator

from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlmodel import Session, SQLModel, create_engine

from app.core.config import get_settings

_engine: Engine | None = None


def _enable_sqlite_foreign_keys(dbapi_connection, _connection_record) -> None:
    # SQLite ignores FOREIGN KEY constraints unless this pragma is on.
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
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
            connect_args={"check_same_thread": False},
        )
        event.listen(_engine, "connect", _enable_sqlite_foreign_keys)
    return _engine


def reset_engine() -> None:
    """Close all connections and forget the engine (used by tests)."""
    global _engine
    if _engine is not None:
        _engine.dispose()
    _engine = None


def create_tables() -> None:
    # Importing the models registers them with SQLModel.metadata.
    from app.db import models  # noqa: F401

    SQLModel.metadata.create_all(get_engine())


def get_session() -> Iterator[Session]:
    """FastAPI dependency: one database session per request."""
    with Session(get_engine()) as session:
        yield session
