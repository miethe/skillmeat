#!/usr/bin/env bash
# SkillMeat Production Deployment Script
# Deploys the Memory & Context Intelligence System to production
#
# SAFETY: Requires --confirm flag to execute
# STRATEGY: Blue-green deployment with automatic rollback on failure
#
# Usage:
#   ./deploy.sh --confirm                    # Full production deployment
#   ./deploy.sh --confirm --skip-staging     # Skip staging verification (emergency only)
#   ./deploy.sh --confirm --version v1.2.3   # Deploy specific version
#   ./deploy.sh --rollback                   # Rollback to previous version
#   ./deploy.sh --status                     # Show current deployment status

set -euo pipefail

# ===================================================================
# CONFIGURATION
# ===================================================================
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
COMPOSE_FILE="$SCRIPT_DIR/docker-compose.production.yml"
ENV_FILE="$SCRIPT_DIR/env.production"
SMOKE_TESTS="$SCRIPT_DIR/smoke-tests.sh"
STAGING_SMOKE_TESTS="$PROJECT_ROOT/deploy/staging/smoke-tests.sh"

# Deployment configuration
DEPLOYMENT_TIMEOUT=300  # 5 minutes
HEALTH_CHECK_RETRIES=40
HEALTH_CHECK_INTERVAL=5

# Blue-green deployment
BACKUP_DIR="$SCRIPT_DIR/.deployment-backups"
CURRENT_LINK="$BACKUP_DIR/current"
PREVIOUS_LINK="$BACKUP_DIR/previous"

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# Track deployment state
DEPLOYMENT_STARTED=false
ROLLBACK_NEEDED=false
DEPLOYMENT_ID=""
DEPLOY_VERSION="${SKILLMEAT_VERSION:-latest}"

# Flags
CONFIRM=false
SKIP_STAGING=false
DO_ROLLBACK=false
SHOW_STATUS=false

# ===================================================================
# ARGUMENT PARSING
# ===================================================================

while [[ $# -gt 0 ]]; do
    case $1 in
        --confirm)
            CONFIRM=true
            shift
            ;;
        --skip-staging)
            SKIP_STAGING=true
            shift
            ;;
        --version)
            DEPLOY_VERSION="$2"
            shift 2
            ;;
        --rollback)
            DO_ROLLBACK=true
            shift
            ;;
        --status)
            SHOW_STATUS=true
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --confirm              Required flag to execute production deployment"
            echo "  --skip-staging         Skip staging smoke test verification (emergency only)"
            echo "  --version VERSION      Deploy specific version (default: latest)"
            echo "  --rollback             Rollback to previous deployment"
            echo "  --status               Show current deployment status"
            echo "  -h, --help             Show this help message"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Run $0 --help for usage"
            exit 1
            ;;
    esac
done

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

log_banner() {
    echo -e "\n${BOLD}${RED}$1${NC}"
}

notify() {
    local message="$1"
    local severity="${2:-info}"

    # Placeholder: Slack notification
    # if [ -n "${SKILLMEAT_SLACK_WEBHOOK_URL:-}" ]; then
    #     curl -s -X POST "$SKILLMEAT_SLACK_WEBHOOK_URL" \
    #         -H 'Content-Type: application/json' \
    #         -d "{\"text\":\"[SkillMeat Production] [$severity] $message\"}" || true
    # fi

    # Placeholder: Email notification
    # if [ -n "${SKILLMEAT_ALERT_EMAIL:-}" ]; then
    #     echo "$message" | mail -s "[SkillMeat Production] $message" "$SKILLMEAT_ALERT_EMAIL" || true
    # fi

    log_info "Notification ($severity): $message"
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

    # Create backup directory
    mkdir -p "$BACKUP_DIR"

    log_info "All prerequisites satisfied"
    return 0
}

verify_staging() {
    log_step "Verifying staging environment"

    if [ "$SKIP_STAGING" = true ]; then
        log_warn "========================================="
        log_warn "STAGING VERIFICATION SKIPPED (--skip-staging)"
        log_warn "This should only be used for emergency deployments"
        log_warn "========================================="
        return 0
    fi

    if [ ! -f "$STAGING_SMOKE_TESTS" ]; then
        log_error "Staging smoke tests not found: $STAGING_SMOKE_TESTS"
        log_error "Staging must be deployed and passing before production deployment"
        log_error "Use --skip-staging to bypass (emergency only)"
        return 1
    fi

    # Check if staging is running
    local staging_compose="$PROJECT_ROOT/deploy/staging/docker-compose.staging.yml"
    if [ -f "$staging_compose" ]; then
        if docker-compose -f "$staging_compose" ps skillmeat-api 2>/dev/null | grep -q "Up"; then
            log_info "Staging is running, executing smoke tests..."
            export SKILLMEAT_API_URL="http://localhost:8080"
            chmod +x "$STAGING_SMOKE_TESTS"
            if "$STAGING_SMOKE_TESTS"; then
                log_info "Staging smoke tests passed"
                return 0
            else
                log_error "Staging smoke tests failed"
                log_error "Fix staging issues before deploying to production"
                return 1
            fi
        else
            log_warn "Staging containers are not running"
            log_warn "Cannot verify staging health -- ensure staging was validated recently"
            return 0
        fi
    else
        log_warn "Staging compose file not found"
        log_warn "Ensure staging environment has been validated before production deployment"
        return 0
    fi
}

save_deployment_state() {
    log_step "Saving current deployment state for rollback"

    DEPLOYMENT_ID="deploy-$(date +%Y%m%d-%H%M%S)"
    local backup_path="$BACKUP_DIR/$DEPLOYMENT_ID"
    mkdir -p "$backup_path"

    # Save current container image IDs
    local current_api_image
    current_api_image=$(docker inspect --format='{{.Image}}' skillmeat-api-production 2>/dev/null || echo "none")

    # Save deployment metadata
    cat > "$backup_path/metadata.txt" <<EOF
deployment_id=$DEPLOYMENT_ID
timestamp=$(date -u +%Y-%m-%dT%H:%M:%SZ)
version=$DEPLOY_VERSION
previous_api_image=$current_api_image
compose_file=$COMPOSE_FILE
EOF

    # Save current compose config
    if [ -f "$COMPOSE_FILE" ]; then
        cp "$COMPOSE_FILE" "$backup_path/docker-compose.production.yml.bak"
    fi

    # Save current env
    if [ -f "$ENV_FILE" ]; then
        cp "$ENV_FILE" "$backup_path/env.production.bak"
    fi

    # Update symlinks
    if [ -L "$CURRENT_LINK" ]; then
        # Move current to previous
        local current_target
        current_target=$(readlink "$CURRENT_LINK")
        ln -sfn "$current_target" "$PREVIOUS_LINK"
    fi
    ln -sfn "$backup_path" "$CURRENT_LINK"

    log_info "Deployment state saved: $DEPLOYMENT_ID"
    return 0
}

build_images() {
    log_step "Building Docker images (version: $DEPLOY_VERSION)"

    # Check if Dockerfiles exist
    local api_dockerfile="$PROJECT_ROOT/Dockerfile"
    local web_dockerfile="$PROJECT_ROOT/web/Dockerfile"

    if [ ! -f "$api_dockerfile" ]; then
        log_warn "API Dockerfile not found at $api_dockerfile"
        log_warn "Skipping API image build (using existing image)"
    else
        log_info "Building API image..."
        docker build -t "skillmeat/api:$DEPLOY_VERSION" -f "$api_dockerfile" "$PROJECT_ROOT" || {
            log_error "Failed to build API image"
            return 1
        }
        # Tag as latest if deploying a specific version
        if [ "$DEPLOY_VERSION" != "latest" ]; then
            docker tag "skillmeat/api:$DEPLOY_VERSION" "skillmeat/api:latest"
        fi
        log_info "API image built successfully"
    fi

    if [ ! -f "$web_dockerfile" ]; then
        log_warn "Web Dockerfile not found at $web_dockerfile"
        log_warn "Skipping web image build (using existing image or service disabled)"
    else
        log_info "Building web image..."
        docker build -t "skillmeat/web:$DEPLOY_VERSION" -f "$web_dockerfile" "$PROJECT_ROOT/web" || {
            log_error "Failed to build web image"
            return 1
        }
        if [ "$DEPLOY_VERSION" != "latest" ]; then
            docker tag "skillmeat/web:$DEPLOY_VERSION" "skillmeat/web:latest"
        fi
        log_info "Web image built successfully"
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
    if docker-compose -f "$COMPOSE_FILE" ps skillmeat-api 2>/dev/null | grep -q "Up"; then
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
            "skillmeat/api:$DEPLOY_VERSION" \
            alembic -c /app/skillmeat/cache/migrations/alembic.ini upgrade head || {
            log_warn "Failed to run migrations in temporary container"
            log_info "Migrations will be attempted after service start"
            return 0
        }
    fi

    log_info "Database migrations completed"
    return 0
}

start_services() {
    log_step "Starting services (blue-green deployment)"

    DEPLOYMENT_STARTED=true

    # Pull latest images for monitoring services
    log_info "Pulling monitoring service images..."
    docker-compose -f "$COMPOSE_FILE" pull prometheus grafana alertmanager || {
        log_warn "Failed to pull some monitoring images (may use cached versions)"
    }

    # Start services with the new version
    log_info "Starting all services with version: $DEPLOY_VERSION..."
    SKILLMEAT_VERSION="$DEPLOY_VERSION" docker-compose -f "$COMPOSE_FILE" up -d || {
        log_error "Failed to start services"
        ROLLBACK_NEEDED=true
        return 1
    }

    log_info "Services started"
    return 0
}

wait_for_health() {
    log_step "Waiting for services to be healthy"

    local retries=0
    local api_url="http://localhost:8080"

    log_info "Checking API health endpoint: $api_url/health"

    while [ $retries -lt $HEALTH_CHECK_RETRIES ]; do
        if curl -sf --max-time 5 "$api_url/health" > /dev/null 2>&1; then
            log_info "API is healthy"
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
    if docker-compose -f "$COMPOSE_FILE" ps skillmeat-api 2>/dev/null | grep -q "Up"; then
        log_info "Attempting migrations inside running container..."
        docker-compose -f "$COMPOSE_FILE" exec -T skillmeat-api \
            alembic -c /app/skillmeat/cache/migrations/alembic.ini upgrade head 2>/dev/null || {
            log_warn "Migrations command not available or already up to date"
        }
        log_info "Post-deployment migrations check complete"
    fi

    return 0
}

run_smoke_tests() {
    log_step "Running production smoke tests"

    # Make smoke tests executable
    chmod +x "$SMOKE_TESTS"

    # Run smoke tests
    export SKILLMEAT_API_URL="http://localhost:8080"
    if "$SMOKE_TESTS"; then
        log_info "All smoke tests passed"
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
    if docker-compose -f "$COMPOSE_FILE" ps skillmeat-web 2>/dev/null | grep -q "Up"; then
        echo "  Web UI:       http://localhost:3001"
    fi

    echo ""
    log_info "Feature flags:"
    echo "  Memory & Context System: DISABLED (graduated rollout)"
    echo "  See rollout-plan.md for activation procedure"

    echo ""
    log_info "Useful commands:"
    echo "  View logs:       docker-compose -f $COMPOSE_FILE logs -f skillmeat-api"
    echo "  Restart service: docker-compose -f $COMPOSE_FILE restart skillmeat-api"
    echo "  Stop all:        docker-compose -f $COMPOSE_FILE down"
    echo "  Run smoke tests: $SMOKE_TESTS"
    echo "  Rollback:        $0 --rollback"

    # Show deployment history if available
    if [ -d "$BACKUP_DIR" ] && [ -L "$CURRENT_LINK" ]; then
        echo ""
        log_info "Deployment history:"
        echo "  Current: $(basename "$(readlink "$CURRENT_LINK")" 2>/dev/null || echo 'unknown')"
        if [ -L "$PREVIOUS_LINK" ]; then
            echo "  Previous: $(basename "$(readlink "$PREVIOUS_LINK")" 2>/dev/null || echo 'unknown')"
        fi
    fi

    return 0
}

rollback() {
    log_banner "========================================="
    log_error "INITIATING ROLLBACK"
    log_banner "========================================="

    if [ "$DO_ROLLBACK" = true ]; then
        # Manual rollback requested
        if [ ! -L "$PREVIOUS_LINK" ]; then
            log_error "No previous deployment found to rollback to"
            log_error "Manual intervention required"
            exit 1
        fi

        local previous_path
        previous_path=$(readlink "$PREVIOUS_LINK")

        if [ ! -f "$previous_path/docker-compose.production.yml.bak" ]; then
            log_error "Previous deployment backup is incomplete"
            exit 1
        fi

        log_info "Rolling back to: $(basename "$previous_path")"

        # Get the previous version from metadata
        local prev_version
        prev_version=$(grep "^version=" "$previous_path/metadata.txt" 2>/dev/null | cut -d= -f2 || echo "latest")

        # Stop current services
        log_info "Stopping current services..."
        docker-compose -f "$COMPOSE_FILE" down || {
            log_error "Failed to stop current services"
            log_error "Manual intervention required"
            exit 1
        }

        # Restore previous configuration
        cp "$previous_path/docker-compose.production.yml.bak" "$COMPOSE_FILE"
        cp "$previous_path/env.production.bak" "$ENV_FILE"

        # Start with previous version
        log_info "Starting previous version ($prev_version)..."
        SKILLMEAT_VERSION="$prev_version" docker-compose -f "$COMPOSE_FILE" up -d || {
            log_error "Failed to start previous version"
            log_error "Manual intervention required"
            exit 1
        }

        # Wait for health
        wait_for_health || {
            log_error "Previous version also failed health checks"
            log_error "Manual intervention required"
            exit 1
        }

        # Update symlinks
        ln -sfn "$previous_path" "$CURRENT_LINK"

        notify "ROLLBACK COMPLETE to $(basename "$previous_path")" "warning"
        log_info "Rollback complete"
        show_status
        exit 0
    fi

    # Automatic rollback during failed deployment
    if [ "$DEPLOYMENT_STARTED" = true ]; then
        log_info "Stopping failed deployment..."
        docker-compose -f "$COMPOSE_FILE" down || {
            log_error "Failed to stop services during rollback"
            log_error "Manual intervention required"
            notify "DEPLOYMENT FAILED - manual intervention required" "critical"
            exit 1
        }

        # Try to restore previous version if available
        if [ -L "$PREVIOUS_LINK" ]; then
            local previous_path
            previous_path=$(readlink "$PREVIOUS_LINK")
            local prev_version
            prev_version=$(grep "^version=" "$previous_path/metadata.txt" 2>/dev/null | cut -d= -f2 || echo "latest")

            log_info "Attempting automatic rollback to: $(basename "$previous_path")"
            SKILLMEAT_VERSION="$prev_version" docker-compose -f "$COMPOSE_FILE" up -d || {
                log_error "Automatic rollback failed"
            }

            if curl -sf --max-time 10 "http://localhost:8080/health" > /dev/null 2>&1; then
                log_info "Automatic rollback succeeded"
                notify "Deployment failed, automatic rollback to $(basename "$previous_path") succeeded" "warning"
                show_status
                exit 1
            fi
        fi

        log_info "Services stopped"
    fi

    notify "DEPLOYMENT FAILED - rollback initiated" "critical"

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
    echo "     docker logs skillmeat-api-production --tail 100"
    echo ""
    echo "To restore previous deployment manually:"
    echo "  $0 --rollback"
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
    notify "Deployment interrupted by user" "warning"
    if [ "$DEPLOYMENT_STARTED" = true ]; then
        log_info "Services may be in partial state. Check status with:"
        echo "  docker-compose -f $COMPOSE_FILE ps"
        echo "To clean up:"
        echo "  docker-compose -f $COMPOSE_FILE down"
        echo "To rollback:"
        echo "  $0 --rollback"
    fi
    exit 130
}

# ===================================================================
# HANDLE --status AND --rollback
# ===================================================================

if [ "$SHOW_STATUS" = true ]; then
    show_status
    exit 0
fi

if [ "$DO_ROLLBACK" = true ]; then
    rollback
    exit 0
fi

# ===================================================================
# SAFETY GATE: Require --confirm for production deployment
# ===================================================================

if [ "$CONFIRM" != true ]; then
    log_error "========================================="
    log_error "PRODUCTION DEPLOYMENT REQUIRES CONFIRMATION"
    log_error "========================================="
    echo ""
    echo "This script deploys to PRODUCTION. To proceed, run:"
    echo ""
    echo "  $0 --confirm"
    echo ""
    echo "Other options:"
    echo "  $0 --confirm --version v1.2.3    Deploy specific version"
    echo "  $0 --confirm --skip-staging       Skip staging checks (emergency)"
    echo "  $0 --status                       Show current deployment status"
    echo "  $0 --rollback                     Rollback to previous version"
    echo "  $0 --help                         Show all options"
    echo ""
    exit 1
fi

# ===================================================================
# MAIN DEPLOYMENT WORKFLOW
# ===================================================================

main() {
    log_info "========================================="
    log_info "SkillMeat PRODUCTION Deployment"
    log_info "========================================="
    log_info "Environment: production"
    log_info "Version:     $DEPLOY_VERSION"
    log_info "Compose:     $COMPOSE_FILE"
    log_info "Started at:  $(date)"
    echo ""

    # Set trap for errors and interrupts
    trap 'if [ "$ROLLBACK_NEEDED" = true ]; then rollback; fi' ERR
    trap cleanup_on_interrupt INT TERM

    notify "Production deployment started (version: $DEPLOY_VERSION)" "info"

    # Pre-deployment checks
    check_prerequisites || exit 1
    verify_staging || exit 1

    # Save state for rollback
    save_deployment_state || log_warn "Could not save deployment state"

    # Build
    build_images || exit 1

    # Attempt pre-deployment migrations (may fail if DB not ready)
    run_migrations || log_warn "Pre-deployment migrations skipped or failed"

    # Deployment
    start_services || exit 1
    wait_for_health || exit 1

    # Post-deployment
    run_post_deployment_migrations || log_warn "Post-deployment migrations check completed"
    run_smoke_tests || exit 1

    # Success
    notify "Production deployment succeeded (version: $DEPLOY_VERSION)" "info"

    log_info ""
    log_info "========================================="
    log_info "PRODUCTION DEPLOYMENT SUCCESSFUL"
    log_info "========================================="
    show_status

    log_info ""
    log_info "Deployment completed at: $(date)"
    log_info "Deployment ID: $DEPLOYMENT_ID"
    log_info ""
    log_info "NEXT STEPS:"
    log_info "  1. Verify infrastructure with: $SMOKE_TESTS"
    log_info "  2. Follow rollout-plan.md to enable Memory & Context system"
    log_info "  3. Monitor dashboards for anomalies"
    log_info ""

    exit 0
}

# Run main function
main "$@"
