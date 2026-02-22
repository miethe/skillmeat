---
type: context
schema_version: 2
doc_type: context
title: "Skill-Contained Artifacts - Context"
prd: "skill-contained-artifacts-v1"
feature_slug: "skill-contained-artifacts-v1"
status: active
created: 2026-02-21
updated: 2026-02-21
prd_ref: "docs/project_plans/PRDs/features/skill-contained-artifacts-v1.md"
plan_ref: "docs/project_plans/implementation_plans/features/skill-contained-artifacts-v1.md"
---

# Skill-Contained Artifacts - Context

## Key Architecture Decisions

### D1: Companion CompositeArtifact Row (Option A)
Skills with embedded artifacts get a companion `CompositeArtifact` row with `composite_type="skill"`.
The skill `Artifact.uuid` is stored in `CompositeArtifact.metadata_json` as `{"artifact_uuid": "..."}`.
This reuses ALL existing CompositeMembership infrastructure without schema surgery.

### D2: composite_type CHECK Constraint Extension
Alembic migration adds "skill" to the CHECK constraint `('plugin', 'stack', 'suite', 'skill')`.
SQLite requires `batch_alter_table`; PostgreSQL uses standard ALTER.

### D3: Import Atomicity
All skill import writes (Artifact + CompositeArtifact + CompositeMembership rows) in single transaction.
Rollback on any failure.

### D4: Deduplication Strategy
Content-hash (SHA-256) based dedup for embedded artifacts, same as plugin import.
If embedded command already exists in collection, create CompositeMembership link only.

### D5: Feature Flag
`SKILL_CONTAINED_ARTIFACTS_ENABLED` guards import-time membership creation and coordinated deployment.
Default: false until Phase 8 testing passes.

## Key Files

| File | Purpose |
|------|---------|
| `skillmeat/cache/models.py` | CompositeArtifact, CompositeMembership models |
| `skillmeat/core/importer.py` | Import pipeline extension point |
| `skillmeat/core/services/composite_service.py` | CompositeService — add create_skill_composite() |
| `skillmeat/api/routers/artifacts.py` | GET /associations endpoint — skill UUID resolution |
| `skillmeat/core/deployment.py` | DeploymentManager — member-aware deploy |
| `skillmeat/web/components/artifact/artifact-contains-tab.tsx` | Members tab label generalization |
| `skillmeat/web/components/artifact/artifact-part-of-section.tsx` | Part of section (verify no change needed) |
| `skillmeat/web/components/marketplace/source-artifact-modal.tsx` | Source modal tab label generalization |
| `skillmeat/web/components/sync-status/sync-status-tab.tsx` | Per-member drift rows |
| `skillmeat/core/marketplace/heuristic_detector.py` | Embedded artifact detection (read-only reference) |

## Critical Path

```
Phase 1 (schema) → Phase 2 (import) → Phase 3 (API) → Phase 5 (collection UI) → Phase 8 (E2E)
```

Phase 4 (marketplace UI) and Phase 6 (deployment) are off the critical path — run concurrently with Phase 5.
Phase 7 backend (TASK-7.1, TASK-7.3) can run concurrently with Phase 5 once Phase 3 is complete.

## Important Gotchas

### metadata_json Lookup Pattern
The associations router resolves a skill artifact to its companion CompositeArtifact via:
```python
# Query pattern — may need JSON extraction depending on DB backend
session.query(CompositeArtifact).filter(
    CompositeArtifact.metadata_json["artifact_uuid"].astext == str(skill_uuid)
)
```
SQLite JSON support differs from PostgreSQL — verify query works on both. May need `func.json_extract()` for SQLite.

### SCA-P1-02 Agent Assignment Discrepancy
The implementation plan assigns SCA-P1-02 (ORM model update) to `data-layer-expert`, but the progress
tracking file assigns TASK-1.2 to `python-backend-engineer` per Opus orchestration preferences.
Either agent can handle this task — it is a small ORM model docstring/constraint update.

### Phase 2 Task Count
The implementation plan has 4 Phase 2 tasks (SCA-P2-01 through SCA-P2-04, where P2-04 is observability).
The progress tracking consolidates to 3 tasks (TASK-2.1 through TASK-2.3). Observability instrumentation
(SCA-P2-04) is folded into TASK-2.3 scope when implementing the atomic transaction wiring.

### Phase 8 Task Count
The implementation plan has 4 Phase 8 tasks (including SCA-P8-04: enable feature flag).
The progress tracking covers 3 tasks (TASK-8.1 through TASK-8.3). Feature flag enablement
(SCA-P8-04) is folded into TASK-8.3 scope as a final step after benchmarks pass.

### Composite Service File Location
`skillmeat/core/services/composite_service.py` may or may not exist yet — verify before delegating.
The predecessor composite-artifact-infrastructure plan created it; check `skillmeat/core/services/`.
Fallback: `skillmeat/core/composite_service.py` or inline in `importer.py`.

## Blockers & Notes

(Empty — will be populated during implementation)
