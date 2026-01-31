---
title: "Implementation Plan: API Rate Limiting Redesign"
description: "Replace token bucket with burst detection for abuse/loop prevention"
audience: [ai-agents, developers]
tags: [implementation, api, rate-limiting, performance, middleware]
created: 2025-01-31
updated: 2025-01-31
category: "enhancements"
status: draft
related:
  - /skillmeat/api/middleware/rate_limit.py
  - /tests/api/test_middleware/test_rate_limit.py
---

# Implementation Plan: API Rate Limiting Redesign

**Problem:** Current token bucket rate limiting (100 req/hr) triggers during normal web UI usage. Need abuse detection that won't interfere with human interaction.

**Solution:** Replace slow token bucket with sliding window burst detection focused on identifying runaway loops/automation.

**Total Effort:** ~8 story points

**Phases:** 2

---

## Phase Overview

| Phase | Title | Effort | Key Deliverables |
|-------|-------|--------|------------------|
| 1 | Core Burst Detection | 5 pts | Sliding window tracker, request fingerprinting |
| 2 | Integration & Testing | 3 pts | Update middleware, test suite, migration path |

---

## Phase 1: Core Burst Detection

**Duration:** 1-2 days
**Assigned Subagent(s):** python-backend-engineer

### Objective

Build sliding window burst detection system that identifies abuse patterns (rapid identical requests) without throttling normal usage.

### Design Principles

**Human-Friendly**:
- Very short detection window (5-10 seconds)
- High burst threshold (20+ requests in window)
- Quick reset after triggering (5-10 seconds of quiet)

**Abuse Detection**:
- Request fingerprinting (endpoint + method + key params)
- Same fingerprint appearing 20+ times in 10 seconds = loop
- Different endpoints = normal browsing (not flagged)

### Tasks

| ID | Task | Description | Acceptance Criteria | Est |
|----|------|-------------|-------------------|-----|
| RL-001 | Create RequestFingerprint | Hash function for (endpoint, method, params) | Fingerprint uniquely identifies request shape | 1 |
| RL-002 | Implement SlidingWindowTracker | Track requests in last N seconds per IP | Window slides, old requests drop off | 2 |
| RL-003 | Add BurstDetector | Detect same fingerprint exceeding threshold | Returns True when 20+ identical in 10s | 1 |
| RL-004 | Implement QuickReset | Clear block after quiet period | Block expires after 5-10s of no requests | 1 |

### Data Structures

```python
@dataclass
class RequestFingerprint:
    """Unique identifier for request shape."""
    endpoint: str
    method: str
    param_hash: str  # Hash of sorted query/body params

    def __hash__(self) -> int:
        return hash((self.endpoint, self.method, self.param_hash))

@dataclass
class RequestRecord:
    """Single request in sliding window."""
    timestamp: float
    fingerprint: RequestFingerprint
    ip: str

class SlidingWindowTracker:
    """Track requests in sliding time window per IP."""

    def __init__(self, window_seconds: int = 10):
        self.window_seconds = window_seconds
        # IP -> list of RequestRecords
        self.requests: Dict[str, List[RequestRecord]] = defaultdict(list)
        # IP -> blocked_until timestamp
        self.blocks: Dict[str, float] = {}

    def add_request(self, ip: str, fingerprint: RequestFingerprint) -> None:
        """Add request to tracking window."""
        now = time.time()

        # Clean old requests (outside window)
        self.requests[ip] = [
            r for r in self.requests[ip]
            if now - r.timestamp < self.window_seconds
        ]

        # Add new request
        self.requests[ip].append(
            RequestRecord(timestamp=now, fingerprint=fingerprint, ip=ip)
        )

    def detect_burst(self, ip: str, threshold: int = 20) -> bool:
        """Check if IP exceeds burst threshold."""
        # Count requests by fingerprint
        fingerprint_counts = defaultdict(int)
        for record in self.requests[ip]:
            fingerprint_counts[record.fingerprint] += 1

        # Check if any fingerprint exceeds threshold
        for count in fingerprint_counts.values():
            if count >= threshold:
                return True

        return False

    def is_blocked(self, ip: str) -> bool:
        """Check if IP is currently blocked."""
        if ip not in self.blocks:
            return False

        # Check if block expired
        if time.time() > self.blocks[ip]:
            del self.blocks[ip]
            return False

        return True

    def block_ip(self, ip: str, duration: int = 10) -> None:
        """Block IP for duration seconds."""
        self.blocks[ip] = time.time() + duration
```

### Key Files

**Create:**
- `skillmeat/api/middleware/burst_detection.py` (new burst detection logic)

**Modify:**
- None yet (Phase 2)

### Success Criteria
- [ ] RequestFingerprint correctly identifies request shape
- [ ] SlidingWindowTracker maintains accurate sliding window
- [ ] BurstDetector triggers on 20+ identical requests in 10s
- [ ] BurstDetector does NOT trigger on 20 different endpoints
- [ ] Block expires after 10 seconds of quiet
- [ ] Unit tests pass for all components

---

## Phase 2: Integration & Testing

**Duration:** 1 day
**Assigned Subagent(s):** python-backend-engineer

### Objective

Replace token bucket in RateLimitMiddleware with burst detection system and update tests.

### Migration Strategy

**Backward Compatible**:
- Keep existing RateLimitMiddleware interface
- Replace internal implementation
- Maintain excluded paths behavior
- Preserve rate limit headers (updated semantics)

**Configuration**:
```python
class BurstLimitConfig:
    """Configuration for burst detection."""
    window_seconds: int = 10         # Sliding window size
    burst_threshold: int = 20        # Requests per window
    block_duration: int = 10         # Block duration in seconds
    excluded_paths: List[str] = ["/health", "/docs", "/redoc", "/openapi.json"]
```

### Tasks

| ID | Task | Description | Acceptance Criteria | Est |
|----|------|-------------|-------------------|-----|
| RL-005 | Update RateLimitMiddleware | Replace TokenBucket with SlidingWindowTracker | Middleware uses new detection logic | 1 |
| RL-006 | Update rate limit headers | Adjust headers for burst semantics | Headers show window/threshold instead of hourly | 1 |
| RL-007 | Deprecate TokenBucket classes | Mark old classes as deprecated | Deprecation warnings in place | 0.5 |
| RL-008 | Update test suite | Rewrite tests for burst detection | All tests pass with new logic | 0.5 |

### Updated RateLimitMiddleware

```python
class RateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware for burst detection and abuse prevention."""

    def __init__(
        self,
        app,
        window_seconds: int = 10,
        burst_threshold: int = 20,
        block_duration: int = 10,
        excluded_paths: Optional[List[str]] = None,
    ):
        super().__init__(app)
        self.tracker = SlidingWindowTracker(window_seconds=window_seconds)
        self.burst_threshold = burst_threshold
        self.block_duration = block_duration
        self.excluded_paths = excluded_paths or [
            "/health", "/docs", "/redoc", "/openapi.json", "/"
        ]

        logger.info(
            f"Burst detection initialized: {burst_threshold} req/{window_seconds}s window"
        )

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with burst detection."""
        path = request.url.path

        # Check if path is excluded
        if self._is_excluded(path):
            return await call_next(request)

        # Get client IP
        client_ip = self._get_client_ip(request)

        # Check if IP is blocked
        if self.tracker.is_blocked(client_ip):
            return self._rate_limit_response(self.block_duration)

        # Create request fingerprint
        fingerprint = self._create_fingerprint(request)

        # Add request to tracker
        self.tracker.add_request(client_ip, fingerprint)

        # Check for burst
        if self.tracker.detect_burst(client_ip, self.burst_threshold):
            # Block IP
            self.tracker.block_ip(client_ip, self.block_duration)
            logger.warning(
                f"Burst detected for {client_ip} on {path} "
                f"({self.burst_threshold}+ req/{self.tracker.window_seconds}s)"
            )
            return self._rate_limit_response(self.block_duration)

        # Process request
        response = await call_next(request)
        self._add_rate_limit_headers(response, client_ip)

        return response

    def _create_fingerprint(self, request: Request) -> RequestFingerprint:
        """Create request fingerprint from request."""
        # Extract key params (query + body hash)
        query_params = sorted(request.query_params.items())
        param_hash = hashlib.md5(
            str(query_params).encode()
        ).hexdigest()[:8]

        return RequestFingerprint(
            endpoint=request.url.path,
            method=request.method,
            param_hash=param_hash,
        )

    def _add_rate_limit_headers(self, response: Response, ip: str) -> None:
        """Add burst detection headers to response."""
        requests_in_window = len(self.tracker.requests[ip])

        response.headers["X-RateLimit-Window"] = str(self.tracker.window_seconds)
        response.headers["X-RateLimit-Threshold"] = str(self.burst_threshold)
        response.headers["X-RateLimit-Current"] = str(requests_in_window)
        response.headers["X-RateLimit-Blocked"] = str(self.tracker.is_blocked(ip))
```

### Updated Response Headers

**Before (Token Bucket)**:
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 73
X-RateLimit-Reset: 1738368000
```

**After (Burst Detection)**:
```
X-RateLimit-Window: 10
X-RateLimit-Threshold: 20
X-RateLimit-Current: 5
X-RateLimit-Blocked: false
```

### Test Updates

**Remove:**
- Token bucket-specific tests (refill, time_until_refill, etc.)

**Add:**
- Sliding window accuracy tests
- Fingerprint collision tests
- Burst detection threshold tests
- Quick reset tests
- Mixed endpoint tests (should NOT trigger)

**Update:**
- Middleware integration tests (adjust thresholds)
- Header validation tests (new header names)
- Excluded paths tests (unchanged)

### Key Files

**Modify:**
- `skillmeat/api/middleware/rate_limit.py` (replace implementation)
- `tests/api/test_middleware/test_rate_limit.py` (update test suite)
- `skillmeat/api/server.py` (update RateLimitMiddleware initialization)

**Deprecate:**
- `TokenBucket` class (mark deprecated, keep for backward compat)
- `RateLimiter` class (mark deprecated)
- `RateLimitConfig` class (mark deprecated)

### Success Criteria
- [ ] RateLimitMiddleware uses SlidingWindowTracker
- [ ] Middleware initialization updated in server.py
- [ ] Rate limit headers use new semantics
- [ ] Old classes marked deprecated with warnings
- [ ] All test cases updated and passing
- [ ] Manual testing confirms normal usage doesn't trigger limits
- [ ] Manual testing confirms burst detection works (20+ identical in 10s)

---

## Testing Strategy

### Unit Tests

**Burst Detection** (`test_burst_detection.py`):
- RequestFingerprint hashing and equality
- SlidingWindowTracker sliding window accuracy
- Burst detection threshold (19 requests OK, 20 triggers)
- Block expiration (block active for 10s, clears after)
- Different fingerprints don't trigger (20 different endpoints)

**Middleware** (`test_rate_limit.py`):
- Normal requests pass through
- Burst triggers 429 response
- Excluded paths bypass detection
- Per-IP tracking (IP1 blocked doesn't affect IP2)
- Headers present and correct

### Integration Tests

**Real API** (`test_integration_rate_limit.py`):
- Search workflow (rapid different queries) doesn't trigger
- Navigation (clicking through pages) doesn't trigger
- Runaway loop (same request 25 times) triggers block
- Block clears after 10 seconds

### Manual Testing

```bash
# Normal usage (should NOT trigger)
for i in {1..30}; do
  curl http://localhost:8000/api/v1/artifacts?page=$i
done

# Runaway loop (should trigger after 20)
for i in {1..25}; do
  curl http://localhost:8000/api/v1/artifacts?page=1
done

# Wait 10 seconds, should work again
sleep 10
curl http://localhost:8000/api/v1/artifacts?page=1
```

---

## Configuration Tuning

Default values can be adjusted via environment variables:

```bash
# More aggressive (for high-traffic production)
SKILLMEAT_RATE_LIMIT_WINDOW=5
SKILLMEAT_RATE_LIMIT_THRESHOLD=15
SKILLMEAT_RATE_LIMIT_BLOCK_DURATION=30

# More lenient (for development)
SKILLMEAT_RATE_LIMIT_WINDOW=10
SKILLMEAT_RATE_LIMIT_THRESHOLD=50
SKILLMEAT_RATE_LIMIT_BLOCK_DURATION=5
```

**Recommended Defaults**:
- `window_seconds: 10` (short enough to catch loops)
- `burst_threshold: 20` (high enough for normal usage)
- `block_duration: 10` (just enough to kill loops)

---

## Risk Mitigation

| Risk | Impact | Mitigation |
|------|--------|------------|
| False positives (normal usage flagged) | High | Start with conservative threshold (20+), monitor logs |
| Memory growth (tracking all requests) | Low | Sliding window auto-cleans, add periodic cleanup |
| Fingerprint collisions | Low | Include method + params in hash, not just endpoint |
| Breaking existing integrations | Medium | Keep RateLimitMiddleware interface compatible |

---

## Rollout Plan

### Phase 1 (Development)
1. Deploy burst detection with lenient config (threshold: 50)
2. Monitor logs for any triggers during normal usage
3. Adjust threshold if needed

### Phase 2 (Production)
1. Deploy with recommended config (threshold: 20)
2. Add observability metrics (burst triggers per hour)
3. Set up alert if burst rate exceeds expected baseline

### Phase 3 (Refinement)
1. Analyze fingerprint patterns (are loops using same params?)
2. Consider endpoint-specific thresholds if needed
3. Add admin endpoint to view/clear blocks

---

## Future Enhancements

**Out of Scope for v1** (consider for future iterations):

- **Distributed tracking**: Redis-backed tracker for multi-instance deployments
- **Admin dashboard**: View current blocks, request patterns
- **Allowlisting**: Trusted IPs bypass detection
- **Endpoint-specific thresholds**: Tighter limits on expensive operations
- **Adaptive thresholds**: Learn normal patterns per IP
- **WebSocket support**: Extend detection to WebSocket connections

---

## Definition of Done

- [ ] SlidingWindowTracker implemented with sliding window logic
- [ ] RequestFingerprint correctly identifies request shape
- [ ] BurstDetector triggers on 20+ identical requests in 10 seconds
- [ ] BurstDetector does NOT trigger on varied normal usage
- [ ] RateLimitMiddleware uses new burst detection
- [ ] Rate limit headers updated to new semantics
- [ ] Old TokenBucket classes deprecated with warnings
- [ ] Test suite updated and passing (unit + integration)
- [ ] Manual testing confirms normal usage works (30+ different requests)
- [ ] Manual testing confirms burst detection works (25 identical requests)
- [ ] Documentation updated (API docs, CLAUDE.md middleware section)
- [ ] Configuration tunable via environment variables
