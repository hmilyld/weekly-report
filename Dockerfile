# ─── Stage 1: Build frontend ────────────────────────────
FROM node:18-alpine AS frontend-build

WORKDIR /build/frontend

# Install pnpm
RUN corepack enable && corepack prepare pnpm@latest --activate

# Copy package files and install
COPY frontend/package.json frontend/pnpm-lock.yaml* ./
RUN pnpm install --frozen-lockfile 2>/dev/null || pnpm install

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

# Create data directory for SQLite
RUN mkdir -p /app/data

# Expose port
EXPOSE 8000

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV DATABASE_URL=sqlite:///./data/weekly_report.db
ENV JWT_SECRET_KEY=change-this-in-production

# Run with uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
