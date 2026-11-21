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
from app.database import Base, SessionLocal, engine
from app.encryption_utils import ContentDecryptionError, EncryptionKeyMissingError
from app.envelope import get_kek, load_all_user_deks
from app.migration import (
    _cleanup_plaintext_content,
    backup_before_envelope_migration,
    migrate_app_config_secret,
)
from app.models import AppConfig
from app.models_token import ApiToken  # noqa: F401 — ensure table is created
from app.routers import auth, config, daily, monthly, tasks, tokens, users, weekly

logger = logging.getLogger(__name__)


def _migrate_db():
    """Add missing columns to existing tables (SQLite ALTER TABLE)."""
    from sqlalchemy import inspect, text

    try:
        existing_tables = inspect(engine).get_table_names()
    except Exception as e:
        print(f"⚠️  Migration: cannot inspect tables: {e}")
        return

    # ── users table ────────────────────────────────────────
    if "users" in existing_tables:
        try:
            columns = {col["name"] for col in inspect(engine).get_columns("users")}
            migrations = [
                ("password_version", "INTEGER NOT NULL DEFAULT 0"),
                ("role", "VARCHAR(20) NOT NULL DEFAULT 'user'"),
                ("needs_encryption_migration", "BOOLEAN NOT NULL DEFAULT 1"),
                ("last_login_at", "DATETIME"),
                ("wrapped_dek", "TEXT"),
                ("wrapped_dek_version", "INTEGER NOT NULL DEFAULT 1"),
            ]
            for col_name, col_def in migrations:
                if col_name not in columns:
                    with engine.begin() as conn:
                        conn.execute(text(f"ALTER TABLE users ADD COLUMN {col_name} {col_def}"))
                    print(f"✅ Migration: added users.{col_name}")
            if "role" not in columns:
                with engine.begin() as conn:
                    conn.execute(text("UPDATE users SET role = 'admin' WHERE id = 1"))
        except Exception as e:
            print(f"⚠️  Migration users failed: {e}")
    else:
        print("ℹ️  users table does not exist yet (first run)")

    # ── encryption columns for each content table ──────────
    for table in ("daily_reports", "weekly_reports", "tasks", "monthly_reports"):
        if table not in existing_tables:
            continue
        try:
            columns = {col["name"] for col in inspect(engine).get_columns(table)}
            enc_cols = [
                ("content_encrypted", "TEXT"),
                ("content_salt", "VARCHAR(64)"),
                ("content_nonce", "VARCHAR(64)"),
                ("content_tag", "VARCHAR(64)"),
                ("content_version", "INTEGER"),
            ]
            for col_name, col_def in enc_cols:
                if col_name not in columns:
                    with engine.begin() as conn:
                        conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {col_name} {col_def}"))
                    print(f"✅ Migration: added {table}.{col_name}")
        except Exception as e:
            print(f"⚠️  Migration {table} failed: {e}")


def _init_db():
    """Create tables and seed defaults on first run."""
    try:
        Base.metadata.create_all(bind=engine)
        print("✅ Database tables created/verified")
        _migrate_db()
        # One-time safety snapshot BEFORE any destructive upgrade step, so the
        # irreversible envelope migration always has a rollback point.
        backup_db = SessionLocal()
        try:
            backup_path = backup_before_envelope_migration(backup_db)
        finally:
            backup_db.close()
        if backup_path:
            print(
                f"✅ Pre-migration backup saved: {backup_path} (0600, keep until upgrade verified)"
            )
        _cleanup_plaintext_content(SessionLocal())
    except Exception as e:
        print(f"❌ Database init failed: {e}")
        raise

    db = SessionLocal()
    try:
        # Seed default config only (users are created via /api/v1/auth/setup)
        if not db.query(AppConfig).filter(AppConfig.id == 1).first():
            cfg = AppConfig(
                id=1,
                llm_api_url="http://localhost:11434/v1/chat/completions",
                llm_model_name="llama2",
                api_key="",
            )
            db.add(cfg)
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    _init_db()
    # Envelope encryption: validate the master key, then restore every user's
    # DEK from the DB so content is readable without anyone logging in.
    get_kek()  # raises on invalid/missing master key → refuse to start
    db = SessionLocal()
    try:
        migrate_app_config_secret(db)
        failed = load_all_user_deks(db)
        if failed:
            print(
                f"⚠️  DEK unwrap failed for user ids {failed} — "
                "check ENCRYPTION_MASTER_KEY; their content is unreadable until fixed"
            )
    finally:
        db.close()
    yield


app = FastAPI(
    title="Weekly Report System",
    version="1.0.1",
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
STATIC_DIR = Path(__file__).resolve().parent.parent / "frontend" / "dist"
if not STATIC_DIR.exists():
    STATIC_DIR = Path("/app/frontend/dist")


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
    app.mount("/assets", StaticFiles(directory=str(STATIC_DIR / "assets")), name="assets")

    @app.api_route("/{full_path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
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
