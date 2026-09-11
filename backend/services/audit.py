"""Audit: scrie fiecare actiune in activity_logs SI in fisierul rotativ."""
from __future__ import annotations

import json
import logging
from typing import Any

from fastapi import Request
from sqlalchemy.orm import Session

from models import ActivityLog, User
from services.security import client_ip

logger = logging.getLogger("app.audit")


def _json_default(value: Any) -> str:
    return str(value)


def log_action(
    db: Session,
    action: str,
    *,
    actor: User | None = None,
    actor_user_id: int | None = None,
    target_user_id: int | None = None,
    entity_type: str | None = None,
    entity_id: int | None = None,
    detail: dict[str, Any] | None = None,
    request: Request | None = None,
) -> ActivityLog:
    """Adauga o intrare in sesiune (commit-ul e al apelantului) si logheaza in fisier.

    `detail` este serializat JSON; foloseste-l pentru `{"before": ..., "after": ...}`.
    Nu pune niciodata parole sau hash-uri in `detail`.
    """
    resolved_actor_id = actor_user_id if actor_user_id is not None else (actor.id if actor else None)

    ip = user_agent = None
    if request is not None:
        ip = client_ip(request)
        user_agent = request.headers.get("user-agent")

    entry = ActivityLog(
        actor_user_id=resolved_actor_id,
        target_user_id=target_user_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        detail=json.dumps(detail or {}, default=_json_default, ensure_ascii=False),
        ip_address=ip,
        user_agent=(user_agent[:400] if user_agent else None),
    )
    db.add(entry)

    logger.info(
        "%s actor=%s target=%s entity=%s/%s ip=%s",
        action,
        resolved_actor_id if resolved_actor_id is not None else "-",
        target_user_id if target_user_id is not None else "-",
        entity_type or "-",
        entity_id if entity_id is not None else "-",
        ip or "-",
    )
    return entry
