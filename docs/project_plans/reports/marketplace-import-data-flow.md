# Marketplace Import Data Flow Report

## Summary

**Issue**: Marketplace-imported artifacts (e.g., `1password`) showed "No upstream source information available" on the Sources tab, while `ui-ux-pro-max` worked correctly.

**Root Cause**: The `/marketplace/sources/{source_id}/artifacts` endpoint was missing a `search` query parameter. The frontend source discovery called `?search=1password` but the endpoint ignored the parameter, returning all items instead of filtering by name.

**Fix**: Added `search` parameter to the endpoint (commit `c8d5e6d5`).

---

## Data Flow (After Fix)

### Phase 1: Source Discovery & Catalog

```
GitHub Repo ──→ HeuristicDetector scans ──→ MarketplaceCatalogEntry (DB)
                                              ├── upstream_url: "https://github.com/owner/repo/tree/ref/path"
                                              ├── description: from frontmatter
                                              └── status: "new" → "imported"
```

**Key file**: `core/marketplace/heuristic_detector.py` (line 2200) constructs upstream_url
**Table**: `marketplace_catalog_entries` (ORM: `MarketplaceCatalogEntry` in `cache/models.py`)

### Phase 2: Catalog-Based Import (`/marketplace-sources/{id}/import`)

```
CatalogEntry.upstream_url ──→ ImportCoordinator ──→ Filesystem (manifest.toml)
                                                      └── upstream = upstream_url
                                                          origin = "marketplace"
                              ──→ populate_collection_artifact_from_import()
                                    └── CollectionArtifact.source = entry.upstream_url ✅
```

**Key file**: `api/routers/marketplace_sources.py` (line 3720)

### Phase 3: Bundle-Based Install (`/marketplace/install`)

```
Bundle.metadata.repository ──→ MarketplaceImportEntry adapter
                                 └── upstream_url = repository
                              ──→ populate_collection_artifact_from_import()
                                    └── CollectionArtifact.source = upstream_url ✅
```

**Key file**: `api/routers/marketplace.py` (line 553)
**Note**: If `bundle.metadata.repository` is None, source stays empty

### Phase 4: DB State

Both artifacts have correct source in database:

| Artifact | Source URL |
|----------|------------|
| `skill:1password` | `https://github.com/steipete/agent-scripts/tree/main/skills/1password` |
| `skill:ui-ux-pro-max` | `https://github.com/nextlevelbuilder/ui-ux-pro-max-skill/tree/main/.claude/skills` |

### Phase 5: API Endpoints

Both endpoints return source correctly:
- `/api/v1/artifacts` - returns `source` field with GitHub URL
- `/api/v1/user-collections/{id}/artifacts` - returns `source` field with GitHub URL

### Phase 6: Frontend Source Discovery

The Sources tab uses a 3-tier display:

| Tier | Condition | Display |
|------|-----------|---------|
| 1 | sourceEntry found via catalog search | Linked source with external link icon |
| 2 | hasValidUpstreamSource() passes | Source text (not linked) |
| 3 | Fallback | "No upstream source information available" |

**Source Discovery Flow** (`artifact-operations-modal.tsx` lines 601-652):

1. Search loaded marketplace sources for one where `artifact.source.includes(owner/repo_name)`
2. Query that source's catalog: `/marketplace/sources/{id}/artifacts?search={name}`
3. Find exact match by name and type
4. If found → Tier 1 (linked source display)

**FIX APPLIED**: The catalog search endpoint now properly filters by the `search` parameter.

---

## Commits (Branch: `fix/marketplace-import-refactor`)

| Commit | Description |
|--------|-------------|
| `c8d5e6d5` | **fix(api): add search parameter to marketplace source artifacts endpoint** - Root cause fix |
| `f3da0171` | fix(api): enrich collection endpoint with filesystem source when DB empty |
| `5fe95e9d` | fix(api): use listing repository for marketplace import source sync |
| `c1509a67` | fix(api): sync marketplace imports to DB cache for source display |
| `330b9986` | fix(api): enrich /artifacts response with DB source for marketplace imports |

---

## Remaining Issues

### Collection Page Search (Separate Bug)

The collection page (`/collection`) has client-side-only search that only filters loaded items (first 20 of 246). This prevents finding artifacts like `1password` via search. This is a **separate pagination/search issue** unrelated to the Source display fix.

**Workaround**: Use `/manage` page which loads more items and has working search.

---

## Verification

After fix, both artifacts show source correctly on the Manage page:

- **1password**: `steipete/agent-scripts` → `skills/1password` → latest ✅
- **ui-ux-pro-max**: `nextlevelbuilder/ui-ux-pro-max-skill` → `.claude/skills` → latest ✅
