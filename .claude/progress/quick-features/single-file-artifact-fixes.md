---
type: quick-feature-plan
feature_slug: single-file-artifact-fixes
request_log_id: null
status: completed
created: 2026-01-02T10:00:00Z
completed_at: 2026-01-02T10:30:00Z
estimated_scope: small
---

# Single-File Artifact Naming and Content Capture Fixes

## Scope

Fix two bugs for single-file artifacts (Commands, Agents, Hooks) in marketplace detection:
1. Remove file extension from artifact names (e.g., "pr.md" → "pr")
2. Capture file contents for display in the Contents tab of CatalogEntry modal

## Affected Files

### Backend (Python)
- `skillmeat/marketplace/heuristic_detector.py`: Fix name extraction at line ~1237

### Frontend (TypeScript)
- `skillmeat/web/components/CatalogEntryModal.tsx`: Handle single-file artifacts in Contents tab
- `skillmeat/web/hooks/use-catalog-files.ts`: May need adjustment for single-file artifacts

## Implementation Steps

1. **Fix artifact name extraction** → @python-backend-engineer
   - In `matches_to_artifacts()`, strip `.md` extension from single-file artifact names
   - Only apply to Commands, Agents, Hooks (not Skills which are directories)

2. **Verify/fix content capture for single-file artifacts** → @ui-engineer-enhanced
   - Ensure single-file artifacts show their content in Contents tab
   - For single-file artifacts, the artifact itself is the only file to display
   - May need to handle case where artifact_path is the file path

## Testing
- Run pytest on marketplace tests
- Manual verification with catalog entries
- Check Commands and Agents display correct names without extensions
- Verify Contents tab shows file content for single-file artifacts

## Completion Criteria
- [x] Artifact names for Commands/Agents/Hooks don't include .md extension
- [x] Contents tab displays file content for single-file artifacts
- [x] Tests pass
- [x] Build succeeds
