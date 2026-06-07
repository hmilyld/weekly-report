"""FastAPI application entry point."""

import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.database import engine, Base, SessionLocal
from app.models import User, AppConfig
from app.models_token import ApiToken  # noqa: F401 — ensure table is created
from app.routers import auth, daily, weekly, config
from app.routers import tokens, external, tasks


def _migrate_db():
    """Add missing columns to existing tables (SQLite ALTER TABLE)."""
    from sqlalchemy import inspect, text

    inspector = inspect(engine)

    # Add password_version to users table if missing
    try:
        existing_tables = inspector.get_table_names()
        if "users" in existing_tables:
            columns = {col["name"] for col in inspector.get_columns("users")}
            if "password_version" not in columns:
                with engine.begin() as conn:
                    conn.execute(text("ALTER TABLE users ADD COLUMN password_version INTEGER NOT NULL DEFAULT 0"))
                print("✅ Migration: added password_version column to users table")
            else:
                print("✅ users.password_version column already exists")
        else:
            print("ℹ️  users table does not exist yet (first run)")
    except Exception as e:
        print(f"⚠️  Migration check failed: {e}")


def _init_db():
    """Create tables and seed defaults on first run."""
    try:
        Base.metadata.create_all(bind=engine)
        print("✅ Database tables created/verified")
        _migrate_db()
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
    yield


app = FastAPI(
    title="Weekly Report System",
    version="1.0.0",
    lifespan=lifespan,
)

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
    if os.getenv("ENV", os.getenv("ENVIRONMENT", "development")) == "production":
        response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains"
    return response


# Routers
app.include_router(auth.router)
app.include_router(daily.router)
app.include_router(weekly.router)
app.include_router(config.router)
app.include_router(tokens.router)
app.include_router(external.router)
app.include_router(tasks.router)


# ─── Health check endpoint ───────────────────────────────
@app.get("/api/v1/health")
async def health():
    return {"status": "ok"}


# ─── Serve frontend static files ────────────────────────
STATIC_DIR = Path(__file__).resolve().parent.parent / "frontend" / "dist"
if not STATIC_DIR.exists():
    STATIC_DIR = Path("/app/frontend/dist")

if STATIC_DIR.exists():
    app.mount("/assets", StaticFiles(directory=str(STATIC_DIR / "assets")), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        """Catch-all: serve index.html for SPA routing."""
        file_path = STATIC_DIR / full_path
        # Resolve and verify the path is within STATIC_DIR (prevent traversal)
        if file_path.is_file():
            resolved = file_path.resolve()
            if not str(resolved).startswith(str(STATIC_DIR.resolve())):
                return FileResponse(str(STATIC_DIR / "index.html"))
            return FileResponse(str(resolved))
        return FileResponse(str(STATIC_DIR / "index.html"))
