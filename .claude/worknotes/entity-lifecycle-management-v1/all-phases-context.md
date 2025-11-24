# Entity Lifecycle Management - Working Context

**Purpose:** Token-efficient context for subagents and resuming work across turns

---

## Current State

**Branch:** claude/execute-entity-lifecycle-mgmt-01Q4432o4ESbxCpxYccsTApi
**Last Commit:** 38a92f2 feat(api): Complete Phase 1 - Backend API Extensions
**Current Phase:** Phase 2 - Shared Components Foundation
**Current Task:** Starting Phase 2

### Phase 1 COMPLETE (27 pts)
- API-001: Project CRUD (POST/PUT/DELETE /projects) ✅
- API-002: Project Validation (Pydantic validators) ✅
- API-003: Artifact Creation (POST /artifacts) ✅
- API-004: Artifact Update (PUT /artifacts/{id}) ✅ (verified existing)
- API-005: Artifact Diff (GET /artifacts/{id}/diff) ✅
- API-006: Pull Endpoint (POST /artifacts/{id}/sync) ✅ (verified existing)
- API-007: SDK Regeneration ✅

---

## Codebase Structure

```
skillmeat/
├── api/
│   ├── routers/
│   │   ├── projects.py    # Project endpoints (GET list, GET detail, POST check-modifications, GET modified)
│   │   └── artifacts.py   # Artifact endpoints (GET list, GET detail, PUT update, DELETE, POST deploy, POST sync)
│   ├── schemas/
│   │   ├── projects.py    # Project schemas
│   │   ├── artifacts.py   # Artifact schemas
│   │   └── common.py      # Shared schemas (ErrorResponse, PageInfo)
│   └── dependencies.py    # FastAPI dependencies
└── web/
    ├── sdk/               # TypeScript SDK (regenerated from OpenAPI)
    └── components/        # React components
```

---

## Phase 1 Analysis

### Existing Endpoints (already implemented)
- `PUT /artifacts/{id}` - Updates metadata, tags, aliases (API-004 requirement)
- `POST /artifacts/{id}/sync` - Syncs changes from project to collection (API-006 requirement)

### Endpoints to Implement
1. `POST /projects` - Create new project
2. `PUT /projects/{id}` - Update project metadata
3. `DELETE /projects/{id}` - Remove project
4. `POST /artifacts` - Create artifact from GitHub URL or local path
5. `GET /artifacts/{id}/diff` - File-level diff between versions

### Key Patterns in Codebase
- Project IDs are base64-encoded paths (`encode_project_id()`/`decode_project_id()`)
- Artifact IDs use format `type:name` (e.g., `skill:canvas-design`)
- All endpoints use `TokenDep` for auth
- All endpoints wrap in try/except with HTTPException
- Use `ErrorResponse` schema for errors
- Use `PageInfo` for cursor pagination
- Logger per module: `logger = logging.getLogger(__name__)`

---

## Key Files for Phase 1

### Modify
- `skillmeat/api/routers/projects.py` - Add POST/PUT/DELETE
- `skillmeat/api/routers/artifacts.py` - Add POST root, GET diff
- `skillmeat/api/schemas/projects.py` - Add request/response schemas
- `skillmeat/api/schemas/artifacts.py` - Add diff response schemas

### Generate
- `skillmeat/web/sdk/` - Regenerate from OpenAPI

---

## Quick Reference

### Run Tests
```bash
pytest skillmeat/api/tests/ -v
```

### Generate OpenAPI
```bash
python -c "from skillmeat.api.server import app; import json; print(json.dumps(app.openapi()))" > skillmeat/api/openapi.json
```

### Regenerate SDK
```bash
cd skillmeat/web && npm run generate-sdk
```

---

## Session Notes

### 2025-11-24 - Session 1

**Analysis Complete:**
- Reviewed existing projects.py and artifacts.py routers
- Identified PUT /artifacts and POST sync already exist
- Listed missing endpoints for Phase 1

**Started:** API-001 - Project CRUD Endpoints
**Subagent:** python-backend-engineer
