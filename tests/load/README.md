# Load Testing

Load tests for SkillMeat cache system using Locust.

## Overview

This directory contains load tests to verify the cache system can handle
concurrent access patterns from multiple users (CLI + web UI simultaneously).

## Setup

Install Locust (not included in main dependencies):

```bash
pip install locust
```

Or with uv:

```bash
uv pip install locust
```

## Running Load Tests

### 1. Start the API Server

```bash
skillmeat web dev --api-only
```

The API should be running on http://localhost:8000.

### 2. Run the Load Test

```bash
cd /Users/miethe/dev/homelab/development/skillmeat
locust -f tests/load/locustfile.py --host http://localhost:8000
```

### 3. Control the Test

Open your browser to http://localhost:8089

You'll see the Locust web interface where you can:
- Set number of users to simulate
- Set spawn rate (users added per second)
- Start/stop the test
- View real-time statistics and charts

## Test Scenarios

### Normal Load Test (Default)

Uses `CacheLoadTest` class with realistic usage patterns:

- **Status checks**: 50% of requests (weight: 5)
- **Project listings**: 30% of requests (weight: 3)
- **Artifact searches**: 20% of requests (weight: 2)
- **Cache refresh**: 10% of requests (weight: 1)
- **Wait time**: 100-500ms between requests

**Recommended parameters:**
- Users: 10-20
- Spawn rate: 2 users/second
- Duration: 30+ seconds

### Stress Test

Uses `StressTest` class to find breaking points:

```bash
locust -f tests/load/locustfile.py --host http://localhost:8000 StressTest
```

- **Minimal wait times**: 10-50ms between requests
- **Heavy status checks**: 10x weight
- **Rapid project listings**: 5x weight
- **Rapid refresh**: 1x weight

**Recommended parameters:**
- Users: Start with 50, increase gradually
- Spawn rate: 5 users/second
- Monitor for errors and response time degradation

## Expected Results

### Performance Benchmarks

Under normal load (10-20 users):
- All endpoints should respond within **200ms**
- 95th percentile should be under **500ms**
- No database lock errors
- Cache hit rate should improve over time

Under stress (50+ users):
- Response times may increase but should remain under **1 second**
- No errors or crashes
- System should gracefully handle load

### Key Metrics to Monitor

1. **Response Time**: Should remain consistent as load increases
2. **Requests Per Second (RPS)**: Should scale linearly with users
3. **Failure Rate**: Should be 0% under normal load, <1% under stress
4. **Cache Hit Rate**: Should increase as test runs (cache warming)

## Troubleshooting

### "Connection refused" errors

The API server is not running. Start it with:
```bash
skillmeat web dev --api-only
```

### "Database is locked" errors

This indicates SQLite WAL mode is not working correctly.
Check that:
- Database directory has write permissions
- WAL mode is enabled in cache initialization
- Multiple processes aren't using incompatible locking

### High response times

If response times exceed 1 second under normal load:
- Check if cache is being populated correctly
- Verify database indexes are in place
- Monitor system resources (CPU, memory, disk I/O)

## Headless Mode

For CI/CD or automated testing, run without the web UI:

```bash
locust -f tests/load/locustfile.py \
    --host http://localhost:8000 \
    --users 20 \
    --spawn-rate 2 \
    --run-time 60s \
    --headless \
    --html results.html
```

This runs the test for 60 seconds with 20 users and generates an HTML report.

## Advanced Usage

### Custom Scenarios

Edit `locustfile.py` to add custom test scenarios:

```python
@task(3)
def my_custom_test(self):
    """Custom test scenario."""
    self.client.get("/api/v1/cache/my-endpoint")
```

### Distributed Load Testing

For very high load, run Locust in distributed mode:

```bash
# Start master
locust -f tests/load/locustfile.py --master

# Start workers (run on multiple machines)
locust -f tests/load/locustfile.py --worker --master-host=<master-ip>
```

## References

- [Locust Documentation](https://docs.locust.io/)
- [SkillMeat Cache System](../../skillmeat/cache/README.md)
- [API Documentation](../../api/README.md)
