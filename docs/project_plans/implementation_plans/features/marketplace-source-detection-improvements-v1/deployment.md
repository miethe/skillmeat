---
parent: ../marketplace-source-detection-improvements-v1.md
section: Environment Configuration & Deployment
status: inferred_complete
schema_version: 2
doc_type: implementation_plan
feature_slug: deployment
prd_ref: null
---
# Environment Configuration & Deployment

## Environment Configuration

### Required Environment Variables

| Variable | Default | Type | Description |
|----------|---------|------|-------------|
| `MARKETPLACE_MAX_MAPPINGS_PER_SOURCE` | 100 | int | Max manual mappings per source |
| `MARKETPLACE_DEDUP_ENABLED` | true | bool | Enable/disable deduplication |
| `MARKETPLACE_DEDUP_MAX_FILE_SIZE_MB` | 10 | int | Skip hashing files > this size |
| `MARKETPLACE_DEDUP_TIMEOUT_SECONDS` | 120 | int | Timeout for dedup operations |
| `MARKETPLACE_HASH_ALGORITHM` | sha256 | str | Algorithm: sha256 (only option for now) |
| `MARKETPLACE_DEDUP_LAZY_HASHING_ENABLED` | true | bool | Use lazy hashing for performance |

### Configuration in Code

**Backend (`skillmeat/api/config.py`):**
```python
class MarketplaceSettings(BaseSettings):
    max_mappings_per_source: int = 100
    dedup_enabled: bool = True
    dedup_max_file_size_mb: int = 10
    dedup_timeout_seconds: int = 120
    hash_algorithm: str = "sha256"
    lazy_hashing_enabled: bool = True
```

---

## Deployment Procedure

### Pre-Deployment Checklist

- [ ] All tests passing (unit, integration, E2E)
- [ ] Code review sign-offs complete
- [ ] Database backup taken (if needed)
- [ ] Monitoring alerts configured
- [ ] Rollback plan documented and tested
- [ ] User documentation finalized
- [ ] Performance testing validated

### Deployment Steps

1. **Stage 1: Backend Deployment (Maintenance Window)**
   - Deploy Python backend changes
   - Verify API endpoints responding
   - Run health check endpoint
   - Monitor error logs for 5 minutes

2. **Stage 2: Frontend Deployment**
   - Deploy Next.js frontend changes
   - Verify page loads correctly
   - Check component rendering
   - Monitor browser console for errors

3. **Stage 3: Canary Rollout (Optional)**
   - Deploy to 10% of users first
   - Monitor metrics for 2 hours
   - Watch for error rate increases
   - If stable, proceed to full rollout

4. **Stage 4: Full Rollout**
   - Deploy to 100% of users
   - Monitor metrics closely for 24 hours
   - Check user feedback channels
   - Prepare for quick rollback if needed

### Rollback Procedure

**If critical issues arise:**

1. Revert backend code to previous commit
2. Revert frontend code to previous commit
3. Clear browser cache / CDN caches
4. Restore database from pre-deployment snapshot (if needed)
5. Monitor system for 24 hours post-rollback
6. Document issue and root cause
