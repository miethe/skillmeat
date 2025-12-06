# Performance Testing Guide

Performance benchmarks for the Discovery & Import Enhancement feature.

---

## Quick Start

### Run All Tests

```bash
# Run all performance tests (benchmark + manual)
pytest skillmeat/api/tests/test_discovery_performance.py -v
```

### Run Specific Test Suites

```bash
# Benchmark tests only (detailed stats)
pytest skillmeat/api/tests/test_discovery_performance.py::TestDiscoveryPerformance -v --benchmark-only

# Manual tests only (quick validation)
pytest skillmeat/api/tests/test_discovery_performance.py::TestDiscoveryPerformanceManual -v -s
```

---

## Test Suites

### TestDiscoveryPerformance

Comprehensive benchmark tests using pytest-benchmark for statistical analysis.

**Tests**:
- `test_benchmark_empty_project` - Empty project baseline
- `test_benchmark_large_collection` - 500 artifacts in collection
- `test_benchmark_large_project` - 200 artifacts in project
- `test_benchmark_combined_collection_and_project` - Combined scenario
- `test_benchmark_skip_preference_overhead` - Skip filtering performance
- `test_memory_usage_large_collection` - Memory profiling (requires psutil)

**Features**:
- Multiple rounds for statistical significance
- Min/Max/Mean/Median/StdDev metrics
- Outlier detection
- Operations per second (OPS)

### TestDiscoveryPerformanceManual

Quick manual tests using `time.perf_counter()` for CI/CD environments.

**Tests**:
- `test_manual_empty_project_performance`
- `test_manual_large_collection_performance`
- `test_manual_large_project_performance`
- `test_manual_skip_preference_overhead`

**Features**:
- Single-run timing
- Printed results to stdout
- Fast execution (<2s total)

---

## Performance Targets

| Scenario | Target | Actual |
|----------|--------|--------|
| Empty project | <1s | 0.17ms |
| Large collection (500) | <2s | 290.09ms |
| Large project (200) | <2s | 73.18ms |
| Combined (500+200) | <2s | 205.81ms |
| Skip overhead (50 entries) | <100ms | 119.34ms |

---

## Test Fixtures

### empty_project
- Empty .claude/ directory
- No artifacts
- Baseline measurement

### large_collection
- 500 artifacts in collection/artifacts/
- 300 skills, 100 commands, 50 agents, 30 hooks, 20 mcps
- Simulates large user collection

### large_project
- 200 artifacts in project/.claude/
- 120 skills, 40 commands, 25 agents, 10 hooks, 5 mcps
- Simulates active project

### project_with_skip_prefs
- 100 artifacts in project
- 50 skip preferences configured
- Tests skip filtering overhead

---

## Advanced Usage

### Benchmark Comparison

```bash
# Save baseline benchmark
pytest skillmeat/api/tests/test_discovery_performance.py::TestDiscoveryPerformance --benchmark-autosave --benchmark-save=baseline

# Compare against baseline
pytest skillmeat/api/tests/test_discovery_performance.py::TestDiscoveryPerformance --benchmark-compare=baseline

# Fail if performance regresses >20%
pytest skillmeat/api/tests/test_discovery_performance.py::TestDiscoveryPerformance --benchmark-compare=baseline --benchmark-compare-fail=mean:20%
```

### Generate Histogram

```bash
# Generate performance histogram (requires matplotlib)
pytest skillmeat/api/tests/test_discovery_performance.py::TestDiscoveryPerformance --benchmark-histogram
```

### Custom Benchmark Options

```bash
# More rounds for better statistics
pytest skillmeat/api/tests/test_discovery_performance.py::TestDiscoveryPerformance --benchmark-min-rounds=10

# Disable warmup
pytest skillmeat/api/tests/test_discovery_performance.py::TestDiscoveryPerformance --benchmark-warmup=off

# Set timeout
pytest skillmeat/api/tests/test_discovery_performance.py::TestDiscoveryPerformance --benchmark-max-time=5.0
```

---

## CI/CD Integration

### GitHub Actions

```yaml
name: Performance Tests

on: [push, pull_request]

jobs:
  performance:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.12'
      - name: Install dependencies
        run: |
          pip install -e ".[dev]"
      - name: Run performance tests
        run: |
          pytest skillmeat/api/tests/test_discovery_performance.py \
            --benchmark-only \
            --benchmark-json=benchmark.json
      - name: Upload results
        uses: benchmark-action/github-action-benchmark@v1
        with:
          tool: 'pytest'
          output-file-path: benchmark.json
```

### Pre-commit Hook

```bash
# .git/hooks/pre-commit
#!/bin/bash
pytest skillmeat/api/tests/test_discovery_performance.py::TestDiscoveryPerformanceManual -q
if [ $? -ne 0 ]; then
  echo "Performance regression detected!"
  exit 1
fi
```

---

## Troubleshooting

### Tests Running Slowly

If tests take longer than expected:

1. Check disk I/O (use SSD for temp directories)
2. Close resource-heavy applications
3. Run with `--benchmark-disable-gc` for more consistent results
4. Use `--benchmark-warmup=off` to skip warmup rounds

### Memory Test Skipped

If `test_memory_usage_large_collection` is skipped:

```bash
# Install psutil
pip install psutil

# Re-run memory test
pytest skillmeat/api/tests/test_discovery_performance.py::TestDiscoveryPerformance::test_memory_usage_large_collection -v
```

### Benchmark Results Vary

Benchmark variance is normal. To reduce:

1. Close background applications
2. Disable CPU throttling
3. Run multiple times and average results
4. Increase `--benchmark-min-rounds`

---

## Performance Reports

Generated reports in this directory:

1. **PERFORMANCE_REPORT.md** - Detailed benchmark results with analysis
2. **PERFORMANCE_SUMMARY.md** - Executive summary and production readiness
3. **README_PERFORMANCE.md** - This guide

---

## Dependencies

### Required
- pytest >= 7.0.0
- pytest-benchmark >= 4.0.0

### Optional
- psutil >= 5.0.0 (for memory profiling)
- matplotlib >= 3.0.0 (for histograms)

---

## Related Documentation

- [Discovery Service](../../../core/discovery.py) - Core implementation
- [Skip Preferences](../../../core/skip_preferences.py) - Skip filtering
- [API Endpoints](../routers/artifacts.py) - Discovery API routes

---

**Last Updated**: 2025-12-04
**Test Suite Version**: 1.0.0
**Phase**: DIS-5.3 Performance Validation
