# Performance Tests

Performance validation tests for marketplace scan workflow with deduplication.

## Quick Start

```bash
# Run all performance tests
pytest tests/core/marketplace/test_scan_performance.py -v

# Run with detailed logging
pytest tests/core/marketplace/test_scan_performance.py -v --log-cli-level=INFO

# Run main performance validation test only
pytest tests/core/marketplace/test_scan_performance.py::TestLargeScalePerformance::test_full_pipeline_1000_artifacts_target -v -s
```

## Performance Target

**Target**: Scan 1000 artifacts in <120 seconds

**Current**: 0.004 seconds (30,000x faster)

## Test Categories

### Baseline Performance (100 artifacts)
- Hash computation speed
- Within-source deduplication
- Cross-source deduplication

### Medium Scale (500 artifacts)
- Representative workload validation
- Full pipeline testing

### Large Scale (1000 artifacts)
- **Main target validation**
- Hash caching effectiveness
- Full pipeline performance

### Overhead Analysis
- Deduplication overhead vs. raw hashing
- Cross-source dedup overhead

### File Size Impact
- Small files (100 bytes)
- Medium files (1KB)
- Large files (10KB)
- File size limit protection (>10MB)

### Scalability
- Linear scaling verification
- Throughput consistency

## Benchmark Results

See: `.claude/context/scan-performance-benchmarks.md`

Key metrics:
- **Throughput**: ~240,000 artifacts/sec
- **Time per artifact**: 0.004ms
- **Dedup overhead**: 48% (acceptable)
- **Scaling**: ~1.75x (near-linear)

## Test Fixtures

### `make_test_artifact(index, content_variant, num_files, file_size)`
Create single test artifact with configurable characteristics.

### `create_artifact_batch(count, duplicate_ratio, num_files, file_size)`
Create batch of artifacts with controlled duplicate rate.

## Markers

Tests are marked with `@pytest.mark.performance` for selective execution:

```bash
# Run only performance tests
pytest -v -m performance
```

## Expected Output

```
PERFORMANCE VALIDATION RESULTS (1000 artifacts)
============================================================
Total scan time:          0.004s
Stage 1 (within-source):  0.004s
Stage 2 (cross-source):   0.000s
Target:                   <120.0s
Status:                   ✓ PASS

Throughput:              239,349 artifacts/sec
Time per artifact:        0.004ms

Results:
  Final unique:           560
  Within-source excluded: 300
  Cross-source excluded:  140
  Total processed:        1000
============================================================
```

## Notes

- Performance will vary by hardware (results from Apple M-series)
- Network I/O is mocked (not measured in these tests)
- Real-world performance may differ based on GitHub API latency
- Hash computation dominates scan time (not network I/O in these tests)
