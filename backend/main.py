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
from app.routers import tokens, external


def _init_db():
    """Create tables and seed defaults on first run."""
    Base.metadata.create_all(bind=engine)
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

# CORS — restrict to specific origins
_cors_origins_str = os.getenv("CORS_ORIGINS", "")
_cors_origins = [o.strip() for o in _cors_origins_str.split(",") if o.strip()] or [
    "http://localhost:5173",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
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
