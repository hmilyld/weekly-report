# Repository Guidelines

## Project Structure

A full-stack weekly/monthly report auto-generation system. Users log daily work via a calendar UI, then an LLM generates weekly or monthly summaries. The UI is in Chinese. Multi-user with admin/user roles.

```
weekly-report/
├── frontend/          # React 18 + Vite 5 SPA
│   ├── src/
│   │   ├── api/         # Axios instance + API wrappers
│   │   ├── components/  # CalendarView, WeekList, DailyEditModal, ReportWorkspace
│   │   │   └── ui/        # Button, Field, Panel, Modal, ConfirmProvider, PeriodBar…
│   │   ├── contexts/    # AuthContext, ThemeContext
│   │   ├── hooks/       # Custom hooks (useMediaQuery)
│   │   ├── pages/       # DailyReport, WeeklyReport, MonthlyReport, Tasks, Settings, UserManagement…
│   │   ├── styles/      # tokens.css → base.css → components.css → app.css
│   │   └── utils/       # date helpers (incl. UTC parsing), clipboard
│   ├── public/          # App icons: favicon.svg, pwa-*.svg/png, apple-touch-icon.png
│   └── scripts/         # generate-pwa-icons.mjs
├── backend/           # Python FastAPI + SQLAlchemy + SQLite
│   ├── app/
│   │   ├── routers/     # auth, daily, weekly, monthly, tasks, config, tokens, external, users
│   │   ├── models.py    # ORM models (User, DailyReport, WeeklyReport, MonthlyReport, Task…)
│   │   ├── crud.py      # Centralized database operations
│   │   ├── auth.py      # JWT creation/decoding, dependencies
│   │   ├── crypto.py    # AES-GCM content encryption
│   │   ├── key_cache.py # In-memory per-user key cache
│   │   └── llm_client.py# OpenAI-compatible LLM client
│   ├── tests/           # Pytest: crypto, CRUD encryption, key cache
│   └── main.py          # App entry, lifespan, migrations, static file serving
├── .github/workflows/ # release-image.yml (tag → ghcr.io)
├── scripts/           # dev.sh (dev helper), docker-publish.sh (Docker Hub)
├── Dockerfile         # Multi-stage build (Node 20 + Python 3.11)
├── docker-compose.yml
├── README.md          # Project intro + usage (users/operators)
├── PRODUCT.md         # Product truth
├── DESIGN.md          # Design system
└── AGENTS.md          # This file
```

## Build, Test, and Development Commands

User-facing installation and deployment steps live in `README.md`; this section is the working
reference for agents (lint, test, release).

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
bash scripts/dev.sh start    # Start both frontend and backend
bash scripts/dev.sh stop     # Stop all services
bash scripts/dev.sh restart  # Restart all services
bash scripts/dev.sh status   # Check if services are running
bash scripts/dev.sh logs     # View recent logs
```

Logs, PIDs and port config live in `.dev/` (git-ignored).

### Docker

```bash
docker compose up --build            # Build and run on :18001
IMAGE=ghcr.io/hmilyld/weekly-report:latest docker compose up -d  # Use a published image
./scripts/docker-publish.sh [tag]    # Build, smoke test, push to Docker Hub
git tag -a v1.2.0 -m "v1.2.0" && git push origin v1.2.0   # Tag → CI builds + pushes ghcr.io
```

`.github/workflows/release-image.yml` verifies the tag exists, builds, runs the container
and checks `/api/v1/health` before pushing. `.dockerignore` must keep `**/data` and `**/*.db`
excluded — the image is published publicly.

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

### Frontend styling

The visual system is documented in `DESIGN.md` and is not re-decided per screen.

- **No literal values in page code.** Colours, sizes, radii, shadows, and durations come from the tokens in `src/styles/tokens.css`. Inline `style={{}}` is only for one-off layout a component cannot express.
- **One component vocabulary.** Use `components/ui/` (`Button`, `Field`, `Panel`, `Modal`, `EmptyState`, `PeriodBar`) instead of new ad-hoc markup. Destructive actions go through `useConfirm()`, never `window.confirm`.
- **Styling layers:** `tokens.css` (values) → `base.css` (reset, focus, browser surfaces) → `components.css` (button/field/panel/modal/tabs/state) → `app.css` (shell, navigation, page surfaces). Add rules to the layer that owns them.
- **Theme by re-pointing tokens**, not by duplicating rules under `[data-theme='dark']`.
- **Every interactive component ships default, hover, focus-visible, active, disabled, and loading.** Icon-only buttons need `aria-label`.

## Testing

- **Backend:** Pytest in `backend/tests/` (`test_crypto.py`, `test_crud_encryption.py`, `test_key_cache.py`). Run: `cd backend && uv run pytest`.
- **Frontend:** No test suite. Before committing UI work, run `pnpm lint`, `pnpm format:check` and `pnpm build`, and check the page at 1440px and 390px in both themes.

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

- **Auth:** JWT with 24h expiry. Password change invalidates old tokens via `password_version`. `require_admin` protects admin-only endpoints. `last_login_at` is written on login and initial setup.
- **Password change** requires `old_password` (the key is re-derived from it), returns a fresh token, and every other session is invalidated by the `password_version` bump. A wrong current password answers `402` so the client shows an inline error instead of dropping the session; `401` always means "session invalid".
- **Logout** calls `POST /auth/logout` while the token is still attached (it clears the server-side key cache) and only then drops the local session.
- **Encryption at rest:** report/task content is AES-GCM encrypted per user; the key is derived from the login password and cached in memory (`key_cache`). A server restart empties the cache, so the UI shows a re-login modal instead of blank content. `_migrate_db()` + `migrate_user_encryption()` upgrade legacy plaintext rows on login.
- **LLM config** lives in the `AppConfig` table (singleton, id=1), editable at runtime via Settings — no env vars needed.
- **External API** (`/api/v1/external/`) authenticates with `X-API-Token` instead of JWT.
- **Migrations** run automatically on startup via `_migrate_db()` in `main.py` (additive only).
- **Timestamps** are stored as UTC without an offset; the frontend parses them with `parseServerDate()` before display.
- **SPA serving:** the backend serves `frontend/dist/` as a catch-all for non-API paths.

## Documentation Map

| File | Owns | Keep out of it |
|---|---|---|
| `README.md` | Project intro, features, install/usage, env vars, API reference | Product rationale, design tokens, agent rules |
| `PRODUCT.md` | Users, purpose, capabilities, constraints, principles | Visual system, commands |
| `DESIGN.md` | Tokens, type, layout, components, do/don't | Product strategy, build commands |
| `AGENTS.md` | Structure, commands, style, testing, commits, release | Marketing copy, design rationale |

When behaviour changes, update the file that owns it — do not duplicate the same fact in two files.
