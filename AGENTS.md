# Repository Guidelines

## Project Structure

A full-stack weekly/monthly report auto-generation system. Users log daily work via a calendar UI, then an LLM generates weekly or monthly summaries. The UI is in Chinese. Multi-user with admin/user roles.

```
weekly-report/
├── frontend/          # React 18 + Vite 5 SPA
│   ├── src/
│   │   ├── api/         # Axios instance + API wrappers
│   │   ├── components/  # CalendarView, WeekList, DailyEditModal, ReportWorkspace
│   │   │   ├── settings/  # LlmPanel, PasswordPanel, TokenPanel
│   │   │   ├── tasks/     # TaskEditor, TaskRow, TaskComposer, deadline helpers
│   │   │   └── ui/        # Button, Field, PasswordInput, Panel, Modal, ConfirmProvider, PeriodBar…
│   │   ├── contexts/    # Auth/Theme providers + auth.js/theme.js hooks
│   │   ├── hooks/       # Custom hooks (useMediaQuery)
│   │   ├── pages/       # DailyReport, WeeklyReport, MonthlyReport, Tasks, Settings, UserManagement…
│   │   ├── styles/      # tokens.css → base.css → components.css → app.css
│   │   └── utils/       # date helpers (incl. UTC parsing), clipboard
│   ├── public/          # App icons: favicon.svg, pwa-*.svg/png, apple-touch-icon.png
│   └── scripts/         # generate-pwa-icons.mjs
├── backend/           # Python FastAPI + SQLAlchemy + SQLite
│   ├── app/
│   │   ├── routers/     # auth, daily, weekly, monthly, tasks, config, tokens, users
│   │   ├── crud/        # Persistence, one module per aggregate (users/reports/tasks/app_config)
│   │   ├── models.py    # ORM models (User, DailyReport, WeeklyReport, MonthlyReport, Task, ApiToken…)
│   │   ├── schemas.py   # Request/response models (+ ListResponse with `_decryption_failed` alias)
│   │   ├── auth.py      # JWT, password hashing/validation, dual-auth dependencies
│   │   ├── config.py    # Settings + secret resolution (`.env`-aware) and validation
│   │   ├── database.py  # Engine/session, SQLite PRAGMAs, per-request commit/rollback
│   │   ├── schema_migrations.py # Startup: create tables, additive ALTERs, snapshot, seed
│   │   ├── crypto.py    # AES-GCM primitives (+ legacy frozen KDF for migration)
│   │   ├── envelope.py  # Envelope encryption: master key → KEK → per-user DEK
│   │   ├── encryption_utils.py # Centralized content encrypt/decrypt (version 2 + AAD)
│   │   ├── key_cache.py # In-memory per-user DEK cache (restored from DB at startup)
│   │   ├── date_range.py# Validated week/month bounds (400 instead of 500)
│   │   ├── migration.py # Startup hygiene + one-time legacy→DEK migration on login
│   │   ├── reencrypt.py # Legacy→DEK re-encryption (single transaction, no commit)
│   │   └── llm_client.py# OpenAI-compatible LLM client (+ SSRF guard)
│   ├── tests/           # Pytest: crypto, envelope, DEK migration, API/auth contracts…
│   └── main.py          # App entry, lifespan, error mapping, static SPA serving
├── .github/workflows/ # ci.yml (PR gate), release-image.yml (tag → ghcr.io)
├── scripts/           # dev.sh (dev helper), docker-publish.sh (Docker Hub)
├── Dockerfile         # Multi-stage build (Node 24 + Python 3.11)
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
| `pnpm test` / `pnpm test:watch` | Vitest unit tests (one run / watch mode) |
| `pnpm format` / `pnpm format:check` | Prettier format / check |
| `pnpm generate:icons` | Regenerate PWA SVG icons |

### Backend (`backend/`)

| Command | Description |
|---|---|
| `uv venv` | Create Python virtual environment |
| `uv pip install -r requirements.txt` | Install runtime dependencies |
| `uv pip install -r requirements.txt -r dev-requirements.txt` | Install runtime + dev tooling (ruff, pytest) |
| `uv run uvicorn main:app --reload --port 18001` | Dev server |
| `uv run ruff check .` | Lint |
| `uv run ruff format .` | Format |
| `uv run pytest` | Run tests |
| `uv run pytest --cov=app --cov-report=term-missing` | Run tests with a coverage report (what CI prints) |

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
- **One component vocabulary.** Use `components/ui/` (`Button`, `Field`, `PasswordInput`, `Panel`, `Modal`, `EmptyState`, `PeriodBar`) instead of new ad-hoc markup. Destructive actions go through `useConfirm()`, never `window.confirm`.
- **Styling layers:** `tokens.css` (values) → `base.css` (reset, focus, browser surfaces) → `components.css` (button/field/panel/modal/tabs/state) → `app.css` (shell, navigation, page surfaces). Add rules to the layer that owns them.
- **Theme by re-pointing tokens**, not by duplicating rules under `[data-theme='dark']`. A pinned theme also updates `<meta name="color-scheme">` and both `theme-color` tags (see `ThemeContext`).
- **Overlays use the platform.** `Modal` is a native `<dialog>` opened with `showModal()`; do not add `role="dialog"`, `aria-modal`, a focus trap, or an Esc handler, and never lock scroll with `overflow: hidden` on `body`.
- **Every interactive component ships default, hover, focus-visible, active, disabled, and loading.** Icon-only buttons need `aria-label`.

## Testing

- **Backend:** Pytest in `backend/tests/` (`test_crypto.py`, `test_envelope.py`, `test_dek_migration.py`, `test_pre_migration_backup.py`, `test_crud_encryption.py`, `test_key_cache.py`, `test_login_migration.py`, `test_unified_auth.py`, `test_unified_api.py`, `test_settings.py`, `test_auth_hardening.py`, `test_config_api.py`, `test_token_lifecycle.py`, `test_input_validation.py`, `test_llm_url_guard.py`, `test_data_layer.py`, `test_response_contract.py`). Run: `cd backend && uv run pytest`. `tests/conftest.py` sets a fixed `ENCRYPTION_MASTER_KEY` and provides the `api_env` TestClient fixture (its `get_db` override mirrors production: commit on success, rollback on error). CI runs the same suite on Python 3.11 and 3.12 with `pytest-cov` and prints the coverage table; it is informational, not a gate.
- **Frontend:** Vitest + jsdom + Testing Library in `src/**/__tests__/` (utils: date/listInput/clipboard; api client; ui: Button/Field/PasswordInput/PeriodBar; pages: Settings; `useMediaQuery` hook). Run: `cd frontend && pnpm test`. `src/test/setup.js` loads jest-dom matchers and a memory `localStorage` (Node 25's global stub has no methods). Unit tests cover pure logic and the API client; UI changes still need a manual pass at 1440px and 390px in both themes.

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
- **Password change** requires `old_password`, returns a fresh token, and every other session is invalidated by the `password_version` bump. Content ciphertext is NEVER touched (the DEK is independent of the password). A wrong current password answers `402` so the client shows an inline error instead of dropping the session; `401` always means "session invalid".
- **Logout** calls `POST /auth/logout` while the token is still attached, then drops the local session. It does NOT clear `key_cache`: the DEK is a server-side key shared by all devices of the account, recoverable from the DB at any time.
- **Encryption at rest (envelope):** `ENCRYPTION_MASTER_KEY` → HKDF → KEK wraps a random per-user DEK (`users.wrapped_dek`, AAD-bound). Startup unwraps all DEKs into `key_cache`, so restarts need no login. Content is AES-GCM under the DEK with `content_version=2` and AAD binding table+user; `content_salt` is deprecated (no longer written). Writes without a DEK raise `EncryptionKeyMissingError` → HTTP 409, never plaintext. Legacy users (`wrapped_dek` NULL) migrate once at login via `migrate_user_to_dek()` (single transaction, idempotent, rollback on failure); migration failure does NOT block login — reads are flagged, writes 409, and the failing table/record id is logged. While legacy users exist, startup takes a one-time `data/pre-envelope-*.db` snapshot (SQLite backup API, 0600) as a rollback point. The legacy password-derived KDF in `auth.derive_user_key` is FROZEN — changing its parameters destroys legacy data. Decrypted views (content AND `AppConfig.api_key`) use `set_committed_value` so plaintext is never autoflushed back into mapped columns.
- **LLM config** lives in the `AppConfig` table (singleton, id=1), editable at runtime via Settings — no env vars needed. The API key is envelope-wrapped (`ek1:` prefix) with legacy JWT-secret-derived fallback on read; startup re-wraps legacy values.
- **Unified API / dual auth:** one route set serves both clients. Data endpoints (`/daily`, `/weekly`, `/monthly`, `/tasks`) use `get_authenticated_user` (Bearer JWT or `X-API-Token`; JWT wins when both are present, and an invalid JWT does not fall back to the token). Auth/config/user/token endpoints keep `get_current_user`/`require_admin`, so API tokens are structurally limited to data access. The old `/api/v1/external/*` surface was removed — clients use the canonical routes (`POST /daily` accepts optional `date` + `append`; `POST /weekly/{week_start}?force=false` returns `generated=false` without an LLM call, and 409 when the existing report cannot be decrypted; `GET /tasks/pending`). Machine-readable contract: `/openapi.json`.
- **API Token security (current):** tokens are stored in plaintext, never expire, and have no scopes (hardening deferred — see README). Changing the password does NOT revoke them (only JWTs are invalidated by `password_version`); `DELETE /tokens` is the explicit revoke-all. Treat a token as equivalent to data access for that account.
- **Auth semantics:** `401` = missing/invalid credential, `402` = wrong current password inside a valid session, `403` = authenticated but not admin. `get_current_user` uses `HTTPBearer(auto_error=False)` so it answers 401 itself.
- **Migrations** run automatically on startup via `app/schema_migrations.py` (additive only); no Alembic.
- **SQLite concurrency:** the connect hook sets `journal_mode=WAL`, `foreign_keys=ON`, `busy_timeout=5000`. Live backups must include `-wal`/`-shm`, or stop the container first.
- **Dependencies:** `backend/requirements.txt` is the single source of truth for runtime packages; dev tooling (ruff, pytest, pytest-cov) lives in `backend/dev-requirements.txt` and is never installed into the image. There is no committed lock file (`uv.lock` is ignored). Verify a bump in a throwaway env: `uv venv --python 3.11 /tmp/x && uv pip install --python /tmp/x/bin/python -r requirements.txt -r dev-requirements.txt`.
- **Reverse proxy:** the login rate limiter keys on `request.client.host`, so behind a proxy set `FORWARDED_ALLOW_IPS` (uvicorn honours it) or every client shares one bucket.
- **Settings:** secrets are resolved in `model_validator(mode="after")` so `ENV`/`JWT_SECRET_KEY`/`ENCRYPTION_MASTER_KEY` in `.env` are honored. Production refuses to start without them; placeholder/short JWT keys are rejected. The `data/.encryption_key` fallback is written only when no master key is configured (development).
- **LLM URL guard:** `ipaddress`-based after DNS resolution; loopback is allowed on purpose (local Ollama), private/link-local/reserved ranges are rejected.
- **`_decryption_failed` is wire contract:** response models carry `decryption_failed` with `alias="_decryption_failed"`; keep the JSON key stable (see docs/android-api.md).
- **Timestamps** are stored as UTC without an offset; the frontend parses them with `parseServerDate()` before display.
- **SPA serving:** the backend serves `frontend/dist/` as a catch-all for non-API paths.

## Documentation Map

| File | Owns | Keep out of it |
|---|---|---|
| `README.md` | Project intro, features, install/usage, env vars, API reference | Product rationale, design tokens, agent rules |
| `PRODUCT.md` | Users, purpose, capabilities, constraints, principles | Visual system, commands |
| `DESIGN.md` | Tokens, type, layout, components, do/don't | Product strategy, build commands |
| `AGENTS.md` | Structure, commands, style, testing, commits, release | Marketing copy, design rationale |
| `CONTRIBUTING.md` | Contributor setup, PR checklist, commit format | Repo internals, release procedure |
| `SECURITY.md` | Vulnerability reporting, supported versions, known trade-offs | Feature docs, install steps |
| `CHANGELOG.md` | User-visible changes per released version | Internal refactor detail, design rationale |

When behaviour changes, update the file that owns it — do not duplicate the same fact in two files.
