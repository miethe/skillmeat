---
title: "SkillBOM Gradual Rollout Plan"
description: "Phased rollout strategy for SkillBOM feature, including canary deployment, staged releases, metrics monitoring, and rollback procedures."
audience: "operators, devops, release managers"
tags: ["rollout", "deployment", "feature-flag", "monitoring", "gradual-release"]
created: "2026-03-13"
updated: "2026-03-13"
category: "Operations"
status: "published"
related_documents: ["skillbom-workflow.md", "attestation-compliance.md"]
---

# SkillBOM Gradual Rollout Plan

This document outlines the phased rollout strategy for the SkillBOM feature (Phase 11 validation). The plan minimizes risk through gradual exposure and continuous monitoring.

## Overview

**Total Rollout Duration**: 3–4 weeks
**Target Users**: All SkillMeat users (single-tenant and enterprise)
**Risk Level**: Low (read-only features and backward-compatible)

The rollout follows a standard canary → staged release → GA pattern with feature flags controlling visibility at each stage.

## Feature Flags

All SkillBOM features are controlled by a master flag and per-component subflags:

| Flag | Default | Controls | Scope |
|------|---------|----------|-------|
| `skillbom_enabled` | `false` | Master switch for all BOM operations | Global |
| `bom_generation_enabled` | `true` (if parent) | `/api/v1/bom/generate` endpoint | API |
| `bom_verification_enabled` | `true` (if parent) | `/api/v1/bom/verify` endpoint | API |
| `attestations_enabled` | `true` (if parent) | Attestation endpoints | API |
| `git_hook_support` | `true` (if parent) | `skillmeat bom install-hook` command | CLI |
| `signature_enforcement` | `false` | Require valid signatures (strict mode) | Policy |

**Configuration**: Edit `APISettings` in `skillmeat/api/config.py` or via environment variables:

```bash
export SKILLMEAT_SKILLBOM_ENABLED=true
export SKILLMEAT_BOM_GENERATION_ENABLED=true
export SKILLMEAT_ATTESTATIONS_ENABLED=true
```

## Rollout Phases

### Phase 1: Canary (Days 1–3)

**Scope**: Internal team + early adopters (5% of user base)

**Objectives**:
- Verify basic functionality in production
- Monitor error rates and performance
- Gather user feedback
- Test backup/restore procedures

**Actions**:

1. **Enable feature flags for canary users only**:
   ```bash
   # In APISettings or feature flag service
   skillbom_enabled = true
   for user in canary_users:
     set_feature_flag(user, "skillbom_enabled", true)
   ```

2. **Monitor critical metrics**:
   - BOM generation success rate (target: >99%)
   - Signature verification latency (<100ms p99)
   - Attestation API error rate (target: <0.1%)
   - Database query performance

3. **Canary users report issues via**:
   - Slack channel: `#skillbom-canary`
   - GitHub issues: `skill-meat/skillbom/canary`
   - Direct feedback: ask 2–3 power users

4. **Go/No-Go decision**:
   - If success rate >99% and no critical bugs → proceed to Phase 2
   - If issues found → hotfix and restart Phase 1

**Rollback threshold**: Any unrecovered outage >5 minutes

### Phase 2a: Internal Staging (Days 4–7)

**Scope**: All internal SkillMeat team (50 users)

**Objectives**:
- Test full workflow end-to-end
- Verify CLI operations in real projects
- Test Git hook installation and usage
- Train team on feature usage

**Actions**:

1. **Enable for all internal team**:
   ```bash
   set_feature_flag_group("team:skillmeat-internal", "skillbom_enabled", true)
   ```

2. **Run integration tests**:
   ```bash
   pytest tests/integration/test_bom_e2e.py -v
   ```

3. **Verify CLI workflows**:
   ```bash
   skillmeat bom keygen
   skillmeat bom generate
   skillmeat bom sign
   skillmeat bom verify
   skillmeat bom install-hook
   skillmeat bom restore --commit <sha>
   ```

4. **Training session**: Record walkthrough of SkillBOM workflow for later reference

5. **Metrics to monitor**:
   - Key generation success rate
   - BOM generation performance (p50, p95, p99)
   - Signature verification accuracy
   - Git hook execution success

**Rollback threshold**: Any critical bug affecting core workflow

### Phase 2b: Early Adopters (Days 8–10)

**Scope**: Volunteer external users (25% of user base)

**Objectives**:
- Real-world usage patterns
- Feedback on documentation
- Edge case discovery
- Performance validation at scale

**Actions**:

1. **Opt-in enrollment**:
   - Post announcement in community
   - Request 50–75 volunteers
   - Provide early access enrollment link

2. **Rollout to early adopters**:
   ```bash
   for user in early_adopters:
     set_feature_flag(user, "skillbom_enabled", true)
   ```

3. **Monitor new metrics**:
   - CLI command success rates by command
   - Attestation creation patterns (scopes, visibility)
   - BOM snapshot size distribution
   - Signature verification failure causes

4. **Gather feedback**:
   - Weekly survey: "How satisfied are you with SkillBOM?" (1–5)
   - Feature requests GitHub board
   - Documentation clarity feedback

5. **Community engagement**:
   - Answer questions in `#support` channel
   - Create FAQ based on common questions
   - Highlight creative use cases

**Go/No-Go decision** (Day 10):
- Community sentiment positive (>3.5/5 rating)
- No unresolved critical bugs
- Documentation gaps identified and scheduled

### Phase 3: Staged Rollout (Days 11–21)

**Timeline**:

| Day | Coverage | Milestone |
|-----|----------|-----------|
| 11–14 | 25% | Ramp to 25% of all users |
| 15–18 | 50% | Ramp to 50% of all users |
| 19–21 | 100% | Full GA |

**Actions for each stage**:

```bash
# Day 11: 25% rollout
set_feature_flag_percentage("skillbom_enabled", 0.25)
# Alert: enable monitoring dashboards

# Day 15: 50% rollout
set_feature_flag_percentage("skillbom_enabled", 0.50)
# Alert: verify error rates still <0.1%

# Day 21: 100% GA
set_feature_flag_percentage("skillbom_enabled", 1.0)
# Alert: archive canary metrics
```

**Monitoring during staged rollout**:

- **Error rate**: Target <0.1% (alert if >0.5%)
- **Latency p99**: Target <200ms (alert if >500ms)
- **Adoption rate**: Track percentage of users generating BOMs
- **Signature verification accuracy**: Target 100%
- **Database query performance**: Alert if any query >500ms

**Daily reviews**:
- Run: `scripts/ops/bom-rollout-check.sh`
- Review: error logs, performance metrics, user feedback
- Escalate: any anomalies to on-call engineer

**Rollback threshold**: Any metric exceeds alert threshold for >1 hour

### Phase 4: General Availability (Day 21+)

**Scope**: All users, feature flags permanently enabled

**Actions**:

1. **Cleanup**:
   - Remove feature flag checks from code (optional; can leave for future toggles)
   - Archive canary metrics
   - Publish post-mortem (if any issues occurred)

2. **Documentation updates**:
   - Update SkillBOM setup guides to assume feature is available
   - Integrate SkillBOM into onboarding docs
   - Archive rollout metrics

3. **Ongoing monitoring**:
   - Continue tracking metrics in production dashboard
   - Monitor for regressions monthly
   - Collect feedback for future enhancements

## Metrics & Monitoring

### Key Performance Indicators

**Availability**:
- BOM generation success rate (target: >99.9%)
- Attestation API uptime (target: >99.99%)
- Signature verification success (target: 100%)

**Performance**:
- BOM generation latency p50: <100ms
- BOM generation latency p99: <200ms
- Signature verification latency p99: <50ms
- Attestation list query p99: <100ms

**Adoption**:
- % of users who generated at least one BOM
- % of projects with Git hooks installed
- % of BOMs with signatures

### Monitoring Setup

**Prometheus metrics** (auto-exposed from FastAPI):

```python
# In skillmeat/api/routers/bom.py
from prometheus_client import Counter, Histogram

bom_generation_total = Counter(
    'bom_generation_total',
    'Total BOM generation requests',
    ['status']  # success, failure, error
)

bom_generation_duration_seconds = Histogram(
    'bom_generation_duration_seconds',
    'BOM generation latency'
)
```

**Grafana dashboards**:
- `SkillBOM / BOM Operations` — generation, verification latency
- `SkillBOM / Attestations` — creation rate, visibility distribution
- `SkillBOM / Adoption` — user cohort tracking

**Alerts** (in Alertmanager):

```yaml
- alert: BomGenerationErrorRateHigh
  expr: rate(bom_generation_total{status="error"}[5m]) > 0.005
  for: 10m
  annotations:
    summary: "BOM generation error rate > 0.5%"

- alert: BomVerificationLatencyHigh
  expr: histogram_quantile(0.99, bom_verification_duration_seconds) > 0.1
  for: 5m
  annotations:
    summary: "BOM verification p99 latency > 100ms"
```

## Rollback Procedures

### Immediate Rollback

If critical bug discovered, immediately:

```bash
# 1. Disable feature flag
set_feature_flag_percentage("skillbom_enabled", 0.0)

# 2. Alert team
pagerduty trigger "SkillBOM Rollback" --severity critical

# 3. Rollback database schema (if migrations involved)
alembic downgrade -1

# 4. Deploy previous API version
# (CI/CD automated)
```

### Partial Rollback

If issue affects only specific endpoint:

```bash
# Disable just that endpoint
bom_generation_enabled = false  # But keep attestations_enabled = true
```

### Data Preservation

**Important**: Never delete attestation or BOM snapshot records during rollback. Just disable the API endpoints and flag.

Rollback should only affect:
- API endpoint availability
- Feature flag state
- Database schema (if migrations caused issue)

DO NOT delete:
- `attestation_records` table
- `bom_snapshots` table
- Git commit hooks (users will re-run install-hook after fix)

### Post-Rollback Recovery

After rollback and fix:

```bash
# 1. Fix code
git checkout main
git pull origin main

# 2. Deploy fixed version
./scripts/deploy.sh --environment=production

# 3. Re-enable flags gradually
set_feature_flag_percentage("skillbom_enabled", 0.05)  # Back to canary

# 4. Verify metrics are healthy
# Run: scripts/ops/bom-rollout-check.sh

# 5. Resume staged rollout
```

## Pre-Deployment Checklist

Before rollout begins, verify:

- [ ] All Phase 11 implementation tasks marked complete
- [ ] BOM and attestation database migrations applied
- [ ] Unit tests pass (`pytest tests/unit/ -k bom`)
- [ ] Integration tests pass (`pytest tests/integration/ -k bom`)
- [ ] API contracts validated against OpenAPI spec
- [ ] CLI commands tested manually end-to-end
- [ ] Feature flags implemented and tested in code
- [ ] Monitoring dashboards created and verified
- [ ] Alerting rules configured and tested
- [ ] Rollback procedures documented and rehearsed
- [ ] On-call engineer trained on SkillBOM
- [ ] Documentation published and reviewed
- [ ] Canary user list identified
- [ ] Communication plan approved by PM/marketing

## Communication Plan

### Pre-rollout (Day 0)

- [ ] Internal announcement: "SkillBOM rollout begins"
- [ ] Canary users notified: "You have early access"
- [ ] Slack channel created: `#skillbom`
- [ ] Status page prepared (for issues)

### During rollout

- [ ] Daily status updates to leadership
- [ ] Weekly community update (if volunteers enrolled)
- [ ] Escalation process documented (who to contact if issues)

### Post-GA

- [ ] Launch announcement blog post
- [ ] Feature highlights in release notes
- [ ] Thank you message to canary/early adopters
- [ ] Retrospective meeting with team

## Success Criteria

**Rollout is successful when**:

1. All users have access to SkillBOM (feature flag at 100%)
2. No critical bugs reported post-GA
3. Adoption rate >20% within 2 weeks of GA
4. User satisfaction rating ≥4.0/5.0
5. Zero unplanned rollbacks
6. Documentation completeness reviewed and verified

## Related Documents

- [Implementation Plan](../project_plans/implementation_plans/features/skillbom-attestation-v1.md) — Detailed feature specifications
- [SkillBOM Workflow Guide](../guides/skillbom-workflow.md) — User documentation
- [Attestation & Compliance Guide](../guides/attestation-compliance.md) — RBAC and compliance workflows
- [BOM API Reference](../api/bom-api.md) — REST API endpoints

## Appendix: Rollout Scripts

### Health Check Script

```bash
#!/bin/bash
# scripts/ops/bom-rollout-check.sh

set -e

echo "SkillBOM Rollout Health Check"
echo "=============================="

# Check API health
echo -n "API health: "
curl -s http://localhost:8080/health | jq -r '.status'

# Check BOM endpoint
echo -n "BOM endpoint: "
curl -s http://localhost:8080/api/v1/bom/snapshot -H "Authorization: Bearer test" | jq '.bom.artifact_count' 2>/dev/null || echo "N/A"

# Check attestation endpoint
echo -n "Attestation endpoint: "
curl -s http://localhost:8080/api/v1/attestations -H "Authorization: Bearer test" | jq '.items | length' 2>/dev/null || echo "N/A"

# Prometheus query for metrics
echo -n "BOM generation success rate (last 5m): "
curl -s 'http://prometheus:9090/api/v1/query?query=rate(bom_generation_total%7Bstatus=%22success%22%7D%5B5m%5D)' | jq '.data.result[].value[1]' 2>/dev/null || echo "N/A"

echo ""
echo "Check complete. Review logs if any errors above."
```

### Feature Flag Toggle Script

```bash
#!/bin/bash
# scripts/ops/bom-flag.sh <action> <percentage|user>

ACTION=$1
TARGET=$2

case $ACTION in
  enable-canary)
    echo "Enabling SkillBOM for canary users..."
    # Call feature flag API or update DB
    ;;
  enable-percentage)
    echo "Enabling SkillBOM for ${TARGET}% of users..."
    # Update feature flag percentage
    ;;
  disable)
    echo "Disabling SkillBOM..."
    # Set flag to 0%
    ;;
  *)
    echo "Usage: $0 {enable-canary|enable-percentage|disable} [percentage|user]"
    exit 1
    ;;
esac
```

---

**Last Updated**: 2026-03-13
**Owner**: Platform/DevOps Team
**Review Cycle**: Before each phase transition
