# Ownership Resolution and Membership Semantics

**Date**: 2026-03-11
**Author**: Codex
**Status**: Draft design-spec for future planning

## Summary

SkillMeat now has a clear product direction toward three ownership tiers: `user`, `team`, and `enterprise`. The current auth and repository layers are not yet capable of resolving those scopes correctly at request time.

This spec defines the missing design layer between:
- authentication (`AuthContext`),
- membership storage (`team_members`, `enterprise_team_members`),
- resource ownership (`owner_type`, `owner_id`),
- visibility and RBAC enforcement,
- create/list/filter API behavior.

The goal is to preserve the current AAA/RBAC foundations while introducing a dedicated ownership-resolution layer, rather than overloading `AuthContext` with team or enterprise selection state.

## Why This Spec Exists

Current planning and review work established:
- `enterprise` is a true `OwnerType`,
- SkillBOM and future governance features need owner-scoped reads and writes,
- current auth primitives do not yet expose effective ownership resolution.

This gap was explicitly identified in the SkillBOM review:
- current auth exposes `user_id`, `tenant_id`, `roles`, and `scopes`,
- existing ownership assumptions were ahead of the actual auth model,
- team and enterprise visibility logic cannot safely be implemented by assuming `team_id` is already on `AuthContext`.

## Current State

### Auth context

Current request auth is intentionally lean:
- `user_id`
- `tenant_id`
- `roles`
- `scopes`

There is no team-membership list, active team selection, or effective owner target on `AuthContext`.

### Ownership model

Current documented DB-layer ownership model still only includes:
- `OwnerType.user`
- `OwnerType.team`

The current auth architecture also still documents only `user` and `team` ownership in the main reference.

### Membership storage already exists

The codebase already has membership tables:
- local: `users`, `teams`, `team_members`
- enterprise: `enterprise_users`, `enterprise_teams`, `enterprise_team_members`

So the missing piece is not storage. The missing piece is a consistent request-time resolver and filter strategy.

### Current repository behavior is still user-centric

Two important current shortcuts exist:

1. Enterprise repository auth application currently resolves `owner_id` from `auth_context.user_id` directly.
2. Shared visibility filters currently treat `visibility == "team"` as tenant-wide visible, with full team-membership checks deferred as a future concern.

Those shortcuts are acceptable for the existing two-tier transitional state, but they are not sufficient for:
- true team visibility,
- enterprise-owned resources,
- union-of-team access,
- owner-scoped attestation and SkillBOM queries.

## Problem Statement

SkillMeat needs a consistent way to answer questions like:

- Which owner scopes can this caller act as?
- Which teams does this caller currently belong to?
- Is this request operating as a user, team, or enterprise actor?
- Which owner scope should be used when creating a new resource?
- Which owner scopes should be visible when listing resources?
- How should multi-team membership behave?

Today, those questions do not have a single authoritative answer in the architecture.

## Goals

1. Add `enterprise` ownership without bloating `AuthContext`.
2. Make team visibility membership-aware instead of tenant-wide.
3. Support deterministic create/update/delete authorization by owner scope.
4. Support list/filter APIs that can safely return `user`, `team`, and `enterprise` records.
5. Preserve local-mode simplicity while keeping schema/behavior compatible with enterprise mode.

## Non-Goals

- Replace the authentication provider model.
- Put full team-membership state into bearer tokens or `AuthContext`.
- Finalize every UI workflow for owner selection.
- Redesign the visibility model beyond what is required for correct ownership resolution.

## Recommended Architecture

### 1. Keep `AuthContext` lean

Do not expand `AuthContext` to carry:
- `team_id`,
- active owner selection,
- lists of memberships,
- enterprise-management flags beyond roles/scopes already present.

Reason:
- this state is request-context enrichment, not authentication identity,
- team membership changes should not require token redesign,
- local and enterprise providers stay simpler if the resolver owns enrichment.

### 2. Add a dedicated ownership resolver layer

Introduce a core service abstraction, for example:
- `OwnershipResolver`
- `MembershipResolver`
- or `OwnershipContextService`

This service should resolve effective ownership from:
- `AuthContext`,
- current edition (`local` or `enterprise`),
- membership repositories,
- optional request parameters such as `owner_type` and `owner_id`.

### 3. Introduce a resolved ownership context object

Recommended output shape:

```python
@dataclass(frozen=True)
class ResolvedOwnershipContext:
    actor_user_id: str
    tenant_id: str | None
    is_system_admin: bool
    team_memberships: list[ResolvedTeamMembership]
    allowed_owner_types: list[str]  # user/team/enterprise
    default_owner_type: str
    default_owner_id: str
    visible_owner_scopes: list[ResolvedOwnerScope]
```

Supporting data:

```python
@dataclass(frozen=True)
class ResolvedTeamMembership:
    team_id: str
    role: str

@dataclass(frozen=True)
class ResolvedOwnerScope:
    owner_type: str
    owner_id: str
```

This object should be request-scoped and derived, not persisted.

## Membership Source of Truth

### Local mode

Use:
- `users`
- `teams`
- `team_members`

### Enterprise mode

Use:
- `enterprise_users`
- `enterprise_teams`
- `enterprise_team_members`

### Recommendation

Create a repository abstraction for membership lookup instead of reading ORM models directly in routers or business services.

Example:
- `IMembershipRepository`
- `LocalMembershipRepository`
- `EnterpriseMembershipRepository`

Core methods:
- `list_user_team_memberships(user_id, tenant_id=None)`
- `is_team_member(user_id, team_id, tenant_id=None)`
- `is_team_admin(user_id, team_id, tenant_id=None)`

## Ownership Resolution Rules

### Rule 1: Default create owner is `user`

If no owner target is specified on create:
- create as `owner_type=user`
- `owner_id=str(auth_context.user_id)`

This keeps current behavior stable and avoids accidental team or enterprise writes.

### Rule 2: Team-owned creates require explicit or unambiguous team selection

If the caller requests `owner_type=team`:
- if `owner_id` is provided, verify membership in that team,
- if `owner_id` is omitted and caller belongs to exactly one eligible team, infer that team,
- if caller belongs to multiple eligible teams, reject with actionable error requiring explicit `owner_id`.

Recommendation:
- user-owned mutations may safely default to the caller,
- team-owned and enterprise-owned mutations must not rely on ambiguous implicit scope selection.

### Rule 3: Enterprise-owned creates require system-admin authority

If the caller requests `owner_type=enterprise`:
- require `system_admin`,
- require `tenant_id` in enterprise mode,
- resolve `owner_id` to the tenant/enterprise principal identifier defined by the schema strategy for enterprise-owned records.

### Rule 4: Membership affects visibility, not just writes

For read/list/filter operations:
- user-owned private resources are visible to the owner and system admins,
- team-owned team/private resources are visible only to members of that team and system admins,
- enterprise-owned resources follow enterprise visibility/policy rules, not implicit team rules.

The current shortcut where team visibility is effectively tenant-wide must be removed.

### Rule 5: Owner scope and visibility remain separate concepts

`owner_type` answers who owns the resource.
`visibility` answers who can read or discover the resource.

Do not collapse these into one field.

## API Semantics

### Create/update endpoints

Recommended request semantics:
- `owner_type` optional
- `owner_id` optional

Behavior:
- omit both: create user-owned resource
- `owner_type=team`, `owner_id=<team>`: validate membership
- `owner_type=enterprise`: validate `system_admin`

Recommendation:
- do not require explicit scope selection for the default user-owned case,
- do require explicit scope selection for team-owned and enterprise-owned mutations.

### List/filter endpoints

Recommended query semantics:
- `owner_scope=user|team|enterprise|all`
- optional `owner_id`

Behavior:
- `user`: caller's own user-owned resources
- `team`: union of team-owned resources across caller memberships by default
- `team` + `owner_id`: one specific team if caller is a member or admin
- `enterprise`: enterprise-owned resources allowed by caller role/policy
- `all`: union of all visible scopes

### Detail endpoints

Recommended behavior:
- resolve visibility through the ownership resolver plus visibility rules,
- preserve current non-disclosure behavior where appropriate,
- continue returning 404 for unauthorized access to private resources if that remains the project standard.

## Multi-Team Membership Semantics

The system must support users belonging to multiple teams.

Recommended rules:
- read/list with `owner_scope=team` returns the union across all memberships unless narrowed,
- write/create with `owner_type=team` must resolve to exactly one team,
- no implicit “active team” should be derived from role alone,
- if UI wants an “active team,” that is a presentation-level choice, not `AuthContext`.

## Enterprise Ownership Semantics

`enterprise` should be a true `OwnerType`, not just a policy overlay.

Recommended interpretation:
- enterprise-owned resources belong to the tenant-level authority,
- they are not owned by an individual user or a team,
- `system_admin` is the acting authority for enterprise write operations,
- tenant context remains mandatory for enterprise-owned operations.

Implementation note:
- the exact `owner_id` representation for enterprise-owned rows must be standardized,
- it should not be left implicit.

Recommended standard:
- in enterprise mode, `owner_type=enterprise` should use the string form of `tenant_id` as `owner_id`.

Why:
- `tenant_id` is already present on `AuthContext`,
- it avoids a second lookup just to resolve the enterprise principal,
- repository filters can express enterprise scope directly as `(owner_type = 'enterprise' AND owner_id = :tenant_id_str)`.

Local-mode note:
- local mode should not pretend to have true tenant-backed enterprise ownership semantics,
- enterprise-owned rows in local mode should be limited to compatibility/test flows unless a later local-enterprise story is explicitly designed.

## Local-Mode Semantics

Local mode should remain simple.

Recommended behavior:
- default owner is still the local admin user,
- team ownership works only if local team rows exist,
- enterprise ownership is representable for schema compatibility and test parity, but operationally limited to local admin flows,
- local mode should not pretend to have true multi-tenant enterprise governance.

## Required Repository Changes

### Replace raw `owner_id=user_id` assumptions

Current repository helpers that derive owner scope directly from `auth_context.user_id` should be updated to accept resolved owner data from the ownership resolver for writes.

### Replace tenant-wide team visibility shortcut

Current shared visibility filters should stop treating `visibility == "team"` as tenant-wide visible.

Instead, filtering should incorporate membership-aware predicates.

### Add membership-aware filter helpers

Recommended new shared helpers:
- `apply_owner_scope_filter(...)`
- `apply_visibility_and_membership_filter(...)`
- or equivalent membership-aware select/query utilities

These should accept:
- model,
- auth context,
- resolved ownership context,
- optional requested owner scope filters.

## Performance and Caching Considerations

Ownership resolution must avoid both:
- N+1 membership lookups, and
- Python-side post-filtering of large result sets.

Recommended rule:
- the resolver should compile the caller's readable owner scopes once per request,
- repositories should turn that into SQL predicates (`=` / `IN (...)` / joins / EXISTS`) rather than loading broad result sets and filtering in memory.

Recommended resolved context additions where useful:
- `readable_owner_scopes`
- `writable_owner_scopes`
- precomputed team ID set for membership-aware filtering

Caching recommendation:
- keep the resolved ownership context request-scoped,
- allow the underlying membership graph to be cached in a shared short-lived cache only if targeted invalidation is available when memberships or roles change,
- do not tie authorization state to long-lived session caches.

## Migration and Compatibility

### Schema

Required:
- add `enterprise` to `OwnerType`,
- keep current owner columns,
- preserve `owner_id` type consistency rules.

### Behavior

Recommended rollout order:
1. Add enum/schema support for `enterprise`.
2. Add ownership resolver and membership repository layer.
3. Switch read filters to membership-aware behavior.
4. Switch write paths to use resolved ownership targets.
5. Add API-level owner selection semantics.

This avoids breaking existing user-owned flows while ownership logic is upgraded incrementally.

## Testing Requirements

Minimum future test coverage should include:
- user-owned private create/read/update/delete,
- team-owned create by team member,
- rejection of team-owned create without valid membership,
- multi-team user list behavior,
- team visibility isolation between unrelated teams,
- enterprise-owned create by system admin,
- rejection of enterprise-owned create by team admin,
- local-mode default behavior,
- 404/403 semantics for unauthorized access.

## Open Design Questions

1. What exact `owner_id` value should represent enterprise ownership?
2. Should enterprise-owned draft resources default to `private` until explicitly published?
3. Does the product need a distinct `enterprise` or `tenant` visibility mode later, especially if `public` ever becomes cross-tenant/platform-wide?
4. Which read-only APIs should accept implicit merged-scope views versus explicit owner filtering?
5. How far should shared caching go for membership graphs before invalidation complexity outweighs the benefit?

## Immediate Recommendation

Do not block current SkillBOM foundation work on this full design being implemented immediately.

But before Phase 4 and Phase 7 owner-scoped behavior proceeds, SkillMeat should have:
- `enterprise` enum support,
- an ownership resolver abstraction,
- membership repository support,
- membership-aware visibility filtering,
- clear API semantics for owner selection and filtering.

## Source References

- `/Users/miethe/dev/homelab/development/skillmeat/docs/project_plans/PRDs/refactors/enterprise-governance-3-tier.md`
- `/Users/miethe/dev/homelab/development/skillmeat/docs/project_plans/reports/skillbom-attestation-plan-review-2026-03-11.md`
- `/Users/miethe/dev/homelab/development/skillmeat/.claude/context/key-context/auth-architecture.md`
- `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/schemas/auth.py`
- `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/cache/auth_types.py`
- `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/core/repositories/filters.py`
- `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/cache/enterprise_repositories.py`
- `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/cache/models.py`
- `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/cache/models_enterprise.py`
