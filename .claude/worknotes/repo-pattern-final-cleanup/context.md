---
type: context
schema_version: 2
doc_type: context
prd: "repo-pattern-final-cleanup"
feature_slug: "repo-pattern-final-cleanup"
created: "2026-03-06"
updated: "2026-03-06"
---

# Context: Repository Pattern Final Cleanup

## Key Files

| Asset | Path |
|-------|------|
| Implementation plan | `docs/project_plans/implementation_plans/refactors/repo-pattern-final-cleanup-v1.md` |
| Progress tracking | `.claude/progress/repo-pattern-final-cleanup/all-phases-progress.md` |
| Repository ABCs | `skillmeat/core/interfaces/repositories.py` |
| Repository DTOs | `skillmeat/core/interfaces/dtos.py` |
| DB implementations | `skillmeat/cache/repositories.py` (DbUserCollectionRepo@5522, DbCollectionArtifactRepo@6247) |
| DI aliases | `skillmeat/api/dependencies.py` (DbUserCollectionRepoDep, DbCollectionArtifactRepoDep) |
| Target: user_collections | `skillmeat/api/routers/user_collections.py` (36 violations) |
| Target: artifact_history | `skillmeat/api/routers/artifact_history.py` (3 violations) |

## Decisions

- Single progress file (all-phases) since total plan is small (4 phases, 14 tasks)
- Phase 3 runs in parallel with Phase 2 (different files, no dependencies)
- No new PRD needed — this is a cleanup task blocking enterprise-db-storage-v1

## Out of Scope (captured in MeatyCapture)

- Services layer violations (40+ in artifact_cache_service.py, artifact_metadata_service.py) — REQ-20260306-skillmeat
- ORM model imports in 5 other routers (structural, not functional) — REQ-20260306-skillmeat
