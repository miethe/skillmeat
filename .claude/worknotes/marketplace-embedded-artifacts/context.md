---
type: context
schema_version: 2
doc_type: context
prd: "marketplace-embedded-artifacts"
feature_slug: "marketplace-embedded-artifacts"
plan_ref: "docs/project_plans/implementation_plans/bugs/marketplace-embedded-artifacts-v1.md"
created: "2026-02-21"
updated: "2026-02-21"
---

# marketplace-embedded-artifacts - Context Worknotes

## Key Files

| File | Purpose |
|------|---------|
| `skillmeat/core/marketplace/heuristic_detector.py` | Primary fix: lines 770-1008 (_detect_single_file_artifacts), 1128-1228 (skill/composite detection) |
| `skillmeat/core/marketplace/github_scanner.py` | Scanner orchestration; propagates DetectedArtifact to storage |
| `skillmeat/api/routers/marketplace_sources.py` | File serving endpoint: lines 5429-5600 |
| `skillmeat/web/sdk/services/MarketplaceSourcesService.ts` | Frontend SDK URL construction: lines 1005-1026 |
| `skillmeat/web/app/marketplace/sources/[id]/page.tsx` | Source detail page rendering |

## Bug Reproduction

Source: `5e2a8c2c-25b9-42e6-bd96-cf6330b4df0d`
Artifact: `skills/agentient-frontend-tools/skills/agentient-frontend-ui/commands/add-animation.md`
Error: 404 on file content load; path duplication in URL

## Observations

(Agents add observations here during implementation)
