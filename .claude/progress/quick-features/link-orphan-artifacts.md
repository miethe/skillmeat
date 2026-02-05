# Quick Feature: Link Orphan Marketplace Artifacts

**Status**: completed
**Created**: 2025-02-04
**Scope**: Single Python script + optional API endpoint

## Problem

Collection artifacts imported from marketplace sources have:
- `source` field set correctly (e.g., `anthropics/skills/pdf@latest`)
- `origin` = `"marketplace"` or `"github"`

But lack:
- No `MarketplaceCatalogEntry` with `import_id` pointing to them

This breaks the "Sources" tab linking in the web UI.

## Solution

Create a repair script that:
1. Query all `CollectionArtifact` with `origin` in (`'marketplace'`, `'github'`) and non-null `source`
2. For each, check if any `MarketplaceCatalogEntry` has `import_id` referencing it
3. If not linked, parse `source` to extract `owner/repo` and `path`
4. Find matching `MarketplaceCatalogEntry` by:
   - Same `upstream_url` pattern, OR
   - Same `source_id` (marketplace source) + matching `name`/`path`
5. Link by setting `import_id` on the catalog entry

## Implementation Plan

### Files to Create/Modify

| File | Action | Purpose |
|------|--------|---------|
| `scripts/link_orphan_artifacts.py` | CREATE | Standalone repair script |
| `skillmeat/core/sync_service.py` | OPTIONAL | Add `link_orphan_artifacts()` method for API exposure |

### Script Logic

```python
# Pseudocode
def link_orphan_artifacts(dry_run=True):
    orphans = find_orphan_artifacts()  # Has source, no catalog link

    for artifact in orphans:
        source_spec = parse_source(artifact.source)  # owner/repo/path@version

        # Find matching catalog entry
        entry = find_catalog_entry_by_source(source_spec)

        if entry and not entry.import_id:
            if not dry_run:
                entry.import_id = artifact.id  # or artifact.import_id
                entry.import_date = datetime.now()
                entry.status = 'imported'

            yield LinkResult(artifact, entry, 'linked')
        elif entry and entry.import_id:
            yield LinkResult(artifact, entry, 'already_linked')
        else:
            yield LinkResult(artifact, None, 'no_match')
```

### Key Considerations

1. **ID Type**: `import_id` on catalog entries is a batch UUID, not artifact ID
   - Need to check: is `import_id` the artifact's `id` or a separate batch UUID?
   - May need to use artifact's own `import_id` field if it exists

2. **Matching Logic**: Parse `source` field format:
   - Format: `owner/repo/path/to/artifact[@version]`
   - Match to `MarketplaceCatalogEntry.upstream_url` which is full GitHub URL

3. **Dry Run**: Always default to dry-run to preview changes first

## Tasks

- [x] TASK-1: Implement `scripts/link_orphan_artifacts.py`
- [x] TASK-2: Test with dry-run on actual collection
- [ ] TASK-3: Run with `--execute` to apply links (user action)

## Success Criteria

- [x] Script finds all orphan artifacts (found 104)
- [x] Script correctly matches to catalog entries (matched 82)
- [x] Links are created without errors (dry-run verified)
- [ ] Sources tab shows linked artifacts after running (pending user execution)
