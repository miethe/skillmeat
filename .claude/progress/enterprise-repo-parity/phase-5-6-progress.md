---
type: progress
schema_version: 2
doc_type: progress
prd: enterprise-repo-parity
feature_slug: enterprise-repo-parity
phase: 5-6
phase_title: Repository Implementation (Marketplace) & Edition-Aware Wiring
status: completed
created: 2026-03-12
updated: '2026-03-12'
prd_ref: docs/project_plans/PRDs/refactors/enterprise-repo-parity-v2.md
plan_ref: docs/project_plans/implementation_plans/refactors/enterprise-repo-parity-v2.md
commit_refs: []
pr_refs: []
owners:
- python-backend-engineer
contributors:
- backend-architect
tasks:
- id: ENT2-5.1
  title: EnterpriseMarketplaceSourceRepository implementation
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies: []
- id: ENT2-5.2
  title: EnterpriseProjectTemplateRepository stub
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies: []
- id: ENT2-5.3
  title: Audit marketplace catalog service & transaction handler
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies: []
- id: ENT2-5.4
  title: Update DI providers for Phase 5 repositories
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - ENT2-5.1
  - ENT2-5.2
- id: ENT2-5.5
  title: Unit tests for marketplace source repository
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - ENT2-5.4
- id: ENT2-6.1
  title: Edition-aware wiring for DbCollectionArtifactRepository
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies: []
- id: ENT2-6.2
  title: Edition-aware wiring for DbArtifactHistoryRepository
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies: []
- id: ENT2-6.3
  title: Edition-aware wiring for DuplicatePairRepository
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies: []
- id: ENT2-6.4
  title: Edition-aware wiring for concrete MarketplaceSourceRepository
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies: []
- id: ENT2-6.5
  title: Full grep audit for remaining SQLite instantiations
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - ENT2-6.1
  - ENT2-6.2
  - ENT2-6.3
  - ENT2-6.4
parallelization:
  batch_1:
  - ENT2-5.1
  - ENT2-5.2
  batch_2:
  - ENT2-5.3
  - ENT2-5.4
  - ENT2-5.5
  batch_3:
  - ENT2-6.1
  - ENT2-6.2
  - ENT2-6.3
  - ENT2-6.4
  batch_4:
  - ENT2-6.5
total_tasks: 10
completed_tasks: 10
in_progress_tasks: 0
blocked_tasks: 0
progress: 100
---

# Phase 5-6: Repository Implementation (Marketplace) & Edition-Aware Wiring

Implement marketplace source repository, add stubs for template repo, and wire all repositories for edition-aware instantiation.

## Quick Reference

```bash
python .claude/skills/artifact-tracking/scripts/update-status.py \
  -f .claude/progress/enterprise-repo-parity/phase-5-6-progress.md \
  -t ENT2-5.1 -s completed
```

## Phase Overview

**Phase 5** implements the final specialized repository (EnterpriseMarketplaceSourceRepository) and adds a stub for templates. The marketplace catalog service and transaction handler are audited to ensure they integrate with the new enterprise storage layer without hardcoding SQLite references.

**Phase 6** performs the crucial wiring work: updating `repository_factory.py` to instantiate edition-aware providers for all 14 repository interfaces. This includes wiring the 4 non-primary repositories (DbCollectionArtifactRepository, DbArtifactHistoryRepository, DuplicatePairRepository, and the concrete MarketplaceSourceRepository). A final grep audit ensures no remaining SQLite-only instantiations exist in the codebase.

Key constraints:
- Enterprise repos always use PostgreSQL session factory (checked at instantiation time)
- Local repos use SQLite session factory with automatic fallback
- Edition awareness is centralized in `repository_factory.py`
- All 14 interfaces must be wired for both editions before Phase 7 tests can run
