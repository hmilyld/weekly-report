# ─── Stage 1: Build frontend ────────────────────────────
FROM node:24-alpine AS frontend-build

WORKDIR /build/frontend

# Install pnpm (pin to v9, compatible with Node 24)
RUN corepack enable && corepack prepare pnpm@9 --activate

# Copy package files and install
COPY frontend/package.json frontend/pnpm-lock.yaml* ./
RUN pnpm install --frozen-lockfile

# Copy source and build
COPY frontend/ ./

# Version argument from build context
ARG APP_VERSION=dev
RUN APP_VERSION=${APP_VERSION} pnpm run build

# ─── Stage 2: Runtime ───────────────────────────────────
FROM python:3.11-slim

WORKDIR /app

# Install Python dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code (tests and packaging files stay out of the image)
COPY backend/app ./app
COPY backend/main.py ./

# Copy built frontend from stage 1
COPY --from=frontend-build /build/frontend/dist ./frontend/dist

# Create data directory and non-root user
RUN mkdir -p /app/data && \
    addgroup --system app && \
    adduser --system --ingroup app app && \
    chown -R app:app /app

# Switch to non-root user
USER app

# Expose port
EXPOSE 18001

# Runtime configuration. ENV=production makes JWT_SECRET_KEY and
# ENCRYPTION_MASTER_KEY mandatory: the container refuses to start without them
# instead of silently generating development keys.
ARG APP_VERSION=dev
ENV APP_VERSION=${APP_VERSION}
ENV ENV=production
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV DATABASE_URL=sqlite:///./data/weekly_report.db

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:18001/api/v1/health')" || exit 1

# Run with uvicorn (single process: the DEK cache and the login rate limiter are
# per process, and SQLite has a single writer).
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "18001"]
