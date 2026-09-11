"""Aplicatia FEG BET: middleware, migrari, montare frontend, rute /api."""
from __future__ import annotations

import logging
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from slowapi.errors import RateLimitExceeded

from config import settings
from database import SessionLocal, _migrate
from routers import admin as admin_router
from routers import admin_groups as admin_groups_router
from routers import auth as auth_router
from routers import e2e as e2e_router
from routers import groups as groups_router
from routers import leaderboard as leaderboard_router
from routers import matches as matches_router
from routers import players as players_router
from routers import settings as settings_router
from routers import teams as teams_router
from routers import tickets as tickets_router
from seed import seed_all
from services.rate_limit import limiter

logger = logging.getLogger("app")
access_logger = logging.getLogger("app.access")

BASE_DIR = Path(__file__).resolve().parent
FRONTEND_DIST = BASE_DIR.parent / "frontend" / "dist"

# --- middleware de blocare scanere -------------------------------------------------
_BLOCK_SUBSTRINGS = (".env", ".git", "wp-admin", "phpunit", "/vendor/", "xmlrpc")
_BLOCK_SUFFIXES = (".php", ".asp", ".sql", ".bak")

# --- culori ANSI pentru consola --------------------------------------------------
_RESET = "\x1b[0m"
_DIM = "\x1b[2m"
_GREEN = "\x1b[32m"
_YELLOW = "\x1b[33m"
_RED = "\x1b[31m"


def _status_color(status: int) -> str:
    if status >= 500:
        return _RED
    if status >= 400:
        return _YELLOW
    return _GREEN


def _client_ip(request: Request) -> str:
    """IP-ul real: X-Forwarded-For (primul) daca vine prin reverse proxy."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "-"


def _identity_from_request(request: Request) -> str:
    """Emailul din JWT pentru access log, sau '-' daca lipseste/invalid."""
    auth = request.headers.get("authorization", "")
    if not auth.lower().startswith("bearer "):
        return "-"
    from services.security import email_from_token

    return email_from_token(auth[7:].strip()) or "-"


@asynccontextmanager
async def lifespan(_app: FastAPI):
    settings.validate()
    _migrate()
    with SessionLocal() as db:
        seed_all(db)
    logger.info("FEG BET pornit. DB migrata si populata.")
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan, docs_url="/docs", redoc_url=None)
app.state.limiter = limiter


@app.exception_handler(RateLimitExceeded)
async def _rate_limit_handler(_request: Request, _exc: RateLimitExceeded) -> JSONResponse:
    return JSONResponse(
        status_code=429,
        content={"detail": "Prea multe încercări. Așteaptă un minut și încearcă din nou."},
    )

if settings.cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


# Ordinea conteaza: middleware-ul definit ULTIMUL ruleaza primul (cel mai in exterior).
# Vrem access_log in exterior ca sa logheze si cererile respinse de blocarea de scanere.


@app.middleware("http")
async def block_scanners_middleware(request: Request, call_next):
    """Respinge cu 404 cererile tipice de scanare (inainte de rutare)."""
    path = request.url.path.lower()
    if any(s in path for s in _BLOCK_SUBSTRINGS) or path.endswith(_BLOCK_SUFFIXES):
        return JSONResponse(status_code=404, content={"detail": "Not Found"})
    return await call_next(request)


@app.middleware("http")
async def access_log_middleware(request: Request, call_next):
    """O linie per cerere: IP, email (sau '-'), metoda, path, status, durata.

    Consola: colorat. Fisier logs/server.log: fara ANSI (PlainFormatter).
    """
    start = time.perf_counter()
    response = await call_next(request)
    elapsed_ms = (time.perf_counter() - start) * 1000

    ip = _client_ip(request)
    identity = _identity_from_request(request)
    color = _status_color(response.status_code)
    access_logger.info(
        "%s%s%s %s %s %s %s%d%s %s%.1fms%s",
        _DIM, ip, _RESET,
        identity,
        request.method,
        request.url.path,
        color, response.status_code, _RESET,
        _DIM, elapsed_ms, _RESET,
    )
    return response


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "app": settings.app_name}


app.include_router(auth_router.router)
app.include_router(teams_router.router)
app.include_router(players_router.router)
app.include_router(matches_router.router)
app.include_router(tickets_router.router)
app.include_router(settings_router.router)
app.include_router(leaderboard_router.router)
app.include_router(groups_router.router)
app.include_router(admin_router.router)
app.include_router(admin_groups_router.router)

# routers/e2e.py: doar pentru suita Playwright, NICIODATA in productie — vezi
# docstring-ul modulului. Ruta nu exista deloc in aplicatie fara acest flag (nu
# doar "refuzata"), ca sa nu poata ajunge accesibila printr-o greseala de config.
if settings.e2e_test_mode:
    logger.warning(
        "E2E_TEST_MODE=1: ruta /api/e2e/reset-groups e activa. "
        "NU rula asta pe serverul de productie."
    )
    app.include_router(e2e_router.router)


# --- montare frontend (SPA) -----------------------------------------------------
# Dupa toate rutele /api. In dev, frontend/dist nu exista si se sare peste.
if FRONTEND_DIST.is_dir():
    app.mount(
        "/assets",
        StaticFiles(directory=FRONTEND_DIST / "assets"),
        name="assets",
    )

    @app.get("/{full_path:path}")
    async def spa_fallback(full_path: str):
        if full_path.startswith("api/"):
            return JSONResponse(status_code=404, content={"detail": "Ruta inexistenta."})
        candidate = FRONTEND_DIST / full_path
        if full_path and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(FRONTEND_DIST / "index.html")
