---
title: Pre-Deployment Compliance Checklist
description: Required sign-offs and validation checks before any production deployment
version: "1.0.0"
---

# Pre-Deployment Compliance Checklist

**Required sign-offs before any production deployment.**

This checklist must be completed and attached to the deployment ticket. Deployments
to production without a completed checklist are a compliance violation.

---

## 1. Security Review

- [ ] OWASP Top 10 evaluated for all new/modified endpoints
- [ ] Authentication and authorization logic reviewed by security team
- [ ] No new secrets, credentials, or API keys hardcoded in source code
- [ ] Secrets scanning (`detect-secrets` or equivalent) passed on final commit
- [ ] Dependency vulnerability scan (`pip audit` / `npm audit`) — no critical CVEs
- [ ] Static analysis (Bandit/Semgrep) passed with no new high-severity findings

## 2. Data Handling Verification

- [ ] New PII fields are documented in the data inventory
- [ ] Field-level encryption applied to all Tier 1 PII fields
- [ ] PII is masked or absent from all log statements in changed files
- [ ] Retention delete/anonymize logic tested for any new data stores
- [ ] If new cross-border transfer: legal mechanism documented and approved

## 3. Audit and Compliance

- [ ] Audit log events emitted for all new state-changing operations
- [ ] Audit log schema reviewed — no PII in log fields
- [ ] If payment path: tokenization flow verified in staging
- [ ] If SOX-scope system: change management ticket raised and approved
- [ ] If AML/KYC path: transaction monitoring thresholds reviewed with compliance

## 4. Testing Gate

- [ ] Unit test coverage ≥ 95% for financial calculation logic
- [ ] Integration tests pass against sandbox environment
- [ ] Performance/load test completed if new payment or high-volume path
- [ ] Regression suite passed (no new failures)

## 5. Operational Readiness

- [ ] Runbook updated for any new operational procedures
- [ ] Rollback plan documented and tested
- [ ] On-call team notified of deployment window
- [ ] Monitoring/alerting configured for new endpoints or services
- [ ] Feature flags configured for gradual rollout (if applicable)

## 6. Sign-Offs Required

| Role | Required For | Signature |
|------|-------------|-----------|
| **Engineering Lead** | All deployments | ________ |
| **Security Reviewer** | Auth/payment/PII changes | ________ |
| **Compliance Officer** | Regulatory logic, AML/KYC, SOX | ________ |
| **Data Privacy Officer** | New PII collection, cross-border transfer | ________ |

---

**Deployment approved by**: ________________  
**Date**: ________________  
**Deployment ticket**: ________________  
