---
title: "Sync Status Performance Refactor: Rollout Checklist and Operational Watchpoints"
description: "Deploy/rollback checklist and operational monitoring for sync-status-performance-refactor with risk controls"
audience: "developers, platform engineers, on-call"
tags:
  - sync-status
  - performance
  - deployment
  - rollout
  - checklist
created: 2026-02-21
updated: 2026-02-21
category: refactors
status: ready
related_documents:
  - docs/project_plans/implementation_plans/refactors/sync-status-performance-refactor-v1.md
  - docs/project_plans/reports/sync-status-performance-analysis-2026-02-20.md
---

# Sync Status Performance Refactor: Rollout Checklist

## Pre-Deploy Checklist

### Backend

- [ ] `pytest tests/ -v --cov=skillmeat/api/routers/deployments.py skillmeat/api/routers/artifacts.py --cov-min-percent=80` passes
- [ ] `mypy skillmeat/core/deployment.py skillmeat/storage/deployment.py --ignore-missing-imports` shows no new errors
- [ ] API contract tests pass: `pytest tests/api/ -k "diff" -v` (summary-first mode + legacy mode)
- [ ] Cache invalidation tests pass: `pytest tests/api/test_cache_invalidation.py -v`
- [ ] Verify OpenAPI schema updated: `skillmeat/api/openapi.json` includes `?mode=summary` parameter docs
- [ ] No integration test regressions: full `pytest tests/integration/` pass

### Frontend

- [ ] `pnpm type-check` passes (no new TS errors in sync-status, diff-viewer, artifact-operations-modal)
- [ ] `pnpm test -- --testPathPattern="sync-status|diff-viewer|artifact-operations" --coverage` passes with >80% coverage
- [ ] `pnpm lint` clean on modified components (no new exhaustive-deps warnings)
- [ ] E2E test for sync-modal load: `pnpm test:e2e -- sync-modal.spec.ts` passes
- [ ] Manual regression: open sync modal on small and large projects, verify no console errors

### Cross-Layer

- [ ] Backend perf instrumentation logs present and readable (check structured logs)
- [ ] Frontend React DevTools Profiler confirms lazy-load markers fire
- [ ] No breaking changes to API contracts (additive query params only, default behavior unchanged)

---

## Deploy Steps

### Sequence (Both layers can deploy independently, backend first recommended)

#### 1. Deploy Backend (Production)

1. **Pre-flight check**: Verify all backend tests green
2. **Deploy API service**: Rolling update with health checks (old/new instances in traffic 30s each)
3. **Verify health**: 3-5 sync diff requests from health check dashboard return 2xx
4. **Monitor**: Watch error rate on `/diff`, `/deployments` endpoints for 2 min
5. **Fallback ready**: Cache can be disabled via config flag `CACHE_DIFF_ENABLED=false` if needed

#### 2. Deploy Frontend (Production)

1. **Pre-flight check**: Verify all frontend tests and type-check green
2. **Build**: `pnpm build` completes without warnings
3. **Deploy**: Static assets to CDN, canary 10% traffic for 5 min
4. **Verify**: Check JavaScript bundle size increase <5% (perf regression early warning)
5. **Monitor**: Frontend error rate from Sentry for 2 min
6. **Ramp**: Increase to 100% traffic after no errors observed

**Note**: Backend new API params are additive and backward compatible. Frontend will default to optimized queries; rollback does not require backend rollback.

---

## Operational Watchpoints (2 hours post-deploy)

### Metrics to Monitor (Real-Time)

| Metric | Expected | Alert Threshold | Dashboard |
|--------|----------|-----------------|-----------|
| Diff endpoint error rate | <0.5% | >2% | API Metrics → `/diff` |
| Diff endpoint p95 latency | 100-200ms (improved) | >500ms | API Metrics → `/diff` |
| Deployment list error rate | <0.5% | >2% | API Metrics → `/deployments` |
| Sync modal JS errors | 0 | >5/min | Sentry → `artifact-operations-modal` |
| Diff viewer render time (FCP) | 300-500ms | >1s | Frontend Performance → sync-tab |
| Cache hit rate (backend) | 60-80% on repeated diffs | <40% | API Instrumentation logs |

### Log Patterns to Grep (Every 10 min)

```bash
# Backend: Check cache invalidation is working
grep "cache_invalidated.*diff" /var/log/skillmeat/api.log | wc -l
# Expected: >5 per 10 min during active use

# Backend: Check no timeout errors
grep -E "timeout|upstream.*error" /var/log/skillmeat/api.log | wc -l
# Expected: 0 per 10 min

# Frontend: Check lazy-load markers are firing
grep -i "perf:diff.*lazy-loaded" /var/log/skillmeat/frontend.log | wc -l
# Expected: >10 per 10 min during active sync use
```

### Manual Verification (First 30 min)

1. **Sync tab cold start**: Open artifact with 5+ deployments in new browser tab
   - Verify: Initial diff loads in <500ms
   - Verify: No console errors (F12 → Console tab)

2. **Scope switching**: Switch between `source-vs-collection` → `collection-vs-project` → `source-vs-project`
   - Verify: Scope loads in <300ms (cached from earlier load)
   - Verify: Sidebar stats (additions/deletions) remain correct

3. **Large diff rendering**: Open diff for artifact with >50 modified files
   - Verify: File list sidebar loads immediately without parsing delay
   - Verify: Clicking a file to view unified diff loads in <200ms

4. **Modal reopen**: Close and reopen sync modal quickly
   - Verify: Data reuses cache (no duplicate network calls in DevTools → Network)

---

## Rollback Plan

### If Behavior Regression Detected

**Step 1: Identify scope** (backend, frontend, or both)
- Backend issues: error rate spikes on `/diff` or `/deployments` endpoints
- Frontend issues: JavaScript errors in Sentry or slow render times

**Step 2: Backend Rollback (If Needed)**

```bash
# Rollback API service to previous version
kubectl rollout undo deployment/skillmeat-api -n production

# Verify API health
curl -s https://api.skillmeat.local/health | jq .
# Or via dashboard: confirm error rate <0.5% within 30 sec
```

**Step 3: Frontend Rollback (If Needed)**

```bash
# Revert CDN to previous build (redeploy from Git tag)
gh workflow run deploy-frontend.yml -f ref=v0.3.0-rc1 -f environment=production

# CDN cache clears in <1 min; verify in browser DevTools → Application → Cache Storage
```

**Step 4: Resume**

- **If cache stale data issue**: Disable cache via config `CACHE_DIFF_ENABLED=false`, redeploy backend
- **If contract drift**: Verify frontend and backend versions match feature flags (see Phase 5 docs)
- **If perf degradation**: Check for unintended eager loading in sync-tab (revert Phase 5 query changes only)

### Reversibility Matrix

| Component | Reversible | Notes |
|-----------|-----------|-------|
| Backend cache layer | Yes | Disable via config flag, no code rollback needed |
| Summary-first diff mode | Yes | Default behavior unchanged; old clients still work |
| Frontend query gating | Yes | Revert to eager loading (Phase 5 changes only) |
| Lazy diff rendering | Yes | Revert to eager parse (Phase 6 changes only) |

**Bottom line**: All changes are additive and feature-flagged. No irreversible data migrations or schema changes.

---

## Known Risks and Mitigations

| Risk | Severity | Mitigation | Owner |
|------|----------|-----------|-------|
| **Cache serves stale diff** | Medium | Short TTL (30s), explicit invalidation on deploy/sync, fallback to uncached path on stale detection | Backend |
| **Contract drift during migration** | Medium | Keep both legacy + summary-first modes active, contract tests cover both, frontend and backend deployed together | Ops |
| **Large diffs timeout during parse** | Medium | Guardrail: diffs >50 files paginated, large files behind load button, streaming response for very large payloads (Phase 6) | Frontend |
| **Cache key collision across projects** | Low | Cache keys include artifact_id + project_id + collection_id; tested in P4 suite | Backend |
| **Upstream rate limit (GitHub)** | Low | Cache reduces upstream calls 60-80%, short-lived; fallback to uncached path if cache unavailable | Backend |
| **Regression in sync correctness** | Low | Full regression suite in P7; all existing semantics unchanged, only performance optimized | QA |

### How to Escalate

- **For perf anomalies** → Grep logs (watchpoints above), check cache hit rate, verify no upstream timeouts
- **For behavior bugs** → Check backend error logs for contract violations, frontend console for parse errors
- **For data consistency** → Run `skillmeat sync --verify` locally; if collection/project state diverged, rebuild cache via `POST /cache/refresh`

---

## Success Criteria (2-Hour Window)

- [x] All backend tests green (pre-deploy)
- [x] All frontend tests green (pre-deploy)
- [x] Error rates on `/diff` and `/deployments` remain <0.5%
- [x] p95 latency on `/diff` improved vs baseline (target: <200ms)
- [x] Cache hit rate on repeated diffs >60%
- [x] No new JavaScript errors in Sentry
- [x] Sync modal load time improved vs baseline (target: <500ms cold start)
- [x] Manual verification pass (4 scenarios above)

**If all 8 criteria met**: Rollout complete, lock in 100% traffic.

**If any criterion failed**: Execute rollback plan (see above), document incident, re-review changes before retry.
