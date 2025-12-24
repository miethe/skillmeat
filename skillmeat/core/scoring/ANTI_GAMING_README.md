# Anti-Gaming Protection Module

Protects artifact rating system from score manipulation through rate limiting and anomaly detection.

## Quick Start

```python
from skillmeat.core.scoring import AntiGamingGuard

guard = AntiGamingGuard()

# Before accepting a rating
allowed, reason = guard.can_submit_rating("user123", "skill:canvas")
if not allowed:
    raise RateLimitError(reason)

# After successful rating
guard.record_rating("user123", "skill:canvas", 5)
```

## Components

### RateLimiter
Enforces submission rate limits per user and artifact.

**Defaults**:
- 5 ratings per user per day
- 1 rating per artifact (24-hour cooldown)

### AnomalyDetector
Detects suspicious rating patterns.

**Detection**:
- Burst: >10 ratings in 1 hour
- Pattern: Uniform ratings (all 5-stars)
- Suspicion scoring: 0-1 scale

### AntiGamingGuard
Unified interface combining all protection mechanisms.

**Features**:
- All-in-one protection checks
- Violation tracking and querying
- Configurable thresholds

## Configuration

```python
from skillmeat.core.scoring import RateLimiter, RateLimitConfig, AnomalyDetector

# Custom rate limits
config = RateLimitConfig(
    max_ratings_per_day=10,
    max_ratings_per_artifact=2,
    cooldown_hours=12,
)

# Custom anomaly thresholds
detector = AnomalyDetector(
    burst_threshold=15,
    burst_window_minutes=60,
    pattern_threshold=0.9,
)

guard = AntiGamingGuard(
    rate_limiter=RateLimiter(config=config),
    anomaly_detector=detector,
)
```

## API Integration

```python
from fastapi import HTTPException
from skillmeat.core.scoring import AntiGamingGuard

guard = AntiGamingGuard()

@router.post("/ratings")
async def submit_rating(artifact_id: str, rating: int, user_id: str):
    # Check protections
    allowed, reason = guard.can_submit_rating(user_id, artifact_id)
    if not allowed:
        raise HTTPException(status_code=429, detail=reason)

    # Save rating...

    # Track for anti-gaming
    guard.record_rating(user_id, artifact_id, rating)
    return {"success": True}
```

## Monitoring

```python
from datetime import datetime, timedelta

# Get violations for user
violations = guard.get_violations(user_id="user123")

# Get violations for artifact
violations = guard.get_violations(artifact_id="skill:canvas")

# Get recent violations (last 24h)
since = datetime.now() - timedelta(hours=24)
violations = guard.get_violations(since=since)
```

## Design Principles

1. **Conservative Thresholds**: Avoid false positives on legitimate use
2. **Graceful Degradation**: Pattern anomalies logged but don't block users
3. **Monitoring First**: Comprehensive violation tracking for analysis
4. **Type Safe**: Full type hints throughout

## Testing

```bash
# Run tests
pytest tests/core/scoring/test_anti_gaming.py -v

# Check coverage
pytest tests/core/scoring/test_anti_gaming.py --cov=skillmeat.core.scoring.anti_gaming
```

**Coverage**: 98.5%
**Tests**: 24 comprehensive test cases

## Documentation

- **Usage Guide**: `ANTI_GAMING_USAGE.md` - Comprehensive examples and patterns
- **Module Source**: `anti_gaming.py` - Well-documented implementation
- **Tests**: `test_anti_gaming.py` - Test cases serve as examples

## Performance

- **Memory**: In-memory tracking with automatic cleanup
- **Time**: All checks <1ms typically
- **Scale**: Suitable for current usage; Redis-backed for high traffic

## Limitations

- **Not Thread-Safe**: Use with single-threaded access or add locking
- **In-Memory Only**: Use Redis for distributed systems
- **No Persistence**: Violations cleared on restart

## Future Enhancements

- Persistent storage (database/Redis)
- IP-based tracking
- Machine learning-based detection
- Real-time violation alerts
- Admin monitoring dashboard
