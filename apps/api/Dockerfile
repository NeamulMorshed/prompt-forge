FROM python:3.13-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Install deps first — cached unless lockfile changes
COPY apps/api/pyproject.toml apps/api/uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# Copy app source (separate from deps for cache efficiency)
COPY apps/api/app ./app
COPY apps/api/migrations ./migrations
COPY apps/api/alembic.ini ./alembic.ini

# crs_loader.py resolves 5 parents up to /; schemas + patterns live at /packages/
COPY packages/schemas /packages/schemas
COPY packages/patterns /packages/patterns

COPY apps/api/start.sh ./start.sh
RUN chmod +x ./start.sh

ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="/app"

EXPOSE 8000
CMD ["./start.sh"]
