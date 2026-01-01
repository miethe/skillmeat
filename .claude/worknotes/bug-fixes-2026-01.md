# Bug Fixes - January 2026

## 2026-01-01

### Single-File Artifacts Not Detected in Marketplace Sources

**Issue**: Marketplace source scanner only detected directory-based artifacts (directories with manifest files like `COMMAND.md`). Single-file artifacts (individual `.md` files directly inside container directories) were not detected.

- **Location**: `skillmeat/core/marketplace/heuristic_detector.py:analyze_paths()`
- **Root Cause**: The heuristic detector only iterated through directories in `dir_to_files`, looking for manifest files within each directory. It never considered individual `.md` files as artifacts themselves.

  **Example repository**: `mrgoonie/claudekit-skills`
  ```
  commands/
    git/
      cm.md     <- NOT detected (single-file command)
      cp.md     <- NOT detected
      pr.md     <- NOT detected
    use-mcp.md  <- NOT detected (single-file command)
  agents/
    mcp-manager.md  <- NOT detected (single-file agent)
  ```

  Expected: 5 commands, 1 agent, multiple skills
  Actual: Only skills detected (and `commands/git` as 1 incorrect artifact)

- **Fix**: Added single-file artifact detection in heuristic detector:
  1. New method `_detect_single_file_artifacts()` that finds `.md` files directly in or nested under typed containers (commands/, agents/, hooks/, mcp/)
  2. New method `_is_single_file_grouping_directory()` to prevent directory-based detection from picking up grouping directories
  3. Modified `analyze_paths()` to call single-file detection before directory-based detection
  4. Excludes README.md, CHANGELOG.md, and manifest files (SKILL.md, COMMAND.md, etc.)
  5. Computes proper `organization_path` for nested grouping directories

- **Files Modified**:
  - `skillmeat/core/marketplace/heuristic_detector.py` (2 new methods + 1 modified method)
  - `tests/core/marketplace/test_heuristic_detector.py` (15 new tests in TestSingleFileArtifacts class)

- **Verification**:
  - All 116 heuristic detector tests pass (101 existing + 15 new)
  - No regressions in directory-based detection
  - `test_claudekit_structure` specifically tests the real-world repository structure

- **Commit(s)**: 876a370
- **Status**: RESOLVED
