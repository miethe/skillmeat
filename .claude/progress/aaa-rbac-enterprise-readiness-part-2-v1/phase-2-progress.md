---
type: progress
schema_version: 2
doc_type: progress
prd: aaa-rbac-enterprise-readiness-part-2
feature_slug: aaa-rbac-enterprise-readiness-part-2
phase: 2
status: completed
created: 2026-03-07
updated: '2026-03-07'
prd_ref: /docs/project_plans/PRDs/features/aaa-rbac-foundation-v1.md
plan_ref: /docs/project_plans/implementation_plans/features/aaa-rbac-enterprise-readiness-part-2-v1.md
commit_refs: []
pr_refs: []
owners:
- python-backend-engineer
- data-layer-expert
contributors:
- backend-architect
tasks:
- id: ENT2-001
  name: Provider Inventory and Routing Matrix
  status: completed
  assigned_to:
  - backend-architect
  - python-backend-engineer
  dependencies: []
- id: ENT2-002
  name: Enterprise Artifact/Collection Providers
  status: completed
  assigned_to:
  - python-backend-engineer
  - data-layer-expert
  dependencies:
  - ENT2-001
- id: ENT2-003
  name: Enterprise Provider Coverage for Adjacent Services
  status: completed
  assigned_to:
  - python-backend-engineer
  - backend-architect
  dependencies:
  - ENT2-001
- id: ENT2-004
  name: Request-Lifecycle Tenant Wiring Validation
  status: completed
  assigned_to:
  - data-layer-expert
  - python-backend-engineer
  dependencies:
  - ENT2-002
  - ENT2-003
parallelization:
  batch_1:
  - ENT2-001
  batch_2:
  - ENT2-002
  - ENT2-003
  batch_3:
  - ENT2-004
total_tasks: 4
completed_tasks: 4
in_progress_tasks: 0
blocked_tasks: 0
progress: 100
---

# Phase 2: Enterprise Edition Dependency Graph Completion

## Goals
- Make the 10 API dependency providers in `dependencies.py` return enterprise repository implementations when `edition == "enterprise"`
- Thread DB session requirements and repository construction through the hexagonal provider layer
- Eliminate `Unsupported edition` failures for supported enterprise AAA surfaces

## Quality Gates
- [ ] Supported enterprise edition routes resolve repository dependencies successfully
- [ ] Artifact and collection services operate through enterprise repositories in main API mode
- [ ] Unsupported enterprise paths are explicit, documented, and non-accidental
- [ ] Tenant context and DB session lifecycles remain correct under enterprise mode
