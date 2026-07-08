# Repository Guidelines

## Project Structure

A full-stack weekly/monthly report auto-generation system. Users log daily work via a calendar UI, then an LLM generates weekly or monthly summaries. The UI is in Chinese. Multi-user with admin/user roles.

```
weekly-report/
├── frontend/          # React 18 + Vite 5 SPA
│   ├── src/
│   │   ├── api/         # Axios instance + API wrappers
│   │   ├── components/  # CalendarView, DailyEditModal
│   │   ├── contexts/    # AuthContext, ThemeContext
│   │   ├── hooks/       # Custom hooks (useMediaQuery)
│   │   ├── pages/       # DailyReport, WeeklyReport, MonthlyReport, Settings, etc.
│   │   ├── styles/      # global.css (CSS custom properties for theming)
│   │   └── utils/       # date helpers
│   └── public/          # PWA icons (SVG)
├── backend/           # Python FastAPI + SQLAlchemy + SQLite
│   ├── app/
│   │   ├── routers/     # Route modules: auth, daily, weekly, monthly, config, tokens, external, users
│   │   ├── models.py    # ORM models (User, DailyReport, WeeklyReport, MonthlyReport, Task, etc.)
│   │   ├── crud.py      # Centralized database operations
│   │   ├── auth.py      # JWT creation/decoding, dependencies
│   │   └── llm_client.py# OpenAI-compatible LLM client
│   ├── tests/           # Pytest tests (crypto, CRUD encryption, key cache)
│   └── main.py          # App entry, lifespan, static file serving
├── scripts/           # Dev helper script, Docker publish
├── Dockerfile         # Multi-stage build (Node 18 + Python 3.11)
└── docker-compose.yml
```

## Build, Test, and Development Commands

### Frontend (`frontend/`)

| Command | Description |
|---|---|
| `pnpm install` | Install dependencies |
| `pnpm dev` | Vite dev server on `:5173`, proxies `/api` to `:18001` |
| `pnpm build` | Production build |
| `pnpm lint` / `pnpm lint:fix` | ESLint check / auto-fix |
| `pnpm format` / `pnpm format:check` | Prettier format / check |
| `pnpm generate:icons` | Regenerate PWA SVG icons |

### Backend (`backend/`)

| Command | Description |
|---|---|
| `uv venv` | Create Python virtual environment |
| `uv pip install -r requirements.txt` | Install dependencies |
| `uv run uvicorn main:app --reload --port 18001` | Dev server |
| `uv run ruff check .` | Lint |
| `uv run ruff format .` | Format |
| `uv run pytest` | Run tests |

### Dev Helper (project root)

```bash
./scripts/dev start    # Start both frontend and backend
./scripts/dev stop     # Stop all services
./scripts/dev restart  # Restart all services
./scripts/dev status   # Check if services are running
./scripts/dev logs     # View recent logs
```

### Docker

```bash
docker compose up --build   # Build and run on :18001
./scripts/docker-publish.sh [tag]  # Build and push to Docker Hub
```

## Coding Style

### Backend (Python / Ruff)

- **4-space indent**, double quotes, LF line endings.
- 100-char line length. `E501` suppressed — formatter handles wrapping.
- Import ordering via `isort` rules (`I`). First-party: `app`.
- `RUF001`/`RUF002` ignored — fullwidth CJK punctuation is intentional.
- `B008` ignored — FastAPI `Depends()` in default arguments is expected.

### Frontend (JavaScript / ESLint + Prettier)

- **2-space indent**, no semicolons, single quotes, 100-char width.
- Trailing commas everywhere. Arrow parens always.
- LF line endings. UTF-8 charset (see `.editorconfig`).
- React 18 — `react/react-in-jsx-scope` off (no explicit React imports).
- `prop-types` off — typed via conventions, not PropTypes.

## Testing

- **Backend:** Pytest in `backend/tests/`. Tests cover encryption, crypto utilities, and key caching.
- **Frontend:** No test suite currently configured.
- Run backend tests: `cd backend && uv run pytest`

## Commit Conventions

Commit messages follow [Conventional Commits](https://www.conventionalcommits.org/) with Chinese descriptions:

```
feat: 新增月报功能
fix: 修复深色模式下登录按钮无边框的bug
style: 优化移动端显示
refactor: 修复 code review 问题
docs: 更新文档
```

Prefixes: `feat`, `fix`, `style`, `refactor`, `docs`. Description in Chinese is the norm.

## Pull Request Guidelines

- Provide a clear description of what changed and why.
- Reference related issues where applicable.
- Include screenshots for UI changes.
- Ensure `pnpm lint` and `pnpm format:check` pass for frontend changes.
- Ensure `uv run ruff check .` passes for backend changes.

## Architecture Notes

- **Auth:** JWT with 24h expiry. Password change invalidates old tokens via `password_version`. `require_admin` dependency protects admin-only endpoints.
- **LLM config** is stored in the `AppConfig` DB table (singleton, id=1) and editable at runtime via the Settings page — no env vars needed for LLM setup.
- **External API** (`/api/v1/external/`) uses `ApiToken` auth instead of JWT.
- **Database migrations** run automatically on startup via `_migrate_db()` in `main.py`.
- **SPA serving:** The backend serves `frontend/dist/` as a catch-all for non-API paths.
