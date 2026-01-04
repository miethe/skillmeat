# Path-Based Tag Extraction - Implementation Context

## Overview

Context file for path-based tag extraction feature implementation. This feature automatically extracts tags from marketplace source paths (e.g., `anthropics/skills/data-analysis` → org:anthropics, category:data-analysis) to improve organization and discoverability.

---

## References

### Planning Documents

- **PRD**: `docs/project_plans/PRDs/features/path-based-tag-extraction-v1.md`
- **Implementation Plan**: `docs/project_plans/implementation_plans/features/path-based-tag-extraction-v1.md`

### Progress Tracking

- **Phase 1 Progress**: `.claude/progress/path-based-tag-extraction/phase-1-progress.md`
- **Phase 2 Progress**: `.claude/progress/path-based-tag-extraction/phase-2-progress.md`
- **Phase 3 Progress**: `.claude/progress/path-based-tag-extraction/phase-3-progress.md`

---

## Architectural Decisions

### 1. Storage Strategy

**Decision**: Store extracted tags in `path_tags` JSONB column on `marketplace_sources` table.

**Rationale**:
- Avoids complex many-to-many relationship
- Allows flexible schema (segment types can evolve)
- Enables efficient querying with JSONB operators
- Separates auto-extracted tags from user-applied tags

**Schema**:
```json
{
  "org": "anthropics",
  "repo": "skills",
  "category": "data-analysis",
  "skill-name": "csv-processor"
}
```

### 2. Extraction Service Design

**Decision**: Use dataclass-based configuration with regex patterns.

**Rationale**:
- Type-safe pattern definitions
- Easy to extend with new segment types
- Supports transform functions (lowercase, titlecase)
- Testable in isolation

**Key Classes**:
- `PathTagConfig`: Pattern definition (regex, segment_type, transform)
- `ExtractedSegment`: Extraction result (value, type, original_value)
- `PathSegmentExtractor`: Extraction logic

### 3. Scanner Integration

**Decision**: Extract tags during marketplace scan, before import.

**Rationale**:
- User sees tags during review (before committing to import)
- Tags available immediately after scan
- No need to re-scan sources for tags
- Extraction happens once per source

**Flow**:
1. User scans marketplace URL
2. Scanner creates `MarketplaceSource` record
3. `PathSegmentExtractor.extract_segments()` called
4. Results stored in `path_tags` column
5. User reviews/edits tags in UI
6. Import applies tags to artifact

### 4. UI Integration

**Decision**: Add "Review Tags" step to import modal workflow.

**Rationale**:
- Non-blocking (user can skip)
- Inline editing for quick fixes
- Reset button for mistakes
- Clear visual grouping by segment type

**Workflow**:
1. **Scan URL** → Extract path tags
2. **Review Tags** → Edit/reset segments (optional)
3. **Confirm Import** → Apply tags to artifact

### 5. Tag Application

**Decision**: Tags applied additively during import (controlled by checkbox).

**Rationale**:
- Preserves user-applied tags
- User can disable if unwanted
- Default enabled (opt-out, not opt-in)
- No risk of tag conflicts (additive merge)

---

## Critical File Inventory

### Backend - Database Layer

| File | Purpose | Phase |
|------|---------|-------|
| `skillmeat/api/migrations/versions/{timestamp}_add_path_tags_column.py` | Add path_tags JSONB column | 1 |
| `skillmeat/api/models/marketplace_source.py` | Add path_tags field to model | 1 |

### Backend - Business Logic

| File | Purpose | Phase |
|------|---------|-------|
| `skillmeat/core/marketplace/path_tags.py` | Dataclasses (PathTagConfig, ExtractedSegment), constants | 1 |
| `skillmeat/core/marketplace/extractor.py` | PathSegmentExtractor service | 1 |
| `skillmeat/core/marketplace/scanner.py` | Scanner integration (calls extractor) | 1 |
| `skillmeat/core/marketplace/import_service.py` | Tag application during import | 3 |

### Backend - API Layer

| File | Purpose | Phase |
|------|---------|-------|
| `skillmeat/api/schemas/marketplace.py` | Pydantic schemas (PathTagSegmentResponse, etc.) | 1 |
| `skillmeat/api/routers/marketplace.py` | GET/PATCH endpoints for path tags | 1 |

### Frontend - API & Hooks

| File | Purpose | Phase |
|------|---------|-------|
| `skillmeat/web/lib/api/marketplace.ts` | API client functions (fetchPathTags, updatePathTags) | 2 |
| `skillmeat/web/types/marketplace.ts` | TypeScript types (PathTagSegment, etc.) | 2 |
| `skillmeat/web/hooks/use-path-tags.ts` | React Query hooks | 2 |
| `skillmeat/web/hooks/use-bulk-import.ts` | Updated to accept apply_path_tags | 3 |

### Frontend - Components

| File | Purpose | Phase |
|------|---------|-------|
| `skillmeat/web/components/marketplace/path-tag-review.tsx` | Main tag review component | 2 |
| `skillmeat/web/components/marketplace/import-modal.tsx` | Modal integration + checkbox | 2, 3 |

### Tests

| File | Purpose | Phase |
|------|---------|-------|
| `tests/unit/test_path_extractor.py` | Extractor unit tests | 1 |
| `tests/unit/test_marketplace_path_tags_api.py` | API endpoint unit tests | 1 |
| `tests/integration/test_path_tags_workflow.py` | Backend integration tests | 1 |
| `skillmeat/web/components/marketplace/__tests__/path-tag-review.test.tsx` | Component unit tests | 2 |
| `skillmeat/web/e2e/marketplace-tag-review.spec.ts` | UI E2E tests | 2 |
| `tests/integration/test_import_with_tags.py` | Import integration tests | 3 |
| `skillmeat/web/e2e/marketplace-import-tags.spec.ts` | Full workflow E2E tests | 3 |

### Documentation

| File | Purpose | Phase |
|------|---------|-------|
| `docs/api/marketplace.md` | API endpoint docs | 1, 3 |
| `docs/accessibility/path-tag-review.md` | A11y audit results | 2 |
| `docs/features/marketplace-import.md` | User-facing feature docs | 3 |
| `CHANGELOG.md` | Feature release notes | 3 |

---

## Default Path Tag Patterns

Defined in `skillmeat/core/marketplace/path_tags.py`:

```python
DEFAULT_PATH_TAG_PATTERNS = [
    PathTagConfig(
        pattern=r"^([^/]+)",
        segment_type="org",
        transform="lowercase"
    ),
    PathTagConfig(
        pattern=r"^[^/]+/([^/]+)",
        segment_type="repo",
        transform="lowercase"
    ),
    PathTagConfig(
        pattern=r"/([^/]+)/[^/]+$",
        segment_type="category",
        transform="lowercase"
    ),
    PathTagConfig(
        pattern=r"([^/]+)$",
        segment_type="skill-name",
        transform="lowercase"
    ),
]
```

**Example Extraction**:
- Input: `anthropics/skills/data-analysis/csv-processor`
- Output:
  - `org`: `anthropics`
  - `repo`: `skills`
  - `category`: `data-analysis`
  - `skill-name`: `csv-processor`

---

## Key Patterns and Conventions

### Backend Error Handling

```python
try:
    segments = extractor.extract_segments(path, configs)
except Exception as e:
    logger.warning(f"Failed to extract path tags: {e}")
    # Store empty dict (graceful degradation)
    path_tags = {}
```

### Frontend Error Handling

```typescript
if (!response.ok) {
  const errorBody = await response.json().catch(() => ({}));
  throw new Error(errorBody.detail || `Failed to fetch path tags: ${response.statusText}`);
}
```

### Cache Invalidation (React Query)

```typescript
onSuccess: (_, { sourceId }) => {
  queryClient.invalidateQueries({ queryKey: pathTagKeys.detail(sourceId) });
  queryClient.invalidateQueries({ queryKey: pathTagKeys.all });
}
```

### Tag Application (Additive Merge)

```python
# In import_service.py
if apply_path_tags:
    path_tags = source.path_tags or {}
    existing_tags = artifact.tags or []
    new_tags = list(path_tags.values())
    # Merge (no duplicates)
    artifact.tags = list(set(existing_tags + new_tags))
```

---

## Testing Strategy

### Phase 1 (Backend)

1. **Unit Tests - Extractor**:
   - Test default patterns against sample paths
   - Test custom patterns
   - Test transform functions
   - Test edge cases (missing segments, malformed paths)

2. **Unit Tests - API**:
   - Test GET endpoint (success, 404)
   - Test PATCH endpoint (success, validation errors)
   - Mock database interactions

3. **Integration Tests**:
   - Test: Scan → verify path_tags populated
   - Test: GET → verify response
   - Test: PATCH → verify persistence

### Phase 2 (Frontend)

1. **Unit Tests - Component**:
   - Test: Renders segments correctly
   - Test: Inline editing updates state
   - Test: Reset button works
   - Test: Save button calls mutation

2. **E2E Tests**:
   - Test: Modal → scan → review step appears
   - Test: Edit segment → save → verify API call
   - Test: Skip review → import

### Phase 3 (Integration)

1. **Integration Tests - Import**:
   - Test: apply_path_tags=True → tags applied
   - Test: apply_path_tags=False → tags NOT applied
   - Test: Missing path_tags → no error

2. **E2E Tests - Full Workflow**:
   - Test: Scan → review → edit → import → verify tags in collection
   - Test: Skip review → import → verify auto-tags
   - Test: Uncheck "Apply tags" → import → verify no tags

---

## Known Limitations

1. **Pattern Matching**:
   - Regex-based (not semantic)
   - May fail on unusual path structures
   - No support for multi-level categories (flat structure)

2. **Transform Functions**:
   - Limited to lowercase, titlecase (can extend later)
   - No support for custom mappings (e.g., "ts" → "TypeScript")

3. **Tag Conflicts**:
   - Additive merge may create duplicates if case differs
   - No de-duplication logic (assumes normalized tags)

4. **Scalability**:
   - Extraction happens per-source (not batched)
   - JSONB queries may be slow on large datasets

---

## Future Enhancements

1. **Custom Pattern Editor**:
   - UI to define custom regex patterns
   - Per-source pattern overrides

2. **Semantic Extraction**:
   - Use LLM to infer category from README
   - Suggest tags based on artifact content

3. **Batch Extraction**:
   - Re-extract tags for all sources (migration)
   - Scheduled background job

4. **Tag Normalization**:
   - De-duplicate case-insensitive tags
   - Suggest canonical tag names

---

## Gotchas and Learnings

### Database Migrations

- **Gotcha**: JSONB default value syntax varies by Alembic version
- **Solution**: Use `default=dict` in model, `server_default='{}'::jsonb` in migration

### React Query Cache

- **Gotcha**: Invalidating parent keys doesn't invalidate child keys
- **Solution**: Explicitly invalidate both `pathTagKeys.all` and `pathTagKeys.detail(id)`

### Accessibility

- **Gotcha**: Inline editing without ARIA labels breaks screen readers
- **Solution**: Add `aria-label` to each input with segment type

### Frontend Stubs

- **Gotcha**: Hooks may throw `ApiError(..., 501)` if backend not implemented
- **Solution**: Check for stubs before testing, implement API client first

---

## Rollout Plan

### Phase 1 Rollout (Backend)
1. Deploy migration (add path_tags column)
2. Enable scanner integration (flag-gated)
3. Test with sample sources
4. Enable API endpoints (public)

### Phase 2 Rollout (Frontend)
1. Deploy component behind feature flag
2. Test with beta users
3. Enable for all users

### Phase 3 Rollout (Integration)
1. Deploy checkbox (default checked)
2. Monitor tag application rate
3. Gather user feedback
4. Iterate on patterns

---

## Contact & Ownership

- **Feature Owner**: (TBD)
- **Backend Lead**: python-backend-engineer (Opus/Sonnet)
- **Frontend Lead**: ui-engineer-enhanced (Opus)
- **QA Lead**: karen (Sonnet)
- **Docs Lead**: documentation-writer (Haiku)

For questions or issues, consult this context file or progress tracking files.
