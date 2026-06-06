# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A weekly report auto-generation system (周报自动生成系统). Users maintain daily work logs via a calendar UI, then an LLM generates a weekly report summary. The UI is entirely in Chinese.

## Tech Stack

- **Frontend:** React 18, Vite 5, React Router 6, Axios, Lucide React icons — custom CSS (no Tailwind)
- **Backend:** Python 3.11, FastAPI, SQLAlchemy, SQLite, httpx (LLM client)
- **Auth:** JWT (python-jose + passlib/bcrypt), 24-hour expiry
- **LLM:** OpenAI-compatible Chat Completion API (configurable at runtime via Settings page)

## Development Commands

### Frontend (`frontend/`)
```bash
cd frontend
pnpm install          # install deps
pnpm dev              # Vite dev server on :5173, proxies /api to :8000
pnpm build            # production build (output goes to ../app/frontend/)
pnpm lint             # ESLint
pnpm lint:fix         # ESLint with auto-fix
pnpm format           # Prettier (no semicolons, single quotes, 100-char width)
pnpm format:check     # Prettier check
pnpm generate:icons   # regenerate PWA SVG icons (in public/)
```

### Backend (`backend/`)
```bash
cd backend
uv pip install -r requirements.txt   # install deps (use uv, not pip)
uv run uvicorn main:app --reload --port 8000   # dev server
uv run ruff check .              # lint
uv run ruff format .             # format
```

### Docker
```bash
docker compose up --build   # multi-stage build, serves on :8000
./scripts/docker-publish.sh [tag]  # 构建并推送到 Docker Hub (默认 tag=latest)
```

## Architecture

### Backend (`backend/`)
- `main.py` — FastAPI app entry, lifespan events, static file serving for SPA
- `app/config.py` — pydantic-settings (JWT, DB, LLM defaults via environment)
- `app/database.py` — SQLAlchemy engine, session factory, Base
- `app/models.py` — ORM models: `User`, `DailyReport`, `WeeklyReport`, `AppConfig`
- `app/models_token.py` — `ApiToken` model (64-char hex tokens for external API access)
- `app/auth.py` — JWT creation/decoding, `get_current_user` dependency
- `app/crud.py` — all database operations (centralized CRUD layer)
- `app/llm_client.py` — httpx-based OpenAI-compatible client + system prompt for report generation
- `app/routers/` — route modules: `auth`, `daily`, `weekly`, `config`, `tokens`, `external`

All API routes are under `/api/v1/`. The backend serves the SPA as a catch-all for non-API paths.

### Frontend (`frontend/src/`)
- `App.jsx` — Router, auth gates, responsive layout (TopNav desktop / Sidebar mobile)
- `api/index.js` — Axios instance + all API wrapper functions
- `pages/` — Login, Setup (first-run), DailyReport (calendar view), WeeklyReport, Settings
- `components/` — CalendarView (monthly grid), DailyEditModal
- `contexts/ThemeContext.jsx` — System/Light/Dark theme cycling
- `styles/global.css` — all styles, uses CSS custom properties for theming

### PWA
- Configured via `vite-plugin-pwa` in `vite.config.js`
- SVG icons in `public/pwa-{192,512}x{192,512}.svg` — calendar + document design with AI sparkle
- Run `pnpm generate:icons` to regenerate icons (script at `scripts/generate-pwa-icons.mjs`)
- Service worker precaches app shell; API calls use NetworkFirst strategy

### Database
- **User** — single-user auth system (id, username, password_hash, password_version)
- **DailyReport** — one per user per date (unique: user_id + date)
- **WeeklyReport** — one per user per week_start (unique: user_id + week_start)
- **AppConfig** — singleton (id=1) holding LLM API URL, model, API key
- **ApiToken** — tokens for external API authentication

## Code Style

- **Frontend:** no semicolons, single quotes, 100-char line width, 2-space indent (ESLint + Prettier)
- **Backend:** Ruff — 100-char line, 4-space indent, double quotes. RUF001/RUF002 ignored (intentional fullwidth CJK punctuation)
- **EditorConfig:** UTF-8, LF line endings everywhere

## Key Patterns

- LLM config is stored in DB (`AppConfig` table) and editable via the Settings page — no env vars needed at runtime
- The weekly report generation calls the LLM with all daily reports for that week as context
- The frontend `app/` directory contains a pre-built dist committed to the repo (used by Docker)
- External API endpoints (`/api/v1/external/`) use `ApiToken` auth instead of JWT
