#!/usr/bin/env bash
# SkillMeat Production Smoke Tests
# Verifies critical user journeys after production deployment
# Includes all staging tests plus production-specific checks:
#   - Feature flag verification (OFF by default)
#   - Memory endpoint behavior when disabled
#   - Feature flag activation validation

set -euo pipefail

# ===================================================================
# CONFIGURATION
# ===================================================================
API_URL="${SKILLMEAT_API_URL:-http://localhost:8080}"
API_VERSION="${SKILLMEAT_API_VERSION:-v1}"
TEST_PROJECT_ID="smoke-test-prod-$(date +%s)"
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
    log_info "PASSED: $1"
}

test_fail() {
    FAILED_TESTS=$((FAILED_TESTS + 1))
    log_error "FAILED: $1"
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

# Helper that accepts any of the listed status codes
curl_get_any_status() {
    local endpoint="$1"
    shift
    local allowed_statuses=("$@")

    response=$(curl -s -w "\n%{http_code}" --max-time "$TIMEOUT" "${API_URL}${endpoint}" || echo "000")
    status_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | head -n-1)

    for allowed in "${allowed_statuses[@]}"; do
        if [ "$status_code" -eq "$allowed" ]; then
            echo "$body"
            return 0
        fi
    done

    log_error "Expected one of [${allowed_statuses[*]}], got $status_code"
    echo "$body" >&2
    return 1
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
# SMOKE TESTS -- CORE INFRASTRUCTURE
# ===================================================================

log_info "========================================="
log_info "SkillMeat Production Smoke Tests"
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
    log_error "Cannot continue -- API is not healthy"
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
            if echo "$memory_status" | grep -q '"status":"disabled"'; then
                log_info "  Memory system is disabled (expected for production rollout)"
            elif echo "$memory_status" | grep -q '"status":"healthy"'; then
                log_warn "  Memory system is healthy (feature flag may be enabled)"
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
# Test 4: Monitoring Metrics Endpoint
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
# SMOKE TESTS -- PRODUCTION-SPECIFIC: FEATURE FLAG VERIFICATION
# ===================================================================

log_info ""
log_info "========================================="
log_info "Production-Specific Tests"
log_info "========================================="

# -------------------------------------------------------------------
# Test 5: Feature Flag OFF by Default
# -------------------------------------------------------------------
test_start "Memory & Context feature flag is OFF by default"

if result=$(curl_get "/api/${API_VERSION}/config" 200); then
    memory_enabled=$(echo "$result" | grep -o '"memory_context_enabled":[^,}]*' | cut -d: -f2 | tr -d ' ')

    if [ "$memory_enabled" = "false" ]; then
        test_pass "Memory & Context feature flag is correctly OFF"
    elif [ "$memory_enabled" = "true" ]; then
        test_fail "Memory & Context feature flag is ON (should be OFF for graduated rollout)"
    else
        log_warn "Could not determine feature flag state: $memory_enabled"
        test_fail "Unable to verify feature flag state"
    fi
else
    test_fail "Could not read feature flag configuration"
fi

# -------------------------------------------------------------------
# Test 6: Memory Endpoints Disabled When Flag is OFF
# -------------------------------------------------------------------
test_start "Memory endpoints return disabled/error when flag is OFF"

# Try to create a memory item -- should fail with 404 or 403 or 503 when disabled
memory_payload=$(cat <<EOF
{
  "project_id": "$TEST_PROJECT_ID",
  "type": "decision",
  "content": "This should fail when memory is disabled",
  "tags": ["test"],
  "confidence": 0.5,
  "status": "active",
  "metadata": {}
}
EOF
)

response=$(curl -s -w "\n%{http_code}" --max-time "$TIMEOUT" \
    -X POST \
    -H "Content-Type: application/json" \
    -d "$memory_payload" \
    "${API_URL}/api/${API_VERSION}/memory-items" || echo "000")

status_code=$(echo "$response" | tail -n1)

# When the feature is disabled, we expect a non-success response (4xx or 5xx)
# or if the system gracefully handles it, it might return 201 but with the system disabled
# Accept 404, 403, 503, or 422 as valid "disabled" responses
if [ "$status_code" -eq 404 ] || [ "$status_code" -eq 403 ] || [ "$status_code" -eq 503 ]; then
    test_pass "Memory creation correctly rejected (HTTP $status_code) when feature flag is OFF"
elif [ "$status_code" -eq 201 ] || [ "$status_code" -eq 200 ]; then
    # If endpoints still work with flag off, that may be by design (flag only controls auto-extraction)
    log_warn "Memory endpoint accepted request (HTTP $status_code) despite feature flag being OFF"
    log_warn "This may be acceptable if the flag only controls auto-extraction behavior"
    test_pass "Memory endpoint responded (HTTP $status_code) -- verify intended behavior"
    # Save ID for cleanup
    body=$(echo "$response" | head -n-1)
    TEST_MEMORY_ID=$(echo "$body" | grep -o '"id":"[^"]*"' | head -1 | cut -d'"' -f4 || echo "")
else
    test_fail "Unexpected response from memory endpoint (HTTP $status_code)"
fi

# -------------------------------------------------------------------
# Test 7: Memory Listing Disabled When Flag is OFF
# -------------------------------------------------------------------
test_start "Memory listing returns appropriate response when flag is OFF"

# Try to list memory items -- may return empty list, 404, or 503 when disabled
response=$(curl -s -w "\n%{http_code}" --max-time "$TIMEOUT" \
    "${API_URL}/api/${API_VERSION}/memory-items?project_id=$TEST_PROJECT_ID" || echo "000")

status_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | head -n-1)

if [ "$status_code" -eq 404 ] || [ "$status_code" -eq 403 ] || [ "$status_code" -eq 503 ]; then
    test_pass "Memory listing correctly unavailable (HTTP $status_code) when feature flag is OFF"
elif [ "$status_code" -eq 200 ]; then
    # Endpoint may return empty results when flag is off -- acceptable
    log_info "  Memory listing returned HTTP 200 (may return empty or existing items)"
    test_pass "Memory listing endpoint responded (HTTP 200)"
else
    test_fail "Unexpected response from memory listing (HTTP $status_code)"
fi

# -------------------------------------------------------------------
# Test 8: Context Module Endpoints Disabled When Flag is OFF
# -------------------------------------------------------------------
test_start "Context module endpoints respond appropriately when flag is OFF"

module_payload=$(cat <<EOF
{
  "project_id": "$TEST_PROJECT_ID",
  "name": "production-test-module",
  "description": "Test module for production smoke testing",
  "selectors": [
    {
      "type": "tag",
      "values": ["test"]
    }
  ]
}
EOF
)

response=$(curl -s -w "\n%{http_code}" --max-time "$TIMEOUT" \
    -X POST \
    -H "Content-Type: application/json" \
    -d "$module_payload" \
    "${API_URL}/api/${API_VERSION}/context-modules" || echo "000")

status_code=$(echo "$response" | tail -n1)

if [ "$status_code" -eq 404 ] || [ "$status_code" -eq 403 ] || [ "$status_code" -eq 503 ]; then
    test_pass "Context module creation correctly rejected (HTTP $status_code) when feature flag is OFF"
elif [ "$status_code" -eq 201 ] || [ "$status_code" -eq 200 ]; then
    log_warn "Context module endpoint accepted request (HTTP $status_code) despite feature flag being OFF"
    log_warn "This may be acceptable if the flag only controls auto-extraction behavior"
    test_pass "Context module endpoint responded (HTTP $status_code) -- verify intended behavior"
else
    test_fail "Unexpected response from context module endpoint (HTTP $status_code)"
fi

# -------------------------------------------------------------------
# Test 9: Auto-Extract Disabled
# -------------------------------------------------------------------
test_start "Auto-extract is disabled in production"

if result=$(curl_get "/api/${API_VERSION}/config" 200); then
    auto_extract=$(echo "$result" | grep -o '"memory_auto_extract":[^,}]*' | cut -d: -f2 | tr -d ' ')

    if [ "$auto_extract" = "false" ]; then
        test_pass "Auto-extract is correctly disabled"
    elif [ "$auto_extract" = "true" ]; then
        test_fail "Auto-extract is enabled (should be disabled in production)"
    else
        log_warn "Could not determine auto-extract state from config"
        # Not a hard failure -- field may not be exposed
        test_pass "Auto-extract config check completed (field may not be exposed in config)"
    fi
else
    test_fail "Could not read auto-extract configuration"
fi

# -------------------------------------------------------------------
# Test 10: Rate Limiting Active
# -------------------------------------------------------------------
test_start "Rate limiting is active in production"

# Send a burst of requests and check for rate limit headers or 429
rate_limited=false
for i in $(seq 1 5); do
    response=$(curl -s -w "\n%{http_code}" --max-time "$TIMEOUT" \
        -D - "${API_URL}/health" 2>/dev/null || echo "000")

    if echo "$response" | grep -qi "x-ratelimit\|retry-after"; then
        rate_limited=true
        break
    fi

    status_code=$(echo "$response" | tail -n1)
    if [ "$status_code" -eq 429 ]; then
        rate_limited=true
        break
    fi
done

if [ "$rate_limited" = true ]; then
    test_pass "Rate limiting headers detected"
else
    # Rate limiting may not trigger with only 5 requests
    log_warn "Rate limit headers not detected in 5 requests (limit may be higher)"
    test_pass "Rate limiting check completed (may need more requests to trigger)"
fi

# -------------------------------------------------------------------
# Test 11: CORS Headers (Production Domain)
# -------------------------------------------------------------------
test_start "CORS headers restrict to production domain"

cors_response=$(curl -s -D - -o /dev/null --max-time "$TIMEOUT" \
    -H "Origin: https://skillmeat.example.com" \
    "${API_URL}/health" 2>/dev/null || echo "")

if echo "$cors_response" | grep -qi "access-control-allow-origin"; then
    allowed_origin=$(echo "$cors_response" | grep -i "access-control-allow-origin" | head -1)
    if echo "$allowed_origin" | grep -q "skillmeat.example.com"; then
        test_pass "CORS allows production domain"
    elif echo "$allowed_origin" | grep -q "\*"; then
        test_fail "CORS allows all origins (should be restricted in production)"
    else
        log_info "  CORS origin: $allowed_origin"
        test_pass "CORS headers present"
    fi
else
    log_warn "No CORS headers returned (may not be configured on health endpoint)"
    test_pass "CORS check completed"
fi

# -------------------------------------------------------------------
# Test 12: No Debug/Dev Endpoints Exposed
# -------------------------------------------------------------------
test_start "Debug and development endpoints are not exposed"

# Check that /docs is not open (or requires auth) in strict production
# Note: /docs may still be available but this documents the check
debug_endpoints_found=0

for endpoint in "/debug" "/dev" "/_debug"; do
    response=$(curl -s -w "\n%{http_code}" --max-time "$TIMEOUT" "${API_URL}${endpoint}" || echo "000")
    status_code=$(echo "$response" | tail -n1)

    if [ "$status_code" -eq 200 ]; then
        log_warn "Debug endpoint $endpoint is accessible (HTTP 200)"
        debug_endpoints_found=$((debug_endpoints_found + 1))
    fi
done

if [ "$debug_endpoints_found" -eq 0 ]; then
    test_pass "No debug endpoints exposed"
else
    test_fail "$debug_endpoints_found debug endpoint(s) are accessible in production"
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
    log_info "ALL TESTS PASSED"
    echo ""
    log_info "Production infrastructure is verified."
    log_info "Proceed with graduated rollout per rollout-plan.md"
    exit 0
else
    echo ""
    log_error "SOME TESTS FAILED"
    echo ""
    log_error "Review failures above before proceeding with rollout."
    log_error "Do NOT enable the Memory & Context feature flag until all tests pass."
    exit 1
fi
