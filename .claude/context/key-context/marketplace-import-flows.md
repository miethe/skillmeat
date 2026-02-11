# Marketplace Import Data Flows

Load when: working on marketplace import, source display, or artifact cache sync.

## Two Import Endpoints (Critical Distinction)

| Endpoint | Router File | Import Mechanism | DB Sync |
|----------|-------------|------------------|---------|
| `POST /marketplace-sources/{id}/import` | `routers/marketplace_sources.py` | `ImportCoordinator` via catalog entry | Calls `refresh_single_artifact_cache()` per artifact |
| `POST /marketplace/install` | `routers/marketplace.py` | `BundleImporter.import_bundle()` | **Must also call** `refresh_single_artifact_cache()` (added in fix branch) |

**Invariant**: Every import endpoint **must** call `refresh_single_artifact_cache()` after filesystem write. `BundleImporter` does NOT sync DB — callers are responsible.

## Import Data Flow (Catalog-Based)

```
1. HeuristicDetector scans GitHub repo
   → MarketplaceCatalogEntry (DB: marketplace_catalog_entries)
     .upstream_url = "https://github.com/owner/repo/tree/ref/path"
   File: core/marketplace/heuristic_detector.py

2. POST /marketplace-sources/{id}/import
   → CatalogEntry.upstream_url → ImportCoordinator
   → Writes filesystem: manifest.toml (upstream = upstream_url, origin = "marketplace")
   → populate_collection_artifact_from_import()
     → CollectionArtifact.source = entry.upstream_url
   → refresh_single_artifact_cache() per artifact
   File: routers/marketplace_sources.py

3. refresh_single_artifact_cache(session, artifact_mgr, artifact_id)
   → Reads artifact.upstream from filesystem
   → Writes CollectionArtifact.source to DB
   File: api/services/artifact_cache_service.py
```

## Import Data Flow (Bundle-Based)

```
1. POST /marketplace/install
   → BundleImporter().import_bundle(bundle_path, strategy)
   File: routers/marketplace.py

2. BundleImporter extracts bundle manifest
   → Artifact(upstream=artifact_data.get("upstream"))
   → collection.add_artifact() (filesystem)
   → Updates lock file with upstream
   File: core/sharing/importer.py
   Note: If bundle.metadata.repository is None, source stays empty

3. Caller must call refresh_single_artifact_cache() for each imported artifact
   → Same DB sync as catalog-based flow
```

## Frontend Source Discovery (3-Tier)

Located in `web/components/artifact-operations-modal.tsx`:

| Tier | Condition | Display |
|------|-----------|---------|
| 1 | `sourceEntry` found via catalog search | Linked source with external link icon |
| 2 | `hasValidUpstreamSource()` passes | Source text (not linked) |
| 3 | Fallback | "No upstream source information available" |

**Tier 1 discovery flow**:
1. Search loaded marketplace sources for one where `artifact.source.includes(owner/repo_name)`
2. Query `GET /marketplace/sources/{id}/artifacts?search={name}` (search param required)
3. Find exact match by name and type
4. If found → linked source display

**Key dependency**: `hasValidUpstreamSource()` in `web/lib/sync-utils.ts` gates upstream queries.

## API Response Source Resolution

In `routers/artifacts.py`, `artifact_to_response()`:

```
source = db_source or (artifact.upstream if artifact.upstream else "local")
```

The `/artifacts` endpoint batch-queries DB for sources:
```
SELECT artifact_id, source FROM CollectionArtifact
WHERE artifact_id IN (...) AND source IS NOT NULL
```

Falls back to filesystem `artifact.upstream` if DB source is NULL.

## Key Files

| File | Role |
|------|------|
| `api/routers/marketplace.py` | Bundle install endpoint |
| `api/routers/marketplace_sources.py` | Catalog import endpoint, source artifacts listing |
| `api/routers/marketplace_catalog.py` | Catalog browsing/search |
| `api/routers/artifacts.py` | `artifact_to_response()` source resolution |
| `api/services/artifact_cache_service.py` | `refresh_single_artifact_cache()` — FS→DB sync |
| `core/sharing/importer.py` | `BundleImporter` — filesystem import (no DB sync) |
| `core/marketplace/heuristic_detector.py` | Upstream URL construction from repo scanning |
| `cache/models.py` | `CollectionArtifact.source`, `MarketplaceCatalogEntry.upstream_url` |
| `web/components/artifact-operations-modal.tsx` | Frontend source display (3-tier) |
| `web/lib/sync-utils.ts` | `hasValidUpstreamSource()` |

## Known Issues

- **Collection page search**: Client-side only, filters loaded items (first 20 of 246). Use `/manage` page for full search. Separate pagination bug.
- **Bundle imports without repository**: If `bundle.metadata.repository` is None, artifact source stays empty permanently.
