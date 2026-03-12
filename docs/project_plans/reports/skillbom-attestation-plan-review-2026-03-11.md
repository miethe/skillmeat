# SkillBOM Attestation Plan Review

**Date**: 2026-03-11
**Status**: Review Captured
**Scope**: `docs/project_plans/implementation_plans/features/skillbom-attestation-v1.md` and linked phase plans

## Executive Summary

The SkillBOM plan has strong coverage at the feature level, but the original version had four major architecture gaps:

1. The ownership model assumed `enterprise` and team-resolution primitives that do not yet exist in the current auth layer.
2. The history phase overlapped with the existing artifact-history/version-lineage surface without defining a clean boundary.
3. The Git integration used the wrong hook lifecycle for commit-message mutation and commit-to-BOM linkage.
4. The Backstage phase mixed backend scaffolder work with frontend EntityPage UI work inside a backend-only package.

Following stakeholder discussion on 2026-03-11, the plan direction is now:

- Keep a **separate artifact activity history** for all artifact actions and changes.
- Treat **SkillBOM** as a provenance-focused packaging/view over selected activity records plus snapshots.
- Add **`enterprise` as a true `OwnerType`** for this feature track.
- Split **Backstage backend integration** from any future Backstage frontend EntityPage card work.

This report captures the review findings and the agreed design adjustments so later discussion can reference a stable record.

## Stakeholder Decisions

### Decision 1: Separate activity history from BOM provenance

Stakeholder intent:

- Maintain a separate history for all artifacts covering any relevant change or action.
- Treat BOMs as a specific provenance package built from selected history items, similar to SBOM usage.

Recommended design:

- Keep the existing version-lineage / modal history surface intact.
- Introduce a separate **artifact activity history** model and service for audit-style events:
  - artifact create/update/delete
  - deploy/undeploy
  - sync/pull/push/merge
  - memory-item changes
  - BOM generate/sign/verify/restore
  - attestation create/verify/revoke
- Build BOM provenance views from:
  - the activity log
  - BOM snapshot state
  - attestation metadata

Wider-ranging effects:

1. The product will now have **two distinct history concepts**:
   - version lineage / rollback history
   - audit/activity/provenance history
2. UI copy and route naming must make that distinction explicit, otherwise users will read both as “history” and get confused.
3. API and hook naming should avoid colliding with the existing `/api/v1/artifacts/{id}/history` surface.
4. Capture must happen at **service/repository boundaries**, not ORM listeners, because filesystem-first write flows would otherwise be missed.

Recommended rule:

- Existing artifact history remains the rollback/version timeline.
- New activity history is the authoritative audit stream for provenance and attestation.
- SkillBOM is a filtered/package layer, not the primary event store.

### Decision 2: `enterprise` is a real owner type

Stakeholder intent:

- `enterprise` will be a true `OwnerType`.
- If needed, it can be added in this implementation rather than deferred.

Recommended implementation consequence:

- Treat `enterprise` enum support as a prerequisite for Phases 4 and 7.
- Do not assume `team_id` is present on `AuthContext`; instead resolve effective ownership via an ownership resolver/membership lookup.
- Update RBAC tests and visibility rules to cover:
  - user-owned records
  - team-owned records
  - enterprise-owned records
- Standardize enterprise-owned records on a canonical owner identifier. Recommended direction: use the string form of `tenant_id` for `owner_type=enterprise` in enterprise mode.

### Decision 3: Split Backstage backend from frontend

Stakeholder intent:

- Backstage backend/scaffolder work should be separated from any future frontend card UI.

Recommended implementation consequence:

- Current plan version should cover:
  - IDP API payload
  - scaffolder backend actions
  - backend-side tests
- A future follow-on plan should cover:
  - Backstage frontend package
  - EntityPage card
  - frontend E2E in a real Backstage app

## Findings

### 1. Ownership and RBAC assumptions were ahead of the current auth model

The original plan used `owner_scope=user|team|enterprise`, team-scoped filtering, and `enterprise` ownership, but the current auth primitives only expose `user_id`, `tenant_id`, `roles`, and `scopes`, and the existing enum only includes `user` and `team`.

Impact:

- Phase 4 visibility logic was underspecified.
- Phase 7 API contracts depended on owner types not yet represented in code.

Resolution:

- Update the plan to explicitly add `enterprise` ownership.
- Introduce ownership resolution as a first-class design concern rather than assuming raw `team_id` on `AuthContext`.
- Ensure the resolver compiles readable/writable owner scopes once per request and passes SQL-friendly scope data to repositories, rather than relying on Python-side filtering.

### 2. The history phase needed a sharper architectural boundary

The original plan positioned the new history model as if it were replacing or directly extending the current artifact-history surface, but SkillMeat already has a unified version/deployment/analytics history used by the web app.

Impact:

- High risk of duplicate timelines with ambiguous semantics.
- High risk of missing filesystem-first mutations if implemented via ORM listeners.

Resolution:

- Reframe the new system as **artifact activity history**, distinct from version lineage.
- Capture events through explicit service/repository/domain-event calls.
- Let BOM surfaces query/select from activity history rather than owning the primary event store.

### 3. Git hook semantics were incorrect

The original Phase 5 used a `pre-commit` hook to mutate the commit message and referenced SHA-256 using a 40-character hash length.

Impact:

- The hook plan would not reliably append commit-message metadata.
- Commit-to-snapshot linkage would be fragile.

Resolution:

- Use the correct hook lifecycle:
  - `prepare-commit-msg` or `commit-msg` for footer mutation
  - `post-commit` for final commit SHA linkage
- Standardize on `sha256:<64-char-hex>`.

### 4. Backstage frontend work was assigned to a backend-only package

The original Phase 10 attempted to place a React EntityPage card in the existing `backstage-plugin-scaffolder-backend` package.

Impact:

- Scope confusion between backend scaffolder module and frontend UI package.
- Invalid deliverables for the current repo layout.

Resolution:

- Restrict this plan version to backend/scaffolder integration.
- Track a separate frontend follow-on.

### 5. Web and CLI extension points needed to align with existing surfaces

The original plan referenced new files such as `skillmeat/cli.py` and introduced new history hooks without enough regard for current extension points.

Impact:

- Risk of parallel CLI entry points.
- Risk of replacing existing history UI patterns instead of extending them.

Resolution:

- Anchor CLI work in `skillmeat/cli/__init__.py` and `skillmeat/cli/commands/`.
- Preserve the existing version-history UI and add provenance/activity UI beside it.

## Plan Revisions Recommended

### Main plan

- Reword history as **artifact activity history**.
- Reword BOM as a provenance package/view over activity history plus snapshots.
- Update Phase 5 to use the proper Git hook lifecycle.
- Narrow Phase 10 to backend/scaffolder scope.
- Treat ownership resolution as a prerequisite implementation track before SkillBOM Phase 4 / 7 owner-scoped behavior closes.
- Track the prerequisite work explicitly in `/docs/project_plans/implementation_plans/refactors/ownership-resolution-membership-foundation-v1.md`.

### Phase 3-4

- Replace ORM-listener-first capture with explicit activity-event emission.
- Introduce ownership resolution for `user|team|enterprise`.
- Avoid tenant-wide shortcuts for team visibility; use membership-aware repository filtering.

### Phase 5-6

- Replace pre-commit-only design with hook-chain design.
- Fix hash format and commit-linkage semantics.

### Phase 7-8

- Separate general activity-history API from BOM-specific APIs conceptually.
- Update CLI deliverables to current package structure.

### Phase 9-10

- Keep existing artifact version-history UI intact.
- Add provenance/activity UI as a separate surface.
- Limit current Backstage scope to backend integration and scaffolder actions.

## Recommended Next Discussion Topics

1. Final API naming for the new activity history surface versus the existing artifact history surface.
2. Exact ownership-resolution source for team and enterprise scope.
3. Whether a distinct `enterprise` or `tenant` visibility mode is needed later if `public` semantics expand beyond tenant scope.
4. Whether the future Backstage frontend card deserves a separate PRD/implementation plan now or later.
