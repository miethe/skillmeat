# =============================================================================
# SkillMeat API - Multi-Stage Production Dockerfile
# =============================================================================
# Build: docker build -t skillmeat-api .
# Run:   docker run -p 8080:8080 -v skillmeat-data:/home/app/.skillmeat skillmeat-api
# =============================================================================

# ---------------------------------------------------------------------------
# Stage 1: Builder - install dependencies and build wheels
# ---------------------------------------------------------------------------
FROM python:3.12-slim AS builder

WORKDIR /build

# Install build-time system dependencies required by cryptography, psycopg2, etc.
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
        libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency metadata and source
COPY pyproject.toml LICENSE README.md ./
COPY skillmeat/ ./skillmeat/

# Build wheels for all runtime dependencies + psycopg2-binary for Postgres support
RUN pip wheel --no-cache-dir --wheel-dir /build/wheels \
    . \
    psycopg2-binary

# ---------------------------------------------------------------------------
# Stage 2: Production - minimal runtime image
# ---------------------------------------------------------------------------
FROM python:3.12-slim AS production

LABEL org.opencontainers.image.source="https://github.com/miethe/skillmeat"
LABEL org.opencontainers.image.description="SkillMeat API - Personal collection manager for Claude Code artifacts"

# Install only runtime system libraries (libpq for psycopg2, git for GitPython)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        libpq5 \
        git \
        curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd --create-home --shell /bin/bash --uid 1000 app

# Install wheels from builder stage (no pip/setuptools left in final layer cache)
COPY --from=builder /build/wheels /tmp/wheels
RUN pip install --no-cache-dir --no-deps /tmp/wheels/*.whl && \
    rm -rf /tmp/wheels

# Remove pip and setuptools from the final image to reduce attack surface
RUN pip uninstall -y pip setuptools 2>/dev/null; \
    rm -rf /usr/local/lib/python3.12/ensurepip

# Create data directory for collection persistence
RUN mkdir -p /home/app/.skillmeat && \
    chown -R app:app /home/app/.skillmeat

WORKDIR /app

# Copy application source (needed for uvicorn module resolution)
# This includes alembic migrations at skillmeat/cache/migrations/
COPY --chown=app:app skillmeat/ ./skillmeat/

# Copy entrypoint script
COPY --chown=app:app docker-entrypoint.sh /app/docker-entrypoint.sh
RUN chmod +x /app/docker-entrypoint.sh

# ---------------------------------------------------------------------------
# Runtime configuration
# ---------------------------------------------------------------------------

# Server
ENV SKILLMEAT_HOST=0.0.0.0
ENV SKILLMEAT_PORT=8080
ENV SKILLMEAT_ENV=production

# Database: defaults to SQLite (local mode). Set DATABASE_URL for Postgres.
# Examples:
#   SQLite:   sqlite:///home/app/.skillmeat/skillmeat.db
#   Postgres: postgresql://user:pass@host:5432/skillmeat
ENV SKILLMEAT_COLLECTION_DIR=/home/app/.skillmeat/collections

# Expose API port
EXPOSE 8080

# Health check against the /health endpoint
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Run as non-root
USER app

ENTRYPOINT ["/app/docker-entrypoint.sh"]
CMD ["python", "-m", "uvicorn", "skillmeat.api.server:app", "--host", "0.0.0.0", "--port", "8080"]
