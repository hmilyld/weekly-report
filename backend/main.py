"""FastAPI application entry point."""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
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

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(auth.router)
app.include_router(daily.router)
app.include_router(weekly.router)
app.include_router(config.router)
app.include_router(tokens.router)
app.include_router(external.router)

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
        if file_path.is_file():
            return FileResponse(str(file_path))
        return FileResponse(str(STATIC_DIR / "index.html"))
