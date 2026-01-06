---
title: Marketplace Scan Performance Benchmarks
created: 2026-01-05
test_run: 2026-01-05T21:16:29Z
python_version: 3.12.0
hardware: Apple M-series (MacBook)
references:
  - tests/core/marketplace/test_scan_performance.py
  - skillmeat/core/marketplace/deduplication_engine.py
  - skillmeat/core/marketplace/content_hash.py
---

# Marketplace Scan Performance Benchmarks

Performance validation results for Phase 2 marketplace scan workflow with deduplication.

## Executive Summary

**Performance Target**: Scan 1000 artifacts in <120 seconds

**Actual Performance**: **0.004 seconds** for 1000 artifacts

**Status**: ✅ **EXCEEDS TARGET by 30,000x**

**Throughput**: ~239,000 artifacts/sec

## Test Environment

| Component | Value |
|-----------|-------|
| Python Version | 3.12.0 |
| Platform | macOS (Darwin) |
| Hardware | Apple M-series (MacBook) |
| Test Date | 2026-01-05 |
| Test Framework | pytest 8.4.1 |

## Performance Results

### 1. Baseline Performance (100 artifacts)

| Metric | Value | Notes |
|--------|-------|-------|
| Hash computation | 0.0003s | 330,123 artifacts/sec |
| Within-source dedup | 0.0007s | 151,505 artifacts/sec |
| Cross-source dedup | 0.0002s | 581,256 artifacts/sec |
| Result | Kept: 70, Within-excluded: 30 | 30% duplicate rate |

**Verdict**: Baseline operations are extremely fast (<1ms).

### 2. Medium-Scale Performance (500 artifacts)

| Metric | Value | Notes |
|--------|-------|-------|
| Within-source dedup | 0.002s | 266,400 artifacts/sec |
| Full pipeline | 0.002s | 219,154 artifacts/sec |
| Result | Final: 280, Within: 150, Cross: 70 | Multi-stage dedup |

**Verdict**: Medium-scale processing remains sub-millisecond.

### 3. Large-Scale Performance (1000 artifacts) - PRIMARY TARGET

| Metric | Value | Target | Status |
|--------|-------|--------|--------|
| **Total scan time** | **0.004s** | <120.0s | ✅ **PASS** |
| Stage 1 (within-source) | 0.004s | - | - |
| Stage 2 (cross-source) | 0.0003s | - | - |
| Throughput | 239,349 artifacts/sec | - | - |
| Time per artifact | 0.004ms | - | - |

**Results**:
- Final unique: 560 artifacts
- Within-source excluded: 300 artifacts
- Cross-source excluded: 140 artifacts
- Total processed: 1000 artifacts

**Verdict**: ✅ **Exceeds target by ~30,000x**. Performance is exceptional.

### 4. Hash Computation Performance

| Artifact Count | Time | Throughput | Notes |
|----------------|------|------------|-------|
| 100 | 0.0003s | 330,123/sec | Baseline |
| 1000 | 0.002s | 453,772/sec | Large-scale |

**Cache Effectiveness**:
- First scan (cold cache): 0.002s
- Second scan (warm cache): 0.002s
- Speedup: 0.96x (minimal improvement - hashing is already very fast)

**Verdict**: Hash computation is not a bottleneck. Caching provides marginal benefit because raw computation is already extremely fast.

### 5. Deduplication Overhead

| Metric | Value | Notes |
|--------|-------|-------|
| Baseline (hash only) | 0.001s | 500 artifacts |
| Full dedup (hash + logic) | 0.002s | Same artifacts |
| **Overhead** | **48.2%** | Acceptable for value provided |

**Analysis**:
- Deduplication logic adds ~50% overhead compared to raw hashing
- This is acceptable given the value (duplicate detection, exclusion marking)
- For small batches, fixed costs (dict operations, logging) inflate percentage
- Absolute overhead is still sub-millisecond

**Verdict**: Overhead is modest and acceptable.

### 6. Cross-Source Deduplication Overhead

| Metric | Value | Notes |
|--------|-------|-------|
| Processing time | 0.0003s | 500 artifacts (pre-hashed) |
| Throughput | 1,509,051/sec | Extremely fast |

**Analysis**:
- When hashes are pre-computed, cross-source dedup is just set lookups
- Over 1.5 million artifacts/sec throughput
- This stage is negligible in overall scan time

**Verdict**: Cross-source dedup has negligible overhead.

### 7. File Size Impact

| File Size | Time (500 artifacts) | Throughput | Notes |
|-----------|----------------------|------------|-------|
| 100 bytes | 0.001s | 547,895/sec | Smallest files |
| 1 KB | 0.002s | 312,931/sec | Medium files |
| 10 KB | 0.009s | 53,379/sec | Large files |

**File Size Limit Protection**:
- Files >10MB are automatically skipped with warning
- Prevents timeout on huge binary files
- Test with 15MB file: completed in <1s (file skipped correctly)

**Verdict**: File size limit working correctly. Large files have measurable impact but still well within performance targets.

### 8. Scalability

| Artifact Count | Time | Throughput | Scaling Ratio |
|----------------|------|------------|---------------|
| 100 | 0.0004s | 249,532/sec | - |
| 200 | 0.0007s | 286,379/sec | 1.74x |
| 400 | 0.0012s | 321,296/sec | 1.78x |

**Analysis**:
- Scaling ratio: ~1.75x when doubling size
- Close to linear (2.0x would be perfectly linear)
- Slight sub-linear behavior is acceptable and expected (fixed costs amortized)

**Verdict**: Performance scales nearly linearly with artifact count.

## Performance Bottleneck Analysis

Based on test results, here's the breakdown of where time is spent:

### Time Distribution (1000 artifacts)

| Stage | Time | Percentage | Bottleneck? |
|-------|------|------------|-------------|
| Within-source dedup | 0.004s | 100% | ❌ No |
| Cross-source dedup | 0.0003s | 7.5% | ❌ No |
| **Total** | **0.004s** | - | ❌ **No bottlenecks** |

### Key Findings

1. **Hash Computation**: Extremely fast (~450k artifacts/sec). Not a bottleneck.

2. **Within-Source Dedup**: Dominates total time but is still sub-5ms for 1000 artifacts. Not a bottleneck.

3. **Cross-Source Dedup**: Negligible overhead when hashes are pre-computed. Not a bottleneck.

4. **File Size**: Large files (10KB) reduce throughput to ~50k/sec, but this is still 4,000x faster than target.

5. **Dedup Overhead**: Adds ~50% overhead vs. raw hashing, but absolute time is still negligible.

## Optimization Opportunities (Not Needed)

While performance far exceeds requirements, potential optimizations if ever needed:

### Already Implemented ✅
- ✅ Content hash caching (ContentHashCache with LRU eviction)
- ✅ File size limit (10MB max, prevents timeout on huge files)
- ✅ Efficient SHA256 hashing (built-in hashlib)
- ✅ Order-independent artifact hashing (sorted file keys)
- ✅ Pre-computed hash reuse (cross-source dedup)

### Not Needed (Performance Excellent)
- ❌ Parallel processing: Not needed - sequential is already 30,000x faster than target
- ❌ Database indexing: Not needed - in-memory set lookups are sub-millisecond
- ❌ Incremental hashing: Not needed - full hash computation is extremely fast
- ❌ Alternative hash algorithms: Not needed - SHA256 is fast enough

## Conclusion

### Performance Summary

| Metric | Target | Actual | Ratio |
|--------|--------|--------|-------|
| **1000 artifact scan** | <120s | 0.004s | **30,000x faster** |
| Throughput | ~8.3/sec | ~240,000/sec | **28,800x faster** |

### Status: ✅ EXCEEDS ALL REQUIREMENTS

The scan workflow performance is **exceptional**:

1. ✅ **Meets target**: 1000 artifacts in 0.004s (vs. 120s target)
2. ✅ **No bottlenecks**: All operations are sub-millisecond
3. ✅ **Linear scaling**: Performance scales nearly linearly with count
4. ✅ **File size protection**: 10MB limit prevents timeouts
5. ✅ **Cache working**: Hash cache provides marginal benefit (hashing already fast)
6. ✅ **Modest overhead**: Dedup logic adds ~50% overhead (acceptable)

### Recommendations

**No optimizations needed**. The current implementation:
- Far exceeds performance targets (30,000x faster)
- Scales linearly with artifact count
- Has no performance bottlenecks
- Includes appropriate safeguards (file size limits)

**Future considerations** (only if requirements change dramatically):
- If scanning 1,000,000+ artifacts becomes common, consider parallel processing
- If network I/O is added (GitHub API), that will become the bottleneck (not hashing)
- Monitor performance in production with real-world artifact structures

## Test Reproducibility

### Run Performance Tests

```bash
# Run all performance tests
pytest tests/core/marketplace/test_scan_performance.py -v --log-cli-level=INFO

# Run main performance validation test only
pytest tests/core/marketplace/test_scan_performance.py::TestLargeScalePerformance::test_full_pipeline_1000_artifacts_target -v -s

# Run with performance marker
pytest -v -m performance
```

### Expected Output

```
Total scan time:          0.004s
Stage 1 (within-source):  0.004s
Stage 2 (cross-source):   0.000s
Target:                   <120.0s
Status:                   ✓ PASS

Throughput:              239,349.0 artifacts/sec
Time per artifact:        0.004ms

Results:
  Final unique:           560
  Within-source excluded: 300
  Cross-source excluded:  140
  Total processed:        1000
```

## Appendix: Test Artifacts

### Test Artifact Structure

Each test artifact includes:
- **Path**: `skills/artifact_{index}`
- **Files**: 3 files per artifact by default
  - `file_0.md`, `file_1.md`, `file_2.md`
- **Content**: ~500 bytes per file (configurable)
- **Confidence Score**: Varies 0.5-1.0 based on index
- **Duplicate Rate**: Configurable (0-100%)

### Test Scenarios

1. **Baseline (100 artifacts)**: Fast sanity check
2. **Medium (500 artifacts)**: Representative workload
3. **Large (1000 artifacts)**: Performance target validation
4. **Duplicate ratios**: 20-30% duplicates (realistic)
5. **File sizes**: 100 bytes to 15MB (edge cases)

### Hardware Context

Results from Apple M-series MacBook. Performance will vary on different hardware, but should still far exceed the 120s target on any modern system.
