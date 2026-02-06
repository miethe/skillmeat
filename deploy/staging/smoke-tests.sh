#!/usr/bin/env bash
# SkillMeat Staging Smoke Tests
# Verifies critical user journeys after deployment

set -euo pipefail

# ===================================================================
# CONFIGURATION
# ===================================================================
API_URL="${SKILLMEAT_API_URL:-http://localhost:8080}"
API_VERSION="${SKILLMEAT_API_VERSION:-v1}"
TEST_PROJECT_ID="smoke-test-$(date +%s)"
TIMEOUT=10

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test results
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

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

test_start() {
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    echo ""
    log_info "Test $TOTAL_TESTS: $1"
}

test_pass() {
    PASSED_TESTS=$((PASSED_TESTS + 1))
    log_info "✓ PASSED: $1"
}

test_fail() {
    FAILED_TESTS=$((FAILED_TESTS + 1))
    log_error "✗ FAILED: $1"
}

curl_get() {
    local endpoint="$1"
    local expected_status="${2:-200}"

    response=$(curl -s -w "\n%{http_code}" --max-time "$TIMEOUT" "${API_URL}${endpoint}" || echo "000")
    status_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | head -n-1)

    if [ "$status_code" -eq "$expected_status" ]; then
        echo "$body"
        return 0
    else
        log_error "Expected HTTP $expected_status, got $status_code"
        echo "$body" >&2
        return 1
    fi
}

curl_post() {
    local endpoint="$1"
    local data="$2"
    local expected_status="${3:-200}"

    response=$(curl -s -w "\n%{http_code}" --max-time "$TIMEOUT" \
        -X POST \
        -H "Content-Type: application/json" \
        -d "$data" \
        "${API_URL}${endpoint}" || echo "000")

    status_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | head -n-1)

    if [ "$status_code" -eq "$expected_status" ]; then
        echo "$body"
        return 0
    else
        log_error "Expected HTTP $expected_status, got $status_code"
        echo "$body" >&2
        return 1
    fi
}

# ===================================================================
# CLEANUP FUNCTION
# ===================================================================

cleanup() {
    log_info "Cleaning up test data..."

    # Clean up test memory items (best effort - don't fail if errors)
    if [ -n "${TEST_MEMORY_ID:-}" ]; then
        curl -s -X DELETE "${API_URL}/api/${API_VERSION}/memory-items/${TEST_MEMORY_ID}" || true
    fi

    log_info "Cleanup complete"
}

trap cleanup EXIT

# ===================================================================
# SMOKE TESTS
# ===================================================================

log_info "========================================="
log_info "SkillMeat Staging Smoke Tests"
log_info "========================================="
log_info "API URL: $API_URL"
log_info "Test Project: $TEST_PROJECT_ID"
log_info ""

# -------------------------------------------------------------------
# Test 1: Health Check
# -------------------------------------------------------------------
test_start "API health endpoint returns OK"

if result=$(curl_get "/health" 200); then
    if echo "$result" | grep -q '"status":"healthy"'; then
        test_pass "Health check returned healthy status"
    else
        test_fail "Health check did not return healthy status"
    fi
else
    test_fail "Health endpoint not responding"
    log_error "Cannot continue - API is not healthy"
    exit 1
fi

# -------------------------------------------------------------------
# Test 2: Detailed Health Check
# -------------------------------------------------------------------
test_start "Detailed health endpoint returns component status"

if result=$(curl_get "/health/detailed" 200); then
    if echo "$result" | grep -q '"components"'; then
        test_pass "Detailed health check includes components"

        # Check memory system status
        if echo "$result" | grep -q '"memory_system"'; then
            memory_status=$(echo "$result" | grep -o '"memory_system":[^}]*}' || echo "")
            if echo "$memory_status" | grep -q '"status":"healthy"'; then
                log_info "  Memory system is healthy"
            elif echo "$memory_status" | grep -q '"status":"disabled"'; then
                log_warn "  Memory system is disabled"
            else
                log_warn "  Memory system status: $memory_status"
            fi
        fi
    else
        test_fail "Detailed health check missing components"
    fi
else
    test_fail "Detailed health endpoint failed"
fi

# -------------------------------------------------------------------
# Test 3: Feature Flag Configuration
# -------------------------------------------------------------------
test_start "Feature flag endpoints respond correctly"

if result=$(curl_get "/api/${API_VERSION}/config" 200); then
    if echo "$result" | grep -q '"memory_context_enabled"'; then
        test_pass "Config endpoint returns feature flags"

        # Log feature flag status
        memory_enabled=$(echo "$result" | grep -o '"memory_context_enabled":[^,}]*' | cut -d: -f2)
        log_info "  Memory & Context System: $memory_enabled"
    else
        test_fail "Config endpoint missing feature flags"
    fi
else
    test_fail "Config endpoint not responding"
fi

# -------------------------------------------------------------------
# Test 4: Create Memory Item
# -------------------------------------------------------------------
test_start "Create a memory item"

memory_payload=$(cat <<EOF
{
  "project_id": "$TEST_PROJECT_ID",
  "type": "decision",
  "content": "Smoke test: Use staging environment for pre-production validation",
  "tags": ["testing", "staging"],
  "confidence": 0.95,
  "status": "active",
  "metadata": {
    "test": true,
    "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  }
}
EOF
)

if result=$(curl_post "/api/${API_VERSION}/memory-items" "$memory_payload" 201); then
    TEST_MEMORY_ID=$(echo "$result" | grep -o '"id":"[^"]*"' | head -1 | cut -d'"' -f4)

    if [ -n "$TEST_MEMORY_ID" ]; then
        test_pass "Memory item created with ID: $TEST_MEMORY_ID"
    else
        test_fail "Memory item created but no ID returned"
    fi
else
    test_fail "Failed to create memory item"
    log_warn "Memory system may be disabled or encountering errors"
fi

# -------------------------------------------------------------------
# Test 5: List Memory Items
# -------------------------------------------------------------------
test_start "Verify memory item appears in listing"

if [ -n "${TEST_MEMORY_ID:-}" ]; then
    if result=$(curl_get "/api/${API_VERSION}/memory-items?project_id=$TEST_PROJECT_ID" 200); then
        if echo "$result" | grep -q "$TEST_MEMORY_ID"; then
            test_pass "Memory item found in listing"
        else
            test_fail "Memory item not found in listing"
        fi
    else
        test_fail "Failed to list memory items"
    fi
else
    log_warn "Skipping (no memory item created)"
    TOTAL_TESTS=$((TOTAL_TESTS - 1))
fi

# -------------------------------------------------------------------
# Test 6: Create Context Module
# -------------------------------------------------------------------
test_start "Create a context module"

module_payload=$(cat <<EOF
{
  "project_id": "$TEST_PROJECT_ID",
  "name": "smoke-test-module",
  "description": "Test module for smoke testing",
  "selectors": [
    {
      "type": "tag",
      "values": ["testing"]
    }
  ]
}
EOF
)

if result=$(curl_post "/api/${API_VERSION}/context-modules" "$module_payload" 201); then
    TEST_MODULE_ID=$(echo "$result" | grep -o '"id":"[^"]*"' | head -1 | cut -d'"' -f4)

    if [ -n "$TEST_MODULE_ID" ]; then
        test_pass "Context module created with ID: $TEST_MODULE_ID"
    else
        test_fail "Context module created but no ID returned"
    fi
else
    test_fail "Failed to create context module"
fi

# -------------------------------------------------------------------
# Test 7: List Context Modules
# -------------------------------------------------------------------
test_start "Verify context module appears in listing"

if [ -n "${TEST_MODULE_ID:-}" ]; then
    if result=$(curl_get "/api/${API_VERSION}/context-modules?project_id=$TEST_PROJECT_ID" 200); then
        if echo "$result" | grep -q "$TEST_MODULE_ID"; then
            test_pass "Context module found in listing"
        else
            test_fail "Context module not found in listing"
        fi
    else
        test_fail "Failed to list context modules"
    fi
else
    log_warn "Skipping (no context module created)"
    TOTAL_TESTS=$((TOTAL_TESTS - 1))
fi

# -------------------------------------------------------------------
# Test 8: Generate Context Pack Preview
# -------------------------------------------------------------------
test_start "Generate context pack preview"

pack_payload=$(cat <<EOF
{
  "project_id": "$TEST_PROJECT_ID",
  "budget_tokens": 4000
}
EOF
)

if result=$(curl_post "/api/${API_VERSION}/context-packs/preview" "$pack_payload" 200); then
    if echo "$result" | grep -q '"items_available"'; then
        items_available=$(echo "$result" | grep -o '"items_available":[0-9]*' | cut -d: -f2)
        items_included=$(echo "$result" | grep -o '"items_included":[0-9]*' | cut -d: -f2)

        test_pass "Context pack preview generated (available: $items_available, included: $items_included)"
    else
        test_fail "Context pack preview missing expected fields"
    fi
else
    test_fail "Failed to generate context pack preview"
fi

# -------------------------------------------------------------------
# Test 9: Generate Context Pack
# -------------------------------------------------------------------
test_start "Generate full context pack"

if result=$(curl_post "/api/${API_VERSION}/context-packs/generate" "$pack_payload" 200); then
    if echo "$result" | grep -q '"markdown"'; then
        markdown_length=$(echo "$result" | grep -o '"markdown":"[^"]*"' | wc -c)

        if [ "$markdown_length" -gt 100 ]; then
            test_pass "Context pack generated with markdown content"
        else
            test_fail "Context pack markdown is suspiciously short"
        fi
    else
        test_fail "Context pack missing markdown field"
    fi
else
    test_fail "Failed to generate context pack"
fi

# -------------------------------------------------------------------
# Test 10: Monitoring Metrics Endpoint
# -------------------------------------------------------------------
test_start "Monitoring metrics endpoint is accessible"

if result=$(curl_get "/metrics" 200); then
    if echo "$result" | grep -q "skillmeat_"; then
        test_pass "Prometheus metrics are being exported"

        # Check for key metrics
        if echo "$result" | grep -q "skillmeat_api_requests_total"; then
            log_info "  Request counter metrics found"
        fi
        if echo "$result" | grep -q "skillmeat_memory_items_total"; then
            log_info "  Memory item metrics found"
        fi
    else
        test_fail "Metrics endpoint not returning SkillMeat metrics"
    fi
else
    test_fail "Metrics endpoint not responding"
fi

# ===================================================================
# SUMMARY
# ===================================================================

echo ""
log_info "========================================="
log_info "Test Summary"
log_info "========================================="
log_info "Total Tests:  $TOTAL_TESTS"
log_info "Passed:       $PASSED_TESTS"
log_info "Failed:       $FAILED_TESTS"

if [ "$FAILED_TESTS" -eq 0 ]; then
    echo ""
    log_info "✓ ALL TESTS PASSED"
    exit 0
else
    echo ""
    log_error "✗ SOME TESTS FAILED"
    exit 1
fi
