---
type: progress
schema_version: 2
doc_type: progress
prd: enterprise-repo-parity
feature_slug: enterprise-repo-parity
phase: 3-4
phase_title: "Repository Implementation (Core & Deployment)"
status: pending
created: 2026-03-12
updated: 2026-03-12
prd_ref: docs/project_plans/PRDs/refactors/enterprise-repo-parity-v2.md
plan_ref: docs/project_plans/implementation_plans/refactors/enterprise-repo-parity-v2.md
commit_refs: []
pr_refs: []

owners: ["python-backend-engineer"]
contributors: ["backend-architect"]

tasks:
  - id: "ENT2-3.1"
    title: "EnterpriseTagRepository implementation"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: []
  - id: "ENT2-3.2"
    title: "EnterpriseGroupRepository implementation"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: []
  - id: "ENT2-3.3"
    title: "EnterpriseSettingsRepository implementation"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: []
  - id: "ENT2-3.4"
    title: "EnterpriseContextEntityRepository implementation"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: []
  - id: "ENT2-3.5"
    title: "Update DI providers for Phase 3 repositories"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["ENT2-3.1", "ENT2-3.2", "ENT2-3.3", "ENT2-3.4"]
  - id: "ENT2-3.6"
    title: "Unit tests for Phase 3 repositories"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["ENT2-3.5"]
  - id: "ENT2-4.1"
    title: "EnterpriseProjectRepository implementation"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: []
  - id: "ENT2-4.2"
    title: "EnterpriseDeploymentRepository implementation"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: []
  - id: "ENT2-4.3"
    title: "EnterpriseDeploymentSetRepository & EnterpriseDeploymentProfileRepository"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: []
  - id: "ENT2-4.4"
    title: "Update DI providers for Phase 4 repositories"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["ENT2-4.1", "ENT2-4.2", "ENT2-4.3"]
  - id: "ENT2-4.5"
    title: "Unit tests for Phase 4 repositories"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["ENT2-4.4"]

parallelization:
  batch_1: ["ENT2-3.1", "ENT2-3.2"]
  batch_2: ["ENT2-3.3", "ENT2-3.4"]
  batch_3: ["ENT2-3.5", "ENT2-3.6"]
  batch_4: ["ENT2-4.1", "ENT2-4.2"]
  batch_5: ["ENT2-4.3"]
  batch_6: ["ENT2-4.4", "ENT2-4.5"]
---

# Phase 3-4: Repository Implementation (Core & Deployment)

Implement 8 enterprise repositories covering tag/group/settings/context-entity management and project/deployment lifecycle.

## Quick Reference

```bash
python .claude/skills/artifact-tracking/scripts/update-status.py \
  -f .claude/progress/enterprise-repo-parity/phase-3-4-progress.md \
  -t ENT2-3.1 -s completed
```

## Phase Overview

Phases 3 and 4 execute implementation of all enterprise repository classes in `skillmeat/cache/enterprise_repositories.py`. These implementations follow SQLAlchemy 2.x `select()` patterns and include tenant isolation via `_apply_tenant_filter()` in every query method.

**Phase 3** focuses on tag/group/settings/context-entity management (4 repositories).
**Phase 4** focuses on project/deployment lifecycle (4 repositories + 2 composite repos).

Each repository must:
- Inherit from appropriate base class with tenant context injection
- Implement all public methods matching the local repository interface
- Include tenant isolation on every query
- Use `select()` style SQLAlchemy queries
- Include docstrings documenting enterprise-specific behavior (soft deletes, tenant scoping, etc.)

After all implementations are complete, DI providers are updated in `repository_factory.py` to instantiate enterprise repositories when in enterprise mode, and comprehensive unit tests validate all methods.
