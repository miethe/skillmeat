# Quick Feature: Default Collection for Groups Support

**Status**: `completed`
**Created**: 2026-01-16
**Branch**: `fix/marketplace-source-total-count` (or create `feat/default-collection-for-groups`)

## Problem Statement

The Groups feature requires a `collection_id`, but most artifacts are added without an explicit collection association (appearing in "All Collections" view with blank collection_id). This means:
1. Artifacts can't be added to Groups unless they're explicitly in a collection
2. Users who don't use multiple collections can't use Groups at all
3. The "All Collections" view doesn't have a collection_id to pass to the Groups API

## Solution

1. Create/ensure a "default" collection exists in the database
2. Automatically assign artifacts to the "default" collection when no collection is specified
3. Default the `/collection` page to show the "default" collection instead of "All Collections"
4. Update collection-switcher to show "default" collection selected by default

## Scope Analysis

**Files to modify**:
- Backend:
  - `skillmeat/api/server.py` - Ensure default collection on startup
  - `skillmeat/api/routers/artifacts.py` - Use "default" collection when none specified
  - `skillmeat/api/routers/user_collections.py` - Ensure default collection exists endpoint
  - `skillmeat/cache/models.py` - Add DEFAULT_COLLECTION_ID constant

- Frontend:
  - `skillmeat/web/context/collection-context.tsx` - Default to "default" collection ID
  - `skillmeat/web/components/collection/collection-switcher.tsx` - Show "default" when no selection
  - `skillmeat/web/app/collection/page.tsx` - Default view to "default" collection

**Estimated scope**: ~6 files, single-session implementation

## Implementation Tasks

### Phase 1: Backend - Default Collection Constant and Initialization

| Task | Status | Files |
|------|--------|-------|
| Add DEFAULT_COLLECTION_ID constant | pending | `cache/models.py` |
| Create ensure_default_collection() function | pending | `api/routers/user_collections.py` |
| Call ensure_default_collection on server startup | pending | `api/server.py` |

### Phase 2: Backend - Auto-assign to Default Collection

| Task | Status | Files |
|------|--------|-------|
| Update create_artifact to use default collection | pending | `api/routers/artifacts.py` |
| Update import_artifacts to use default collection | pending | `api/routers/marketplace_sources.py` |

### Phase 3: Frontend - Default Collection Selection

| Task | Status | Files |
|------|--------|-------|
| Default selectedCollectionId to "default" constant | pending | `context/collection-context.tsx` |
| Update collection-switcher display logic | pending | `components/collection/collection-switcher.tsx` |
| Update collection page to default to specific collection | pending | `app/collection/page.tsx` |

## Technical Details

### Default Collection ID

```python
# In skillmeat/cache/models.py
DEFAULT_COLLECTION_ID = "default"
DEFAULT_COLLECTION_NAME = "Default Collection"
```

### Database Initialization

```python
# In ensure_default_collection()
def ensure_default_collection(session: Session) -> Collection:
    """Ensure the default collection exists, creating it if necessary."""
    existing = session.query(Collection).filter_by(id=DEFAULT_COLLECTION_ID).first()
    if existing:
        return existing

    default_collection = Collection(
        id=DEFAULT_COLLECTION_ID,
        name=DEFAULT_COLLECTION_NAME,
        description="Default collection for all artifacts",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    session.add(default_collection)
    session.commit()
    return default_collection
```

### Frontend Default Selection

```typescript
// In collection-context.tsx
const DEFAULT_COLLECTION_ID = 'default';

// Initial state should be 'default' instead of null
const [selectedCollectionId, setSelectedCollectionIdState] = useState<string | null>(DEFAULT_COLLECTION_ID);

// Load from localStorage, but fall back to 'default' instead of null
useEffect(() => {
  const stored = localStorage.getItem(STORAGE_KEY);
  setSelectedCollectionIdState(stored || DEFAULT_COLLECTION_ID);
}, []);
```

## Quality Gates

```bash
# Backend tests
pytest skillmeat/api/tests/ -v -k "collection"

# Frontend tests
cd skillmeat/web && pnpm test -- --testPathPattern="collection"

# Type checks
pnpm typecheck

# Full quality check
pnpm lint && pnpm build
```

## Migration Consideration

Existing artifacts without collection associations will need to be migrated to the default collection. This can be a one-time migration script or handled lazily when artifacts are accessed.

**Option 1 (Recommended)**: Lazy migration - when listing artifacts, auto-add to default collection if not in any collection
**Option 2**: Batch migration script on server startup

## Notes

- The "All Collections" view can remain as a way to see all artifacts across all collections
- Users can still create additional collections and move artifacts
- This is backwards compatible - existing behavior preserved, just defaults change
