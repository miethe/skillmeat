---
type: context
prd: smart-import-discovery
title: Smart Import & Discovery - Development Context
status: active
created: '2025-11-30'
updated: '2025-11-30'
critical_notes_count: 0
implementation_decisions_count: 5
active_gotchas_count: 0
agent_contributors: []
agents: []
phase_status: []
blockers: []
decisions: []
integrations: []
gotchas: []
modified_files: []
schema_version: 2
doc_type: context
feature_slug: smart-import-discovery
---

# Smart Import & Discovery - Implementation Context

**PRD**: `/docs/project_plans/PRDs/enhancements/smart-import-discovery-v1.md`
**Progress Tracking**: `.claude/progress/smart-import-discovery/phase-1-progress.md`
**Implementation Plan**: `/docs/project_plans/implementation_plans/enhancements/smart-import-discovery-v1.md`

**Last Updated**: 2025-11-30

---

## Feature Overview

**Smart Import & Discovery** automates artifact acquisition through three complementary features:

1. **Auto-Discovery**: Scan `.claude/` directories to discover existing artifacts and offer bulk import with full preview and parameter editing
2. **Auto-Population**: Fetch metadata from GitHub and other sources to minimize manual data entry when adding artifacts
3. **Post-Import Parameter Editing**: Allow users to modify artifact source, version, scope, tags after initial import

**Priority**: HIGH | **Complexity**: Large (L) | **Effort**: 95-110 story points | **Timeline**: 4-6 weeks

---

## Key Feature Scope

### Auto-Discovery (Phase 1-4)
- Scan `.claude/artifacts/` recursively on page load
- Detect all artifact types: skill, command, agent, hook, MCP server
- Extract metadata from SKILL.md/COMMAND.md/AGENT.md frontmatter
- Display discovered artifacts in modal table with:
  - Type, name, version, source, tags columns
  - Checkbox selection per row (Select All / Deselect All)
  - Edit button per row to modify parameters before import
  - Atomic bulk import action
- Show discovery banner when artifacts found on /manage page
- Success toast with import count after completion

### Auto-Population (Phase 1-4)
- Parse GitHub URLs in standard format: `user/repo/path[@version]`
- Support HTTPS URLs: normalize to standard format
- Fetch metadata from three sources (priority order):
  1. SKILL.md / COMMAND.md / AGENT.md (frontmatter)
  2. README.md first paragraph
  3. GitHub API (owner, topics, license)
- Auto-populate form fields: name, description, author, topics, license
- Show loading state during fetch (skeleton or spinner)
- Allow user to edit auto-populated fields
- Graceful error handling if fetch fails (don't block submission, allow manual entry)
- Implement 1-hour TTL cache to reduce GitHub API load

### Post-Import Parameter Editing (Phase 4-5)
- Add "Edit Parameters" button on artifact detail page (Overview tab)
- Modal with fields: source, version, scope (select), tags, aliases
- Validation feedback on field blur
- Save button with loading state
- Atomic update to manifest and lock file
- Success/error feedback after save

---

## Technical Architecture Summary

### Layered Approach (MeatyPrompts Pattern)

```
Layer 6: Deployment & Monitoring
  └─ Feature flags, error tracking, analytics, monitoring

Layer 5: Documentation & API Specs
  └─ API endpoint docs, user guides, schema definitions

Layer 4: UI Layer (React/Next.js)
  └─ Discovery Banner, Bulk Import Modal, Auto-Population Form
  └─ Parameter Editor, React Query Hooks, Form validation

Layer 3: API Layer (FastAPI)
  └─ POST /artifacts/discover - scan .claude/
  └─ POST /artifacts/discover/import - bulk import
  └─ GET /artifacts/metadata/github - fetch metadata
  └─ PUT /artifacts/{id}/parameters - edit parameters

Layer 2: Service Layer (Python)
  └─ ArtifactDiscoveryService - scan and detect artifacts
  └─ GitHubMetadataExtractor - parse URLs, fetch metadata
  └─ ArtifactImporter - batch import with atomic transactions
  └─ MetadataCache - 1-hour TTL in-memory cache
  └─ ParameterValidator - source/version validation

Layer 1: Data Layer
  └─ No new DB schema (filesystem-based)
  └─ In-memory cache implementation
  └─ Manifest/lock file updates (existing infrastructure)
```

### New Services (Phase 1-2)

**ArtifactDiscoveryService** (`skillmeat/core/discovery.py`):
- `discover_artifacts()` - main entry point
- `_extract_artifact_metadata(artifact_path)` - extract YAML frontmatter
- `_detect_artifact_type(artifact_path)` - determine skill/command/agent/etc
- `_validate_artifact(artifact_path)` - check required files
- Returns: DiscoveryResult with list of DiscoveredArtifact + errors

**GitHubMetadataExtractor** (`skillmeat/core/github_metadata.py`):
- `parse_github_url(url)` - parse user/repo/path format and HTTPS URLs
- `fetch_metadata(source)` - main entry point with caching
- `_fetch_file_content(owner, repo, path)` - raw GitHub file fetch
- `_extract_frontmatter(content)` - YAML frontmatter parsing
- `_fetch_repo_metadata(owner, repo)` - GitHub API repo metadata
- Returns: GitHubMetadata with title, description, author, topics, license

**MetadataCache** (`skillmeat/core/cache.py`):
- `get(key)` - retrieve cached metadata if fresh
- `set(key, value)` - cache metadata with TTL
- `invalidate(key)` - remove cached entry
- Thread-safe, in-memory, 1-hour default TTL

**ArtifactImporter** (`skillmeat/core/importer.py`):
- `bulk_import(batch)` - main entry point for atomic import
- `_validate_batch(batch)` - validate all artifacts before import
- `_check_duplicate(source)` - detect duplicate sources
- `_atomic_transaction(artifacts)` - execute or rollback
- Returns: BulkImportResult with per-artifact status

**ParameterValidator** (`skillmeat/core/parameters.py`):
- `validate_parameters(params)` - check source format, version, scope, tags
- `update_parameters(artifact_id, params)` - atomic update to manifest/lock
- Returns: ValidationResult or updated artifact

### New API Endpoints (Phase 2)

**POST /api/v1/artifacts/discover**:
- Query: (optional) scan_path
- Response: DiscoveryResult (artifacts list, errors, scan_duration_ms)
- Status codes: 200 OK, 400 Bad Request, 401 Unauthorized, 500 Server Error

**POST /api/v1/artifacts/discover/import**:
- Body: BulkImportRequest (artifacts array with source, type, metadata)
- Response: BulkImportResult (per-artifact status, summary counts)
- Status codes: 200 OK, 400 Bad Request, 401 Unauthorized, 422 Unprocessable, 500 Server Error
- Atomic: all succeed or all fail (rollback on first error)

**GET /api/v1/artifacts/metadata/github**:
- Query: source (required, format: user/repo/path)
- Response: MetadataFetchResponse (metadata or error)
- Status codes: 200 OK, 400 Bad Request, 401 Unauthorized, 404 Not Found, 429 Rate Limited, 500 Server Error
- Cached: 1-hour TTL per source

**PUT /api/v1/artifacts/{artifact_id}/parameters**:
- Path: artifact_id (format: type:name)
- Body: ParameterUpdateRequest (source, version, scope, tags, aliases)
- Response: ParameterUpdateResponse (success, updated_fields)
- Status codes: 200 OK, 400 Bad Request, 401 Unauthorized, 404 Not Found, 422 Unprocessable, 500 Server Error
- Atomic: manifest and lock file updated together

### New Frontend Components (Phase 3)

**DiscoveryBanner** (`skillmeat/web/components/discovery/DiscoveryBanner.tsx`):
- Props: discoveredCount, onReview callback, dismissible flag
- Display: Alert with count, "Review & Import" button, optional dismiss
- Styling: shadcn/ui Alert component
- Accessibility: ARIA labels, keyboard navigation

**BulkImportModal** (`skillmeat/web/components/discovery/BulkImportModal.tsx`):
- Props: artifacts array, open bool, onClose, onImport callback
- Table columns: checkbox, type, name, version, source, tags, edit button
- Features: Select All / Deselect All, edit per row (opens ParameterEditor)
- Loading state during import, error toast on failure
- Styling: shadcn/ui Dialog, Table, Button, Checkbox
- Accessibility: keyboard navigation, screen reader announcements

**AutoPopulationForm** (`skillmeat/web/components/discovery/AutoPopulationForm.tsx`):
- Props: artifactType, onImport callback
- Input: GitHub source field with real-time validation
- Loading state: spinner/skeleton during metadata fetch
- Auto-populated fields: name, description, author, topics, license (read-only initially)
- User can edit auto-populated fields
- Error handling: show error toast, allow manual entry as fallback
- Styling: shadcn/ui Form, Input, Button, Skeleton

**ParameterEditorModal** (`skillmeat/web/components/discovery/ParameterEditorModal.tsx`):
- Props: artifact object, open bool, onClose, onSave callback
- Form fields: source, version, scope (select), tags, aliases
- Client-side validation with error messages on field blur
- Save button calls onSave with parameter updates
- Cancel button closes without saving
- Loading state during save
- Styling: shadcn/ui Dialog, Form, Input, Select, Button

### React Query Hooks (Phase 3)

**useDiscovery()** (`skillmeat/web/hooks/useDiscovery.ts`):
- Query: POST /artifacts/discover
- Returns: discoveredArtifacts, isDiscovering, discoverError
- Mutation: bulkImport (POST /artifacts/discover/import)
- Returns: bulkImport function, isImporting state
- Auto-invalidates artifact list on success

**useGitHubMetadata()** (`skillmeat/web/hooks/useGitHubMetadata.ts`):
- Mutation: GET /artifacts/metadata/github?source={source}
- Returns: metadata, isLoading, error
- Debounced fetch on URL change

**useEditArtifactParameters()** (`skillmeat/web/hooks/useEditArtifactParameters.ts`):
- Mutation: PUT /artifacts/{artifact_id}/parameters
- Input: artifactId, parameters object
- Returns: success response, updated fields
- Auto-invalidates artifact detail query on success

---

## Key Technical Decisions

### 1. Atomic Transactions for Bulk Import
- **Decision**: All artifacts in batch import atomically (all succeed or all fail)
- **Rationale**: Prevents partial corruption of collection, simplifies user experience
- **Implementation**: Validate all before import, use transaction wrapper, rollback on first error

### 2. GitHub Metadata Cache (1-hour TTL)
- **Decision**: In-memory cache with 1-hour TTL, not persistent
- **Rationale**: Reduces GitHub API load, simple implementation, sufficient for MVP
- **Future**: Persistent cache (Redis/database) in phase 2
- **Implementation**: MetadataCache class with get/set/invalidate methods

### 3. Graceful Error Handling for GitHub Failures
- **Decision**: If metadata fetch fails, don't block form submission (allow manual entry)
- **Rationale**: GitHub API is external dependency, users need fallback path
- **Implementation**: Error toast notifying user, form remains functional, user can edit fields manually

### 4. Server-Side Validation for All Parameters
- **Decision**: Backend validates all artifact parameters before saving
- **Rationale**: Security, data consistency, prevents malformed manifest/lock files
- **Implementation**: ParameterValidator service, consistent rules across all endpoints

### 5. Feature Flags for Gradual Rollout
- **Decision**: ENABLE_AUTO_DISCOVERY and ENABLE_AUTO_POPULATION feature flags
- **Rationale**: Allows gradual rollout, easy rollback if issues found
- **Implementation**: Check flags in API endpoints, return 501 Not Implemented if disabled

---

## Data Models & Schemas

### DiscoveredArtifact (Discovery Response)
```python
type: str  # skill, command, agent, hook, mcp
name: str
source: Optional[str]  # GitHub source or local path
version: Optional[str]
scope: Optional[str]  # user, local
tags: Optional[List[str]]
description: Optional[str]
path: str  # filesystem path for reimport
discovered_at: datetime
```

### GitHubMetadata (Auto-Population Response)
```python
title: Optional[str]  # artifact name
description: Optional[str]  # what it does
author: Optional[str]  # repo owner
license: Optional[str]  # MIT, Apache-2.0, etc
topics: List[str]  # GitHub topics/tags
url: str  # GitHub repo URL
fetched_at: datetime
source: str = "auto-populated"  # badge indicator
```

### BulkImportRequest (Import Action)
```python
artifacts: List[BulkImportArtifact]
  source: str  # required
  artifact_type: str  # required
  name: Optional[str]  # auto-derived if None
  description: Optional[str]
  author: Optional[str]
  tags: Optional[List[str]]
  scope: Optional[str] = "user"
auto_resolve_conflicts: bool = False
```

### ArtifactParameters (Post-Import Edit)
```python
source: Optional[str]  # user/repo/path
version: Optional[str]  # @latest, @v1.0.0, @sha
scope: Optional[str]  # user, local
tags: Optional[List[str]]
aliases: Optional[List[str]]
```

---

## Dependencies & Constraints

### External Dependencies

**Backend**:
- `pydantic` v2: Schema validation (required)
- `requests` or `httpx`: GitHub API client (required)
- `pathlib`: Directory scanning (stdlib)
- `python-frontmatter` or `yaml`: Markdown frontmatter (required)

**Frontend**:
- `@tanstack/react-query`: Server state management (existing)
- `react-hook-form`: Form state management (existing)
- `zod`: URL/schema validation (existing)
- `@radix-ui/dialog`, `@radix-ui/select`: Base components (existing)
- `shadcn/ui`: Higher-level components (existing)

**External APIs**:
- GitHub REST API v3: Rate limits 60/hr (unauthenticated), 5000/hr (authenticated)

### Internal Dependencies

**Existing Infrastructure Used**:
- ArtifactManager: Existing artifact creation and validation
- FileSystemStorage: Collection directory access
- Manifest parsing: TOML-based manifest structure
- Lock file updates: Version tracking infrastructure
- Entity detail page: Where parameter editing integrates
- /manage page: Where discovery integrates

**PRD Dependencies**:
- Entity Lifecycle Management PRD: Form infrastructure
- Web UI Consolidation PRD: Entity detail and table components

---

## Performance Targets

| Operation | Target | Benchmark | Notes |
|-----------|--------|-----------|-------|
| Discovery scan (50+ artifacts) | <2 seconds | Phase 5 SID-027 | Sequential scan, no parallelization |
| GitHub metadata fetch (uncached) | <1 second | Phase 5 SID-027 | Depends on GitHub API latency |
| GitHub metadata fetch (cached) | <100ms | Phase 5 SID-027 | Cache hit should be instant |
| Bulk import (20 artifacts) | <3 seconds | Phase 5 SID-027 | Includes validation and file I/O |
| URL paste to form auto-fill | <500ms | Phase 1-3 | User sees loading state |

**Optimization Strategies**:
- In-memory cache for GitHub metadata (1-hour TTL)
- Lazy loading for discovery modal (skeleton screens)
- Debounced fetch on URL input change (prevent excessive requests)
- Parallel reading of SKILL.md files during discovery
- Batch manifest/lock file updates (single write, not per-artifact)

---

## Testing Strategy Summary

### Phase 1-2: Unit Tests (Backend Services & API)
- **Coverage Target**: >80% for services, >70% for endpoints
- **Services**: test_discovery_service.py, test_github_metadata.py
- **API**: test_discovery_endpoints.py
- **Key Scenarios**: Success paths, error handling, cache behavior, validation

### Phase 3-4: Component & Integration Tests (Frontend)
- **Coverage Target**: >70% for components
- **Components**: discovery.test.tsx (Banner, Modal, Form, Editor)
- **Hooks**: Test async operations, error states, query invalidation
- **E2E Tests**: discovery.spec.ts, auto-population.spec.ts (full user journeys)

### Phase 5: Performance & Error Scenario Tests
- **Performance**: Benchmarks for scan, fetch, import (SID-027)
- **Error Scenarios**: GitHub API down, invalid artifacts, network failures (SID-028)
- **Accessibility**: Keyboard navigation, screen reader announcements (SID-029)
- **Smoke Tests**: Full system integration (SID-035)

---

## Documentation Requirements

### User Guides (Phase 5)
1. **Discovery Guide** (docs/guides/discovery-guide.md):
   - What is artifact discovery
   - How discovery works, when it runs
   - Bulk import workflow and parameters
   - Troubleshooting: artifacts not found, import fails
   - Best practices

2. **Auto-Population Guide** (docs/guides/auto-population-guide.md):
   - What is auto-population
   - Supported sources (GitHub primary)
   - How to paste GitHub URL
   - What metadata is auto-populated
   - Manual override if fetch fails
   - Troubleshooting: incomplete metadata

3. **API Documentation** (docs/api/discovery-endpoints.md):
   - All 4 endpoint specifications
   - Request/response schemas
   - Example requests and responses
   - Error codes and meanings
   - Rate limiting and caching details

---

## Risks & Mitigations

### High Priority Risks

**Risk: Bulk import fails partway, partial corruption**
- **Mitigation**: Atomic transactions with rollback; validate all before import
- **Owner**: Backend (SID-008)

**Risk: GitHub API rate limiting blocks metadata fetch**
- **Mitigation**: 1-hour cache, optional GitHub token, graceful fallback to manual entry
- **Owner**: Backend (SID-001)

**Risk: User selects wrong artifacts in bulk import**
- **Mitigation**: Clear preview table, explicit confirmation, atomic rollback
- **Owner**: Frontend (SID-014, SID-023)

### Medium Priority Risks

**Risk: Invalid artifacts in .claude/ crash discovery scan**
- **Mitigation**: Per-artifact error handling, skip invalid entries, detailed logging
- **Owner**: Backend (SID-002)

**Risk: Duplicate artifacts if user imports same source twice**
- **Mitigation**: Duplicate detection in batch, merge UI for conflicts
- **Owner**: Backend (SID-008), Frontend (SID-014)

**Risk: Discovery scan slow for projects with 100+ artifacts**
- **Mitigation**: Incremental scanning, background jobs, cache results (phase 2+)
- **Owner**: Backend (Phase 5 SID-027)

---

## Session Handoff Notes

### For Next Session Lead

**Current Status**: Progress tracking and context files created; ready for Phase 1 implementation

**Immediate Next Steps**:
1. Delegate Phase 1, Batch 1 to python-backend-engineer (SID-001/002/003 parallel)
2. Prepare test fixtures for directory scanning and GitHub API mocking
3. Set up CI/CD configuration for new tests and performance benchmarks

**Critical Success Factors**:
1. **Atomic Transactions**: Bulk import must be fully atomic (all-or-nothing)
2. **Performance Targets**: Meet <2s discovery, <1s cached fetch benchmarks
3. **Error Handling**: GitHub API failures must not block user flows
4. **Feature Flags**: Enable gradual rollout and easy rollback if issues arise

**Key Decisions to Ratify**:
- [ ] In-memory cache (not persistent) is sufficient for MVP
- [ ] Atomic bulk import with rollback is critical for data integrity
- [ ] Server-side validation required for all parameters
- [ ] GitHub as primary auto-population source; others COULD be phase 2

**Known Blockers**: None - all prerequisites (Entity Lifecycle, Web UI Consolidation) already in place

**Documentation Priority**: User guides critical for feature launch; API docs secondary

---

**Created**: 2025-11-30
**Status**: Ready for implementation kickoff
**Context Prepared By**: Claude Code (Opus-level orchestration)
