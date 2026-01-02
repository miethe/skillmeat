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

- **Commit(s)**: fc5b735
- **Status**: RESOLVED

---

### Duplicate React Keys When Loading More Marketplace Artifacts

**Issue**: Clicking "Load More" on marketplace source detail page (`/marketplace/sources/{id}`) caused 50+ React warnings: "Encountered two children with the same key" and app crashes.

- **Location**: `skillmeat/web/app/marketplace/sources/[id]/page.tsx:335-345`
- **Root Cause**: The `allEntries` memoization used `flatMap()` without deduplication. When backend pagination returned overlapping cursor ranges, duplicate entry IDs accumulated across pages.

  **Before**:
  ```typescript
  const allEntries = useMemo(() => {
    return catalogData?.pages.flatMap((page) => page.items) || [];
  }, [catalogData]);
  ```

- **Fix**: Added Set-based deduplication to filter duplicate entry IDs while preserving order:

  ```typescript
  const allEntries = useMemo(() => {
    if (!catalogData?.pages) return [];
    const seen = new Set<string>();
    return catalogData.pages
      .flatMap((page) => page.items)
      .filter((entry) => {
        if (seen.has(entry.id)) return false;
        seen.add(entry.id);
        return true;
      });
  }, [catalogData]);
  ```

- **Commit(s)**: db1e595
- **Status**: RESOLVED

---

## 2026-01-02

### CHECK Constraint Violation When Marking Catalog Entry as Excluded

**Issue**: Attempting to mark a marketplace catalog entry as "excluded" (via PATCH `/marketplace/sources/{id}/artifacts/{entry_id}/exclude`) failed with `IntegrityError: CHECK constraint failed: check_catalog_status`.

- **Location**: `skillmeat/api/routers/marketplace_sources.py:1288-1293` (exclude_artifact endpoint)
- **Root Cause**: The migration `20251231_2103_add_exclusion_to_catalog` added `excluded_at` and `excluded_reason` columns to support marking entries as excluded, but it **did not update** the `check_catalog_status` CHECK constraint. The database still had the old constraint: `status IN ('new', 'updated', 'removed', 'imported')` which did not include `'excluded'`.

  **Additionally**, `skillmeat/cache/schema.py` (line 257) also had the outdated constraint definition, meaning new databases created directly via schema.py would have the same issue.

  **Constraint Mismatch**:
  - SQLAlchemy model (`models.py:1474-1476`): ✅ Had `'excluded'` in constraint
  - Database (from migration): ❌ Missing `'excluded'`
  - schema.py: ❌ Missing `'excluded'`

- **Fix**: Created migration `20260102_1000_update_catalog_status_constraint` to:
  1. Drop the old `check_catalog_status` constraint
  2. Create new constraint with `status IN ('new', 'updated', 'removed', 'imported', 'excluded')`
  3. Used `batch_alter_table` for SQLite compatibility (SQLite requires table recreation to modify CHECK constraints)

  **Also** updated `skillmeat/cache/schema.py` line 257 to include `'excluded'` for consistency with new databases.

- **Files Modified**:
  - `skillmeat/cache/migrations/versions/20260102_1000_update_catalog_status_constraint.py` (new)
  - `skillmeat/cache/schema.py` (line 257 - added 'excluded')

- **Commit(s)**: 7017495
- **Status**: RESOLVED
