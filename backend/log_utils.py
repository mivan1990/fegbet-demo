"""Utilitare de logging: formatter care scoate codurile ANSI pentru fisier."""
from __future__ import annotations

import logging
import os
import re
from logging.handlers import RotatingFileHandler

_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


def strip_ansi(text: str) -> str:
    return _ANSI_RE.sub("", text)


class PlainFormatter(logging.Formatter):
    """Ca Formatter standard, dar elimina secventele ANSI (culori) din mesaj."""

    def format(self, record: logging.LogRecord) -> str:
        return strip_ansi(super().format(record))


class MakedirsRotatingFileHandler(RotatingFileHandler):
    """RotatingFileHandler care creeaza folderul tinta daca lipseste.

    uvicorn configureaza logging-ul inainte de a importa aplicatia, deci
    `logs/` s-ar putea sa nu existe cand se instantiaza handler-ul.
    """

    def __init__(self, filename: str, *args: object, **kwargs: object) -> None:
        directory = os.path.dirname(filename)
        if directory:
            os.makedirs(directory, exist_ok=True)
        super().__init__(filename, *args, **kwargs)  # type: ignore[arg-type]
