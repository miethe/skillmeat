---
parent: ../marketplace-source-detection-improvements-v1.md
section: Metrics & Success Criteria
status: inferred_complete
---
# Metrics & Success Criteria

## Implementation Metrics

| Metric | Target | Owner | Frequency |
|--------|--------|-------|-----------|
| Code coverage (Phase 2) | >75% heuristic, >80% dedup | Backend | Per commit |
| Code coverage (Phase 3) | >75% API routes | Backend | Per commit |
| Code coverage (Phase 4) | >60% components | Frontend | Per commit |
| Test pass rate | 100% | QA | Per commit |
| Code review sign-offs | 100% | Tech leads | Per phase |

## Production Metrics

| Metric | Target | Owner | Frequency |
|--------|--------|-------|-----------|
| Detection accuracy (non-skills) | >= 85% | Product | Monthly |
| Duplicate detection rate | >= 90% | Product | Monthly |
| Manual mapping adoption | > 30% of sources | Product | Monthly |
| Scan time regression | < 10% increase | Backend | Weekly |
| User satisfaction survey | >= 4/5 stars | Product | Monthly |
| Error rate | < 2% on marketplace endpoints | DevOps | Daily |

## Observability

**Logging added:**
```
[INFO] Scan started: source_id=src_123, repo=user/repo
[INFO] Detection completed: artifacts=42, time_ms=3200
[INFO] Deduplication started: total_artifacts=42
[INFO] Within-source dedup: duplicates_found=4, surviving=38
[INFO] Cross-source dedup: duplicates_found=3, surviving=35
[INFO] Scan completed: time_ms=4100, duplicates_within=4, duplicates_across=3
```

**Metrics to track:**
```
marketplace_scan_duration_seconds (histogram)
marketplace_artifacts_detected (counter, tagged by source_id)
marketplace_duplicates_within_source (counter)
marketplace_duplicates_across_sources (counter)
marketplace_manual_mappings_used (counter)
marketplace_scan_errors (counter, tagged by error_type)
```
