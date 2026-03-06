#!/usr/bin/env bash
# run_enterprise_tests.sh — Start PostgreSQL via docker-compose, run enterprise
# integration tests against it, then tear down the container.
#
# Usage:
#   ./scripts/run_enterprise_tests.sh                  # run all enterprise tests
#   ./scripts/run_enterprise_tests.sh -k test_schema   # pass extra pytest args
#
# Environment:
#   DATABASE_URL — override the default connection string if needed
set -euo pipefail

COMPOSE_FILE="docker-compose.test.yml"
DB_URL="${DATABASE_URL:-postgresql://skillmeat_test:skillmeat_test@localhost:5433/skillmeat_test}"

cleanup() {
  echo "Stopping PostgreSQL..."
  docker compose -f "$COMPOSE_FILE" down
}
trap cleanup EXIT

# Start PostgreSQL
echo "Starting PostgreSQL..."
docker compose -f "$COMPOSE_FILE" up -d postgres

# Wait for healthy
echo "Waiting for PostgreSQL to be ready..."
until docker compose -f "$COMPOSE_FILE" exec -T postgres \
    pg_isready -U skillmeat_test -d skillmeat_test > /dev/null 2>&1; do
  sleep 1
done
echo "PostgreSQL is ready."

# Run Alembic migrations
echo "Running migrations..."
DATABASE_URL="$DB_URL" \
  python -m alembic -c skillmeat/cache/migrations/alembic.ini upgrade head

# Run enterprise integration tests, forwarding any extra arguments
echo "Running enterprise integration tests..."
DATABASE_URL="$DB_URL" \
  pytest tests/integration/ -v "$@"
