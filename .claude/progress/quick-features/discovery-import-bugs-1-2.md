---
type: quick-feature-plan
feature_slug: discovery-import-bugs-1-2
request_log_id: null
status: completed
created: 2026-01-12T12:00:00Z
completed_at: 2026-01-12T18:30:00Z
estimated_scope: medium
---

# Discovery & Import Bug Fixes (Bugs 1 & 2)

## Scope

Fix two critical bugs preventing import of file-based artifacts (commands, agents):
1. Bug 1: Importer requires directories but commands/agents are single files
2. Bug 2: Discovery existence check only looks for directories, missing file-based artifacts

## Affected Files

- `skillmeat/core/importer.py`: Update `_validate_artifact_structure()` to handle file-based artifacts
- `skillmeat/core/discovery.py`: Update `check_artifact_exists()` to detect file-based artifacts

## Implementation Steps

1. Fix importer validation → @python-backend-engineer
   - Import ARTIFACT_SIGNATURES from artifact_detection.py
   - Check signature.is_directory to determine expected structure
   - Allow single files for commands/agents, require directories for skills
   - Update metadata file validation for single-file artifacts

2. Fix discovery existence check → @python-backend-engineer
   - Import ARTIFACT_SIGNATURES from artifact_detection.py
   - For file-based artifacts, search for .md files (direct and nested)
   - For directory-based artifacts, keep current behavior
   - Apply to both collection and project checks

## Testing

- Run existing tests to ensure no regressions
- Quality gate validation (pnpm test, typecheck, lint)

## Completion Criteria

- [x] Implementation complete
- [x] Tests pass
- [x] Build succeeds
- [x] Commands can import without "not a directory" error
- [x] Deployed artifacts show correct status in discovery
