---
type: quick-feature-plan
feature_slug: fix-confidence-scoring-nested-detection
request_log_id: null
status: completed
completed_at: 2026-01-01T00:30:00Z
created: 2026-01-01T00:00:00Z
estimated_scope: medium
---

# Fix Confidence Scoring and Nested Artifact Detection

## Problem Summary

Two related issues in `skillmeat/core/marketplace/heuristic_detector.py`:

1. **Nested files scoring higher than parent skills**: A skill like `skills/ui-styling` (with SKILL.md) scores 54%, but nested files like `skills/ui-styling/references/shadcn-theming.md` score 75%. The depth should PENALIZE, not BOOST.

2. **Detecting artifacts inside artifacts**: Files nested inside skills are being detected as single-file artifacts when they should be excluded (they're supporting files, not separate artifacts).

## Root Causes

### Issue 1: Single-File Detection Inside Artifacts
**Location**: `_detect_single_file_artifacts()` lines 335-339

```python
# Current: Only checks if dir is inside a CONTAINER (like skills/)
for c_path, c_type in container_types.items():
    if dir_path.startswith(c_path + "/"):
        container_type = c_type
        container_dir = c_path
        break
```

This causes `skills/ui-styling/references` to be considered "inside container `skills/`" rather than "inside artifact `skills/ui-styling`".

### Issue 2: Hardcoded Confidence for Single-File
**Location**: `_detect_single_file_artifacts()` lines 374-375

```python
is_direct = dir_path == container_dir
confidence = 80 if is_direct else 75  # Hardcoded, no depth penalty!
```

Single-file artifacts get 75-80% confidence regardless of nesting depth.

### Issue 3: Low Manifest Score
Skills with SKILL.md only get ~58% confidence while nested files get 75%.

## Scope

Fix the algorithm to:
1. Exclude nested paths inside already-detected artifacts from single-file detection
2. Apply depth penalty to single-file artifact detection
3. Boost manifest-based detection to ensure parent skills score higher
4. Validate that commands/hooks/agents don't have nested subdirectories

## Affected Files

- `skillmeat/core/marketplace/heuristic_detector.py`: Core detection fixes
- `tests/core/marketplace/test_heuristic_detector.py`: Add regression tests

## Implementation Steps

1. **Identify artifact directories with manifests** → Build set of paths with manifest files
2. **Exclude nested paths from single-file detection** → Skip if inside an artifact directory
3. **Apply depth penalty to single-file confidence** → Reduce confidence for deeper nesting
4. **Validate flat structure for commands/hooks/agents** → Reduce confidence if nested dirs found
5. **Add tests for these edge cases** → Verify parent skill > nested file scoring

## Testing

- Create test with skill + nested reference file
- Verify parent skill has higher confidence than any nested file
- Verify files inside skills are not detected as artifacts
- Verify commands/agents with nested dirs get reduced confidence

## Completion Criteria

- [x] Skills with SKILL.md score higher than any nested files
- [x] Nested files inside skills are not detected as single-file artifacts
- [x] Depth penalty applies to single-file detection
- [x] Commands/hooks/agents with nested dirs get reduced confidence
- [x] Tests pass (116/116)
- [x] Build succeeds
