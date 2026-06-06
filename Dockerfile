# ─── Stage 1: Build frontend ────────────────────────────
FROM node:18-alpine AS frontend-build

WORKDIR /build/frontend

# Install pnpm (pin to v9, compatible with Node 18)
RUN corepack enable && corepack prepare pnpm@9 --activate

# Copy package files and install
COPY frontend/package.json frontend/pnpm-lock.yaml* ./
RUN pnpm install --frozen-lockfile

# Copy source and build
COPY frontend/ ./
RUN pnpm run build

# ─── Stage 2: Runtime ───────────────────────────────────
FROM python:3.11-slim

WORKDIR /app

# Install Python dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY backend/ ./

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
EXPOSE 8000

# Environment variables (secrets must be injected at runtime)
ENV PYTHONUNBUFFERED=1
ENV DATABASE_URL=sqlite:///./data/weekly_report.db

# Run with uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
