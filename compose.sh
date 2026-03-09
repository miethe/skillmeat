#!/usr/bin/env bash
# =============================================================================
# SkillMeat Compose Wrapper
# =============================================================================
# Auto-detects Docker or Podman and runs the appropriate compose command.
#
# Usage:
#   ./compose.sh --profile local up -d
#   ./compose.sh --profile enterprise -f docker-compose.yml -f docker-compose.monitoring.yml up -d
#   ./compose.sh down
#
# Environment:
#   COMPOSE_ENGINE=docker|podman   Override auto-detection
# =============================================================================
set -euo pipefail

# ── Auto-detect container runtime ──────────────────────────────────────────

detect_engine() {
    # Honour explicit override
    if [ -n "${COMPOSE_ENGINE:-}" ]; then
        echo "$COMPOSE_ENGINE"
        return
    fi

    # Prefer Docker if available and daemon is reachable
    if command -v docker &>/dev/null; then
        # Check if Docker daemon is actually running (not just the CLI shim)
        if docker info &>/dev/null 2>&1; then
            echo "docker"
            return
        fi
    fi

    # Fall back to Podman
    if command -v podman &>/dev/null; then
        echo "podman"
        return
    fi

    echo >&2 "ERROR: Neither Docker nor Podman found. Install one of them first."
    exit 1
}

ENGINE=$(detect_engine)

# ── Resolve compose command ────────────────────────────────────────────────

resolve_compose() {
    local engine="$1"

    if [ "$engine" = "podman" ]; then
        # Ensure Podman socket is exposed for compose compatibility
        if [ -z "${DOCKER_HOST:-}" ]; then
            local sock="/run/user/$(id -u)/podman/podman.sock"
            if [ -S "$sock" ]; then
                export DOCKER_HOST="unix://$sock"
            else
                echo >&2 "WARN: Podman socket not found at $sock"
                echo >&2 "      Run: systemctl --user enable --now podman.socket"
            fi
        fi

        # Prefer 'podman compose' (v2-compatible, ships with Podman 4.7+)
        if podman compose version &>/dev/null 2>&1; then
            echo "podman compose"
            return
        fi

        # Fall back to standalone podman-compose
        if command -v podman-compose &>/dev/null; then
            echo "podman-compose"
            return
        fi

        echo >&2 "ERROR: Podman detected but no compose plugin found."
        echo >&2 "       Install one of:"
        echo >&2 "         - podman compose (built-in since Podman 4.7)"
        echo >&2 "         - pip install podman-compose"
        exit 1
    fi

    # Docker: prefer v2 plugin, fall back to standalone
    if docker compose version &>/dev/null 2>&1; then
        echo "docker compose"
    elif command -v docker-compose &>/dev/null; then
        echo "docker-compose"
    else
        echo >&2 "ERROR: Docker detected but no compose command found."
        echo >&2 "       Install Docker Compose: https://docs.docker.com/compose/install/"
        exit 1
    fi
}

COMPOSE_CMD=$(resolve_compose "$ENGINE")

echo "[compose.sh] Using: $COMPOSE_CMD (engine: $ENGINE)"

# ── Podman build workarounds ─────────────────────────────────────────────

if [ "$ENGINE" = "podman" ]; then
    # podman-compose doesn't pass --ulimit to podman build, so we
    # pre-build any services that have a build context, then let
    # compose do the rest (start/pull only).
    export BUILDAH_ULIMIT="nofile=65536:65536"

    # Check if this is an "up --build" or "build" invocation
    NEEDS_PREBUILD=false
    for arg in "$@"; do
        case "$arg" in
            --build|build) NEEDS_PREBUILD=true ;;
        esac
    done

    if [ "$NEEDS_PREBUILD" = true ]; then
        echo "[compose.sh] Pre-building images with Podman (--ulimit nofile=65536:65536)..."

        # Resolve project name (directory basename, lowercased)
        PROJECT_NAME=$(basename "$(pwd)" | tr '[:upper:]' '[:lower:]' | tr -cd '[:alnum:]_-')

        # Build skillmeat-api (root context)
        if [ -f Dockerfile ]; then
            echo "[compose.sh]   Building ${PROJECT_NAME}_skillmeat-api..."
            podman build --ulimit nofile=65536:65536 \
                --format docker \
                -t "${PROJECT_NAME}_skillmeat-api" \
                -f Dockerfile .
        fi

        # Build skillmeat-web (web context)
        if [ -f skillmeat/web/Dockerfile ]; then
            echo "[compose.sh]   Building ${PROJECT_NAME}_skillmeat-web..."
            podman build --ulimit nofile=65536:65536 \
                --format docker \
                -t "${PROJECT_NAME}_skillmeat-web" \
                -f skillmeat/web/Dockerfile skillmeat/web
        fi

        echo "[compose.sh] Pre-build complete. Starting services..."

        # Strip --build from args so compose doesn't re-build
        FILTERED_ARGS=()
        for arg in "$@"; do
            [ "$arg" != "--build" ] && FILTERED_ARGS+=("$arg")
        done
        set -- "${FILTERED_ARGS[@]}"
    fi
fi

# ── Execute ────────────────────────────────────────────────────────────────

# shellcheck disable=SC2086
exec $COMPOSE_CMD "$@"
