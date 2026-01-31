---
type: progress
prd: "rate-limit-redesign"
request_log: "REQ-20260128-skillmeat"
status: not_started
progress: 0
total_effort: 8
created: 2026-01-31
updated: 2026-01-31

phases:
  - id: 1
    name: "Core Burst Detection"
    status: pending
    effort: 5
  - id: 2
    name: "Integration & Testing"
    status: pending
    effort: 3

tasks:
  # Phase 1: Core Burst Detection
  - id: "RL-001"
    name: "Create RequestFingerprint"
    phase: 1
    status: pending
    assigned_to: ["python-backend-engineer"]
    model: "sonnet"
    effort: 1
    dependencies: []
    acceptance: "Fingerprint uniquely identifies request shape (endpoint + method + params)"

  - id: "RL-002"
    name: "Implement SlidingWindowTracker"
    phase: 1
    status: pending
    assigned_to: ["python-backend-engineer"]
    model: "opus"
    effort: 2
    dependencies: ["RL-001"]
    acceptance: "Sliding window tracks requests, old entries drop off after window_seconds"

  - id: "RL-003"
    name: "Add BurstDetector"
    phase: 1
    status: pending
    assigned_to: ["python-backend-engineer"]
    model: "sonnet"
    effort: 1
    dependencies: ["RL-001", "RL-002"]
    acceptance: "Returns True when 20+ identical fingerprints in 10s window"

  - id: "RL-004"
    name: "Implement QuickReset"
    phase: 1
    status: pending
    assigned_to: ["python-backend-engineer"]
    model: "sonnet"
    effort: 1
    dependencies: ["RL-002"]
    acceptance: "Block expires after 10s of no requests from blocked IP"

  # Phase 2: Integration & Testing
  - id: "RL-005"
    name: "Update RateLimitMiddleware"
    phase: 2
    status: pending
    assigned_to: ["python-backend-engineer"]
    model: "opus"
    effort: 1
    dependencies: ["RL-001", "RL-002", "RL-003", "RL-004"]
    acceptance: "Middleware uses SlidingWindowTracker instead of TokenBucket"

  - id: "RL-006"
    name: "Update rate limit headers"
    phase: 2
    status: pending
    assigned_to: ["python-backend-engineer"]
    model: "haiku"
    effort: 1
    dependencies: ["RL-005"]
    acceptance: "Headers show X-RateLimit-Window, Threshold, Current, Blocked"

  - id: "RL-007"
    name: "Deprecate TokenBucket classes"
    phase: 2
    status: pending
    assigned_to: ["python-backend-engineer"]
    model: "haiku"
    effort: 0.5
    dependencies: ["RL-005"]
    acceptance: "TokenBucket, RateLimiter, RateLimitConfig marked deprecated with warnings"

  - id: "RL-008"
    name: "Update test suite"
    phase: 2
    status: pending
    assigned_to: ["python-backend-engineer"]
    model: "sonnet"
    effort: 0.5
    dependencies: ["RL-005", "RL-006"]
    acceptance: "All tests updated for burst detection, passing"

parallelization:
  phase_1_batch_1: ["RL-001"]
  phase_1_batch_2: ["RL-002", "RL-004"]
  phase_1_batch_3: ["RL-003"]
  phase_2_batch_1: ["RL-005"]
  phase_2_batch_2: ["RL-006", "RL-007", "RL-008"]
---

# Rate Limit Redesign - Progress Tracking

## Overview

Replace token bucket rate limiting with burst detection to prevent interference with normal usage while still catching abuse/loops.

**Problem**: 100 req/hr limit triggers during normal browsing
**Solution**: Sliding window (10s) + fingerprinting + high threshold (20 req)

## Quick Reference

### CLI Status Updates

```bash
# Mark task complete
python .claude/skills/artifact-tracking/scripts/update-status.py \
  -f .claude/progress/rate-limit-redesign/all-phases-progress.md \
  -t RL-001 -s completed

# Batch update
python .claude/skills/artifact-tracking/scripts/update-batch.py \
  -f .claude/progress/rate-limit-redesign/all-phases-progress.md \
  --updates "RL-001:completed,RL-002:completed"
```

### Orchestration Commands

```python
# Phase 1 Batch 1 - RequestFingerprint
Task("python-backend-engineer", """
Create RequestFingerprint dataclass in skillmeat/api/middleware/burst_detection.py

Requirements:
- Hash of (endpoint, method, param_hash)
- param_hash = MD5 of sorted query params (first 8 chars)
- Implement __hash__ and __eq__ for use as dict key

See implementation plan: docs/project_plans/implementation_plans/enhancements/rate-limit-redesign-v1.md
""", model="sonnet")

# Phase 1 Batch 2 - SlidingWindowTracker (parallel)
Task("python-backend-engineer", """
Implement SlidingWindowTracker in skillmeat/api/middleware/burst_detection.py

Requirements:
- Track requests per IP in sliding window (default 10s)
- Auto-clean old requests on each add_request call
- Block tracking with block_ip() and is_blocked()
- detect_burst() checks if any fingerprint exceeds threshold

See implementation plan: docs/project_plans/implementation_plans/enhancements/rate-limit-redesign-v1.md
""", model="opus")

# Phase 2 Batch 1 - Update Middleware
Task("python-backend-engineer", """
Update RateLimitMiddleware in skillmeat/api/middleware/rate_limit.py

Requirements:
- Replace TokenBucket with SlidingWindowTracker
- Create fingerprint per request
- Check for burst, block IP if detected
- Keep excluded paths behavior
- Update server.py initialization

See implementation plan: docs/project_plans/implementation_plans/enhancements/rate-limit-redesign-v1.md
""", model="opus")
```

## Phase 1: Core Burst Detection

| Task | Status | Assigned | Effort |
|------|--------|----------|--------|
| RL-001: Create RequestFingerprint | pending | python-backend-engineer | 1 |
| RL-002: Implement SlidingWindowTracker | pending | python-backend-engineer | 2 |
| RL-003: Add BurstDetector | pending | python-backend-engineer | 1 |
| RL-004: Implement QuickReset | pending | python-backend-engineer | 1 |

**Key File**: `skillmeat/api/middleware/burst_detection.py` (new)

## Phase 2: Integration & Testing

| Task | Status | Assigned | Effort |
|------|--------|----------|--------|
| RL-005: Update RateLimitMiddleware | pending | python-backend-engineer | 1 |
| RL-006: Update rate limit headers | pending | python-backend-engineer | 1 |
| RL-007: Deprecate TokenBucket classes | pending | python-backend-engineer | 0.5 |
| RL-008: Update test suite | pending | python-backend-engineer | 0.5 |

**Key Files**:
- `skillmeat/api/middleware/rate_limit.py` (modify)
- `skillmeat/api/server.py` (modify)
- `tests/api/test_middleware/test_rate_limit.py` (modify)

## Success Criteria

- [ ] Normal usage (30+ varied requests) does NOT trigger limits
- [ ] Runaway loops (20+ identical requests in 10s) DO trigger
- [ ] Block clears after 10s of quiet
- [ ] All tests passing
- [ ] Old classes deprecated with warnings

## Notes

<!-- Agent notes go here during implementation -->
