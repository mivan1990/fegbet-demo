"""Engine, sesiune, Base declarativ si migrare idempotenta (fara Alembic)."""
from __future__ import annotations

import logging
from collections.abc import Iterator

from sqlalchemy import create_engine, event, inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.schema import CreateColumn

from config import settings

logger = logging.getLogger("app.db")

_is_sqlite = settings.database_url.startswith("sqlite")

engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False} if _is_sqlite else {},
    future=True,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


class Base(DeclarativeBase):
    pass


if _is_sqlite:

    @event.listens_for(engine, "connect")
    def _sqlite_pragmas(dbapi_connection, _connection_record):  # noqa: ANN001
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.close()


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _existing_columns(connection, table_name: str) -> set[str]:
    """Coloanele existente pentru un tabel, via PRAGMA table_info (parametru legat)."""
    rows = connection.execute(
        text("SELECT name FROM pragma_table_info(:t)"), {"t": table_name}
    ).fetchall()
    return {r[0] for r in rows}


def _migrate(target_engine: Engine | None = None) -> None:
    """Migrare idempotenta.

    1. `create_all` creeaza tabelele lipsa complet.
    2. Pentru tabelele existente, adauga coloanele lipsa cu ALTER TABLE ADD COLUMN.

    Identificatorii (nume de tabel/coloana) provin exclusiv din metadata modelelor
    noastre, nu din input de utilizator; valorile din interogari sunt legate ca
    parametri, nu interpolate.
    """
    import models  # noqa: F401  (inregistreaza toate modelele pe Base.metadata)

    eng = target_engine or engine
    Base.metadata.create_all(eng)

    known_tables = set(Base.metadata.tables.keys())
    inspector = inspect(eng)
    dialect = eng.dialect

    with eng.begin() as connection:
        db_tables = set(inspector.get_table_names())
        for table_name, table in Base.metadata.tables.items():
            if table_name not in known_tables or table_name not in db_tables:
                continue
            present = _existing_columns(connection, table_name)
            for column in table.columns:
                if column.name in present:
                    continue
                col_ddl = CreateColumn(column).compile(dialect=dialect).string
                logger.info("migrare: %s ADD COLUMN %s", table_name, column.name)
                connection.execute(text(f'ALTER TABLE "{table_name}" ADD COLUMN {col_ddl}'))
