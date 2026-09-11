"""Rate limiting cu slowapi. Cheia = IP-ul real (X-Forwarded-For prin reverse proxy)."""
from __future__ import annotations

import os

from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address


def _key(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return get_remote_address(request)


# Dezactivabil pentru testele E2E (RATE_LIMIT_ENABLED=false). Implicit activ.
_ENABLED = os.getenv("RATE_LIMIT_ENABLED", "true").strip().lower() not in {"false", "0", "no"}

limiter = Limiter(key_func=_key, enabled=_ENABLED)
