---
title: Auth Rollout Deployment Guide
description: Step-by-step guide for safely rolling out authentication in SkillMeat, from zero-auth local mode through full Clerk JWT enforcement.
category: deployment
tags: [auth, deployment, rollout, operations, clerk, rbac]
status: active
last_updated: 2026-03-07
audience: [operators, platform-engineers, sre]
---

# Auth Rollout Deployment Guide

This guide documents the authentication modes available in SkillMeat's API, from the default zero-auth local mode through full Clerk JWT enforcement. Choose the mode appropriate for your deployment. Operators running shared or production instances can enable these modes incrementally — see the Recommended Progression tip below.

## Overview

SkillMeat's auth system is designed for flexible activation. The `SKILLMEAT_AUTH_ENABLED` flag and `SKILLMEAT_AUTH_PROVIDER` setting are the two primary levers controlling auth behavior at runtime. Switching between modes does not require a code change — only an environment variable update and a process restart.

> **Recommended Progression:** For operators moving from a personal deployment to a shared or production environment, enabling modes incrementally is a safe approach: start with Zero-Auth Local Mode, validate Clerk connectivity in Write-Protected Mode, then advance to Full Enforcement Mode once all clients are issuing valid tokens. Each mode is independently deployable and individually rollback-safe.

### Auth Provider Summary

| Provider | When Active | Behavior |
|---|---|---|
| `local` (default) | `auth_enabled=false` or `auth_provider=local` | Every request succeeds as `local_admin` with `system_admin` role and all scopes. No token inspected. |
| `clerk` | `auth_enabled=true`, `auth_provider=clerk` | JWT extracted from `Authorization: Bearer` header, validated against Clerk JWKS, mapped to `AuthContext`. |
| Enterprise PAT | Enterprise edition, `ENTERPRISE_PAT_SECRET` set | Static shared secret via `Authorization: Bearer`. Grants `system_admin` with stable service-account UUID. |

### Role and Scope Hierarchy

Roles (most to least privileged): `system_admin` > `team_admin` > `team_member` > `viewer`

Scopes used in enforcement:
- `artifact:read`, `artifact:write`
- `collection:read`, `collection:write`
- `deployment:read`, `deployment:write`
- `admin:*` (wildcard — satisfies all scope checks)

Clerk org-role mappings: `org:admin` → `team_admin`, `org:member` → `team_member`, no org → `viewer`.

`system_admin` is reserved for service accounts only: `local_admin`, enterprise PAT. Clerk users are capped at `team_admin`.

---

## Authentication Modes

### Zero-Auth Local Mode (Default)

No auth enforced. Every request succeeds as `local_admin`. This is the default configuration and requires no setup. Good for personal or local-only use.

**Environment:**
```bash
SKILLMEAT_AUTH_ENABLED=false
SKILLMEAT_AUTH_PROVIDER=local
SKILLMEAT_ENV=production
```

**What happens:**
- `require_auth()` dependency returns `LOCAL_ADMIN_CONTEXT` for every request.
- `AuthMiddleware.dispatch()` calls `is_auth_enabled()` → `False`, passes all requests through immediately.
- No `Authorization` header is required or inspected.
- All endpoints respond normally.

**Verification:**
```bash
# Should return 200 with system_admin role and all scopes
curl -s http://localhost:8080/api/v1/artifacts | jq '.[] | length'

# Health endpoint always open
curl -s http://localhost:8080/health | jq .
```

---

### Write-Protected Mode

Auth required for write operations only. Read endpoints remain open. Good for shared instances where you want to protect mutations but keep browsing accessible without credentials.

This mode validates Clerk connectivity and JWT flow before applying full enforcement. Write endpoints use `require_auth(scopes=["artifact:write"])` (and similar) so callers without the scope receive HTTP 403.

**Environment:**
```bash
SKILLMEAT_AUTH_ENABLED=true         # Enforcement begins
SKILLMEAT_AUTH_PROVIDER=clerk
CLERK_JWKS_URL=https://<your-clerk-frontend-api>/.well-known/jwks.json
CLERK_ISSUER=https://<your-clerk-frontend-api>
CLERK_AUDIENCE=<your-audience-if-set>   # Optional
SKILLMEAT_ENV=production
```

**What happens:**
- `ClerkAuthProvider` initializes and fetches JWKS keys at startup.
- `is_auth_enabled()` returns `True`.
- `require_auth()` delegates to `ClerkAuthProvider.validate()` for every protected route.
- Routes without `require_auth` (e.g., `/health`, `/docs`) remain open.
- `POST`, `PUT`, `DELETE` endpoints with `artifact:write` / `collection:write` / `deployment:write` scopes begin rejecting unauthenticated or insufficiently-scoped requests.

Confirm JWKS connectivity at startup:
```bash
# Check startup logs for this line
grep "ClerkAuthProvider initialised" /var/log/skillmeat/api.log

# Or check directly
curl -s "$CLERK_JWKS_URL" | jq '.keys | length'
```

**Verification:**
```bash
# Read endpoint — should return 200 with no token (reads still open)
curl -s http://localhost:8080/api/v1/artifacts

# Write endpoint — should return 401 with no token
curl -s -X POST http://localhost:8080/api/v1/artifacts \
  -H "Content-Type: application/json" \
  -d '{"name":"test"}' | jq '.detail'
# Expected: "Missing Authorization header"

# Write with valid token and write scope — should return 201
curl -s -X POST http://localhost:8080/api/v1/artifacts \
  -H "Authorization: Bearer $CLERK_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"test","artifact_type":"skill","source":"owner/repo"}' | jq .

# Write with valid token missing write scope — should return 403
curl -s -X POST http://localhost:8080/api/v1/artifacts \
  -H "Authorization: Bearer $READ_ONLY_CLERK_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"test"}' | jq '.detail'
# Expected: message mentioning "artifact:write"
```

**Verification checklist:**
- [ ] API starts without errors
- [ ] JWKS URL reachable from the server
- [ ] `ClerkAuthProvider initialised` present in startup logs
- [ ] Write endpoints return 401 with no token
- [ ] Write endpoints return 403 with read-only token
- [ ] Write endpoints return 2xx with valid write-scoped token
- [ ] Read endpoints still accessible without token
- [ ] `/health`, `/health/ready`, `/health/live` return 200 with no token
- [ ] Auth failure rate (401 + 403) remains below 5% of total requests in the first hour
- [ ] No increase in application error rate (5xx)

---

### Full Enforcement Mode

Auth required for all `/api/v1` endpoints. Health checks and documentation endpoints remain open. Good for production multi-user deployments where all clients are expected to hold valid Clerk tokens.

**Environment:**
```bash
SKILLMEAT_AUTH_ENABLED=true
SKILLMEAT_AUTH_PROVIDER=clerk
CLERK_JWKS_URL=https://<your-clerk-frontend-api>/.well-known/jwks.json
CLERK_ISSUER=https://<your-clerk-frontend-api>
SKILLMEAT_ENV=production
```

**What happens:**
`AuthMiddleware` is initialized with `protected_paths=["/api/v1"]` (the default). Every sub-path under `/api/v1` is guarded at the middleware layer in addition to the dependency layer. The excluded paths remain open:
- `/health`
- `/docs`
- `/redoc`
- `/openapi.json`
- `/`
- `/api/v1/version`

**Verification:**
```bash
# Any read endpoint without token — should return 401
curl -s http://localhost:8080/api/v1/artifacts | jq '.detail'
# Expected: "Missing or invalid Authorization header"

# Same endpoint with valid token — should return 200
curl -s http://localhost:8080/api/v1/artifacts \
  -H "Authorization: Bearer $CLERK_TOKEN" | jq '.[] | length'

# Health checks remain open
curl -s http://localhost:8080/health | jq '.status'
curl -s http://localhost:8080/health/ready | jq '.status'
curl -s http://localhost:8080/health/live | jq '.status'
```

**Verification checklist:**
- [ ] All `/api/v1` routes return 401 without token
- [ ] All `/api/v1` routes return 200/201 with valid token
- [ ] Health checks remain unauthenticated
- [ ] Zero auth-related 5xx errors
- [ ] Auth success rate above 95% for known-good clients

---

## Feature Flags Reference

All auth behavior is controlled by environment variables with the `SKILLMEAT_` prefix:

| Variable | Type | Default | Purpose |
|---|---|---|---|
| `SKILLMEAT_AUTH_ENABLED` | bool | `false` | Master enforcement switch. When `false`, `is_auth_enabled()` returns `False` and all auth checks are bypassed. |
| `SKILLMEAT_AUTH_PROVIDER` | string | `local` | Provider selection: `local` or `clerk`. |
| `CLERK_JWKS_URL` | string | — | Clerk JWKS endpoint. Required when `auth_provider=clerk`. Also accepted as `SKILLMEAT_CLERK_JWKS_URL`. |
| `CLERK_ISSUER` | string | — | Expected JWT `iss` claim. Optional but recommended. Also `SKILLMEAT_CLERK_ISSUER`. |
| `CLERK_AUDIENCE` | string | — | Expected JWT `aud` claim. Optional. Also `SKILLMEAT_CLERK_AUDIENCE`. |
| `SKILLMEAT_ENTERPRISE_PAT_SECRET` | string | — | Shared secret for enterprise PAT auth (enterprise edition only). |
| `SKILLMEAT_EDITION` | string | `local` | Edition: `local` or `enterprise`. Controls repository implementation selection. |
| `SKILLMEAT_RATE_LIMIT_ENABLED` | bool | `false` | Enable IP-based rate limiting. |
| `SKILLMEAT_RATE_LIMIT_REQUESTS` | int | `100` | Max requests per minute per IP when rate limiting is enabled. |
| `SKILLMEAT_LOG_LEVEL` | string | `INFO` | Set to `DEBUG` to log all auth decisions. |

### Disabling Auth Instantly

To disable auth enforcement without a code deploy, set one environment variable and restart:
```bash
SKILLMEAT_AUTH_ENABLED=false
```

The `is_auth_enabled()` function reads from settings at call time, so the change takes effect on the next request after process restart.

---

## Monitoring Auth Failures

### Key Metrics

SkillMeat exposes Prometheus metrics via `skillmeat.observability.metrics`. The following are directly relevant to auth monitoring:

| Metric | Labels | Alert On |
|---|---|---|
| `skillmeat_api_requests_total` | `method`, `endpoint`, `status` | Rate of `status=401` or `status=403` rising above baseline |
| `skillmeat_api_errors_total` | `method`, `endpoint`, `error_type` | `error_type=HTTPException` on auth endpoints |
| `skillmeat_api_request_duration_seconds` | `method`, `endpoint` | Spikes on auth-protected endpoints (may indicate JWKS latency) |

Auth failures surface as HTTP 401 or 403 responses recorded in `skillmeat_api_requests_total`. They are not application errors (5xx) and will not appear in `skillmeat_api_errors_total` unless JWKS is unreachable (503).

### PromQL Queries

**Auth failure rate (401 + 403) as fraction of total requests:**
```promql
sum(rate(skillmeat_api_requests_total{status=~"401|403"}[5m]))
/
sum(rate(skillmeat_api_requests_total[5m]))
```

**Absolute 401 rate (unauthenticated requests):**
```promql
sum by (endpoint) (rate(skillmeat_api_requests_total{status="401"}[5m]))
```

**JWKS unavailability (503 on auth-protected endpoints):**
```promql
sum(rate(skillmeat_api_requests_total{status="503"}[5m]))
```

**Auth latency percentile (watch for JWKS round-trip impact):**
```promql
histogram_quantile(0.99, sum by (le, endpoint) (
  rate(skillmeat_api_request_duration_seconds_bucket[5m])
))
```

### Log Queries

Auth events are structured JSON logs. Example filters for common log aggregators:

**Unauthorized requests (level=WARNING from auth middleware):**
```json
{ "level": "WARNING", "message": "Unauthorized request*" }
```

**Enterprise PAT failures:**
```json
{ "logger": "skillmeat.api.middleware.enterprise_auth", "level": "WARNING" }
```

**JWKS connectivity errors:**
```json
{ "logger": "skillmeat.api.auth.clerk_provider", "level": "ERROR" }
```

**All auth decisions in DEBUG mode:**
```bash
SKILLMEAT_LOG_LEVEL=DEBUG
# Logs: "Clerk JWT mapped to AuthContext", "set_tenant_context_dep: setting TenantContext..."
```

---

## Alerting Setup

### Recommended Alert Rules

The following alerts cover the primary failure modes during and after rollout.

#### Alert: High Auth Failure Rate
```yaml
# Prometheus alerting rule
- alert: SkillMeatHighAuthFailureRate
  expr: |
    sum(rate(skillmeat_api_requests_total{status=~"401|403"}[5m]))
    /
    sum(rate(skillmeat_api_requests_total[5m])) > 0.10
  for: 5m
  labels:
    severity: warning
    team: platform
  annotations:
    summary: "Auth failure rate above 10% for 5 minutes"
    description: "More than 10% of requests are returning 401 or 403. Check whether Clerk tokens are being issued correctly, or consider rollback if this follows a deployment."
```

#### Alert: JWKS Endpoint Unreachable
```yaml
- alert: SkillMeatJWKSUnavailable
  expr: |
    sum(rate(skillmeat_api_requests_total{status="503"}[2m])) > 0
  for: 2m
  labels:
    severity: critical
    team: platform
  annotations:
    summary: "JWKS endpoint returning 503 — auth service unreachable"
    description: "ClerkAuthProvider cannot reach the JWKS endpoint. All authenticated requests will fail. Verify CLERK_JWKS_URL is reachable from the API server."
```

#### Alert: Spike in Unauthenticated Requests (Full Enforcement)
```yaml
- alert: SkillMeatUnexpected401Spike
  expr: |
    sum(rate(skillmeat_api_requests_total{status="401"}[5m])) > 10
  for: 3m
  labels:
    severity: warning
    team: platform
  annotations:
    summary: "Unusual volume of 401 responses"
    description: "High volume of unauthenticated requests. May indicate a client misconfiguration or a token expiry issue. Check client logs and Clerk dashboard."
```

#### Alert: Auth Latency Degradation
```yaml
- alert: SkillMeatAuthLatencyHigh
  expr: |
    histogram_quantile(0.99,
      sum by (le) (rate(skillmeat_api_request_duration_seconds_bucket[5m]))
    ) > 2.0
  for: 5m
  labels:
    severity: warning
    team: platform
  annotations:
    summary: "p99 API latency above 2s — possible JWKS round-trip delay"
    description: "JWKS key cache may have expired and remote fetches are adding latency. Check JWKS endpoint response time. ClerkAuthProvider cache TTL is 300s by default."
```

---

## Canary Deployment

Use a canary instance to test auth enforcement with a small fraction of traffic before cutting over all instances.

### Setup Pattern

1. Deploy a canary instance with `SKILLMEAT_AUTH_ENABLED=true`.
2. Route 5–10% of traffic to the canary via your load balancer (NGINX, Caddy, Kubernetes ingress weight, etc.).
3. Run the canary for at least 24 hours before promoting to all instances.

### NGINX Canary Example

```nginx
upstream skillmeat_main {
    server 10.0.0.1:8080 weight=9;
}

upstream skillmeat_canary {
    server 10.0.0.2:8080 weight=1;   # 10% of traffic
}

# Route to canary via cookie or weight
split_clients "${remote_addr}AAA" $upstream_pool {
    10%    skillmeat_canary;
    *      skillmeat_main;
}

server {
    location /api/ {
        proxy_pass http://$upstream_pool;
    }
}
```

### Canary Health Signals to Watch

Monitor the canary instance separately:

- 401/403 rate on canary vs. main — should match expected auth-failure baseline.
- p99 latency on canary — JWKS cache miss adds ~50–200ms on first request.
- Application error rate (5xx) — should be unchanged from main.
- Auth success rate — should track Clerk token issuance in your dashboard.

### Canary Promotion Criteria

- [ ] Auth failure rate on canary matches pre-rollout expectation (e.g., below 2% for known-good client population)
- [ ] No increase in 5xx errors on canary
- [ ] p99 latency on canary within 200ms of main
- [ ] Zero JWKS availability incidents during canary window
- [ ] At least 1000 authenticated requests processed successfully

---

## Rollback Procedures

### Immediate Rollback: Disable Auth (Zero Downtime)

The fastest rollback path requires only an environment variable change and process restart. No code change needed.

**Step 1: Set the flag.**
```bash
# In your environment / secrets manager / .env file:
SKILLMEAT_AUTH_ENABLED=false
```

**Step 2: Restart the API server.**
```bash
# Systemd
sudo systemctl restart skillmeat-api

# Docker
docker restart skillmeat-api

# Kubernetes — rolling restart
kubectl rollout restart deployment/skillmeat-api

# Direct uvicorn
kill -HUP $(pgrep -f "uvicorn skillmeat")
```

**Step 3: Verify auth is disabled.**
```bash
# Should return 200 without any Authorization header
curl -s http://localhost:8080/api/v1/artifacts | jq '.[] | length'

# Check logs confirm bypass
grep "is_auth_enabled.*False\|Skip auth" /var/log/skillmeat/api.log
```

**Expected time to recovery:** Under 60 seconds for most deployments.

### Partial Rollback: Revert from Full Enforcement to Write-Protected Mode

If Full Enforcement Mode is causing issues but Write-Protected Mode was stable, you can reduce scope without a full rollback:

- Full Enforcement → Write-Protected: The code-level enforcement difference between these modes lies in which routes use `require_auth`. In the current implementation, `AuthMiddleware` covers all `/api/v1` at the middleware layer. To revert to Write-Protected behavior while keeping `auth_enabled=true`, you need to modify the `AuthMiddleware` excluded path list or redeploy the previous artifact. The simplest production-safe option is to disable auth entirely (`auth_enabled=false`) and re-enable incrementally.

### Rollback Decision Triggers

Consider rolling back when any of the following occur within 30 minutes of enabling a new mode:

| Signal | Threshold | Action |
|---|---|---|
| Auth failure rate | >15% sustained for 5 min | Revert to previous auth mode |
| 5xx error rate increase | >1% increase from baseline | Investigate before proceeding |
| JWKS unavailable (503) | Any sustained outage >2 min | Rollback if Clerk unreachable |
| p99 latency increase | >500ms increase from baseline | Investigate JWKS cache |
| User-reported auth failures | Any from known-good clients | Investigate token issuance |

---

## Health Check Endpoints

All health endpoints are permanently excluded from auth enforcement, in both `AuthMiddleware.excluded_paths` and by the absence of `require_auth` in the health router.

| Endpoint | Purpose | Auth Required |
|---|---|---|
| `GET /health` | Basic liveness — returns `{"status": "healthy"}` | Never |
| `GET /health/detailed` | Component status: collection manager, config manager, filesystem, memory system | Never |
| `GET /health/ready` | Readiness probe for orchestrators — returns 503 if not ready | Never |
| `GET /health/live` | Liveness probe for orchestrators | Never |

### Auth Subsystem Health Check

The health endpoints do not explicitly test Clerk JWT validation. To verify the auth subsystem is healthy:

**Check JWKS reachability:**
```bash
# Fetch JWKS — should return a JSON object with at least one key
curl -sf "$CLERK_JWKS_URL" | jq '.keys | length'
# Expected: a positive integer (typically 2–4 keys)
```

**Validate a known-good token:**
```bash
# Send a request that exercises the full auth path
curl -sv http://localhost:8080/api/v1/artifacts \
  -H "Authorization: Bearer $KNOWN_GOOD_TOKEN" 2>&1 | grep "< HTTP"
# Expected: HTTP/1.1 200 OK
```

**Check ClerkAuthProvider initialized in startup logs:**
```bash
grep "ClerkAuthProvider initialised" /var/log/skillmeat/api.log | tail -1
# Expected: {"timestamp": "...", "level": "INFO", "message": "ClerkAuthProvider initialised", ...}
```

**Verify auth middleware is active (Write-Protected or Full Enforcement):**
```bash
curl -s http://localhost:8080/api/v1/artifacts | jq '.detail'
# When auth_enabled=true and no token: "Missing or invalid Authorization header"
# When auth_enabled=false: will return data (no detail)
```

---

## Production Deployment Checklist

Complete all applicable items before enabling a new auth mode.

### Pre-Deployment (All Modes)

- [ ] Verify Clerk application is configured and JWKS URL is accessible from the production server
- [ ] Confirm `CLERK_JWKS_URL`, `CLERK_ISSUER` env vars are set and valid
- [ ] Check that `CLERK_AUDIENCE` matches the audience claim in tokens (if audience validation is used)
- [ ] Confirm rate limiting policy (`SKILLMEAT_RATE_LIMIT_ENABLED`, `SKILLMEAT_RATE_LIMIT_REQUESTS`) is appropriate for expected load
- [ ] Deploy Prometheus alert rules from the Alerting Setup section
- [ ] Verify `/health` returns 200 on the target instance before any config change

### Write-Protected Mode Checklist

- [ ] Set `SKILLMEAT_AUTH_PROVIDER=clerk` and all `CLERK_*` vars
- [ ] Set `SKILLMEAT_AUTH_ENABLED=true`
- [ ] Restart API server
- [ ] Confirm `ClerkAuthProvider initialised` in startup logs
- [ ] Confirm JWKS URL is reachable: `curl -sf "$CLERK_JWKS_URL" | jq '.keys | length'`
- [ ] Verify write endpoints reject unauthenticated requests (expect 401)
- [ ] Verify read endpoints still accept unauthenticated requests
- [ ] Verify clients with valid tokens can write artifacts
- [ ] Verify clients with read-only tokens receive 403 on write attempts (not 401 or 500)
- [ ] Monitor for 1 hour — auth failure rate should be under 5% (accounting for expected unauthenticated clients)
- [ ] Alert rules are firing only on genuine failures, not false positives

### Full Enforcement Mode Checklist

- [ ] Confirm Write-Protected Mode is stable for at least 72 hours
- [ ] Confirm all client applications (web UI, CLI tools, integrations) are obtaining valid Clerk tokens
- [ ] Confirm the frontend is configured with Clerk publishable key and token refresh logic
- [ ] Canary deployment has been run for at least 24 hours (see Canary Deployment section)
- [ ] Canary auth failure rate is within acceptable bounds
- [ ] Run full test suite against staging with `SKILLMEAT_AUTH_ENABLED=true`
- [ ] Deploy to production with `SKILLMEAT_AUTH_ENABLED=true`
- [ ] Verify all `/api/v1` routes return 401 without token
- [ ] Verify `/health`, `/docs`, `/openapi.json` are still open
- [ ] Monitor for 4 hours post-deployment
- [ ] Confirm auth success rate is above 95% for known-good clients

### Post-Deployment Verification

- [ ] `skillmeat_api_requests_total{status="401"}` rate is at expected baseline
- [ ] No `skillmeat_api_requests_total{status="503"}` (JWKS unavailable)
- [ ] p99 latency has not increased by more than 200ms from pre-auth baseline
- [ ] Application logs show `Clerk JWT mapped to AuthContext` for authenticated requests
- [ ] No `ENTERPRISE_PAT_SECRET is not configured` errors (if enterprise edition)
- [ ] Rollback procedure has been rehearsed in staging

---

## Tenant Context and Enterprise Edition Notes

When `SKILLMEAT_EDITION=enterprise`, the `TenantContextDep` dependency can be added to enterprise routers to scope all database queries to the authenticated tenant.

The `set_tenant_context_dep` dependency:
1. Runs `require_auth()` to obtain `AuthContext`.
2. Extracts `tenant_id` from the context.
3. Sets the `TenantContext` ContextVar for the duration of the request.
4. Clears it in a `finally` block after the handler returns (prevents tenant context leakage).

In local mode (`tenant_id=None`), this dependency is a no-op — enterprise repositories fall back to `DEFAULT_TENANT_ID`.

For enterprise rollouts, set `SKILLMEAT_ENTERPRISE_PAT_SECRET` before exposing enterprise download endpoints. The secret is read from the environment at call time (not import time), so it can be rotated without restarting the process.

---

## Troubleshooting Quick Reference

| Symptom | Likely Cause | Resolution |
|---|---|---|
| All requests return 401 after enabling auth | Clients not sending `Authorization: Bearer` header | Check client configuration; confirm token issuance in Clerk dashboard |
| API starts but logs show JWKS fetch error | `CLERK_JWKS_URL` unreachable from server | Check network egress rules; verify URL is correct for your Clerk instance |
| 403 on write endpoint with valid token | Token has only read scopes | Verify Clerk organization role for user (`org:member` gets write scopes by default) |
| 503 on authenticated endpoints | JWKS endpoint down or rate-limited | Disable auth temporarily (`auth_enabled=false`), investigate Clerk status |
| `InvalidTokenError` in logs | Token audience/issuer mismatch | Verify `CLERK_AUDIENCE` and `CLERK_ISSUER` match actual token claims |
| Enterprise PAT returns 403 | `ENTERPRISE_PAT_SECRET` not set on server | Set the environment variable and restart |
| `ClerkAuthProvider initialised` missing from startup logs | `auth_provider` is still `local` | Set `SKILLMEAT_AUTH_PROVIDER=clerk` and restart |
| Auth works in staging but not production | Environment variable not set in production secrets | Audit all `SKILLMEAT_*` and `CLERK_*` env vars in the production environment |

---

## Related Documentation

- `skillmeat/api/middleware/auth.py` — `AuthMiddleware`, `is_auth_enabled()`, `verify_token()`
- `skillmeat/api/middleware/enterprise_auth.py` — `verify_enterprise_pat()`, `EnterprisePATDep`
- `skillmeat/api/middleware/tenant_context.py` — `set_tenant_context_dep`, `TenantContextDep`
- `skillmeat/api/auth/clerk_provider.py` — `ClerkAuthProvider`, JWKS caching, claim mapping
- `skillmeat/api/auth/local_provider.py` — `LocalAuthProvider` (zero-auth)
- `skillmeat/api/schemas/auth.py` — `AuthContext`, `Role`, `Scope`, `LOCAL_ADMIN_CONTEXT`
- `skillmeat/api/config.py` — `APISettings`, all auth-related env vars
- `skillmeat/api/tests/test_auth_integration.py` — Integration test reference for auth behavior
- `docs/guides/security/` — Security hardening guides
