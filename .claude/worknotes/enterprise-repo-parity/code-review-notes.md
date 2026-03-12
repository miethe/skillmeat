---
title: "ENT2-7.5: Code Review Notes"
created: 2026-03-12
phase: 7
task: ENT2-7.5
reviewer: senior-code-reviewer
---

# ENT2-7.5: Enterprise Repository Code Review

## Overall Assessment: CONDITIONAL PASS

Phases 3-5 repository classes pass all checklist items. Phase 6 `EnterpriseDbCollectionArtifactRepository` has critical tenant isolation gaps and session management violations.

## Violations Requiring Fixes

### CRITICAL-1: EnterpriseDbCollectionArtifactRepository — missing tenant filter on all SELECT queries

- File: `skillmeat/cache/enterprise_repositories.py`
- Lines: 9198-9201, 9228-9232, 9246-9248, 9269-9277, 9332-9335, 9448-9451, 9462-9466, 9477-9479, 9508-9510, 9531-9536
- Impact: A caller with a valid collection_id from another tenant can read/enumerate that tenant's artifacts
- Fix: Add tenant validation step or add `tenant_id` to `EnterpriseCollectionArtifact` join table

### HIGH-1: add_artifacts() calls session.commit() (line 9349)
### HIGH-2: remove_artifact() calls session.commit() (line 9375)

- Impact: Violates repository design contract; prevents atomic multi-step operations
- Fix: Replace `self.session.commit()` with `self.session.flush()`

### MEDIUM-1: EnterpriseDeploymentSetRepository.remove_member() — missing tenant filter (lines 7059-7063)

- Fix: Add `EnterpriseDeploymentSetMember.tenant_id == self._get_tenant_id()` to WHERE clause

## LOW Priority (non-blocking)

- LOW-1: `EnterpriseProjectTemplateRepository` Generic type annotation bug (line 8440)
- LOW-2: `EnterpriseDeploymentRepository` cross-model queries use explicit predicates instead of `_apply_tenant_filter()` (lines 6320, 6432)
- LOW-3: DeploymentSetRepository/DeploymentProfileRepository call `session.rollback()` inside exception handlers

## Passing Classes

All Phase 3-5 classes pass: EnterpriseTagRepository, EnterpriseGroupRepository, EnterpriseSettingsRepository, EnterpriseContextEntityRepository, EnterpriseProjectRepository, EnterpriseDeploymentRepository, EnterpriseDeploymentSetRepository (minus MEDIUM-1), EnterpriseDeploymentProfileRepository, EnterpriseMarketplaceSourceRepository, EnterpriseProjectTemplateRepository (stub), EnterpriseMarketplaceTransactionHandler, EnterpriseArtifactHistoryStub, EnterpriseDuplicatePairStub.

## DI Wiring: PASS

All 8 Group A interfaces and all Group B repos have proper edition branching. No 503 stubs remain. Local branch unchanged.

## Sign-Off

Pending resolution of CRITICAL-1, HIGH-1, HIGH-2, and MEDIUM-1. Once fixed and re-reviewed, this task is approved.

*Reviewed: 2026-03-12 | Reviewer: senior-code-reviewer (claude-sonnet-4-6)*
