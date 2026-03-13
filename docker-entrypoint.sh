#!/bin/bash
set -euo pipefail

# ──────────────────────────────────────────────────────────────────────
# SkillMeat API Container Entrypoint
#
# Responsibilities:
#   1. Ensure data directories exist (ConfigManager needs ~/.skillmeat)
#   2. Detect database backend (Postgres vs SQLite) from DATABASE_URL
#   3. Run Alembic migrations for Postgres
#   4. Handle SIGTERM for graceful shutdown
#   5. Pass through to CMD via exec "$@"
# ──────────────────────────────────────────────────────────────────────

# Graceful shutdown: forward SIGTERM to the child process group
shutdown() {
    echo "[entrypoint] Received SIGTERM, shutting down..."
    # Kill the child process group; the exec below replaces this shell,
    # so this handler only fires if exec hasn't happened yet.
    kill -TERM "$child_pid" 2>/dev/null || true
    wait "$child_pid" 2>/dev/null || true
    exit 0
}
trap shutdown SIGTERM SIGINT

echo "[entrypoint] Starting SkillMeat API container entrypoint"

# ── Reload mode ──────────────────────────────────────────────────────
if [ "${SKILLMEAT_RELOAD:-false}" = "true" ]; then
    echo "[entrypoint] Reload mode is ACTIVE (SKILLMEAT_RELOAD=true)"
fi

# ── Ensure data directory exists (required for BOTH modes) ──────────
# ConfigManager always needs ~/.skillmeat to exist, even when using PostgreSQL.
# SKILLMEAT_COLLECTION_DIR typically points to ~/.skillmeat/collection;
# we create its parent to cover the config file location.
SKILLMEAT_DATA_DIR="${SKILLMEAT_COLLECTION_DIR:-/home/app/.skillmeat}"
if [ -n "${SKILLMEAT_COLLECTION_DIR:-}" ]; then
    SKILLMEAT_DATA_DIR="$(dirname "$SKILLMEAT_COLLECTION_DIR")"
fi
echo "[entrypoint] Ensuring data directory exists: ${SKILLMEAT_DATA_DIR}"
mkdir -p "$SKILLMEAT_DATA_DIR"

# ── Database detection ───────────────────────────────────────────────
DATABASE_URL="${DATABASE_URL:-}"

if [[ "$DATABASE_URL" == postgresql://* ]] || [[ "$DATABASE_URL" == postgres://* ]]; then
    echo "[entrypoint] Detected PostgreSQL database"
    echo "[entrypoint] Running Alembic migrations (alembic upgrade head)..."

    # Run migrations from the repo root. The alembic.ini lives at
    # skillmeat/cache/migrations/alembic.ini with script_location = %(here)s,
    # so point -c at the config file.
    if alembic -c skillmeat/cache/migrations/alembic.ini upgrade head; then
        echo "[entrypoint] Alembic migrations completed successfully"
    else
        echo "[entrypoint] ERROR: Alembic migrations failed" >&2
        exit 1
    fi
else
    echo "[entrypoint] Using SQLite database (local edition)"
fi

# ── Hand off to CMD ─────────────────────────────────────────────────
echo "[entrypoint] Executing command: $*"
exec "$@"
