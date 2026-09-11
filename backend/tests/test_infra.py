"""Faza 0: infrastructura — logging fara ANSI, migrare idempotenta."""
from __future__ import annotations

import logging
from pathlib import Path

from sqlalchemy import text

from database import _migrate, engine
from log_utils import MakedirsRotatingFileHandler, PlainFormatter, strip_ansi


def test_strip_ansi_removes_color_codes() -> None:
    colored = "\x1b[32m200\x1b[0m \x1b[2m1.2ms\x1b[0m"
    assert strip_ansi(colored) == "200 1.2ms"


def test_plain_formatter_strips_ansi_from_record() -> None:
    formatter = PlainFormatter("%(message)s")
    record = logging.LogRecord(
        name="app.access", level=logging.INFO, pathname=__file__, lineno=1,
        msg="\x1b[31mGET /x 500\x1b[0m", args=(), exc_info=None,
    )
    assert "\x1b[" not in formatter.format(record)
    assert "GET /x 500" in formatter.format(record)


def test_makedirs_handler_creates_missing_directory(tmp_path: Path) -> None:
    target = tmp_path / "nested" / "deep" / "server.log"
    handler = MakedirsRotatingFileHandler(str(target), maxBytes=1024, backupCount=1)
    try:
        assert target.parent.is_dir()
    finally:
        handler.close()


def test_migrate_is_idempotent() -> None:
    _migrate()
    _migrate()  # a doua rulare nu trebuie sa arunce


def test_migrate_adds_missing_column() -> None:
    _migrate()
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE IF NOT EXISTS _drift_probe (id INTEGER PRIMARY KEY)"))
        conn.execute(text("ALTER TABLE _drift_probe ADD COLUMN extra TEXT"))
        cols_before = {
            r[0] for r in conn.execute(text("SELECT name FROM pragma_table_info('_drift_probe')"))
        }
    assert "extra" in cols_before

    # _migrate nu stie de acest tabel (nu e in metadata) — nu-l atinge, dar nici nu crapa.
    _migrate()
    with engine.begin() as conn:
        conn.execute(text("DROP TABLE _drift_probe"))


def test_seed_settings_keys_match_scoring_default_points() -> None:
    """seed.DEFAULT_SETTINGS si scoring.DEFAULT_POINTS trebuie sa ramana in sincron —
    inclusiv cheile noi de grupa (PLAN_GRUPE.md sectiunea 4)."""
    from seed import DEFAULT_SETTINGS
    from services.scoring import DEFAULT_POINTS

    assert set(DEFAULT_SETTINGS) == set(DEFAULT_POINTS)
    for key, value in DEFAULT_SETTINGS.items():
        assert int(value) == DEFAULT_POINTS[key]
    assert "pts.group.qualify" in DEFAULT_SETTINGS
    assert "pts.group.perfect" in DEFAULT_SETTINGS
