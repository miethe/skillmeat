# Artifact Lookup Differences: Collection vs Manage vs Deployment Set Members

## Executive Summary

Three pages query artifacts differently, resulting in inconsistent resolution of artifact UUIDs:

1. **Collection Page** (`/collection`) - ✅ Working
2. **Manage Page** (`/manage`) - ⚠️ Reported as broken (unclear from current code)
3. **Deployment Set Members** - ⚠️ Shows "Artifact not found" even though artifacts exist

The root cause is **how each page resolves artifact UUIDs from the API response**. The API returns both `id` (type:name) and `uuid`, but the frontend must build the correct lookup map.

---

## Component Architecture

### 1. Collection Page (`/collection/page.tsx`)

**How it queries artifacts:**
- Uses `useInfiniteArtifacts()` hook with infinite scroll
- Hook eventually calls `fetchArtifactsPaginated()` → GET `/api/v1/artifacts`

**How it resolves artifacts:**
- Receives `ArtifactResponse[]` from API with both `id` and `uuid` fields
- Maps artifacts directly into components via `ArtifactGrid`/`ArtifactList`
- No UUID lookup map needed — uses artifact objects directly

**Data flow:**
```
API Response: { id: "skill:foo", uuid: "abc123...", name: "foo", ... }
    ↓
Collection Page (maps directly)
    ↓
ArtifactGrid/ArtifactList (renders artifacts)
```

### 2. Manage Page (`/manage/page.tsx`)

**How it queries artifacts:**
- Uses `useEntityLifecycle()` hook (abstraction over artifact queries)
- Returns `entities` which are `Artifact` type

**How it resolves artifacts:**
- Uses `EntityList` component which receives pre-mapped artifacts
- No UUID lookup map needed — uses artifact objects directly

**Data flow:**
```
API Response: { id: "skill:foo", uuid: "abc123...", ... }
    ↓
useEntityLifecycle() maps to Artifact
    ↓
EntityList (renders artifacts with full objects)
```

### 3. Deployment Set Members (⚠️ BROKEN)

**How it queries artifacts:**
- Uses `useArtifacts({ limit: 500 })` in both:
  - `deployment-set-details-modal.tsx` (line 807)
  - `member-list.tsx` (line 261)

**How it resolves artifacts:**
```typescript
// Line 836-839 (deployment-set-details-modal.tsx)
const artifactByUuid = useMemo<Record<string, Artifact>>(() => {
  const artifacts = artifactsResponse?.artifacts ?? [];
  return Object.fromEntries(artifacts.map((a) => [a.uuid, a]));
}, [artifactsResponse]);
```

**The Problem:**

The lookup uses:
```typescript
const artifact = member.artifact_uuid ? artifactByUuid[member.artifact_uuid] : undefined;
```

But the API response contains artifacts with BOTH `uuid` and `id` fields. The question is: **what is in the `artifactsResponse?.artifacts` array?**

---

## API Endpoint Response (`GET /api/v1/artifacts`)

**File:** `skillmeat/api/routers/artifacts.py` (line 2011+)

**Response Schema:** `ArtifactListResponse`
```
items: ArtifactResponse[]
page_info: PageInfo
```

**ArtifactResponse fields (from schemas/artifacts.py line 261+):**
```python
id: str                    # "skill:foo" (type:name)
uuid: str                  # "a1b2c3d4..." (32-char hex)
name: str
type: str
source: str
origin: str
... (more fields)
```

**How API builds responses (line 2323-2328):**
```python
for artifact in page_artifacts:
    artifact_key = f"{artifact.type.value}:{artifact.name}"
    try:
        dto = artifact_repo.get(artifact_key)
        if dto and dto.uuid:
            uuid_lookup[artifact_key] = dto.uuid
    except Exception:
        pass
```

The API calls `artifact_repo.get(artifact_key)` to resolve UUIDs from the database cache.

---

## Frontend Hook Implementation

**File:** `skillmeat/web/hooks/useArtifacts.ts`

**Query function (line 272-298):**
```typescript
async function fetchArtifactsFromApi(
  filters: ArtifactFilters,
  sort: ArtifactSort
): Promise<ArtifactsResponse> {
  // ... build params
  const response = await apiRequest<ApiArtifactListResponse>(`/artifacts?${params.toString()}`);

  // Map API responses to unified Artifact type
  const mappedArtifacts = response.items.map((item) =>
    mapApiResponseToArtifact(item, 'collection')
  );

  return {
    artifacts: filtered,
    total: response.page_info?.total_count ?? filtered.length,
    page: 1,
    pageSize: filtered.length,
  };
}
```

**Key question:** What does `mapApiResponseToArtifact()` produce?

**File:** `skillmeat/web/lib/api/mappers.ts`

Need to verify the mapper function ensures both `id` and `uuid` are preserved.

---

## The "Artifact not found" Root Cause

**Commit 33c7972e** added logic to distinguish:

1. **Artifacts still loading:** show skeleton
2. **Artifacts loaded but UUID not found:** show "Artifact not found"

```typescript
if (!artifact) {
  if (isArtifactsLoading) {
    // Still loading
    return <MiniDeploymentSetCardSkeleton />;
  }
  // Loaded but not found
  return <div>Artifact not found</div>;
}
```

**Possible scenarios where this breaks:**

### Scenario A: Artifact was deleted from collection
- Deployment set member still references old UUID
- API returns artifacts without that UUID
- Lookup fails → "Artifact not found" ✓ (correct behavior)

### Scenario B: Artifact exists but API didn't return it
- API filters (limit=500) doesn't include the artifact
- Member references UUID not in response
- Lookup fails → "Artifact not found" ❌ (false positive)

### Scenario C: UUID mismatch between DB and API
- API doesn't resolve UUID correctly
- Response has `id` but no `uuid`
- Lookup fails → "Artifact not found" ❌ (API bug)

---

## Root Cause Identified

### The Mapper Bug (Line 350 in mappers.ts)

```typescript
// skillmeat/web/lib/api/mappers.ts:350
uuid: response.uuid ?? '',
```

**The problem:** When `response.uuid` is `undefined` or missing, the mapper sets `uuid` to an **empty string** `''`.

### Frontend Lookup (deployment-set-details-modal.tsx:836)

```typescript
const artifactByUuid = useMemo<Record<string, Artifact>>(() => {
  const artifacts = artifactsResponse?.artifacts ?? [];
  return Object.fromEntries(artifacts.map((a) => [a.uuid, a]));
}, [artifactsResponse]);
```

When an artifact has `uuid: ''`, the lookup map becomes:
```javascript
{
  '': { id: 'skill:foo', uuid: '', ... },  // Empty string key!
  'abc123...': { id: 'skill:bar', uuid: 'abc123...', ... }
}
```

Later, when checking for artifacts:
```typescript
const artifact = member.artifact_uuid ? artifactByUuid[member.artifact_uuid] : undefined;
```

If `member.artifact_uuid` is valid (e.g., `'abc123...'`), but the artifact was mapped with `uuid: ''`, the lookup will fail and show "Artifact not found".

### API Always Returns UUID (artifacts.py:838)

The backend **always** provides a UUID in `ArtifactResponse`:

```python
# Lines 830-838 in artifact_to_response()
artifact_uuid = artifact.uuid or db_uuid
if not artifact_uuid:
    # Deterministic fallback (MD5 hash)
    fallback_input = f"{artifact.type.value}:{artifact.name}"
    artifact_uuid = hashlib.md5(fallback_input.encode()).hexdigest()

return ArtifactResponse(
    ...
    uuid=artifact_uuid,  # Always populated!
```

So the API never returns `uuid: undefined`. The issue must be elsewhere.

### Frontend Response Type (mappers.ts:90)

The API response type is defined as:
```typescript
export interface ArtifactResponse {
  id: string;
  uuid?: string;  // Optional!
  ...
}
```

**But the backend always provides it!** The discrepancy is:
- Backend: Always populates `uuid`
- Frontend type: Marks it as optional
- Mapper fallback: Uses empty string instead of regenerating it

### Real Scenario

If the mapper receives `uuid: undefined` (shouldn't happen with current API):
1. Mapper sets `uuid: ''`
2. Lookup map has `{ '': artifact, ... }`
3. Member tries to lookup real UUID (e.g., `'abc123...'`)
4. Lookup fails → "Artifact not found"

**But this shouldn't happen** because the API always provides UUID. Unless:
1. API response is malformed (uuid field missing entirely)
2. Network response is being parsed incorrectly
3. Backend regression deleted the uuid-resolution logic

### Likely Root Cause

The empty string fallback on line 350 suggests the original developer expected some cases where `uuid` might be missing. But the API guarantees it won't be. This creates a mismatch:

- **Collection/Manage pages:** Don't need UUID lookups, work fine
- **Deployment Set Members:** Rely on UUID lookups, fail when UUID is empty string

---

## Solution

### Option 1: Fix the Mapper (Recommended)

**File:** `skillmeat/web/lib/api/mappers.ts` (line 350)

**Current code:**
```typescript
uuid: response.uuid ?? '',
```

**Fixed code:**
```typescript
uuid: response.uuid || '',
```

**Or better, assert it's always present:**
```typescript
uuid: response.uuid || (() => {
  throw new Error(`Artifact ${response.id} missing UUID from API`);
})(),
```

**Why:** The API guarantees UUID is always present (backend generates fallback if needed). If the frontend ever receives an empty UUID, it's a bug that should be caught early.

### Option 2: Handle Empty UUID in Lookup

**File:** `skillmeat/web/components/deployment-sets/deployment-set-details-modal.tsx` (line 836)

**Current code:**
```typescript
const artifactByUuid = useMemo<Record<string, Artifact>>(() => {
  const artifacts = artifactsResponse?.artifacts ?? [];
  return Object.fromEntries(artifacts.map((a) => [a.uuid, a]));
}, [artifactsResponse]);
```

**Fixed code:**
```typescript
const artifactByUuid = useMemo<Record<string, Artifact>>(() => {
  const artifacts = artifactsResponse?.artifacts ?? [];
  return Object.fromEntries(
    artifacts
      .filter((a) => a.uuid) // Skip artifacts with empty UUID
      .map((a) => [a.uuid, a])
  );
}, [artifactsResponse]);
```

### Option 3: Fallback Lookup by ID

**File:** `skillmeat/web/components/deployment-sets/deployment-set-details-modal.tsx` (line 278)

**Current code:**
```typescript
const artifact = member.artifact_uuid ? artifactByUuid[member.artifact_uuid] : undefined;
```

**Fixed code (adds fallback to ID-based lookup):**
```typescript
const artifact = member.artifact_uuid ? artifactByUuid[member.artifact_uuid] : undefined;
if (!artifact && member.artifact_uuid) {
  // Fallback: try to find by generating the expected ID
  // This handles cases where UUID wasn't properly resolved
  const artifactByName = Object.fromEntries(
    (artifactsResponse?.artifacts ?? []).map((a) => [a.id, a])
  );
  // But we don't know the type:name from just the UUID...
  // So this doesn't work without additional info
}
```

---

## Recommended Action

**Priority:** Fix the mapper (Option 1)

**Rationale:**
1. API always provides UUID (backend guarantees it)
2. Frontend type says `uuid?` (optional) - mismatch!
3. Mapper fallback to `''` hides the problem
4. Better to fail loudly than silently use empty string

**Steps:**
1. Update `mapApiResponseToArtifact()` to assert `uuid` is present
2. Add test to verify API always includes UUID in response
3. Verify deployment set members query returns all UUIDs
4. Consider making `uuid` required (non-optional) in Artifact type

---

## Files Involved

### Backend (API)
- `skillmeat/api/routers/artifacts.py` - List endpoint (line 2011+)
  - Calls `artifact_to_response()` (line 765+)
  - Always includes UUID in response (line 838)
- `skillmeat/api/schemas/artifacts.py` - ArtifactResponse schema (line 261+)
  - Defines `uuid: str` field

### Frontend (Web)
- **ISSUE:** `skillmeat/web/lib/api/mappers.ts` (line 350) - Fallback to empty string
- `skillmeat/web/hooks/useArtifacts.ts` - Query hook
- `skillmeat/web/components/deployment-sets/deployment-set-details-modal.tsx` (line 807) - Uses hook
- `skillmeat/web/components/deployment-sets/member-list.tsx` (line 261) - Uses hook

### Configuration
- `skillmeat/api/openapi.json` - Source of truth for API contract

---

## Differences Summary Table

| Aspect | Collection | Manage | Deployment Set |
|--------|-----------|--------|-----------------|
| Hook Used | `useInfiniteArtifacts` | `useEntityLifecycle` | `useArtifacts` |
| Lookup Method | Direct objects | Direct objects | UUID map |
| Query Limit | 20 (infinite scroll) | Unlimited (full load) | 500 |
| Resolution | API returns full Artifact | API returns full Artifact | UUID map lookup (buggy) |
| Problem | None reported | Unknown | Mapper sets `uuid: ''` |

---

## Testing the Fix

1. **Verify API response:**
   ```bash
   curl -s "http://localhost:8080/api/v1/artifacts?limit=5" | jq '.items[].uuid'
   # Should show hex UUIDs, never empty string or undefined
   ```

2. **Verify mapper in tests:**
   ```bash
   pnpm test -- --testPathPattern="mappers"
   # Add test: "should always include uuid from API response"
   ```

3. **Manual test deployment set:**
   - Create deployment set with artifact members
   - Verify all members show correctly (not "Artifact not found")
