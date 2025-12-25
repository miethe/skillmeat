# Anti-Gaming Protection Usage Guide

## Overview

The anti-gaming module protects the artifact rating system from score manipulation through:
- **Rate limiting**: Enforce submission limits per user and artifact
- **Burst detection**: Catch rapid-fire rating attempts
- **Pattern analysis**: Detect suspicious rating patterns

## Quick Start

```python
from skillmeat.core.scoring import AntiGamingGuard

# Initialize guard (uses default configuration)
guard = AntiGamingGuard()

# Before accepting a rating
user_id = "user123"
artifact_id = "skill:canvas-design"

allowed, reason = guard.can_submit_rating(user_id, artifact_id)
if not allowed:
    # Reject rating submission
    raise RateLimitError(reason)

# After successful rating
rating_value = 5
guard.record_rating(user_id, artifact_id, rating_value)
```

## Configuration

### Default Limits

```python
RateLimitConfig(
    max_ratings_per_day=5,      # 5 ratings per user per day
    max_ratings_per_artifact=1,  # Can only rate same artifact once
    cooldown_hours=24,           # 24 hours before re-rating
)
```

### Custom Configuration

```python
from skillmeat.core.scoring import RateLimiter, RateLimitConfig

# Custom rate limits
custom_config = RateLimitConfig(
    max_ratings_per_day=10,
    max_ratings_per_artifact=2,
    cooldown_hours=12,
)

limiter = RateLimiter(config=custom_config)
guard = AntiGamingGuard(rate_limiter=limiter)
```

### Anomaly Detection Tuning

```python
from skillmeat.core.scoring import AnomalyDetector

# Custom anomaly thresholds
detector = AnomalyDetector(
    burst_threshold=15,           # Allow up to 15 ratings/hour
    burst_window_minutes=60,      # 1-hour window
    pattern_threshold=0.9,        # Higher threshold = fewer false positives
)

guard = AntiGamingGuard(anomaly_detector=detector)
```

## Integration Example

### Rating Submission API

```python
from fastapi import APIRouter, HTTPException
from skillmeat.core.scoring import AntiGamingGuard

router = APIRouter()
guard = AntiGamingGuard()

@router.post("/ratings")
async def submit_rating(
    artifact_id: str,
    rating: int,
    user_id: str,  # From auth token
):
    # Check anti-gaming protections
    allowed, reason = guard.can_submit_rating(user_id, artifact_id)
    if not allowed:
        raise HTTPException(status_code=429, detail=reason)

    # Validate rating value
    if not 1 <= rating <= 5:
        raise HTTPException(status_code=400, detail="Rating must be 1-5")

    # Save rating to database
    # ... database logic ...

    # Record for anti-gaming tracking
    guard.record_rating(user_id, artifact_id, rating)

    return {"success": True}
```

### Checking Remaining Quota

```python
@router.get("/ratings/quota")
async def get_quota(user_id: str):
    remaining = guard.rate_limiter.get_remaining_ratings(user_id)
    return {
        "remaining_ratings": remaining,
        "max_per_day": guard.rate_limiter.config.max_ratings_per_day,
    }
```

## Monitoring Violations

### Query Violations

```python
from datetime import datetime, timedelta

# Get all violations for a user
violations = guard.get_violations(user_id="user123")

# Get violations for an artifact
violations = guard.get_violations(artifact_id="skill:canvas-design")

# Get recent violations (last 24 hours)
since = datetime.now() - timedelta(hours=24)
violations = guard.get_violations(since=since)

# Process violations
for v in violations:
    print(f"{v.violation_type.value}: {v.details}")
```

### Violation Types

```python
from skillmeat.core.scoring import ViolationType

# Three types of violations:
ViolationType.RATE_LIMIT       # User exceeded daily/artifact limit
ViolationType.ANOMALY_BURST    # Too many ratings in short time
ViolationType.ANOMALY_PATTERN  # Suspicious patterns on artifact
```

## Anti-Gaming Checks

### 1. Rate Limiting

**Per-Day Limit**: Maximum 5 ratings per user per day (default)
- Resets every 24 hours
- Prevents single user from flooding system

**Per-Artifact Limit**: Can only rate same artifact once (default)
- Enforces cooldown period (24 hours)
- Prevents score manipulation through repeated ratings

### 2. Burst Detection

**Threshold**: Maximum 10 ratings in 1 hour (default)
- Catches bot-like rapid submissions
- Blocks suspicious burst activity

### 3. Pattern Analysis

**Uniformity**: All ratings same value (e.g., all 5-stars)
- High suspicion score when diversity is low
- Logged but doesn't block users (artifact-level signal)

**Extremity**: Ratings clustered at extremes (1 or 5)
- Combined with uniformity to calculate suspicion score
- Threshold: 0.8 (80% suspicion to flag)

## Best Practices

### 1. Conservative Thresholds

Default configuration is designed to avoid false positives:
- Legitimate power users should never be blocked
- Rate limits allow reasonable daily activity
- Pattern detection requires multiple data points

### 2. Logging

Always log violations for monitoring:

```python
import logging

logger = logging.getLogger(__name__)

allowed, reason = guard.can_submit_rating(user_id, artifact_id)
if not allowed:
    logger.warning(f"Rating blocked for {user_id}: {reason}")
    raise HTTPException(status_code=429, detail=reason)
```

### 3. User Feedback

Provide clear error messages:

```python
# Good: Specific reason
"Rate limit exceeded: maximum 5 ratings per day"

# Good: Actionable information
"Cooldown active: you can re-rate this artifact in 12.5 hours"

# Bad: Generic error
"Request blocked"
```

### 4. Monitoring Dashboard

Track violations over time:
- Daily violation counts
- Top violators (users with most violations)
- Artifacts with pattern anomalies
- Burst attack attempts

## Testing

### Unit Tests

```python
def test_legitimate_rating_allowed():
    guard = AntiGamingGuard()
    allowed, reason = guard.can_submit_rating("user1", "skill:a")
    assert allowed is True
    assert reason is None
```

### Integration Tests

```python
def test_full_rating_flow():
    guard = AntiGamingGuard()

    # Submit rating
    allowed, _ = guard.can_submit_rating("user1", "skill:a")
    assert allowed is True
    guard.record_rating("user1", "skill:a", 5)

    # Check quota consumed
    remaining = guard.rate_limiter.get_remaining_ratings("user1")
    assert remaining == 4
```

### Load Tests

Simulate power users to verify no false positives:

```python
def test_power_user_not_blocked():
    guard = AntiGamingGuard()

    # Rate 5 different artifacts (daily limit)
    for i in range(5):
        allowed, reason = guard.can_submit_rating("poweruser", f"skill:{i}")
        assert allowed is True, f"Should allow rating {i+1}/5: {reason}"
        guard.record_rating("poweruser", f"skill:{i}", 4)
```

## Performance Considerations

### Memory Usage

- In-memory tracking suitable for current scale
- Cleanup old records automatically
- Retention: 24 hours for burst detection, cooldown period for rate limits

### Scalability

For high-traffic scenarios, consider:
- Redis-backed storage for distributed systems
- Periodic cleanup of old violations
- Rate limit sharding by user ID

### Thread Safety

Current implementation is **not thread-safe**. For concurrent access:
- Use single-threaded API server
- Add locking mechanisms
- Use Redis for distributed rate limiting

## Troubleshooting

### False Positives

If legitimate users are blocked:
1. Review violation logs
2. Adjust thresholds (increase limits)
3. Check for bulk operations (imports, migrations)

### Gaming Attempts

If violations spike:
1. Review pattern anomalies by artifact
2. Check for coordinated attacks (same IP, timing)
3. Lower thresholds temporarily
4. Implement IP-based blocking (outside this module)

### Performance Issues

If anti-gaming checks are slow:
1. Profile violation query performance
2. Limit violation history retention
3. Consider caching remaining quotas
