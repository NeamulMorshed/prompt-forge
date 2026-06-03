# PromptForge

Adaptive prompt-generation platform. Phase 0 foundation.

## Layout
- `apps/api` — FastAPI backend (LLM router, DB, auth). Managed with uv.
- `apps/web` — Next.js frontend. Managed with pnpm.
- `infra/` — docker-compose (Postgres + Redis).

## Quickstart
```bash
cp .env.example .env
docker compose -f infra/docker-compose.yml up -d
cd apps/api && uv sync && uv run alembic upgrade head && uv run uvicorn app.main:app --reload
# in another shell:
cd apps/web && pnpm install && pnpm dev
```
