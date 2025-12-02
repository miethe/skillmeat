# SkillMeat Cache Performance Benchmarks

This directory contains comprehensive performance benchmarks for the SkillMeat cache system, validating that all cache operations meet the performance targets defined in the persistent-project-cache PRD.

## Performance Targets

| Operation | Target | Status |
|-----------|--------|--------|
| Cache read (single project) | <10ms | ✓ Validated |
| Cache read (all projects) | <10ms | ✓ Validated |
| Cache write (single project) | <50ms | ✓ Validated |
| Bulk write (100 projects) | <500ms | ✓ Validated |
| Search query | <100ms | ✓ Validated (2-7ms in production) |
| Cache invalidation | <10ms | ✓ Validated |
| Cache status | <10ms | ✓ Validated |
| Database size (100 projects) | <10MB | ✓ Validated |

## Running Benchmarks

### Run All Cache Benchmarks

```bash
pytest tests/benchmarks/test_cache_performance.py -v --benchmark-only
```

### Run Specific Test Class

```bash
# Read performance benchmarks
pytest tests/benchmarks/test_cache_performance.py::TestCacheReadPerformance -v --benchmark-only

# Write performance benchmarks
pytest tests/benchmarks/test_cache_performance.py::TestCacheWritePerformance -v --benchmark-only

# Search performance benchmarks
pytest tests/benchmarks/test_cache_performance.py::TestCacheSearchPerformance -v --benchmark-only
```

### Run Single Benchmark

```bash
pytest tests/benchmarks/test_cache_performance.py::TestCacheReadPerformance::test_cache_read_single_project -v --benchmark-only
```

### Generate Benchmark Report

```bash
# JSON format
pytest tests/benchmarks/test_cache_performance.py --benchmark-only --benchmark-json=benchmark_results.json

# Save results for comparison
pytest tests/benchmarks/test_cache_performance.py --benchmark-only --benchmark-save=baseline

# Compare against baseline
pytest tests/benchmarks/test_cache_performance.py --benchmark-only --benchmark-compare=baseline
```

### Benchmark Options

```bash
# Disable garbage collection during benchmarks (more consistent results)
pytest tests/benchmarks/test_cache_performance.py --benchmark-only --benchmark-disable-gc

# Increase number of rounds for more accurate results
pytest tests/benchmarks/test_cache_performance.py --benchmark-only --benchmark-min-rounds=10

# Set time limits
pytest tests/benchmarks/test_cache_performance.py --benchmark-only --benchmark-max-time=5.0

# Show histogram
pytest tests/benchmarks/test_cache_performance.py --benchmark-only --benchmark-histogram
```

## Benchmark Test Suites

### TestCacheReadPerformance

Validates cache read operations meet <10ms latency target:

- `test_cache_read_single_project` - Read single project by ID
- `test_cache_read_all_projects` - Read all cached projects
- `test_cache_read_project_by_path` - Read project by filesystem path
- `test_cache_read_artifacts_for_project` - Read all artifacts for a project
- `test_cache_read_with_filter_fresh_only` - Read with staleness filter

**Expected Results**: All operations <10ms (typically 0.5-2ms)

### TestCacheWritePerformance

Validates cache write operations meet latency targets:

- `test_cache_write_single_project` - Write single project (<50ms target)
- `test_cache_write_bulk_100_projects` - Bulk write 100 projects (<500ms target)
- `test_cache_write_artifacts_only` - Write artifacts only (<50ms target)
- `test_cache_update_project` - Update existing project (<50ms target)
- `test_cache_batch_update_upstream_versions` - Batch update versions (<100ms target)

**Expected Results**: Single writes <50ms, bulk <500ms

### TestCacheSearchPerformance

Validates search operations (proven at 2-7ms in production):

- `test_cache_search_artifacts` - Search artifacts by name (<100ms target)
- `test_cache_search_with_filters` - Search with type filter
- `test_cache_search_with_pagination` - Search with pagination
- `test_cache_get_outdated_artifacts` - Get outdated artifacts list (<50ms target)

**Expected Results**: All operations <100ms (typically 2-10ms)

### TestCacheManagementPerformance

Validates cache management operations:

- `test_cache_invalidation_single_project` - Invalidate single project (<10ms)
- `test_cache_invalidation_all_projects` - Invalidate all projects (<100ms)
- `test_cache_status` - Get cache statistics (<10ms)
- `test_cache_staleness_check_single` - Check staleness (<10ms)
- `test_cache_clear_all` - Clear entire cache (<200ms)

**Expected Results**: Status operations <10ms, bulk operations <200ms

### TestCacheDatabaseSize

Validates database storage efficiency:

- `test_database_size_100_projects` - Database size <10MB for 100 projects
- `test_database_size_growth_linear` - Verify linear growth (no memory leaks)

**Expected Results**: <10MB for 100 projects (1000 artifacts)

### TestRepositoryPerformance

Validates low-level repository operations:

- `test_repository_create_project` - Create project (<10ms)
- `test_repository_list_projects` - List all projects (<10ms)
- `test_repository_search_artifacts` - SQL search (<50ms)

**Expected Results**: Repository operations <10ms (except complex queries)

### TestColdWarmCachePerformance

Documents cold vs warm cache performance:

- `test_cold_cache_first_read` - First read after population
- `test_warm_cache_repeated_reads` - Repeated reads (should be faster)

**Expected Results**: Both <10ms, warm typically faster

### TestCacheMemoryUsage

Documents memory usage (informational):

- `test_memory_during_bulk_write` - Memory during bulk operations
- `test_memory_during_search` - Memory during search

**Note**: For detailed memory profiling, use `memory_profiler`:

```bash
pip install memory_profiler
python -m memory_profiler tests/benchmarks/test_cache_performance.py
```

## Understanding Benchmark Output

```
Name (time in us)                  Min      Max     Mean   StdDev  Median
-------------------------------------------------------------------------
test_cache_read_single_project  577.21  1378.42  709.55  121.79  669.87
```

- **Min**: Fastest execution time (microseconds)
- **Max**: Slowest execution time
- **Mean**: Average execution time
- **StdDev**: Standard deviation (consistency indicator)
- **Median**: Middle value (less affected by outliers)
- **IQR**: Interquartile range (variability indicator)
- **Outliers**: Number of executions outside normal range

**Converting to milliseconds**: Divide by 1000
- 709.55 μs = 0.71 ms (well under 10ms target)

## CI/CD Integration

Add to CI pipeline to catch performance regressions:

```yaml
# .github/workflows/benchmarks.yml
name: Performance Benchmarks

on: [push, pull_request]

jobs:
  benchmark:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          pip install -e ".[dev]"
          pip install pytest-benchmark
      - name: Run benchmarks
        run: |
          pytest tests/benchmarks/test_cache_performance.py \
            --benchmark-only \
            --benchmark-json=benchmark_results.json
      - name: Store benchmark results
        uses: benchmark-action/github-action-benchmark@v1
        with:
          tool: 'pytest'
          output-file-path: benchmark_results.json
```

## Performance Regression Detection

Compare current performance against baseline:

```bash
# Save baseline (run on main branch)
pytest tests/benchmarks/test_cache_performance.py --benchmark-only --benchmark-save=main

# After making changes, compare
pytest tests/benchmarks/test_cache_performance.py --benchmark-only --benchmark-compare=main

# Fail if performance degrades >10%
pytest tests/benchmarks/test_cache_performance.py --benchmark-only \
  --benchmark-compare=main \
  --benchmark-compare-fail=mean:10%
```

## Profiling Individual Operations

For detailed profiling of specific operations:

```bash
# CPU profiling with cProfile
python -m cProfile -o profile.stats tests/benchmarks/test_cache_performance.py
python -m pstats profile.stats

# Visualize with snakeviz
pip install snakeviz
snakeviz profile.stats

# Memory profiling
pip install memory_profiler
python -m memory_profiler tests/benchmarks/test_cache_performance.py
```

## SQLite Query Analysis

To analyze SQLite query performance:

```python
# Add to test:
import sqlite3
conn = sqlite3.connect(db_path)
conn.set_trace_callback(print)  # Log all SQL queries

# Or use EXPLAIN QUERY PLAN
cursor.execute("EXPLAIN QUERY PLAN SELECT * FROM projects WHERE id = ?", (project_id,))
print(cursor.fetchall())
```

## Troubleshooting

### Benchmarks Failing Performance Targets

1. Check if running in debug mode (disable for benchmarks)
2. Ensure no background processes consuming resources
3. Use `--benchmark-disable-gc` for more consistent results
4. Increase `--benchmark-min-rounds` for more accurate averages
5. Check SQLite indexes are created (see `skillmeat/cache/models.py`)

### High Variance in Results

1. Close other applications to reduce system load
2. Disable background services (indexing, antivirus, etc.)
3. Run on a dedicated machine or CI environment
4. Use `--benchmark-warmup` to stabilize initial runs

### Memory Usage Higher Than Expected

1. Use `memory_profiler` for detailed analysis
2. Check for unclosed database connections
3. Verify SQLite WAL mode is working correctly
4. Look for large object retention in cache

## Performance Optimization Tips

Based on benchmark results:

1. **Enable SQLite Write-Ahead Logging (WAL)**
   - Already enabled in `skillmeat/cache/models.py`
   - Improves concurrent read/write performance

2. **Use Appropriate Indexes**
   - All foreign keys are indexed
   - Search columns have indexes
   - Check `EXPLAIN QUERY PLAN` for missing indexes

3. **Batch Operations**
   - Use `populate_projects()` for bulk inserts
   - Use `update_upstream_versions()` for batch updates
   - Avoid individual inserts in loops

4. **Connection Pooling**
   - Repository uses session-per-operation pattern
   - Consider connection pooling for high concurrency

5. **Cache Warm-up**
   - Background refresh job keeps cache warm
   - Initial reads may be slower (cold cache)

## Related Documentation

- [Cache Architecture](../../skillmeat/cache/README.md)
- [Cache Manager API](../../skillmeat/cache/manager.py)
- [Cache Repository](../../skillmeat/cache/repository.py)
- [Performance Targets (PRD)](./.claude/progress/persistent-project-cache/)
