#!/usr/bin/env bash
# SkillMeat Staging Deployment Script
# Deploys the Memory & Context Intelligence System to staging environment

set -euo pipefail

# ===================================================================
# CONFIGURATION
# ===================================================================
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
COMPOSE_FILE="$SCRIPT_DIR/docker-compose.staging.yml"
ENV_FILE="$SCRIPT_DIR/env.staging"
SMOKE_TESTS="$SCRIPT_DIR/smoke-tests.sh"

# Deployment configuration
DEPLOYMENT_TIMEOUT=300  # 5 minutes
HEALTH_CHECK_RETRIES=30
HEALTH_CHECK_INTERVAL=5

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Track deployment state
DEPLOYMENT_STARTED=false
ROLLBACK_NEEDED=false

# ===================================================================
# HELPER FUNCTIONS
# ===================================================================

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_step() {
    echo -e "\n${BLUE}==>${NC} $1"
}

check_prerequisites() {
    log_step "Checking prerequisites"

    # Check Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed"
        return 1
    fi

    # Check Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose is not installed"
        return 1
    fi

    # Check Docker daemon
    if ! docker info &> /dev/null; then
        log_error "Docker daemon is not running"
        return 1
    fi

    # Check required files
    if [ ! -f "$COMPOSE_FILE" ]; then
        log_error "Docker Compose file not found: $COMPOSE_FILE"
        return 1
    fi

    if [ ! -f "$ENV_FILE" ]; then
        log_error "Environment file not found: $ENV_FILE"
        return 1
    fi

    if [ ! -f "$SMOKE_TESTS" ]; then
        log_error "Smoke tests not found: $SMOKE_TESTS"
        return 1
    fi

    log_info "✓ All prerequisites satisfied"
    return 0
}

build_images() {
    log_step "Building Docker images"

    # Check if Dockerfiles exist
    local api_dockerfile="$PROJECT_ROOT/Dockerfile"
    local web_dockerfile="$PROJECT_ROOT/web/Dockerfile"

    if [ ! -f "$api_dockerfile" ]; then
        log_warn "API Dockerfile not found at $api_dockerfile"
        log_warn "Skipping API image build (using existing image)"
    else
        log_info "Building API image..."
        docker build -t skillmeat/api:latest -f "$api_dockerfile" "$PROJECT_ROOT" || {
            log_error "Failed to build API image"
            return 1
        }
        log_info "✓ API image built successfully"
    fi

    if [ ! -f "$web_dockerfile" ]; then
        log_warn "Web Dockerfile not found at $web_dockerfile"
        log_warn "Skipping web image build (using existing image or service disabled)"
    else
        log_info "Building web image..."
        docker build -t skillmeat/web:latest -f "$web_dockerfile" "$PROJECT_ROOT/web" || {
            log_error "Failed to build web image"
            return 1
        }
        log_info "✓ Web image built successfully"
    fi

    return 0
}

run_migrations() {
    log_step "Running database migrations"

    local migrations_dir="$PROJECT_ROOT/skillmeat/cache/migrations"
    local alembic_ini="$migrations_dir/alembic.ini"

    if [ ! -f "$alembic_ini" ]; then
        log_warn "Alembic configuration not found at $alembic_ini"
        log_warn "Skipping migrations (may not be required for this deployment)"
        return 0
    fi

    # Run migrations inside the API container
    log_info "Running Alembic migrations..."

    # Option 1: If container is already running
    if docker-compose -f "$COMPOSE_FILE" ps skillmeat-api | grep -q "Up"; then
        docker-compose -f "$COMPOSE_FILE" exec -T skillmeat-api \
            alembic -c /app/skillmeat/cache/migrations/alembic.ini upgrade head || {
            log_error "Failed to run migrations"
            return 1
        }
    # Option 2: Run in a temporary container
    else
        docker run --rm \
            -v "$PROJECT_ROOT:/app" \
            -w /app \
            skillmeat/api:latest \
            alembic -c /app/skillmeat/cache/migrations/alembic.ini upgrade head || {
            log_warn "Failed to run migrations in temporary container"
            log_info "Migrations will be attempted after service start"
            return 0
        }
    fi

    log_info "✓ Database migrations completed"
    return 0
}

start_services() {
    log_step "Starting services"

    DEPLOYMENT_STARTED=true

    # Pull latest images for monitoring services
    log_info "Pulling monitoring service images..."
    docker-compose -f "$COMPOSE_FILE" pull prometheus grafana alertmanager || {
        log_warn "Failed to pull some monitoring images (may use cached versions)"
    }

    # Start services
    log_info "Starting all services..."
    docker-compose -f "$COMPOSE_FILE" up -d || {
        log_error "Failed to start services"
        ROLLBACK_NEEDED=true
        return 1
    }

    log_info "✓ Services started"
    return 0
}

wait_for_health() {
    log_step "Waiting for services to be healthy"

    local retries=0
    local api_url="http://localhost:8080"

    log_info "Checking API health endpoint: $api_url/health"

    while [ $retries -lt $HEALTH_CHECK_RETRIES ]; do
        if curl -sf --max-time 5 "$api_url/health" > /dev/null 2>&1; then
            log_info "✓ API is healthy"
            return 0
        fi

        retries=$((retries + 1))
        log_info "Health check attempt $retries/$HEALTH_CHECK_RETRIES (waiting ${HEALTH_CHECK_INTERVAL}s)..."
        sleep $HEALTH_CHECK_INTERVAL
    done

    log_error "API failed to become healthy after $HEALTH_CHECK_RETRIES attempts"
    ROLLBACK_NEEDED=true
    return 1
}

run_post_deployment_migrations() {
    log_step "Running post-deployment migrations (if needed)"

    # If migrations failed earlier, try again now that the service is running
    if docker-compose -f "$COMPOSE_FILE" ps skillmeat-api | grep -q "Up"; then
        log_info "Attempting migrations inside running container..."
        docker-compose -f "$COMPOSE_FILE" exec -T skillmeat-api \
            alembic -c /app/skillmeat/cache/migrations/alembic.ini upgrade head 2>/dev/null || {
            log_warn "Migrations command not available or already up to date"
        }
        log_info "✓ Post-deployment migrations check complete"
    fi

    return 0
}

run_smoke_tests() {
    log_step "Running smoke tests"

    # Make smoke tests executable
    chmod +x "$SMOKE_TESTS"

    # Run smoke tests
    export SKILLMEAT_API_URL="http://localhost:8080"
    if "$SMOKE_TESTS"; then
        log_info "✓ All smoke tests passed"
        return 0
    else
        log_error "Smoke tests failed"
        ROLLBACK_NEEDED=true
        return 1
    fi
}

show_status() {
    log_step "Deployment status"

    echo ""
    log_info "Service status:"
    docker-compose -f "$COMPOSE_FILE" ps

    echo ""
    log_info "Endpoints:"
    echo "  API:          http://localhost:8080"
    echo "  API Health:   http://localhost:8080/health"
    echo "  API Docs:     http://localhost:8080/docs"
    echo "  Metrics:      http://localhost:8080/metrics"
    echo "  Prometheus:   http://localhost:9090"
    echo "  Grafana:      http://localhost:3000"
    echo "  Alertmanager: http://localhost:9093"
    if docker-compose -f "$COMPOSE_FILE" ps skillmeat-web | grep -q "Up"; then
        echo "  Web UI:       http://localhost:3001"
    fi

    echo ""
    log_info "Useful commands:"
    echo "  View logs:       docker-compose -f $COMPOSE_FILE logs -f skillmeat-api"
    echo "  Restart service: docker-compose -f $COMPOSE_FILE restart skillmeat-api"
    echo "  Stop all:        docker-compose -f $COMPOSE_FILE down"
    echo "  Run smoke tests: $SMOKE_TESTS"

    return 0
}

rollback() {
    log_error "========================================="
    log_error "DEPLOYMENT FAILED - INITIATING ROLLBACK"
    log_error "========================================="

    if [ "$DEPLOYMENT_STARTED" = true ]; then
        log_info "Stopping services..."
        docker-compose -f "$COMPOSE_FILE" down || {
            log_error "Failed to stop services during rollback"
            log_error "Manual intervention required"
            exit 1
        }

        log_info "✓ Services stopped"
    fi

    echo ""
    log_error "========================================="
    log_error "ROLLBACK INSTRUCTIONS"
    log_error "========================================="
    echo ""
    echo "The deployment has failed and services have been stopped."
    echo ""
    echo "To investigate the issue:"
    echo "  1. Check service logs:"
    echo "     docker-compose -f $COMPOSE_FILE logs skillmeat-api"
    echo ""
    echo "  2. Check container status:"
    echo "     docker-compose -f $COMPOSE_FILE ps"
    echo ""
    echo "  3. Check recent container logs:"
    echo "     docker logs skillmeat-api-staging --tail 100"
    echo ""
    echo "To restore previous deployment:"
    echo "  1. If you have a backup/snapshot, restore it"
    echo "  2. Deploy the previous stable version"
    echo "  3. Verify with smoke tests: $SMOKE_TESTS"
    echo ""
    echo "For emergency recovery:"
    echo "  1. Check data persistence: ls -la $SCRIPT_DIR/data/"
    echo "  2. Restore from backup if needed"
    echo "  3. Contact the deployment team"
    echo ""

    exit 1
}

cleanup_on_interrupt() {
    log_warn "Deployment interrupted by user"
    if [ "$DEPLOYMENT_STARTED" = true ]; then
        log_info "Services may be in partial state. Check status with:"
        echo "  docker-compose -f $COMPOSE_FILE ps"
        echo "To clean up:"
        echo "  docker-compose -f $COMPOSE_FILE down"
    fi
    exit 130
}

# ===================================================================
# MAIN DEPLOYMENT WORKFLOW
# ===================================================================

main() {
    log_info "========================================="
    log_info "SkillMeat Staging Deployment"
    log_info "========================================="
    log_info "Environment: staging"
    log_info "Compose file: $COMPOSE_FILE"
    log_info "Started at: $(date)"
    echo ""

    # Set trap for errors and interrupts
    trap 'if [ "$ROLLBACK_NEEDED" = true ]; then rollback; fi' ERR
    trap cleanup_on_interrupt INT TERM

    # Pre-deployment steps
    check_prerequisites || exit 1
    build_images || exit 1

    # Attempt pre-deployment migrations (may fail if DB not ready)
    run_migrations || log_warn "Pre-deployment migrations skipped or failed"

    # Deployment
    start_services || exit 1
    wait_for_health || exit 1

    # Post-deployment steps
    run_post_deployment_migrations || log_warn "Post-deployment migrations check completed"
    run_smoke_tests || exit 1

    # Success
    log_info ""
    log_info "========================================="
    log_info "✓ DEPLOYMENT SUCCESSFUL"
    log_info "========================================="
    show_status

    log_info ""
    log_info "Deployment completed at: $(date)"
    log_info ""

    exit 0
}

# Run main function
main "$@"
