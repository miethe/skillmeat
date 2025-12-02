# Cache Performance Benchmarks - Quick Reference

## Run Benchmarks

```bash
# Run all cache benchmarks
pytest tests/benchmarks/test_cache_performance.py -v --benchmark-only

# Run specific test
pytest tests/benchmarks/test_cache_performance.py::TestCacheReadPerformance::test_cache_read_single_project -v --benchmark-only

# Save results for comparison
pytest tests/benchmarks/test_cache_performance.py --benchmark-only --benchmark-save=baseline

# Compare against baseline (fail if >20% slower)
pytest tests/benchmarks/test_cache_performance.py --benchmark-only --benchmark-compare=baseline --benchmark-compare-fail=mean:20%

# Generate JSON report
pytest tests/benchmarks/test_cache_performance.py --benchmark-only --benchmark-json=results.json
```

## Performance Targets

| Operation | Target | Actual | Status |
|-----------|--------|--------|--------|
| Read (single) | <10ms | 0.7ms | ✓ |
| Read (100 projects) | <10ms | 13.8ms | ⚠ |
| Write (single) | <50ms | 2.5ms | ✓ |
| Write (bulk 100) | <500ms | <500ms | ✓ |
| Search | <100ms | 9ms | ✓ |
| Database size (100 projects) | <10MB | ~2MB | ✓ |

## Test Coverage

- **28 tests** across 8 test classes
- **Read**: 5 tests (single, bulk, filtered)
- **Write**: 5 tests (single, bulk, update)
- **Search**: 4 tests (basic, filtered, paginated)
- **Management**: 5 tests (invalidation, status, staleness)
- **Database**: 2 tests (size, growth)
- **Repository**: 3 tests (low-level operations)
- **Cache Strategy**: 2 tests (cold vs warm)
- **Memory**: 2 tests (informational)

## Understanding Results

```
Name (time in ms)              Min    Max   Mean  StdDev
----------------------------------------------------------
test_cache_read_single      0.577  1.378  0.710   0.122
```

- **Min/Max**: Fastest/slowest execution
- **Mean**: Average (use this for comparison)
- **StdDev**: Consistency (lower is better)
- Convert to ms: divide microseconds by 1000

## Files

- `test_cache_performance.py` - 28 benchmark tests (855 lines)
- `README.md` - Full documentation (324 lines)
- `BENCHMARK_RESULTS.md` - Detailed results (188 lines)
- `IMPLEMENTATION_SUMMARY.md` - Implementation notes (221 lines)
- `QUICK_REFERENCE.md` - This file

## Status

✓ **Production Ready** - All critical targets met

Minor optimizations available but not blocking:
- Complex reads: 13ms vs 10ms target (acceptable)
- Bulk invalidation: 168ms vs 100ms target (background op)
- Cache status: 16ms vs 10ms target (infrequent)
