# SkillMeat Performance Testing

This directory contains comprehensive performance testing infrastructure for SkillMeat, including load tests, benchmarks, and SLA compliance checks.

## Overview

The performance testing suite consists of:

- **Load Testing**: Locust-based load tests simulating realistic user behavior
- **API Benchmarks**: Detailed endpoint latency measurements
- **Operation Benchmarks**: Core operation performance tests
- **Frontend Performance**: Lighthouse and Web Vitals measurements
- **SLA Compliance**: Automated checking against performance targets

## Quick Start

### Prerequisites

```bash
# Install Python dependencies
pip install -e ".[dev]"
pip install locust requests

# Install Node.js dependencies (for frontend tests)
cd skillmeat/web
pnpm install
```

### Running Tests Locally

#### 1. API Benchmarks

```bash
# Start the API server
python -m skillmeat.api.server &

# Run API benchmarks
python tests/performance/benchmark_api.py --samples 100

# With custom URL
python tests/performance/benchmark_api.py --url http://localhost:8000 --samples 50
```

#### 2. Operation Benchmarks

```bash
# Run core operation benchmarks
python tests/performance/benchmark_operations.py --iterations 5

# Export results to JSON
python tests/performance/benchmark_operations.py --output results.json
```

#### 3. Load Testing

```bash
# Start the API server
python -m skillmeat.api.server &

# Run load test (headless)
locust -f tests/performance/locustfile.py \
       --headless \
       --users 100 \
       --spawn-rate 10 \
       --run-time 5m \
       --host http://localhost:8000

# Run with web UI
locust -f tests/performance/locustfile.py --host http://localhost:8000
# Then open http://localhost:8089 in your browser
```

#### 4. SLA Compliance Check

```bash
# Check SLA compliance from existing results
python tests/performance/check_slas.py \
    --api-results benchmark_api_results.json \
    --ops-results benchmark_ops_results.json

# Run benchmarks and check SLAs
python tests/performance/check_slas.py --run-benchmarks
```

#### 5. Frontend Performance Tests

```bash
cd skillmeat/web

# Build production bundle
pnpm build

# Start server
pnpm start &

# Run Web Vitals tests
pnpm test:performance

# Run Lighthouse tests
pnpm test:lighthouse --url http://localhost:3000
```

## Test Files

### Backend Performance

- **`locustfile.py`**: Locust load testing scenarios
  - MarketplaceBrowsingUser: Simulates marketplace browsing
  - PowerUser: Heavy operations with shorter wait times
  - AdminUser: Monitoring and health checks
  - Various task sets for different user behaviors

- **`benchmark_api.py`**: API endpoint benchmarking
  - Measures mean, median, P95, P99 latency
  - Tests all major API endpoints
  - Exports results to JSON
  - Checks against SLA targets

- **`benchmark_operations.py`**: Core operation benchmarking
  - Bundle export/import
  - MCP health checks
  - Collection operations
  - Search operations

- **`check_slas.py`**: SLA compliance checker
  - Reads benchmark results
  - Compares against defined targets
  - Outputs violations and warnings
  - Exit code 1 if SLAs not met

### Frontend Performance

- **`skillmeat/web/tests/performance/lighthouse.js`**: Lighthouse audits
  - Performance score
  - Accessibility score
  - Core Web Vitals (FCP, LCP, TTI, CLS)
  - Generates HTML and JSON reports

- **`skillmeat/web/tests/performance/web-vitals.test.ts`**: Playwright Web Vitals tests
  - First Contentful Paint (FCP)
  - Largest Contentful Paint (LCP)
  - Cumulative Layout Shift (CLS)
  - First Input Delay (FID)
  - Interactive element responsiveness

### Existing Benchmarks

- **`test_benchmarks.py`**: pytest-benchmark suite for Phase 2 features
- **`test_diff_benchmarks.py`**: Diff engine performance tests
- **`test_search_benchmarks.py`**: Search operation benchmarks
- **`test_sync_benchmarks.py`**: Sync operation benchmarks

## SLA Targets

See [docs/ops/performance/sla.md](/home/user/skillmeat/docs/ops/performance/sla.md) for complete SLA definitions.

### Summary

| Component | Key Metrics | Target |
|-----------|-------------|--------|
| API Endpoints | P95 latency | <200ms (listing), <100ms (detail) |
| Bundle Operations | Mean time | <2s |
| MCP Health | Mean time | <500ms |
| Web UI FCP | First paint | <1.5s |
| Web UI LCP | Largest paint | <2.5s |
| Load Testing | Error rate | <1% @ 100 users |

## CI/CD Integration

Performance tests run automatically via GitHub Actions:

- **Weekly**: Full performance test suite (Sundays at midnight UTC)
- **On PR**: Tests run if performance-critical code is modified
- **Manual**: Workflow dispatch with test type selection

### Workflow Jobs

1. **api-benchmarks**: API endpoint performance
2. **operation-benchmarks**: Core operation performance
3. **frontend-performance**: Lighthouse and Web Vitals
4. **load-testing**: Locust load tests
5. **sla-check**: SLA compliance verification
6. **performance-report**: Weekly comprehensive report

## Interpreting Results

### API Benchmarks

```
Endpoint                                     Mean     Median   P95      P99
--------------------------------------------------------------------------------
GET /api/marketplace/listings                45.2     42.1     89.3     125.4
```

- **Mean**: Average response time
- **Median**: 50th percentile (half of requests faster)
- **P95**: 95% of requests complete within this time
- **P99**: 99% of requests complete within this time

**Good**: P95 well under SLA target
**Warning**: P95 within 20% of SLA target
**Critical**: P95 exceeds SLA target

### Load Testing

```
Type     Name                                 # reqs  # fails  Avg    Min    Max
--------------------------------------------------------------------------------
GET      /api/marketplace/listings            5000    10      45     12     523
```

- **# reqs**: Total requests made
- **# fails**: Failed requests (errors, timeouts)
- **Avg**: Average response time
- **Min/Max**: Fastest and slowest requests

**Good**: Error rate <1%, avg response time within SLA
**Warning**: Error rate 1-2%, response times approaching SLA
**Critical**: Error rate >2% or consistent SLA violations

### Lighthouse Scores

```
Performance Score:  92/100 (target: ≥90)
FCP:                1200ms (target: <1500ms)
LCP:                2100ms (target: <2500ms)
```

- **Performance Score**: Overall performance (0-100)
- **FCP**: First Contentful Paint (time to first visible content)
- **LCP**: Largest Contentful Paint (time to main content)

**Good**: All scores meet or exceed targets
**Warning**: Scores within 10% of targets
**Critical**: Scores below targets

## Troubleshooting

### API Benchmarks Failing

1. **Check server is running**: `curl http://localhost:8000/health`
2. **Verify dependencies**: `pip install -e ".[dev]" requests`
3. **Check port conflicts**: Ensure port 8000 is available
4. **Review logs**: Check server output for errors

### Load Tests Timing Out

1. **Reduce concurrent users**: Start with 10-20 users
2. **Check system resources**: Monitor CPU, memory usage
3. **Verify network**: Ensure localhost connectivity
4. **Review rate limits**: API rate limiting may affect results

### Frontend Tests Failing

1. **Build production bundle**: `pnpm build` before testing
2. **Check server is running**: `curl http://localhost:3000`
3. **Install Playwright**: `pnpm playwright:install`
4. **Verify lighthouse**: `npm install -g lighthouse chrome-launcher`

### SLA Violations

If SLAs are not met:

1. **Profile slow operations**: Use Python profilers (cProfile)
2. **Check database queries**: Enable query logging
3. **Review resource usage**: Monitor CPU, memory, I/O
4. **Optimize hot paths**: Focus on P95/P99 outliers
5. **Consider caching**: Add Redis for frequently accessed data

## Best Practices

1. **Run benchmarks locally** before pushing changes
2. **Establish baselines** for your environment
3. **Monitor trends** over time, not just point-in-time
4. **Test under realistic load** that matches production
5. **Profile before optimizing** to find actual bottlenecks
6. **Document performance changes** in PR descriptions

## Performance Optimization Tips

### Backend

- Use database indexes on frequently queried fields
- Implement caching (Redis) for hot data
- Optimize N+1 queries with batch loading
- Use async/await for I/O-bound operations
- Enable response compression (gzip/brotli)

### Frontend

- Code split at route boundaries
- Lazy load images with next/image
- Prefetch critical routes
- Minimize JavaScript bundle size
- Use React.memo for expensive components
- Implement service worker for offline caching

## Resources

- [SLA Documentation](../../docs/ops/performance/sla.md)
- [Locust Documentation](https://docs.locust.io/)
- [Lighthouse Documentation](https://developers.google.com/web/tools/lighthouse)
- [Core Web Vitals](https://web.dev/vitals/)
- [pytest-benchmark](https://pytest-benchmark.readthedocs.io/)

## Contributing

When adding performance tests:

1. Define clear SLA targets in [sla.md](../../docs/ops/performance/sla.md)
2. Add test to appropriate file (locustfile.py, benchmark_*.py)
3. Update this README with usage instructions
4. Add test to GitHub Actions workflow if needed
5. Document expected results and troubleshooting

## Support

For questions or issues with performance testing:

- Check [docs/ops/performance/sla.md](../../docs/ops/performance/sla.md) for SLA definitions
- Review GitHub Actions logs for CI failures
- Open an issue with benchmark results and system info
- Contact the SkillMeat development team
