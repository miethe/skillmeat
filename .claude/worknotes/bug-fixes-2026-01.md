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

---

### Single-File Artifact Content Fetch 404 Error

**Issue**: Clicking on a single-file artifact (Command, Agent) in the marketplace catalog and viewing the Contents tab resulted in a 404 error from GitHub API. The URL was malformed, duplicating the filename.

- **Location**: `skillmeat/api/routers/marketplace_sources.py:get_artifact_file_content()`
- **Root Cause**: The file content endpoint concatenated `artifact_path` and `file_path` unconditionally:
  ```python
  full_file_path = f"{artifact_path}/{file_path}"
  ```

  For single-file artifacts:
  - `artifact_path` = `.claude/commands/use-mcp.md` (the file itself)
  - `file_path` = `use-mcp.md` (filename from file tree)
  - Result: `.claude/commands/use-mcp.md/use-mcp.md` (WRONG!)

  **API Error**:
  ```
  404 Client Error: Not Found for url: https://api.github.com/repos/mrgoonie/claudekit-skills/contents/.claude/commands/use-mcp.md/use-mcp.md?ref=main
  ```

- **Fix**: Added detection for single-file artifacts before constructing the full path:
  ```python
  if artifact_path.endswith(f"/{file_path}") or artifact_path == file_path:
      full_file_path = artifact_path  # Single-file: use artifact_path directly
  else:
      full_file_path = f"{artifact_path}/{file_path}"  # Directory: concatenate
  ```

- **Commit(s)**: cacb26c
- **Status**: RESOLVED

---

## 2026-01-03

### Modal Opens After Excluding Artifact

**Issue**: After clicking "Mark as Excluded" in the ExcludeArtifactDialog, the artifact detail modal would open unexpectedly.

- **Location**: `skillmeat/web/components/marketplace/exclude-artifact-dialog.tsx:84-89`
- **Root Cause**: The AlertDialogAction's onClick handler only called `e.preventDefault()` but not `e.stopPropagation()`. Additionally, when the dialog closed, focus would return to the underlying card element which could trigger a click.
- **Fix**:
  1. Added `e.stopPropagation()` to AlertDialogAction's onClick handler
  2. Added `onCloseAutoFocus={(e) => e.preventDefault()}` to AlertDialogContent to prevent focus from returning to the card
- **Commit(s)**: 4eb6d8a
- **Status**: RESOLVED

---

### Nested `<p>` Hydration Error in ExcludeArtifactDialog

**Issue**: Console errors appeared when clicking "Not an artifact" button: "In HTML, `<p>` cannot be a descendant of `<p>`" causing hydration errors.

- **Location**: `skillmeat/web/components/marketplace/exclude-artifact-dialog.tsx:70-80`
- **Root Cause**: `AlertDialogDescription` is a Radix UI primitive that renders as a `<p>` element. The description content used `<p>` tags inside it, creating invalid nested paragraph elements in HTML.
- **Fix**: Changed inner `<p>` tags to `<span className="block">` elements which render as block-level elements but are valid inside a `<p>` parent.
- **Commit(s)**: 4eb6d8a
- **Status**: RESOLVED

---

## 2026-01-04

### Infinite API Calls on Quick Import URL Field (Modal Flickering)

**Issue**: Adding a URL to the Quick Import field in the Add Source modal caused constant flickering. The app repeatedly hit `POST /api/v1/marketplace/sources/infer-url` in an infinite loop rather than once per URL change.

- **Location**: `skillmeat/web/components/marketplace/add-source-modal.tsx:61-86`
- **Root Cause**: The `useEffect` that handles debounced URL inference included `inferUrl` (the mutation object from `useMutation`) in its dependency array:

  ```typescript
  useEffect(() => {
    // ... debounce logic calling inferUrl.mutateAsync
  }, [quickImportUrl, inferUrl]);  // ← Problem: inferUrl in deps
  ```

  When `mutateAsync` is called, the mutation state changes (`isPending` becomes true, then false, etc.), creating a new object reference. This causes the effect to re-run, triggering another debounce, which calls the API again... creating an infinite loop.

  **Cycle**: `inferUrl.mutateAsync()` → state changes → new `inferUrl` ref → effect re-runs → repeat

- **Fix**: Removed `inferUrl` from the dependency array and used a `useRef` to hold a stable reference to the mutation function:

  ```typescript
  // Stable reference to mutation function
  const inferUrlRef = useRef(inferUrl.mutateAsync);
  useEffect(() => {
    inferUrlRef.current = inferUrl.mutateAsync;
  });

  // Debounce effect now only depends on quickImportUrl
  useEffect(() => {
    // ... uses inferUrlRef.current instead of inferUrl.mutateAsync
  }, [quickImportUrl]);  // ← Only depends on URL
  ```

  The first effect (no deps) keeps the ref updated on every render. The debounce effect only re-runs when the URL actually changes.

- **Files Modified**:
  - `skillmeat/web/components/marketplace/add-source-modal.tsx` (added useRef import, ref pattern, updated deps)

- **Commit(s)**: c1fc781
- **Status**: RESOLVED

---

## 2026-01-05

### Missing path_tag_config Column on Marketplace Sources Page

**Issue**: The `/marketplace/sources` page failed to load with SQLAlchemy error: `sqlalchemy.exc.OperationalError: (sqlite3.OperationalError) no such column: marketplace_sources.path_tag_config`.

- **Location**: `skillmeat/cache/models.py:1252-1256` (MarketplaceSource model)
- **Root Cause**: The path-based tag extraction feature (v1) added a `path_tag_config` column to the `MarketplaceSource` SQLAlchemy model, but the corresponding Alembic migration (`20260104_1000_add_path_based_tag_extraction`) had not been applied to the user's database.

  **Migration file existed** at: `skillmeat/cache/migrations/versions/20260104_1000_add_path_based_tag_extraction.py`

  This is a common issue after feature development - the developer's database has migrations applied, but end users need to run `run_migrations()` to update their databases.

- **Fix**: Applied the pending migration using the Python API:
  ```python
  from skillmeat.cache.migrations import run_migrations
  run_migrations()
  ```

  **Note**: Running `alembic upgrade head` directly fails because the CLI doesn't have the database URL configured. The `run_migrations()` helper automatically sets `sqlalchemy.url` to `~/.skillmeat/cache/cache.db`.

- **Prevention**: Auto-migration should be triggered on API startup. Consider adding migration check to `skillmeat/api/server.py` startup event.

- **Commit(s)**: N/A (no code change, just migration applied)
- **Status**: RESOLVED

---

### Path Tags API Returns 404 on Suggested Tags Tab

**Issue**: The new "Suggested Tags" tab on the Catalog Entry modal (from path-based tag extraction v1 feature) failed to load path segments with a 404 error from the `/path-tags` API endpoint.

- **Location**: `skillmeat/web/lib/api/marketplace.ts:41,60`
- **Root Cause**: URL mismatch between frontend and backend:

  | Component | URL Format |
  |-----------|------------|
  | Backend router prefix | `/marketplace/sources` (slash) |
  | Frontend API calls | `/marketplace-sources` (hyphen) |

  The `getPathTags` and `updatePathTagStatus` functions used `/marketplace-sources/...` but the backend router is registered at `/marketplace/sources/...`.

- **Fix**: Updated both API client functions to use the correct URL format:
  ```typescript
  // Before (WRONG)
  buildUrl(`/marketplace-sources/${sourceId}/catalog/${entryId}/path-tags`)

  // After (CORRECT)
  buildUrl(`/marketplace/sources/${sourceId}/catalog/${entryId}/path-tags`)
  ```

- **Files Modified**:
  - `skillmeat/web/lib/api/marketplace.ts` (lines 41, 60)

- **Commit(s)**: 835fa7c
- **Status**: RESOLVED

---

### Bulk Tag Apply Returns 404 for All PATCH Requests

**Date Fixed**: 2026-01-09
**Severity**: high
**Component**: marketplace path-tags API

**Issue**: When applying bulk tags from the marketplace source detail page, every PATCH request to `/api/v1/marketplace/sources/{source_id}/catalog/{entry_id}/path-tags` returned 404 "Segment not found".

- **Location**: `skillmeat/api/routers/marketplace_sources.py:2375`
- **Root Cause**: The segment matching logic used exact string comparison:
  ```python
  if seg["segment"] == request.segment:
  ```

  The frontend sends lowercase tag names (via `normalizeTag()` which lowercases), but the backend stores segments in their original case from the artifact path. This case sensitivity mismatch caused all segment lookups to fail.

  **Example**:
  - Backend stored: `{"segment": "Categories", "normalized": "categories", ...}`
  - Frontend sent: `{"segment": "categories", "status": "approved"}`
  - Comparison: `"Categories" == "categories"` → False → 404

- **Fix**: Made segment matching case-insensitive and added fallback to normalized field:
  ```python
  # Before (case-sensitive, no normalized fallback)
  if seg["segment"] == request.segment:

  # After (case-insensitive, with normalized fallback)
  request_lower = request.segment.lower()
  if seg["segment"].lower() == request_lower or seg.get("normalized", "").lower() == request_lower:
  ```

  This allows:
  1. Case-insensitive matching against the original segment
  2. Matching against the normalized field (handles numeric prefix normalization like "05-data-ai" → "data-ai")
  3. Defensive coding with `.get("normalized", "")` for entries without normalized field

- **Files Modified**:
  - `skillmeat/api/routers/marketplace_sources.py` (lines 2374-2376, 2395-2398)

- **Testing**: All 23 path-tags API tests pass

- **Status**: RESOLVED