---
type: context
schema_version: 2
doc_type: context
prd: "workflow-artifact-wiring"
feature_slug: "workflow-artifact-wiring"
status: active
created: 2026-03-10
updated: 2026-03-10
prd_ref: "docs/project_plans/PRDs/features/workflow-artifact-wiring-v1.md"
plan_ref: "docs/project_plans/implementation_plans/features/workflow-artifact-wiring-v1.md"
---

# Workflow-Artifact Wiring — Agent Context

## Feature Summary

Wire the Workflow Orchestration Engine into the Artifact Collection system via a write-through sync service. Workflow definitions become first-class Tier 3 artifacts.

## Artifact Tiering Model

See [ADR-008](docs/project_plans/architecture/ADRs/adr-008-artifact-tiering-composition-hierarchy.md) for the formal hierarchy. Key point: Workflows are Tier 3 (Process/Distribution) — highest tier, references T0-T2 only.

## Key Design Decisions

1. **Source of truth**: `workflows` table is authoritative; `artifacts` record is derived write-through
2. **Failure isolation**: Sync failure doesn't roll back primary workflow write
3. **Idempotent upsert**: ON CONFLICT DO UPDATE keyed on workflow_id
4. **Feature flag**: `workflow_artifact_sync_enabled` (default true)
5. **Role validation**: Advisory, non-blocking — warnings not errors
6. **DeploymentSetMember**: New `workflow_id` column, mutually exclusive with existing columns

## Key File Map

| Component | File |
|-----------|------|
| Workflow SWDL models | `skillmeat/core/workflow/models.py` |
| Workflow service (hook here) | `skillmeat/core/workflow/service.py` |
| Workflow repository | `skillmeat/cache/workflow_repository.py` |
| DB models (artifacts + deployment sets) | `skillmeat/cache/models.py` |
| NEW: Sync service | `skillmeat/core/services/workflow_artifact_sync_service.py` |
| Workflow API | `skillmeat/api/routers/workflows.py` |
| Deployment set API | `skillmeat/api/routers/deployment_sets.py` |
| Artifact collection API | `skillmeat/api/routers/artifacts.py` |
| Frontend artifact types | `skillmeat/web/types/artifact.ts` |
| Collection page | `skillmeat/web/app/collection/page.tsx` |
| Manage page | `skillmeat/web/app/manage/page.tsx` |
| Type tabs (already fixed) | `skillmeat/web/components/shared/artifact-type-tabs.tsx` |

## Blockers & Notes

(none yet)

## Out-of-Scope Futures

- **Tier 3 deployment**: Deploy workflow → deploy all constituent artifacts (future PRD)
- **Backstage workflow scaffolding**: Workflows as IDP scaffold targets
- **Multi-target deployment**: CLI vs web vs Backstage vs enterprise API
- **Marketplace distribution**: Publish/import workflows
- **Visual dependency graph**: Workflow → artifact tree UI

## Origin Context

This feature was identified when the Workflows tab on /collection was empty despite workflow definitions existing in the engine. Root cause: two isolated systems (workflow engine + artifact collection) were built without integration. The workflow PRD explicitly specified workflows as a first-class artifact type, but the implementation split them into separate DB tables without a sync bridge.
