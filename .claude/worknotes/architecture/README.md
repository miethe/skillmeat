# Architecture Analysis Documents

This directory contains comprehensive analysis of SkillMeat's architecture patterns and design decisions.

## Documents

### 1. Collections-Artifacts Relationship Analysis
**File**: `collections-artifacts-relationship.md`

Complete breakdown of how collections and artifacts relate across the system:
- Database layer (ORM models and relationships)
- API layer (schemas, endpoints, conversion functions)
- Frontend layer (type definitions, UI logic)
- Data flow from backend to frontend
- The gap: what's missing to complete the implementation

**Key Finding**: Collections-artifacts is a proper many-to-many relationship fully implemented in the database, but the API layer doesn't expose it. The frontend is ready to consume it once the API provides the data.

### 2. Visual Reference Guide
**File**: `collections-artifacts-visual.md`

Visual diagrams and ASCII art showing:
- Database schema relationships
- API request/response flow
- Entity relationship diagrams
- Data structure comparisons (current vs. expected)
- File structure and locations

Use this document for quick visual reference when understanding the architecture.

### 3. Implementation Guide
**File**: `collections-artifacts-implementation.md`

Step-by-step instructions for completing the collections-artifacts integration:
- Current state summary
- Implementation steps (schema changes, function updates)
- Testing plan (unit, integration, frontend tests)
- Deployment checklist
- Impact analysis
- Alternative approaches

Ready to use as a task specification for implementation work.

---

## Quick Reference

### The Gap

The collections-artifacts many-to-many relationship is incomplete at the API layer:

| Component | Status | Notes |
|-----------|--------|-------|
| Database models | ✅ Complete | `Artifact.collections` relationship defined with eager loading |
| API schema | ❌ Missing | `ArtifactResponse` doesn't include `collections` field |
| API conversion | ❌ Missing | `artifact_to_response()` doesn't populate collections |
| Frontend types | ✅ Complete | `Artifact.collections` field defined in TypeScript |
| Frontend logic | ✅ Complete | UI already handles both single and multiple collections |
| Frontend UI | ⚠️ Partial | Collections tab shows only single collection until API populates data |

### Why It Matters

The Collections tab in the unified entity modal should show **all collections** containing an artifact, but currently only shows the primary collection because the API doesn't provide the complete list.

### How to Fix It

1. Add `collections: List[Dict[str, Any]]` field to `ArtifactResponse` schema
2. Populate it in `artifact_to_response()` from the ORM relationship
3. Test with unit, integration, and frontend tests
4. No database changes needed; no frontend code changes needed

**Time estimate**: 1-2 hours
**Complexity**: Low (additive change only)
**Risk**: Very low (backward compatible)

---

## Code Locations

### Backend

**Database Models** (`skillmeat/cache/models.py`):
- `Artifact` class (line 191)
  - Line 275-282: `collections` many-to-many relationship
- `Collection` class (line 623)
  - Line 680-684: `collection_artifacts` relationship
- `CollectionArtifact` class (line 881)
  - Junction table for many-to-many

**API Schemas** (`skillmeat/api/schemas/artifacts.py`):
- `ArtifactResponse` class (line 153)
  - Missing: `collections` field

**API Routers** (`skillmeat/api/routers/artifacts.py`):
- `artifact_to_response()` function (line 432)
  - Needs: populate collections from ORM relationship
- `list_artifacts()` endpoint (line 1512)
  - Uses artifact_to_response()

### Frontend

**Types** (`skillmeat/web/types/artifact.ts`):
- `Artifact` interface (line 46)
  - Line 60-63: `collection` (single)
  - Line 65-72: `collections` (multiple, TODO comment)

**Pages** (`skillmeat/web/app/collection/page.tsx`):
- `enrichArtifactSummary()` function (line 39)
- `artifactToEntity()` function (line 87)
  - Lines 113-130: handles collections array with fallback logic

---

## Related Documentation

### Dependencies
This analysis assumes knowledge of:
- SQLAlchemy ORM relationships (Python backend)
- FastAPI request/response patterns
- React hooks and state management (TypeScript frontend)
- Many-to-many relationship design patterns

### Referenced Rules
- `.claude/rules/api/routers.md` - Router layer patterns
- `.claude/rules/web/hooks.md` - Frontend hook patterns
- `.claude/rules/web/api-client.md` - Frontend API client conventions

### CLAUDE.md Files
- `skillmeat/api/CLAUDE.md` - Backend architecture
- `skillmeat/web/CLAUDE.md` - Frontend architecture
- Project root `CLAUDE.md` - Project directives

---

## Next Steps

1. **Review** these documents to understand the architecture
2. **Implement** the changes outlined in `collections-artifacts-implementation.md`
3. **Test** using the provided test plans
4. **Deploy** following the deployment checklist
5. **Verify** Collections tab shows all collections for artifacts

---

## Contact Points

When working on collections-artifacts integration, key files to edit:
1. `skillmeat/api/schemas/artifacts.py` - Add schema field
2. `skillmeat/api/routers/artifacts.py` - Populate from ORM
3. `skillmeat/api/tests/test_artifacts_routes.py` - Add tests

No frontend changes needed—UI will automatically work once API provides data.

---

## Document Maintenance

Last updated: 2026-01-11
Created for: Collections-artifacts relationship analysis and implementation planning

If you modify the database models, API schemas, or router logic related to artifacts or collections, please update these documents to stay synchronized.

