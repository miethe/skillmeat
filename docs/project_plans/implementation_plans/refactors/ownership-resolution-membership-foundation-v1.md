---
schema_version: 2
doc_type: implementation_plan
title: "Ownership Resolution & Membership Foundation - Implementation Plan"
description: >
  Prerequisite refactor plan for request-time ownership resolution, membership-aware
  visibility filtering, and enterprise owner-scope support across local and enterprise editions.
audience:
  - ai-agents
  - backend-engineers
  - platform-engineers
  - security-engineers
tags:
  - implementation-plan
  - planning
  - refactor
  - rbac
  - ownership
  - enterprise
created: 2026-03-12
updated: 2026-03-12
category: product-planning
status: draft
priority: HIGH
risk_level: high
feature_slug: ownership-resolution-membership-foundation
prd_ref: /docs/project_plans/PRDs/refactors/enterprise-governance-3-tier.md
plan_ref: null
scope: backend
effort_estimate: "16-22 story points"
timeline: "3-4 weeks"
related_documents:
  - /docs/project_plans/PRDs/refactors/enterprise-governance-3-tier.md
  - /docs/project_plans/design-specs/ownership-resolution-and-membership-semantics.md
  - /docs/project_plans/implementation_plans/features/skillbom-attestation-v1.md
  - /.claude/context/key-context/auth-architecture.md
---

# Ownership Resolution & Membership Foundation - Implementation Plan

**Complexity**: Medium-Large | **Track**: Prerequisite Refactor | **Estimated Effort**: 16-22 story points | **Timeline**: 3-4 weeks

---

## Executive Summary

This plan establishes the missing ownership-resolution layer needed before SkillBOM Phase 4 and Phase 7 can safely implement `user|team|enterprise` owner-scoped behavior. It introduces:

- `enterprise` owner-type support,
- membership repository abstractions,
- a request-time ownership resolver,
- membership-aware repository filters,
- API semantics for explicit team and enterprise owner selection.

This is a prerequisite track for SkillBOM owner-scoped queries and a reusable foundation for the broader enterprise-governance roadmap.

## Why This Is a Prerequisite

Current gaps:
- `AuthContext` does not carry resolved team or enterprise scope.
- current visibility helpers still treat `visibility == "team"` as tenant-wide visible,
- enterprise repositories still derive write ownership directly from `auth_context.user_id`,
- SkillBOM Phase 4 and Phase 7 assume owner-scoped reads/writes that current infrastructure cannot enforce safely.

## Scope

In scope:
- owner enum/schema alignment,
- canonical enterprise `owner_id` rule,
- membership lookup repositories,
- request-time ownership resolver,
- membership-aware visibility and owner-scope filtering,
- API/service validation semantics for owner-targeted mutations.

Out of scope:
- full enterprise sync/governance rollout logic,
- frontend owner-selection UX beyond contract definition,
- global visibility redesign beyond resolver compatibility,
- SkillBOM restore architecture.

## Phase Overview

| Phase | Title | Duration | Effort | Key Deliverables |
|-------|-------|----------|--------|------------------|
| 1 | Schema & Enum Alignment | 1 wk | 4-5 pts | `OwnerType.enterprise`, canonical enterprise owner-id rule, DTO/migration alignment |
| 2 | Membership Repositories & Resolver | 1 wk | 5-6 pts | `IMembershipRepository`, local/enterprise implementations, `OwnershipResolver` |
| 3 | Filter & Repository Integration | 1 wk | 5-7 pts | membership-aware query helpers, repository write/read integration |
| 4 | API Contract, Tests, Docs | 1 wk | 4-4 pts | explicit owner-selection semantics, test coverage, implementation guidance |

## Detailed Breakdown

### Phase 1: Schema & Enum Alignment

Tasks:
- add `enterprise` to `OwnerType`,
- standardize enterprise ownership to `owner_type=enterprise`, `owner_id=str(tenant_id)` in enterprise mode,
- update API schemas and DTOs that expose owner fields,
- add migrations/tests covering enum expansion and compatibility.

Exit criteria:
- `OwnerType.enterprise` available in code and schema paths,
- enterprise owner-id convention documented and enforced in tests,
- no existing user/team behavior regresses.

### Phase 2: Membership Repositories & Resolver

Tasks:
- add `IMembershipRepository` abstraction,
- implement local membership lookups over `team_members`,
- implement enterprise membership lookups over `enterprise_team_members`,
- add request-time `OwnershipResolver` / `OwnershipContextService`,
- define resolved ownership context DTOs for readable/writable scopes.

Exit criteria:
- resolver can derive default, readable, and writable scopes from `AuthContext`,
- multi-team memberships are represented without changing `AuthContext`,
- resolver stays request-scoped and does not persist state.

### Phase 3: Filter & Repository Integration

Tasks:
- replace tenant-wide team visibility shortcut with membership-aware filtering,
- replace raw `owner_id=user_id` write assumptions with resolved owner target input,
- add shared SQLAlchemy helpers for owner-scope and membership-aware filtering,
- ensure repositories use SQL predicates rather than Python-side post-filtering,
- benchmark common list queries for scope-union performance.

Exit criteria:
- team visibility is membership-aware in both local and enterprise code paths,
- repositories accept resolved owner targets for writes,
- list/detail queries do not rely on Python-side filtering,
- query performance is acceptable for users with multiple team memberships.

### Phase 4: API Contract, Tests, Docs

Tasks:
- define mutation semantics:
  - default omitted owner target => user-owned
  - explicit team selection required for team-owned writes
  - explicit enterprise selection required for enterprise-owned writes
- define list/filter semantics for `owner_scope=user|team|enterprise|all`,
- add integration tests for user/team/enterprise ownership cases,
- update architecture/docs for ownership resolver usage and anti-patterns.

Exit criteria:
- API semantics documented and enforced,
- integration tests cover user/team/enterprise read/write cases,
- SkillBOM Phase 4 and Phase 7 can depend on this plan as completed prerequisite work.

## Key Files

- `skillmeat/cache/auth_types.py`
- `skillmeat/api/schemas/auth.py`
- `skillmeat/core/interfaces/repositories.py`
- `skillmeat/core/repositories/filters.py`
- `skillmeat/cache/enterprise_repositories.py`
- local membership/ownership repository module(s)
- enterprise membership/ownership repository module(s)
- `skillmeat/api/dependencies.py` or equivalent DI wiring

## Quality Gates

- `enterprise` owner scope available in enums, DTOs, and persistence paths.
- Membership-aware filtering replaces tenant-wide team visibility shortcut.
- Repositories consume resolved ownership context rather than inferring owner from raw `AuthContext.user_id`.
- Multi-team users can read unioned team scope and write to exactly one explicit target team.
- System admins can create enterprise-owned records using canonical tenant-based owner identifiers.
- Local mode remains backward-compatible for default user-owned flows.

## Dependencies

Blocks:
- SkillBOM [skillbom-attestation-v1.md](/Users/miethe/dev/homelab/development/skillmeat/docs/project_plans/implementation_plans/features/skillbom-attestation-v1.md) Phase 4 and Phase 7 close-out
- broader enterprise governance implementation from [enterprise-governance-3-tier.md](/Users/miethe/dev/homelab/development/skillmeat/docs/project_plans/PRDs/refactors/enterprise-governance-3-tier.md)

Depends on:
- existing AAA/RBAC foundation and auth provider wiring
- current local and enterprise membership tables

## Success Metrics

- ownership-resolution unit/integration tests pass in local and enterprise code paths,
- no tenant-wide leakage for team visibility,
- union-of-team scope list queries stay SQL-backed and performant,
- SkillBOM owner-scoped phases can reference this plan as a completed prerequisite instead of embedding ad hoc resolver work.
