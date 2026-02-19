---
type: context
schema_version: 2
doc_type: context
prd: composite-artifact-ux-v2
feature_slug: composite-artifact-ux-v2
title: "Composite Artifact UX v2 — Context Worknotes"
created: "2026-02-19"
updated: "2026-02-19"
prd_ref: "docs/project_plans/PRDs/features/composite-artifact-ux-v2.md"
plan_ref: "docs/project_plans/implementation_plans/features/composite-artifact-ux-v2.md"
---

# Composite Artifact UX v2 — Context Worknotes

This file captures architecture decisions, open questions, and cross-phase context for the Composite Artifact UX v2 feature. It grows organically as agents work through the 5 phases.

---

## Architecture Notes

- **v1 Infrastructure**: CompositeService, CompositeMembershipRepository, and ORM models were built in the composite-artifact-infrastructure-v1 branch. v2 builds the UX layer on top.
- **Type System**: `'composite'` is added to the `ArtifactType` union. The user-facing label is `Plugin` (not `Composite`).
- **API Surface**: 6 new CRUD endpoints under `/api/v1/composites` plus member management sub-routes.
- **Dual-Stack Data Flow**: CLI reads/writes filesystem; web reads from DB cache. Composite CRUD goes through the API (DB-first), with cache refresh on mutations.
- **Atomic Import**: Composite import creates parent + all children in a single transaction. Partial failure rolls back.
- **Color Token**: `text-indigo-500` for all plugin UI (icon, badges, accents).
- **Icon**: Lucide `Blocks` icon for plugin type.

---

## Open Questions

- Does `AssociationsDTO` from v1 already cover the response shape needed for CRUD endpoints, or do we need new schemas?
- Is `@dnd-kit/sortable` already in the dependency tree for drag-to-reorder in MemberList?
- What is the exact heuristic for source classification (detecting if a marketplace source is composite)?
- Should `skillmeat composite create` support `--description` and `--tags` flags, or just positional args for members?

---

## Key Decisions

| Decision | Rationale | Date |
|----------|-----------|------|
| User-facing label is "Plugin" not "Composite" | Friendlier terminology for end users; "composite" stays in code | 2026-02-19 |
| 6 CRUD endpoints (not 3+3) | Separate member management endpoints allow fine-grained operations | 2026-02-19 |
| Phase 5 (CLI) runs in parallel with Phase 4 (UI) | Both depend on Phase 1 API only; no mutual dependency | 2026-02-19 |

---

## Cross-Phase Dependencies

```
Phase 1 (Type System + CRUD API)
  └── Phase 2 (Marketplace Discovery) ── depends on Phase 1
  └── Phase 3 (Import Flow) ── depends on Phase 1 + Phase 2
  └── Phase 4 (Collection UI) ── depends on Phase 1 + Phase 3
  └── Phase 5 (CLI) ── depends on Phase 1 only (parallel with Phase 4)
```

### Key Cross-Phase Task Dependencies

- CUX-P3-01 depends on CUX-P1-01 (type union) and CUX-P2-06 (source classification badge)
- CUX-P3-04 depends on CUX-P1-08 (POST create endpoint)
- CUX-P4-03 depends on CUX-P1-01 (type union)
- CUX-P4-10 depends on CUX-P1-08 (POST create endpoint)
- CUX-P5-01 and CUX-P5-02 depend on CUX-P1-05 (CompositeService verification)

---

## Observations

_This section grows as agents encounter noteworthy patterns, gotchas, or learnings during implementation._
