# CLAUDE.md

This repository keeps one set of agent instructions. **Read [`AGENTS.md`](AGENTS.md) before
making changes** — it owns the project structure, development commands, coding style, testing,
commit conventions and architecture notes.

Claude-specific notes:

- Prefer the tools in the repo over ad-hoc shell: `pnpm` for the frontend, `uv` for the backend.
- The UI is Chinese; keep copy in Chinese and follow `DESIGN.md` for any visual change.
- Before finishing a task, run what the change touches: `pnpm lint`, `pnpm format:check`,
  `pnpm build` (frontend) or `uv run ruff check .`, `uv run pytest` (backend).
