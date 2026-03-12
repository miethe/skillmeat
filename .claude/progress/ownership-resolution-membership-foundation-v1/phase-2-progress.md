---
type: progress
schema_version: 2
doc_type: progress
prd: "ownership-resolution-membership-foundation"
feature_slug: "ownership-resolution-membership-foundation"
phase: 2
status: pending
created: 2026-03-12
updated: 2026-03-12
prd_ref: /docs/project_plans/PRDs/refactors/enterprise-governance-3-tier.md
plan_ref: /docs/project_plans/implementation_plans/refactors/ownership-resolution-membership-foundation-v1.md
commit_refs: []
pr_refs: []

owners: ["opus-orchestrator"]
contributors: ["python-backend-engineer"]

tasks:
  - id: "TASK-2.1"
    title: "Add IMembershipRepository interface"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: []
  - id: "TASK-2.2"
    title: "Define resolved ownership context DTOs"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: []
  - id: "TASK-2.3"
    title: "Implement LocalMembershipRepository"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["TASK-2.1"]
  - id: "TASK-2.4"
    title: "Implement EnterpriseMembershipRepository"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["TASK-2.1"]
  - id: "TASK-2.5"
    title: "Implement OwnershipResolver service"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["TASK-2.1", "TASK-2.2", "TASK-2.3", "TASK-2.4"]
  - id: "TASK-2.6"
    title: "Add tests for membership repos and resolver"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["TASK-2.5"]

parallelization:
  batch_1: ["TASK-2.1", "TASK-2.2"]
  batch_2: ["TASK-2.3", "TASK-2.4"]
  batch_3: ["TASK-2.5"]
  batch_4: ["TASK-2.6"]
---

# Phase 2: Membership Repositories & Resolver

## Objective
Add membership repository abstractions and request-time ownership resolver.

## Key Constraints
- Resolver stays request-scoped, does not persist state
- Multi-team memberships represented without changing AuthContext
- Local mode: single implicit user, no membership lookup needed (fallback to user-owned)
- Enterprise: membership-aware via enterprise_team_members table

## Exit Criteria
- Resolver derives default, readable, writable scopes from AuthContext
- Multi-team memberships represented
- Resolver is request-scoped, stateless
