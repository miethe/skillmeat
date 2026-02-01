---
type: context
prd: "rate-limit-redesign"
request_log: "REQ-20260128-skillmeat"
created: 2026-01-31
updated: 2026-01-31
---

# Rate Limit Redesign - Context

## Problem Statement

Current token bucket rate limiting (100 req/hr = ~1.7 req/min) triggers during normal web UI usage patterns like searching and page navigation.

## Solution Summary

Replace token bucket with **sliding window burst detection**:
- Window: 10 seconds (not hours)
- Threshold: 20+ identical requests
- Reset: 10 seconds of quiet
- Detection: Same request shape (endpoint + method + params)

## Key Design Decisions

1. **Fingerprint-based**: Only identical requests count toward threshold
2. **Short window**: 10s catches loops without penalizing normal usage
3. **Quick reset**: 10s block just kills loops, doesn't punish users
4. **IP-based**: Keep per-IP tracking (no auth-based limiting)

## Key Files

| File | Purpose |
|------|---------|
| `skillmeat/api/middleware/burst_detection.py` | New burst detection logic |
| `skillmeat/api/middleware/rate_limit.py` | Update middleware |
| `skillmeat/api/server.py` | Update initialization |
| `tests/api/test_middleware/test_rate_limit.py` | Update tests |

## Implementation Plan

`docs/project_plans/implementation_plans/enhancements/rate-limit-redesign-v1.md`

## Progress Tracking

`.claude/progress/rate-limit-redesign/all-phases-progress.md`

## Configuration Defaults

```python
window_seconds = 10      # Sliding window size
burst_threshold = 20     # Requests to trigger
block_duration = 10      # Block duration in seconds
```

## Testing Approach

Normal usage (should NOT trigger):
```bash
for i in {1..30}; do curl http://localhost:8000/api/v1/artifacts?page=$i; done
```

Runaway loop (should trigger):
```bash
for i in {1..25}; do curl http://localhost:8000/api/v1/artifacts?page=1; done
```

## Blockers & Decisions

<!-- Record blockers and decisions during implementation -->
