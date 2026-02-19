---
title: 'PRD: Tools API Support for Artifact Metadata'
description: Expose Claude tool usage in artifact APIs and cache to enable tools filtering
  and badges in /collection.
audience:
- ai-agents
- developers
- designers
tags:
- prd
- api
- metadata
- collections
- caching
- web
created: 2026-02-02
updated: 2026-02-02
category: product-planning
status: inferred_complete
related:
- /docs/project_plans/implementation_plans/refactors/artifact-metadata-cache-v1.md
- /docs/design/ui-component-specs-page-refactor.md
- /docs/project_plans/implementation_plans/features/manage-collection-page-refactor-v1.md
---
# Feature Brief & Metadata

**Feature Name:**

> Tools API Support for Artifact Metadata

**Filepath Name:**

> `tools-api-support-v1`

**Date:**

> 2026-02-02

**Author:**

> Codex

**Related Epic(s)/PRD ID(s):**

> N/A

**Related Documents:**

> - `/docs/project_plans/implementation_plans/refactors/artifact-metadata-cache-v1.md`
> - `/docs/design/ui-component-specs-page-refactor.md`
> - `/docs/project_plans/implementation_plans/features/manage-collection-page-refactor-v1.md`

---

## 1. Executive Summary

The `/collection` UX depends on displaying and filtering by Claude tool usage (Bash, Read, Write, WebSearch, etc.). Today, the collection API responses do not include `tools`, and the metadata cache does not store them. This PRD defines backend and API changes to expose tools across artifact endpoints, align with existing enums, and support fast, DB-first responses for the collection UI.

**Priority:** HIGH (blocks Tools filter and tool badges on discovery cards)

**Key Outcomes:**
- `tools` available on `/user-collections/{id}/artifacts` and `/artifacts` responses
- Tools cached in `CollectionArtifact` for DB-first collection browsing
- Consistent tool values across backend and frontend enums

---

## 2. Context & Background

### Current State
- `ArtifactSummary` does **not** include a `tools` field.
- Collection cache table (`collection_artifacts`) does not store tools.
- UI specs and filtering plan expect tools data for discovery.

### Problem Statement
Users want to discover artifacts by tool usage. Without tools in collection API responses, the UI cannot reliably display tool badges or support multi-select tools filtering.

### Architectural Context
- File system remains the source of truth for metadata.
- DB cache is the fast path for `/collection` listing.
- Tool values must match backend enums (`skillmeat/api/schemas/enums.py`) and frontend enums (`skillmeat/web/types/enums.ts`).

---

## 3. Goals & Success Metrics

### Primary Goals
1. **Expose tools in collection API**
   - `tools` field present in `ArtifactSummary` responses
2. **Cache tools for DB-first reads**
   - `tools` stored and refreshed in `CollectionArtifact`
3. **Enum consistency**
   - Tool values match backend and frontend enum definitions

### Success Metrics
| Metric | Target | Measurement |
|--------|--------|-------------|
| `/collection` tool badges available | 100% of artifacts with tools | UI verification |
| Tools filter functioning | 0 errors, correct results | E2E tests |
| Cache hit rate | ≥90% for tools field | Cache metrics |

---

## 4. Scope

### In Scope
- Add `tools` to API schemas and responses
- Store tools in `CollectionArtifact` cache
- Populate and refresh tools in cache population paths
- Update entity mapping to include tools where applicable
- Update tests for tools field

### Out of Scope
- New UI components beyond wiring existing tools badges and filters
- Tool inference or analysis beyond metadata extraction

---

## 5. Requirements

### API & Schema Requirements
- Add `tools: Optional[List[str]]` to:
  - `skillmeat/api/schemas/user_collections.py::ArtifactSummary`
  - `skillmeat/api/schemas/collections.py::ArtifactSummary` (if used in web)
  - Any relevant SDK models if generated
- Ensure `tools` are included in:
  - `/api/v1/user-collections/{id}/artifacts`
  - `/api/v1/artifacts`

### Data Model Requirements
- Add `tools_json` (JSON array string) to `CollectionArtifact`:
  - Migration with nullable column
  - Populate from file-based metadata

### Cache Population Requirements
- Update `populate_collection_artifact_metadata()` to store tools
- Update refresh-cache endpoints to update tools
- When cache miss falls back to file system, include tools in response

### Consistency Requirements
- Tool values must match backend enum `Tool` in `skillmeat/api/schemas/enums.py`
- Frontend should use `Tool` enum in `skillmeat/web/types/enums.ts`

---

## 6. Proposed API Changes

### ArtifactSummary (Collection APIs)
```python
class ArtifactSummary(BaseModel):
    ...
    tools: Optional[List[str]] = Field(default=None, description="Claude tool names")
```

### JSON Shape Example
```json
{
  "id": "skill:pdf",
  "name": "pdf",
  "type": "skill",
  "version": "v2.1.0",
  "description": "Extract text and tables from PDFs",
  "author": "Anthropic",
  "tags": ["document", "extraction"],
  "tools": ["Read", "Write"],
  "collections": [
    {"id": "default", "name": "Default", "artifact_count": 24}
  ]
}
```

---

## 7. Implementation Plan (High-Level)

1. **Schema & Model Updates**
   - Add `tools` to API schemas
   - Add `tools_json` to `CollectionArtifact` model + migration
2. **Cache Population**
   - Populate `tools_json` from file-based metadata
   - Update refresh-cache endpoints to include tools
3. **API Responses**
   - Emit `tools` from cache (DB-first path)
   - Emit `tools` from filesystem fallback path
4. **Frontend Mapping**
   - Map `tools` into `Artifact`/`Entity` as needed
5. **Tests**
   - Unit tests for cache population
   - API response tests for tools field
   - UI filter integration tests

---

## 8. Testing & Validation

- **Unit Tests**: Validate `tools` population from metadata and cache refresh paths
- **API Tests**: Ensure tools appear in list endpoints for both cache hit and miss
- **E2E Tests**: Tools filter works, badge rendering correct in /collection

---

## 9. Rollout & Operations

No feature flags or staged rollout. Release with standard CI checks and post-release monitoring of error rates and cache hit metrics.

---

## 10. Open Questions

- Should tools be normalized to enum values on write (server) or left as-is from metadata?
- Do we need to backfill tools for artifacts missing metadata (empty list vs null)?
- Should `/api/v1/artifacts` and marketplace endpoints also expose tools for consistency?
