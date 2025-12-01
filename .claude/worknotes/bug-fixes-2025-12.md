# Bug Fixes - December 2025

## 2025-12-01

### CollectionManager get_collection Method Not Found

**Issue**: `skillmeat sync-check` CLI command fails with `'CollectionManager' object has no attribute 'get_collection'`
- **Location**: `skillmeat/core/sync.py:413,622,762,1098,1428`
- **Root Cause**: `SyncManager` called `self.collection_mgr.get_collection()` but the correct method name is `load_collection()`
- **Fix**: Replaced all 5 occurrences of `get_collection` with `load_collection` in sync.py; updated corresponding test mocks in tests/test_sync.py
- **Commit(s)**: b13c97d
- **Status**: RESOLVED

### Select Component Import Errors on Web Build

**Issue**: Web build fails with numerous import errors from `@/components/ui/select` - components trying to import Radix UI sub-components that don't exist
- **Location**: `skillmeat/web/components/ui/select.tsx` and 8 consuming components
- **Root Cause**: `select.tsx` was a simple native HTML wrapper, but 2 discovery components expected Radix UI Select sub-components (`SelectContent`, `SelectItem`, `SelectTrigger`, `SelectValue`)
- **Fix**:
  1. Replaced `select.tsx` with full Radix UI-based shadcn/ui Select component
  2. Migrated 6 components from old native API to new Radix API:
     - `components/collection/filters.tsx`
     - `components/entity/entity-form.tsx`
     - `components/sync-status/comparison-selector.tsx`
     - `components/mcp/MCPServerList.tsx`
     - `components/marketplace/MarketplaceFilters.tsx`
     - `components/marketplace/MarketplaceInstallDialog.tsx`
- **Commit(s)**: 62cca2f
- **Status**: RESOLVED

### Collection Object Missing path Attribute

**Issue**: `skillmeat sync-check` fails with `'Collection' object has no attribute 'path'`
- **Location**: `skillmeat/core/sync.py:414,623,764,1099,1436`
- **Root Cause**: Code accessed `collection.path` but `Collection` is a dataclass without a `path` attribute. Path is managed by `ConfigManager`, not the Collection object.
- **Fix**: Replaced all 5 occurrences of `collection.path` with `self.collection_mgr.config.get_collection_path(collection_name)`
- **Commit(s)**: fc24e7b
- **Status**: RESOLVED

### Discovery Service Scans Wrong Directory Structure

**Issue**: Smart Import/Discovery banner never appears on `/manage` page despite feature being "complete"
- **Location**: `skillmeat/core/discovery.py:100-107`
- **Root Cause**: `ArtifactDiscoveryService` scanned `collection_path/artifacts/` directory, but:
  1. The collection directory `~/.skillmeat/collection/` doesn't exist (never initialized)
  2. The design was wrong - discovery should scan project `.claude/` directories, not collection
- **Fix**: Modified `ArtifactDiscoveryService.__init__` to support three scan modes:
  - `project`: Scans `base_path/.claude/` subdirectories (skills/, commands/, agents/, hooks/, mcp/)
  - `collection`: Scans `base_path/artifacts/` (legacy support)
  - `auto` (default): Auto-detects based on directory structure
- **Commit(s)**: 857ef8d
- **Status**: RESOLVED

### Discovery Banner on Wrong Page (Architectural Bug)

**Issue**: Discovery banner was on `/manage` page which manages collection artifacts (already imported), not project artifacts
- **Location**: `skillmeat/web/app/manage/page.tsx:177-186`
- **Root Cause**: Design mismatch - discovery should help users import artifacts FROM projects INTO collection, not discover artifacts in the collection itself
- **Fix**:
  1. Created new `useProjectDiscovery` hook for project-specific scanning (`skillmeat/web/hooks/useProjectDiscovery.ts`)
  2. Added project-aware API endpoint `POST /api/v1/artifacts/discover/project/{project_id}` (`skillmeat/api/routers/artifacts.py`)
  3. Moved discovery banner and bulk import modal to `/projects/{id}` page (`skillmeat/web/app/projects/[id]/page.tsx`)
  4. Removed discovery functionality from `/manage` page
- **Commit(s)**: a14063c, 0ab58c3
- **Status**: RESOLVED

### Invalid Artifact Structure for Planning Skill

**Issue**: Discovery scan encounters "Invalid artifact structure" warning for `.claude/skills/planning`
- **Location**: `.claude/skills/planning/SKILL.md:3`
- **Root Cause**: YAML frontmatter had unquoted colons in the description field (e.g., "Supports: 1)", "Example: ") which YAML interprets as key-value pairs, causing parsing to fail at column 271
- **Fix**: Converted description to YAML folded block scalar syntax (`>`) which safely handles colons and special characters
- **Commit(s)**: 14c249a
- **Status**: RESOLVED

### Import 422 Error - Source Must Include Owner and Repository

**Issue**: Importing discovered local artifacts fails with 422 error "Source must include owner and repository"
- **Location**: `skillmeat/core/validation.py:36`, `skillmeat/core/discovery.py:407`
- **Root Cause**: Local artifacts in `.claude/` directories don't have GitHub-format source fields (owner/repo/path) in their frontmatter. Validation required this format unconditionally.
- **Fix**:
  1. Discovery service now generates synthetic `local/{type}/{name}` sources for artifacts without GitHub sources
  2. Validation accepts `local/` prefix as valid source format
- **Commit(s)**: a010f2c
- **Status**: RESOLVED

### DialogContent Missing DialogTitle Accessibility Warning

**Issue**: Navigating to `/projects/{id}` page throws "DialogContent requires a DialogTitle for accessibility"
- **Location**: `skillmeat/web/components/discovery/BulkImportModal.tsx:143`, `ParameterEditorModal.tsx:153`
- **Root Cause**: Custom ARIA attributes (`aria-labelledby`, `aria-describedby`) on DialogContent were overriding Radix UI's automatic ARIA linking, making Radix think DialogTitle was missing
- **Fix**: Removed custom `aria-labelledby`, `aria-describedby` attributes and `id` attributes from DialogTitle/DialogDescription in both modals. Radix UI handles ARIA automatically.
- **Commit(s)**: 0abde84
- **Status**: RESOLVED
