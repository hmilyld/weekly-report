"""FastAPI application entry point."""

import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.database import SessionLocal
from app.encryption_utils import ContentDecryptionError, EncryptionKeyMissingError
from app.envelope import get_kek, load_all_user_deks
from app.migration import migrate_app_config_secret
from app.routers import auth, config, daily, monthly, tasks, tokens, users, weekly
from app.schema_migrations import init_database

logger = logging.getLogger(__name__)


def configure_logging() -> None:
    """Make application INFO logs visible; uvicorn only configures its own loggers."""
    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO").upper(),
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
    )
    # The LLM client logs every request at INFO; keep the app's log readable.
    logging.getLogger("httpx").setLevel(logging.WARNING)


configure_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_database()
    # Envelope encryption: validate the master key, then restore every user's
    # DEK from the DB so content is readable without anyone logging in.
    get_kek()  # raises on invalid/missing master key → refuse to start
    with SessionLocal() as db:
        migrate_app_config_secret(db)
        failed = load_all_user_deks(db)
    if failed:
        logger.warning(
            "DEK unwrap failed for user ids %s — check ENCRYPTION_MASTER_KEY; "
            "their content is unreadable until fixed",
            failed,
        )
    yield


app = FastAPI(
    title="Weekly Report System",
    version=os.getenv("APP_VERSION", "dev"),
    lifespan=lifespan,
)


# ─── Encryption error mapping ────────────────────────────
# Writes without a DEK and reads that cannot decrypt must fail loudly (409),
# never fall back to plaintext or silently empty content.


@app.exception_handler(EncryptionKeyMissingError)
async def encryption_key_missing_handler(request: Request, exc: EncryptionKeyMissingError):
    return JSONResponse(
        status_code=409,
        content={
            "code": "encryption_key_missing",
            "detail": "服务端加密密钥不可用，已拒绝写入。该账号尚未完成加密迁移（或迁移失败）："
            "请重试登录；若持续失败，请检查服务端日志与 ENCRYPTION_MASTER_KEY 配置。",
        },
    )


@app.exception_handler(ContentDecryptionError)
async def content_decryption_handler(request: Request, exc: ContentDecryptionError):
    return JSONResponse(
        status_code=409,
        content={
            "code": "decryption_failed",
            "detail": "内容解密失败，操作已中止。请确认 ENCRYPTION_MASTER_KEY 正确，"
            "且该账号已在网页端登录完成加密迁移。",
        },
    )


@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    """Domain validation (out-of-range dates, past deadlines) answers 400, not 500.

    Logged with a traceback so a programming error that happens to raise
    ValueError stays visible instead of being silently downgraded.
    """
    logger.warning("Invalid request on %s: %s", request.url.path, exc, exc_info=exc)
    return JSONResponse(status_code=400, content={"detail": str(exc)})


# CORS — if CORS_ORIGINS is set, restrict to those origins; otherwise allow all
# (self-hosted single-user app, security enforced via JWT/API-Token auth)
_cors_origins_str = os.getenv("CORS_ORIGINS", "")
_cors_origins = [o.strip() for o in _cors_origins_str.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins if _cors_origins else ["*"],
    allow_credentials=bool(_cors_origins),
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type", "X-API-Token"],
)


# Security headers middleware
@app.middleware("http")
async def security_headers(request: Request, call_next):
    response: Response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    if settings.is_production:
        response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains"
    return response


# Routers
app.include_router(auth.router)
app.include_router(daily.router)
app.include_router(weekly.router)
app.include_router(monthly.router)
app.include_router(config.router)
app.include_router(tokens.router)
app.include_router(tasks.router)
app.include_router(users.router)


# ─── Health check endpoint ───────────────────────────────
@app.get("/api/v1/health")
async def health():
    return {"status": "ok"}


# ─── Serve frontend static files ────────────────────────
# Repo layout: backend/main.py → ../frontend/dist
# Image layout: /app/main.py     → /app/frontend/dist
_STATIC_CANDIDATES = (
    Path(__file__).resolve().parent / "frontend" / "dist",
    Path(__file__).resolve().parent.parent / "frontend" / "dist",
)
STATIC_DIR = next(
    (candidate for candidate in _STATIC_CANDIDATES if candidate.exists()),
    _STATIC_CANDIDATES[0],
)


def resolve_static_file(full_path: str) -> Path | None:
    """Return the file inside STATIC_DIR for a URL path, or None.

    A plain string prefix check would also accept sibling directories whose name
    starts with "dist" (e.g. dist-old), so path components are compared.
    """
    try:
        resolved = (STATIC_DIR / full_path).resolve()
    except (OSError, RuntimeError):
        return None
    if not resolved.is_relative_to(STATIC_DIR.resolve()):
        return None
    return resolved if resolved.is_file() else None


if STATIC_DIR.exists():
    _assets_dir = STATIC_DIR / "assets"
    if _assets_dir.is_dir():
        app.mount("/assets", StaticFiles(directory=str(_assets_dir)), name="assets")

    @app.api_route(
        "/{full_path:path}",
        methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
        include_in_schema=False,
    )
    async def serve_spa(full_path: str, request: Request):
        """SPA catch-all.

        Unknown API paths answer JSON 404 — never the HTML shell — so clients
        calling removed endpoints (e.g. the old /api/v1/external/*) fail
        clearly instead of parsing a web page.
        """
        if full_path == "api" or full_path.startswith("api/"):
            return JSONResponse(status_code=404, content={"detail": "Not Found"})
        if request.method != "GET":
            return JSONResponse(status_code=405, content={"detail": "Method Not Allowed"})
        resolved = resolve_static_file(full_path)
        if resolved is not None:
            return FileResponse(str(resolved))
        return FileResponse(str(STATIC_DIR / "index.html"))
