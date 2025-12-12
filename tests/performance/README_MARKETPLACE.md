# Marketplace GitHub Ingestion - Performance Tests

Comprehensive performance benchmarks for the marketplace GitHub ingestion feature (Phase 6, TEST-006).

## Performance Targets

| Component | Metric | Target |
|-----------|--------|--------|
| **Scan Performance** | Small repo (50 files) | <5s |
| | Medium repo (500 files) | <15s |
| | Large repo (2000 files) | <30s |
| | Very large repo (5000+ files) | <60s |
| **API Response Times** | GET /sources | <100ms |
| | GET /sources/{id}/artifacts (100 items) | <150ms |
| | GET /artifacts with filters | <200ms |
| **Heuristic Scoring** | Score 1000 paths | <100ms |
| | Score 10000 paths | <1s |
| | Complexity | Linear O(n), no N+1 |
| **Diff Engine** | Compare 1000 entries | <500ms |
| | Compare 10000 entries | <2s |
| **Memory Usage** | Scan jobs (10 runs) | <50MB increase |
| | Heuristic detector (5 runs) | <20MB increase |
| | Diff engine (5 runs) | <20MB increase |

## Running the Tests

### Prerequisites

Install dev dependencies (includes pytest-benchmark and psutil):

```bash
pip install -e ".[dev]"
# or
uv pip install -e ".[dev]"
```

### Run All Performance Tests

```bash
# Run all marketplace performance tests
pytest tests/performance/test_marketplace_performance.py -v

# Include slow tests
pytest tests/performance/test_marketplace_performance.py -v -m slow

# Run with detailed benchmark output
pytest tests/performance/test_marketplace_performance.py -v --benchmark-verbose
```

### Run Specific Test Categories

```bash
# Scan performance only
pytest tests/performance/test_marketplace_performance.py::TestScanPerformance -v

# API performance only
pytest tests/performance/test_marketplace_performance.py::TestAPIPerformance -v

# Heuristic scoring performance
pytest tests/performance/test_marketplace_performance.py::TestHeuristicPerformance -v

# Diff engine performance
pytest tests/performance/test_marketplace_performance.py::TestDiffEnginePerformance -v

# Memory usage tests
pytest tests/performance/test_marketplace_performance.py::TestMemoryUsage -v
```

### Run Individual Tests

```bash
# Small repo scan
pytest tests/performance/test_marketplace_performance.py::TestScanPerformance::test_scan_small_repo_performance -v

# API list sources
pytest tests/performance/test_marketplace_performance.py::TestAPIPerformance::test_list_sources_performance -v

# Heuristic scoring 1000 paths
pytest tests/performance/test_marketplace_performance.py::TestHeuristicPerformance::test_score_1000_paths_performance -v
```

### Generate Benchmark Reports

```bash
# Save benchmark results to JSON
pytest tests/performance/test_marketplace_performance.py --benchmark-json=benchmark_results.json

# Compare with previous results
pytest tests/performance/test_marketplace_performance.py --benchmark-compare=0001 --benchmark-compare-fail=mean:10%

# Save benchmark histogram
pytest tests/performance/test_marketplace_performance.py --benchmark-histogram=benchmark_histogram
```

## Test Structure

### Scan Performance (`TestScanPerformance`)

Tests GitHub repository scanning with varying repo sizes:

- **test_scan_small_repo_performance**: 50 files, target <5s
- **test_scan_medium_repo_performance**: 500 files, target <15s
- **test_scan_large_repo_performance**: 2000 files, target <30s
- **test_scan_very_large_repo_with_pagination**: 5000+ files with pagination, target <60s

Uses mocked GitHub API responses with realistic file trees.

### API Performance (`TestAPIPerformance`)

Tests FastAPI endpoint response times:

- **test_list_sources_performance**: GET /sources, target <100ms
- **test_list_artifacts_with_100_items_performance**: GET /sources/{id}/artifacts with 100 items, target <150ms
- **test_list_artifacts_with_filters_performance**: GET /artifacts with filters, target <200ms

Uses TestClient with mocked repositories.

### Heuristic Scoring (`TestHeuristicPerformance`)

Tests artifact detection heuristics:

- **test_score_1000_paths_performance**: Score 1000 paths, target <100ms
- **test_score_10000_paths_performance**: Score 10000 paths, target <1s
- **test_no_n_plus_1_in_scoring**: Verify linear O(n) complexity, no N+1 issues

### Diff Engine Performance (`TestDiffEnginePerformance`)

Tests catalog comparison:

- **test_diff_1000_entries_performance**: Compare 1000 entries, target <500ms
- **test_diff_10000_entries_performance**: Compare 10000 entries, target <2s

### Memory Usage (`TestMemoryUsage`)

Tests memory efficiency and leak detection:

- **test_scan_memory_stays_bounded**: 10 scan runs, <50MB increase
- **test_heuristic_detector_memory_efficiency**: 5 detection runs, <20MB increase
- **test_diff_engine_memory_efficiency**: 5 diff runs, <20MB increase

Requires `psutil` package (included in dev dependencies).

## Interpreting Results

### Benchmark Output

```
-------------------------------- benchmark: 1 tests ---------------------------------
Name                                    Min      Max    Mean  StdDev  Median     IQR
---------------------------------------------------------------------------------
test_scan_small_repo_performance     1.2345   1.3456  1.2789  0.0234  1.2756  0.0189
---------------------------------------------------------------------------------
```

- **Min/Max**: Fastest and slowest execution times
- **Mean**: Average execution time (compared against targets)
- **StdDev**: Standard deviation (lower is more consistent)
- **Median**: Middle value (less affected by outliers)
- **IQR**: Interquartile range (spread of middle 50% of data)

### Performance Assertions

Each test includes assertions that fail if performance targets are not met:

```python
assert mean_time < 5.0, f"Small repo scan took {mean_time:.2f}s, expected <5s"
```

If a test fails, the error message shows actual vs. target time.

### Memory Usage

Memory tests report increase in RSS (Resident Set Size):

```
Memory increased by 12.3MB after 10 scans, possible leak
```

- **<50MB for scans**: Normal (includes object allocation, GC overhead)
- **>50MB for scans**: Investigate potential memory leak
- **<20MB for detector/diff**: Normal
- **>20MB for detector/diff**: Investigate potential memory leak

## Regression Testing in CI

### GitHub Actions Configuration

Add to `.github/workflows/tests.yml`:

```yaml
- name: Run performance benchmarks
  run: |
    pytest tests/performance/test_marketplace_performance.py \
      --benchmark-json=benchmark_results.json \
      --benchmark-compare=baseline.json \
      --benchmark-compare-fail=mean:10%
```

### Baseline Management

```bash
# Create baseline
pytest tests/performance/test_marketplace_performance.py --benchmark-save=baseline

# Compare against baseline (fail if >10% slower)
pytest tests/performance/test_marketplace_performance.py \
  --benchmark-compare=baseline \
  --benchmark-compare-fail=mean:10%
```

## Profiling

For detailed profiling of slow operations:

```bash
# Profile with cProfile
python -m cProfile -o profile.stats tests/performance/test_marketplace_performance.py

# View results
python -m pstats profile.stats
> sort cumtime
> stats 20

# Or use snakeviz for visual profiling
pip install snakeviz
snakeviz profile.stats
```

## Troubleshooting

### Tests Running Too Slow

1. Check if mocks are properly configured (avoid real GitHub API calls)
2. Reduce iteration counts for faster local development
3. Use `--benchmark-skip` for non-benchmark test runs

### Memory Tests Failing

1. Run garbage collection before memory checks: `import gc; gc.collect()`
2. Close any open file handles or connections
3. Use memory profiler for detailed analysis:
   ```bash
   pip install memory-profiler
   python -m memory_profiler tests/performance/test_marketplace_performance.py
   ```

### Benchmark Variance

High variance (>10% StdDev) may indicate:
- System load (close other applications)
- Thermal throttling (cool down machine)
- Background processes (check Activity Monitor/Task Manager)

Run benchmarks with:
```bash
pytest tests/performance/test_marketplace_performance.py \
  --benchmark-min-rounds=10 \
  --benchmark-warmup=on
```

## Related Documentation

- Implementation Plan: `.claude/specs/prd-marketplace-github-ingestion.md`
- Service Layer: `skillmeat/core/marketplace/github_scanner.py`
- Heuristic Detector: `skillmeat/core/marketplace/heuristic_detector.py`
- Diff Engine: `skillmeat/core/marketplace/diff_engine.py`
- API Router: `skillmeat/api/routers/marketplace.py`

## Contributing

When adding new performance tests:

1. Use realistic data sizes based on actual usage patterns
2. Include both happy path and edge cases
3. Set reasonable targets based on user experience requirements
4. Mock external dependencies (GitHub API, database)
5. Document expected performance characteristics
6. Add assertions to fail on performance regressions

## License

MIT License - See LICENSE file for details
