---
title: "Implementation Plan: Smart Import & Discovery"
description: "Detailed breakdown of implementation phases for auto-scanning, metadata auto-population, and bulk import workflows"
audience: [ai-agents, developers]
tags: [implementation-plan, planning, enhancement, discovery, import, automation]
created: 2025-11-30
updated: 2025-11-30
category: "project-planning"
status: active
prd_link: /docs/project_plans/PRDs/enhancements/smart-import-discovery-v1.md
---

# Implementation Plan: Smart Import & Discovery

**Feature Name:** Smart Import & Discovery

**PRD Reference:** `/docs/project_plans/PRDs/enhancements/smart-import-discovery-v1.md`

**Complexity Level:** Large (L) - Cross-system implementation spanning backend, frontend, and integration layers

**Total Estimated Effort:** 95-110 story points

**Target Timeline:** 4-6 weeks (5 sequential phases with parallel batch opportunities)

**Team Distribution:**
- Backend: python-backend-engineer, backend-architect
- Frontend: ui-engineer-enhanced, frontend-developer
- Data/Storage: data-layer-expert (if DB integration needed)
- Documentation: documentation-writer
- Testing: QA engineering focus

---

## Executive Summary

Smart Import & Discovery is a comprehensive feature set that automates artifact acquisition through three main capabilities:

1. **Auto-Discovery**: Scanning `.claude/` directories to discover existing artifacts and offer bulk import
2. **Auto-Population**: Fetching metadata from GitHub and other sources to minimize manual data entry
3. **Post-Import Editing**: Allowing users to modify artifact parameters after import

The implementation follows the MeatyPrompts layered architecture (Database → Repository → Service → API → UI → Testing → Docs → Deploy), breaking the work into 5 sequential phases that enable parallel execution within each phase.

---

## Architecture Overview

### Layered Architecture Alignment

```
Layer 6: Deployment & Monitoring
  └─ Feature flags, analytics instrumentation, error tracking

Layer 5: Documentation & API Specs
  └─ API endpoint documentation, user guides, schema definitions

Layer 4: UI Layer (React)
  └─ Discovery components, auto-population forms, parameter editors
  └─ React Query hooks, form validation, loading states

Layer 3: API Layer (FastAPI)
  └─ POST /api/v1/artifacts/discover - scan .claude/
  └─ POST /api/v1/artifacts/discover/import - bulk import
  └─ GET /api/v1/artifacts/metadata/github - fetch metadata
  └─ PUT /api/v1/artifacts/{id}/parameters - edit parameters
  └─ Response schemas and validation

Layer 2: Service Layer
  └─ ArtifactDiscoveryService - scan and detect artifacts
  └─ GitHubMetadataExtractor - parse URLs, fetch metadata
  └─ ArtifactImporter - batch import with validation
  └─ MetadataCache - in-memory cache with TTL
  └─ ParameterValidator - source/version validation

Layer 1: Repository & Data Layer
  └─ No new DB schema for MVP (filesystem-based)
  └─ Manifest file management (existing)
  └─ Lock file updates (existing)
  └─ In-memory cache implementation

Layer 0: Testing & Quality
  └─ Unit tests for services (>80% coverage)
  └─ Integration tests for API endpoints
  └─ E2E tests for user workflows
  └─ Performance benchmarks
```

### Component Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                        Frontend (Next.js)                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ Discovery    │  │ Bulk Import  │  │  Parameter   │          │
│  │ Banner       │  │ Modal/Table  │  │  Editor      │          │
│  │ Component    │  │              │  │  Modal       │          │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘          │
│         │                 │                 │                   │
│  ┌──────┴─────────────────┴─────────────────┴─────────┐         │
│  │  React Query Hooks                                 │         │
│  │  - useDiscovery                                    │         │
│  │  - useBulkImport                                  │         │
│  │  - useGitHubMetadata                              │         │
│  │  - useEditParameters                              │         │
│  └──────┬──────────────────────────────────────────────┘         │
└─────────┼────────────────────────────────────────────────────────┘
          │
          │ HTTP/JSON
          │
┌─────────┴──────────────────────────────────────────────────────┐
│                   API Layer (FastAPI)                          │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │ Router: /api/v1/artifacts                              │  │
│  │  POST   /discover          → ArtifactDiscoveryService │  │
│  │  POST   /discover/import   → ArtifactImporter         │  │
│  │  GET    /metadata/github   → GitHubMetadataExtractor  │  │
│  │  PUT    /{id}/parameters   → ParameterValidator       │  │
│  └─────────────────────────────────────────────────────────┘  │
└─────────┬──────────────────────────────────────────────────────┘
          │
┌─────────┴──────────────────────────────────────────────────────┐
│               Service Layer (Python Services)                  │
│  ┌────────────────────┐  ┌────────────────────────────────┐   │
│  │ ArtifactDiscovery  │  │ GitHubMetadataExtractor        │   │
│  │ - scan .claude/    │  │ - parse URLs                   │   │
│  │ - detect types     │  │ - fetch GitHub metadata        │   │
│  │ - extract metadata │  │ - extract frontmatter          │   │
│  │ - validate         │  │ - normalize metadata           │   │
│  └────────────────────┘  └────────────────────────────────┘   │
│  ┌────────────────────┐  ┌────────────────────────────────┐   │
│  │ ArtifactImporter   │  │ MetadataCache                  │   │
│  │ - validate batch   │  │ - in-memory cache              │   │
│  │ - atomic import    │  │ - 1-hour TTL                   │   │
│  │ - transaction mgmt │  │ - cache stats/metrics          │   │
│  │ - error rollback   │  │                                │   │
│  └────────────────────┘  └────────────────────────────────┘   │
└─────────┬──────────────────────────────────────────────────────┘
          │
┌─────────┴──────────────────────────────────────────────────────┐
│           Repository & Data Layer (Filesystem)                 │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │ ~/.skillmeat/collection/                               │ │
│  │ ├── artifacts/                                          │ │
│  │ │   ├── skills/                                        │ │
│  │ │   │   └── [artifact_name]/                           │ │
│  │ │   │       ├── SKILL.md (frontmatter with metadata) │ │
│  │ │   │       ├── manifest-lock.toml                    │ │
│  │ │   │       └── ...                                    │ │
│  │ │   ├── commands/, agents/, etc.                       │ │
│  │ ├── manifest.toml                                      │ │
│  │ └── manifest-lock.toml                                 │ │
│  └──────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

---

## Phase Breakdown

### Phase 1: Data Layer & Service Foundation (Weeks 1-1.5)

**Objectives:**
- Implement artifact discovery scanning logic
- Build GitHub metadata extraction service
- Create in-memory metadata cache
- Design and validate schemas

**Key Deliverables:**
- `ArtifactDiscoveryService` class
- `GitHubMetadataExtractor` class
- `MetadataCache` class
- Updated schema models
- >80% unit test coverage

#### Phase 1 Tasks

| Task ID | Title | Story Points | Assigned To | Dependencies | Acceptance Criteria |
|---------|-------|--------------|-------------|--------------|-------------------|
| SID-001 | Create GitHub Metadata Extraction Service | 8 | python-backend-engineer | None | Parse user/repo/path format, fetch GitHub metadata, cache responses, handle errors |
| SID-002 | Create Artifact Discovery Service | 8 | python-backend-engineer | None | Scan .claude/ directory, detect artifact types, extract basic metadata, validate |
| SID-003 | Implement Metadata Cache | 3 | python-backend-engineer | None | In-memory cache with 1-hour TTL, cache hit/miss tracking, thread-safe |
| SID-004 | Create Discovery & Import Schemas | 5 | backend-architect | SID-001, SID-002 | DiscoveredArtifactSchema, BulkImportRequest, GitHubMetadataResponse schemas |
| SID-005 | Unit Tests: GitHub Metadata Service | 5 | python-backend-engineer | SID-001 | >80% coverage, test URL parsing, API calls, metadata extraction, error scenarios |
| SID-006 | Unit Tests: Artifact Discovery Service | 5 | python-backend-engineer | SID-002 | >80% coverage, test directory scanning, artifact detection, error handling |

**Phase 1 Subtotals:** 34 story points | 1.5 weeks | 4 developers in parallel batches

**Phase 1 Quality Gates:**
- [ ] All services have >80% unit test coverage
- [ ] Error handling for invalid artifacts, GitHub API errors, missing directories
- [ ] Metadata cache correctly implements TTL
- [ ] All schemas validated against existing artifact structures
- [ ] Performance: discovery scan <2 seconds for 50+ artifacts

---

### Phase 2: API Endpoints & Integration (Weeks 1.5-2.5)

**Objectives:**
- Implement discovery API endpoint
- Implement bulk import API endpoint
- Implement metadata fetch endpoint
- Implement parameter edit endpoint
- Integration with existing artifact manager

**Key Deliverables:**
- 4 new API endpoints in `/api/v1/artifacts`
- Integration with ArtifactManager
- Request/response validation
- Error handling and rollback logic
- Integration tests (>70% coverage)

#### Phase 2 Tasks

| Task ID | Title | Story Points | Assigned To | Dependencies | Acceptance Criteria |
|---------|-------|--------------|-------------|--------------|-------------------|
| SID-007 | Implement Discovery Endpoint | 5 | python-backend-engineer | SID-002, SID-004 | POST /discover returns discovered artifacts, validates .claude/ path, handles errors |
| SID-008 | Implement Bulk Import Endpoint | 8 | python-backend-engineer | SID-002, SID-003, SID-004 | POST /discover/import validates batch, imports atomically, returns per-artifact results |
| SID-009 | Implement GitHub Metadata Endpoint | 5 | python-backend-engineer | SID-001, SID-004 | GET /metadata/github fetches metadata, caches response, validates GitHub URL format |
| SID-010 | Implement Parameter Edit Endpoint | 5 | backend-architect | SID-004 | PUT /{id}/parameters updates source/version/tags/scope, validates input, atomic transaction |
| SID-011 | Integration Tests: API Endpoints | 5 | python-backend-engineer | SID-007 through SID-010 | Test all endpoints, error scenarios, validation, atomic behavior |
| SID-012 | Error Handling & Validation | 5 | backend-architect | SID-007 through SID-010 | Consistent error codes, user-friendly messages, validation consistency across layers |

**Phase 2 Subtotals:** 33 story points | 1 week | Mostly sequential with some parallel opportunities

**Phase 2 Quality Gates:**
- [ ] All 4 endpoints implemented and tested
- [ ] Atomic operations verified for bulk import
- [ ] Error responses follow consistent format
- [ ] GitHub rate limiting handled gracefully
- [ ] Integration tests >70% coverage
- [ ] Performance: bulk import <3 seconds for 20 artifacts

---

### Phase 3: Frontend Components & Hooks (Weeks 2-3)

**Objectives:**
- Create discovery banner component
- Create bulk import modal with editable table
- Create auto-population form component
- Create parameter editor modal
- Build React Query hooks for all operations

**Key Deliverables:**
- 4 new React components
- 4 React Query custom hooks
- Form validation and state management
- Loading state management and UX
- Component integration tests

#### Phase 3 Tasks

| Task ID | Title | Story Points | Assigned To | Dependencies | Acceptance Criteria |
|---------|-------|--------------|-------------|--------------|-------------------|
| SID-013 | Create Discovery Banner Component | 3 | ui-engineer-enhanced | SID-007 | Show discovered count, clickable "Review" CTA, dismissible or persistent |
| SID-014 | Create Bulk Import Modal/Table | 8 | ui-engineer-enhanced | SID-007, SID-008 | Selectable rows, show all columns, editable parameters, "Import All" action |
| SID-015 | Create Auto-Population Form | 8 | ui-engineer-enhanced | SID-009 | URL input, loading state during fetch, auto-fill fields, error handling |
| SID-016 | Create Parameter Editor Modal | 5 | ui-engineer-enhanced | SID-010 | Edit source, version, scope, tags, aliases, save button, validation feedback |
| SID-017 | Create React Query Hooks | 5 | frontend-developer | SID-007 through SID-010 | useDiscovery, useBulkImport, useGitHubMetadata, useEditParameters hooks |
| SID-018 | Form Validation & Error States | 5 | frontend-developer | SID-015, SID-016, SID-017 | Client-side validation, error messages, loading states, success feedback |
| SID-019 | Component Integration Tests | 5 | frontend-developer | SID-013 through SID-018 | Test component rendering, user interactions, data flow, error scenarios |

**Phase 3 Subtotals:** 39 story points | 1.5 weeks | Mostly parallel with some sequential dependencies

**Phase 3 Quality Gates:**
- [ ] All 4 components render correctly in isolation and integrated
- [ ] React Query hooks properly handle async operations
- [ ] Form validation matches backend validation
- [ ] Loading states properly displayed
- [ ] Error messages clear and actionable
- [ ] Component tests >70% coverage

---

### Phase 4: Page Integration & UX Polish (Weeks 3-4)

**Objectives:**
- Integrate discovery banner into /manage page
- Integrate auto-population into add artifact form
- Integrate parameter editor into entity detail page
- Polish loading states and error messages
- Add analytics instrumentation

**Key Deliverables:**
- Integrated discovery workflow on /manage
- Integrated auto-population on add form
- Integrated parameter editing on entity detail
- Analytics events and tracking
- E2E test coverage for all workflows

#### Phase 4 Tasks

| Task ID | Title | Story Points | Assigned To | Dependencies | Acceptance Criteria |
|---------|-------|--------------|-------------|--------------|-------------------|
| SID-020 | Integrate Discovery into /manage Page | 5 | frontend-developer | SID-007, SID-013, SID-014 | Scan on load, show banner, modal flow, import success feedback |
| SID-021 | Integrate Auto-Population into Add Form | 5 | frontend-developer | SID-009, SID-015 | URL field with debounced fetch, form auto-fill, error recovery |
| SID-022 | Integrate Parameter Editor into Entity Detail | 3 | ui-engineer-enhanced | SID-010, SID-016 | Edit button placement, modal open/close, success feedback |
| SID-023 | Polish Loading States & Error Messages | 5 | frontend-developer | SID-014, SID-015, SID-016 | Skeleton states, clear error toasts, rollback feedback |
| SID-024 | Analytics Instrumentation | 5 | frontend-developer | SID-007 through SID-023 | Track discovery scans, auto-population fetches, bulk imports, parameter edits |
| SID-025 | E2E Tests: Discovery Flow | 8 | frontend-developer | All Phase 3 & 4 tasks | Full user journey: discover -> review -> import -> success |
| SID-026 | E2E Tests: Auto-Population Flow | 8 | frontend-developer | All Phase 3 & 4 tasks | Full user journey: paste URL -> fetch metadata -> fill form -> import |

**Phase 4 Subtotals:** 39 story points | 1-1.5 weeks | Mix of sequential and parallel

**Phase 4 Quality Gates:**
- [ ] All 3 pages/modals properly integrated
- [ ] E2E tests cover main user journeys
- [ ] Analytics events firing correctly
- [ ] Error scenarios tested and handled
- [ ] Loading states appropriate for each operation
- [ ] Accessibility checks passed

---

### Phase 5: Testing, Documentation & Deployment (Weeks 4.5-5.5)

**Objectives:**
- Complete comprehensive test coverage
- Performance testing and optimization
- Create user and API documentation
- Implement feature flags for gradual rollout
- Deploy and monitor

**Key Deliverables:**
- Comprehensive test suite (>85% coverage)
- Performance benchmarks and optimization
- User guide and API documentation
- Feature flags and monitoring
- Deployment checklist

#### Phase 5 Tasks

| Task ID | Title | Story Points | Assigned To | Dependencies | Acceptance Criteria |
|---------|-------|--------------|-------------|--------------|-------------------|
| SID-027 | Performance Testing & Optimization | 5 | python-backend-engineer | Phase 2, Phase 4 | Discovery <2s for 50+ artifacts, metadata fetch <1s (cached), bulk import <3s for 20 |
| SID-028 | Error Scenario Testing | 5 | python-backend-engineer | Phase 2, Phase 3 | GitHub API down, invalid artifacts, network failures, partial failures |
| SID-029 | Accessibility Audit | 3 | ui-engineer-enhanced | Phase 3, Phase 4 | Modal keyboard navigation, table row selection, loading announcements, error messages |
| SID-030 | User Guide: Discovery | 3 | documentation-writer | SID-007 | How to use discovery, what's discovered, troubleshooting, best practices |
| SID-031 | User Guide: Auto-Population | 3 | documentation-writer | SID-009 | How to use auto-population, supported sources, what gets auto-filled, manual overrides |
| SID-032 | API Documentation | 3 | documentation-writer | SID-007 through SID-010 | OpenAPI spec, endpoint examples, schema documentation, error codes |
| SID-033 | Feature Flag Implementation | 5 | backend-architect | Phase 2 | ENABLE_AUTO_DISCOVERY, ENABLE_AUTO_POPULATION feature flags with gradual rollout |
| SID-034 | Monitoring & Error Tracking | 5 | backend-architect | Phase 2, Phase 4 | Error tracking setup, performance metrics, analytics dashboard, alert thresholds |
| SID-035 | Final Integration & Smoke Tests | 5 | python-backend-engineer | All phases | Full system smoke tests, data consistency checks, no regressions |

**Phase 5 Subtotals:** 37 story points | 1-1.5 weeks | Mostly parallel with final integration sequential

**Phase 5 Quality Gates:**
- [ ] Overall test coverage >85% (backend + frontend combined)
- [ ] All performance benchmarks met
- [ ] All documentation complete and reviewed
- [ ] Feature flags implemented and tested
- [ ] Monitoring and error tracking configured
- [ ] Final smoke tests passed
- [ ] No regressions in existing features

---

## Implementation Details by Layer

### Layer 1: Data & Repository (Filesystem)

**No database schema changes in MVP** - Using existing filesystem structure:

```
~/.skillmeat/collection/
├── artifacts/
│   ├── skills/
│   │   └── [skill_name]/
│   │       ├── SKILL.md          # Frontmatter with metadata
│   │       ├── manifest-lock.toml # Version locking
│   │       ├── skill_content.txt   # Main artifact
│   │       └── ...
│   ├── commands/, agents/, etc.
├── manifest.toml                   # Collection manifest (existing)
└── manifest-lock.toml              # Lock file (existing)
```

**Manifest Structure** (existing, unchanged):

```toml
[tool.skillmeat]
version = "1.0.0"

[[artifacts]]
name = "canvas"
type = "skill"
source = "anthropics/skills/canvas-design"
version = "latest"
scope = "user"
tags = ["design", "canvas"]
description = "Canvas design skill"
```

**In-Memory Cache** (new implementation):

```python
# Python cache implementation
class MetadataCache:
    def __init__(self, ttl_seconds: int = 3600):
        self._cache = {}
        self._ttl = ttl_seconds

    def get(self, key: str) -> Optional[Dict]:
        """Get cached metadata if fresh"""

    def set(self, key: str, value: Dict) -> None:
        """Cache metadata with TTL"""

    def invalidate(self, key: str) -> None:
        """Remove cached entry"""
```

### Layer 2: Service Layer

#### Service 1: ArtifactDiscoveryService

```python
# Location: skillmeat/core/discovery.py

class ArtifactDiscoveryService:
    """Scans .claude/ directory and discovers existing artifacts."""

    def __init__(self, collection_path: Path):
        self.collection_path = collection_path
        self.supported_types = ["skill", "command", "agent", "hook", "mcp"]

    def discover_artifacts(self) -> DiscoveryResult:
        """
        Scan .claude/artifacts/ directory and discover all artifacts.

        Returns:
            DiscoveryResult: List of DiscoveredArtifact objects with metadata

        Raises:
            DiscoveryError: If scan fails
        """

    def _extract_artifact_metadata(self, artifact_path: Path) -> Dict:
        """Extract metadata from SKILL.md/COMMAND.md/AGENT.md frontmatter"""

    def _detect_artifact_type(self, artifact_path: Path) -> str:
        """Detect artifact type from directory structure and metadata file"""

    def _validate_artifact(self, artifact_path: Path) -> bool:
        """Validate artifact structure and required files"""
```

**Input/Output Schemas:**

```python
# Request
class DiscoveryRequest(BaseModel):
    scan_path: Optional[str] = None  # Default: ~/.skillmeat/collection/artifacts

# Response
class DiscoveredArtifact(BaseModel):
    type: str  # skill, command, agent, etc.
    name: str
    source: Optional[str]
    version: Optional[str]
    scope: Optional[str]
    tags: Optional[List[str]]
    description: Optional[str]
    path: str
    discovered_at: datetime

class DiscoveryResult(BaseModel):
    discovered_count: int
    artifacts: List[DiscoveredArtifact]
    errors: List[str]
    scan_duration_ms: float
```

#### Service 2: GitHubMetadataExtractor

```python
# Location: skillmeat/core/github_metadata.py

class GitHubMetadataExtractor:
    """Fetches metadata from GitHub for artifacts."""

    def __init__(self, cache: MetadataCache, token: Optional[str] = None):
        self.cache = cache
        self.token = token
        self.base_url = "https://api.github.com"

    def parse_github_url(self, url: str) -> GitHubSourceSpec:
        """
        Parse GitHub URL/spec format: user/repo/path[@version]

        Supports:
        - anthropics/skills/canvas-design
        - https://github.com/anthropics/repo/tree/main/skills/canvas-design
        - user/repo/path@v1.0.0
        """

    def fetch_metadata(self, source: str) -> GitHubMetadata:
        """
        Fetch metadata from GitHub for given source.

        Returns cached result if available (TTL: 1 hour).

        Fetches from:
        1. SKILL.md / COMMAND.md / AGENT.md (frontmatter)
        2. README.md (first paragraph)
        3. GitHub API (owner, topics, license)

        Returns:
            GitHubMetadata: Extracted and normalized metadata

        Raises:
            GitHubError: If fetch or parse fails
        """

    def _fetch_file_content(self, owner: str, repo: str, path: str) -> str:
        """Fetch file content from GitHub"""

    def _extract_frontmatter(self, content: str) -> Dict:
        """Extract YAML frontmatter from markdown file"""

    def _fetch_repo_metadata(self, owner: str, repo: str) -> Dict:
        """Fetch repo metadata from GitHub API"""
```

**Input/Output Schemas:**

```python
class GitHubSourceSpec(BaseModel):
    owner: str
    repo: str
    path: str
    version: Optional[str] = "latest"

class GitHubMetadata(BaseModel):
    title: Optional[str]
    description: Optional[str]
    author: Optional[str]
    license: Optional[str]
    topics: List[str] = []
    url: str
    fetched_at: datetime
    source: str = "auto-populated"

class MetadataFetchRequest(BaseModel):
    source: str  # GitHub source format

class MetadataFetchResponse(BaseModel):
    success: bool
    metadata: Optional[GitHubMetadata]
    error: Optional[str]
```

#### Service 3: ArtifactImporter

```python
# Location: skillmeat/core/importer.py

class ArtifactImporter:
    """Handles batch import of artifacts with validation and atomic transactions."""

    def __init__(self, artifact_manager: ArtifactManager):
        self.artifact_manager = artifact_manager

    def bulk_import(self, batch: BulkImportRequest) -> BulkImportResult:
        """
        Import multiple artifacts as atomic transaction.

        Process:
        1. Validate all artifacts in batch
        2. Check for duplicates/conflicts
        3. Import all or rollback on first error
        4. Update manifest and lock file

        Returns:
            BulkImportResult: Per-artifact success/failure with detailed status

        Raises:
            ImportError: If validation or import fails
        """

    def _validate_batch(self, batch: BulkImportRequest) -> ValidationResult:
        """Validate all artifacts before import"""

    def _check_duplicate(self, source: str) -> bool:
        """Check if artifact source already imported"""

    def _atomic_transaction(self, artifacts: List) -> None:
        """Execute atomic import or rollback"""
```

**Input/Output Schemas:**

```python
class BulkImportArtifact(BaseModel):
    source: str
    artifact_type: str
    name: Optional[str]  # Auto-derived if None
    description: Optional[str]
    author: Optional[str]
    tags: Optional[List[str]] = []
    scope: Optional[str] = "user"

class BulkImportRequest(BaseModel):
    artifacts: List[BulkImportArtifact]
    auto_resolve_conflicts: bool = False

class ImportResult(BaseModel):
    artifact_id: str
    success: bool
    message: str
    error: Optional[str]

class BulkImportResult(BaseModel):
    total_requested: int
    total_imported: int
    total_failed: int
    results: List[ImportResult]
    duration_ms: float
```

#### Service 4: ParameterValidator

```python
# Location: skillmeat/core/parameters.py

class ParameterValidator:
    """Validates and manages artifact parameters after import."""

    def validate_parameters(self, params: ArtifactParameters) -> ValidationResult:
        """
        Validate artifact parameters.

        Checks:
        - Source format (user/repo/path)
        - Version exists and is accessible
        - Scope is valid (user or local)
        - Tags are non-empty strings

        Returns:
            ValidationResult: Valid or detailed error list
        """

    def update_parameters(self, artifact_id: str, params: Dict) -> None:
        """Update artifact parameters atomically"""
```

**Input/Output Schemas:**

```python
class ArtifactParameters(BaseModel):
    source: Optional[str]
    version: Optional[str]
    scope: Optional[str]
    tags: Optional[List[str]]
    aliases: Optional[List[str]]

class ParameterUpdateRequest(BaseModel):
    parameters: ArtifactParameters

class ParameterUpdateResponse(BaseModel):
    success: bool
    artifact_id: str
    updated_fields: List[str]
    message: str
```

### Layer 3: API Endpoints

#### Endpoint 1: POST /api/v1/artifacts/discover

```python
@router.post("/discover", response_model=DiscoveryResult)
async def discover_artifacts(
    request: DiscoveryRequest,
    artifact_mgr: ArtifactManagerDep,
) -> DiscoveryResult:
    """
    Scan .claude/ directory for existing artifacts.

    Returns list of discovered artifacts with basic metadata.
    """
    service = ArtifactDiscoveryService(artifact_mgr.collection_path)
    result = service.discover_artifacts()
    return result
```

**Endpoint Contract:**
- **Method:** POST
- **Path:** `/api/v1/artifacts/discover`
- **Auth:** Required (Bearer token)
- **Request Body:** DiscoveryRequest (optional scan_path)
- **Response:** DiscoveryResult (artifacts list, error list, duration)
- **Status Codes:**
  - 200 OK: Discovery completed (may have errors per artifact)
  - 400 Bad Request: Invalid request parameters
  - 401 Unauthorized: Missing/invalid token
  - 500 Internal Server Error: Scan failed

#### Endpoint 2: POST /api/v1/artifacts/discover/import

```python
@router.post("/discover/import", response_model=BulkImportResult)
async def bulk_import_artifacts(
    request: BulkImportRequest,
    artifact_mgr: ArtifactManagerDep,
) -> BulkImportResult:
    """
    Bulk import multiple artifacts with atomic transaction.

    Validates all artifacts, imports all or none.
    """
    importer = ArtifactImporter(artifact_mgr)
    result = importer.bulk_import(request)
    return result
```

**Endpoint Contract:**
- **Method:** POST
- **Path:** `/api/v1/artifacts/discover/import`
- **Auth:** Required
- **Request Body:** BulkImportRequest (list of artifacts to import)
- **Response:** BulkImportResult (per-artifact status, summary counts)
- **Status Codes:**
  - 200 OK: Import completed (check per-artifact status)
  - 400 Bad Request: Validation failed
  - 401 Unauthorized: Missing/invalid token
  - 422 Unprocessable Entity: Invalid artifact format
  - 500 Internal Server Error: Import failed

#### Endpoint 3: GET /api/v1/artifacts/metadata/github

```python
@router.get("/metadata/github", response_model=MetadataFetchResponse)
async def fetch_github_metadata(
    source: str = Query(..., description="GitHub source: user/repo/path"),
    artifact_mgr: ArtifactManagerDep = None,
) -> MetadataFetchResponse:
    """
    Fetch metadata from GitHub for given source.

    Uses in-memory cache (TTL: 1 hour).
    """
    extractor = GitHubMetadataExtractor(cache)
    metadata = extractor.fetch_metadata(source)
    return MetadataFetchResponse(success=True, metadata=metadata)
```

**Endpoint Contract:**
- **Method:** GET
- **Path:** `/api/v1/artifacts/metadata/github`
- **Auth:** Required
- **Query Params:** source (required)
- **Response:** MetadataFetchResponse (metadata or error)
- **Status Codes:**
  - 200 OK: Metadata fetched successfully
  - 400 Bad Request: Invalid GitHub source format
  - 401 Unauthorized: Missing/invalid token
  - 404 Not Found: Repository not found
  - 429 Too Many Requests: GitHub rate limit exceeded
  - 500 Internal Server Error: Fetch failed

#### Endpoint 4: PUT /api/v1/artifacts/{artifact_id}/parameters

```python
@router.put("/{artifact_id}/parameters", response_model=ParameterUpdateResponse)
async def update_artifact_parameters(
    artifact_id: str,
    request: ParameterUpdateRequest,
    artifact_mgr: ArtifactManagerDep,
) -> ParameterUpdateResponse:
    """
    Update artifact parameters after import.

    Validates and atomically updates manifest and lock file.
    """
    validator = ParameterValidator()
    validator.validate_parameters(request.parameters)
    artifact_mgr.update_artifact(artifact_id, request.parameters)
    return ParameterUpdateResponse(success=True, ...)
```

**Endpoint Contract:**
- **Method:** PUT
- **Path:** `/api/v1/artifacts/{artifact_id}/parameters`
- **Auth:** Required
- **Path Params:** artifact_id (type:name format)
- **Request Body:** ParameterUpdateRequest (new parameter values)
- **Response:** ParameterUpdateResponse (success/failure, updated fields)
- **Status Codes:**
  - 200 OK: Parameters updated
  - 400 Bad Request: Invalid parameters
  - 401 Unauthorized: Missing/invalid token
  - 404 Not Found: Artifact not found
  - 422 Unprocessable Entity: Parameter validation failed
  - 500 Internal Server Error: Update failed

### Layer 4: Frontend Components

#### Component 1: DiscoveryBanner

```typescript
// Location: skillmeat/web/components/discovery/DiscoveryBanner.tsx

interface DiscoveryBannerProps {
  discoveredCount: number;
  onReview: () => void;
  dismissible?: boolean;
}

export function DiscoveryBanner({
  discoveredCount,
  onReview,
  dismissible = true,
}: DiscoveryBannerProps) {
  const [dismissed, setDismissed] = useState(false);

  if (dismissed) return null;

  return (
    <Alert variant="default" className="mb-4">
      <Info className="h-4 w-4" />
      <AlertTitle>Found {discoveredCount} Artifact(s)</AlertTitle>
      <AlertDescription>
        We discovered {discoveredCount} existing artifact(s) in your project.
        Review and import them to get started quickly.
      </AlertDescription>
      <div className="mt-2 flex gap-2">
        <Button size="sm" onClick={onReview}>
          Review & Import
        </Button>
        {dismissible && (
          <Button
            size="sm"
            variant="ghost"
            onClick={() => setDismissed(true)}
          >
            Dismiss
          </Button>
        )}
      </div>
    </Alert>
  );
}
```

#### Component 2: BulkImportModal

```typescript
// Location: skillmeat/web/components/discovery/BulkImportModal.tsx

interface BulkImportModalProps {
  artifacts: DiscoveredArtifact[];
  open: boolean;
  onClose: () => void;
  onImport: (selected: DiscoveredArtifact[]) => Promise<void>;
}

export function BulkImportModal({
  artifacts,
  open,
  onClose,
  onImport,
}: BulkImportModalProps) {
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [editing, setEditing] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleImport = async () => {
    setLoading(true);
    try {
      const toImport = artifacts.filter((a) => selected.has(a.path));
      await onImport(toImport);
      onClose();
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="max-w-3xl">
        <DialogHeader>
          <DialogTitle>Review Discovered Artifacts</DialogTitle>
        </DialogHeader>

        {/* Table of artifacts with checkboxes, edit buttons */}
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-12">
                <Checkbox
                  checked={selected.size === artifacts.length}
                  onCheckedChange={(checked) => {
                    if (checked) {
                      setSelected(new Set(artifacts.map((a) => a.path)));
                    } else {
                      setSelected(new Set());
                    }
                  }}
                />
              </TableHead>
              <TableHead>Type</TableHead>
              <TableHead>Name</TableHead>
              <TableHead>Version</TableHead>
              <TableHead>Source</TableHead>
              <TableHead>Tags</TableHead>
              <TableHead className="w-12">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {artifacts.map((artifact) => (
              <TableRow key={artifact.path}>
                <TableCell>
                  <Checkbox
                    checked={selected.has(artifact.path)}
                    onCheckedChange={(checked) => {
                      const newSelected = new Set(selected);
                      if (checked) {
                        newSelected.add(artifact.path);
                      } else {
                        newSelected.delete(artifact.path);
                      }
                      setSelected(newSelected);
                    }}
                  />
                </TableCell>
                <TableCell className="font-mono text-sm">
                  {artifact.type}
                </TableCell>
                <TableCell>{artifact.name}</TableCell>
                <TableCell>{artifact.version || "—"}</TableCell>
                <TableCell className="font-mono text-xs">
                  {artifact.source || "—"}
                </TableCell>
                <TableCell>{artifact.tags?.join(", ") || "—"}</TableCell>
                <TableCell>
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => setEditing(artifact.path)}
                  >
                    Edit
                  </Button>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>

        {/* Parameter editor inline or modal */}
        {editing && (
          <BulkImportParameterEditor
            artifact={artifacts.find((a) => a.path === editing)!}
            onSave={(updated) => {
              // Update artifact in list
              setEditing(null);
            }}
          />
        )}

        <DialogFooter>
          <Button variant="outline" onClick={onClose}>
            Cancel
          </Button>
          <Button
            onClick={handleImport}
            disabled={selected.size === 0 || loading}
          >
            {loading ? "Importing..." : `Import ${selected.size} Artifact(s)`}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
```

#### Component 3: AutoPopulationForm

```typescript
// Location: skillmeat/web/components/discovery/AutoPopulationForm.tsx

interface AutoPopulationFormProps {
  artifactType: string;
  onImport: (artifact: ArtifactCreateRequest) => Promise<void>;
}

export function AutoPopulationForm({
  artifactType,
  onImport,
}: AutoPopulationFormProps) {
  const [source, setSource] = useState("");
  const [loading, setLoading] = useState(false);
  const [metadata, setMetadata] = useState<GitHubMetadata | null>(null);

  const { mutate: fetchMetadata } = useMutation({
    mutationFn: async (source: string) => {
      const res = await api.get(`/artifacts/metadata/github?source=${source}`);
      return res.data.metadata;
    },
    onSuccess: (data) => setMetadata(data),
  });

  const handleSourceChange = (value: string) => {
    setSource(value);
    // Debounce fetch
    if (value.includes("/")) {
      fetchMetadata(value);
    }
  };

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        // Create artifact with auto-populated metadata
        onImport({
          source,
          artifact_type: artifactType,
          name: metadata?.title,
          description: metadata?.description,
          tags: metadata?.topics,
        });
      }}
    >
      <FormField
        label="GitHub Source"
        placeholder="user/repo/path or https://github.com/..."
        value={source}
        onChange={handleSourceChange}
      />

      {loading && <Skeleton className="h-10" />}

      {metadata && (
        <>
          <FormField label="Name" value={metadata.title} readOnly />
          <FormField label="Description" value={metadata.description} readOnly />
          <FormField
            label="Author"
            value={metadata.author}
            readOnly
          />
          <FormField
            label="Topics"
            value={metadata.topics?.join(", ")}
            readOnly
          />
        </>
      )}

      <Button type="submit" disabled={!source || loading}>
        Import
      </Button>
    </form>
  );
}
```

#### Component 4: ParameterEditorModal

```typescript
// Location: skillmeat/web/components/discovery/ParameterEditorModal.tsx

interface ParameterEditorModalProps {
  artifact: ArtifactResponse;
  open: boolean;
  onClose: () => void;
  onSave: (parameters: ArtifactParameters) => Promise<void>;
}

export function ParameterEditorModal({
  artifact,
  open,
  onClose,
  onSave,
}: ParameterEditorModalProps) {
  const form = useForm({
    defaultValues: {
      source: artifact.source,
      version: artifact.version,
      scope: artifact.scope,
      tags: artifact.tags,
    },
  });

  const onSubmit = async (data: ArtifactParameters) => {
    await onSave(data);
    onClose();
  };

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Edit Artifact Parameters</DialogTitle>
        </DialogHeader>

        <form onSubmit={form.handleSubmit(onSubmit)}>
          <FormField
            label="Source"
            {...form.register("source")}
            placeholder="user/repo/path"
          />
          <FormField
            label="Version"
            {...form.register("version")}
            placeholder="latest or @v1.0.0"
          />
          <FormField
            label="Scope"
            as="select"
            {...form.register("scope")}
          >
            <option value="user">User (Global)</option>
            <option value="local">Local (Project)</option>
          </FormField>
          <FormField
            label="Tags"
            {...form.register("tags")}
            placeholder="Comma-separated tags"
          />

          <DialogFooter>
            <Button variant="outline" onClick={onClose}>
              Cancel
            </Button>
            <Button type="submit">Save Changes</Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
```

### Layer 5: React Query Hooks

```typescript
// Location: skillmeat/web/hooks/useDiscovery.ts

export function useDiscovery() {
  const queryClient = useQueryClient();

  const discoverQuery = useQuery({
    queryKey: ["artifacts", "discover"],
    queryFn: async () => {
      const res = await api.post("/artifacts/discover", {});
      return res.data;
    },
  });

  const bulkImportMutation = useMutation({
    mutationFn: async (request: BulkImportRequest) => {
      const res = await api.post("/artifacts/discover/import", request);
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["artifacts"],
      });
    },
  });

  return {
    discoveredArtifacts: discoverQuery.data?.artifacts || [],
    isDiscovering: discoverQuery.isLoading,
    discoverError: discoverQuery.error,
    bulkImport: bulkImportMutation.mutateAsync,
    isImporting: bulkImportMutation.isPending,
  };
}

export function useGitHubMetadata() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (source: string) => {
      const res = await api.get(`/artifacts/metadata/github?source=${source}`);
      return res.data.metadata;
    },
    onSuccess: (metadata, source) => {
      queryClient.setQueryData(["artifacts", "metadata", source], metadata);
    },
  });
}

export function useEditArtifactParameters() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      artifactId,
      parameters,
    }: {
      artifactId: string;
      parameters: ArtifactParameters;
    }) => {
      const res = await api.put(`/artifacts/${artifactId}/parameters`, {
        parameters,
      });
      return res.data;
    },
    onSuccess: (_, { artifactId }) => {
      queryClient.invalidateQueries({
        queryKey: ["artifacts", artifactId],
      });
    },
  });
}
```

---

## Testing Strategy

### Unit Tests (>80% Coverage)

**Backend Service Tests** (`skillmeat/core/tests/`):

```python
# test_discovery_service.py
def test_discover_artifacts_success(temp_collection):
    """Test successful artifact discovery"""

def test_discover_artifacts_empty_directory():
    """Test discovery when no artifacts found"""

def test_discover_artifacts_invalid_artifact(temp_collection):
    """Test graceful handling of invalid artifacts"""

def test_discover_artifacts_performance(large_collection):
    """Test performance: <2 seconds for 50+ artifacts"""

# test_github_metadata_extractor.py
def test_parse_github_url_standard_format():
    """Test parsing user/repo/path format"""

def test_parse_github_url_https_format():
    """Test parsing https://github.com/... format"""

def test_fetch_metadata_with_cache():
    """Test metadata cache hit"""

def test_fetch_metadata_github_api_error():
    """Test graceful error handling for API failures"""

# test_artifact_importer.py
def test_bulk_import_success(temp_collection):
    """Test successful bulk import"""

def test_bulk_import_atomic_rollback(temp_collection):
    """Test rollback on error"""

def test_bulk_import_duplicate_detection(temp_collection):
    """Test duplicate artifact detection"""
```

**Frontend Component Tests** (`skillmeat/web/tests/`):

```typescript
// DiscoveryBanner.test.tsx
describe("DiscoveryBanner", () => {
  it("displays discovered count", () => {
    render(<DiscoveryBanner discoveredCount={5} onReview={() => {}} />);
    expect(screen.getByText(/Found 5 Artifact/)).toBeInTheDocument();
  });

  it("calls onReview when button clicked", async () => {
    const onReview = vi.fn();
    render(<DiscoveryBanner discoveredCount={5} onReview={onReview} />);
    await userEvent.click(screen.getByText("Review & Import"));
    expect(onReview).toHaveBeenCalled();
  });
});

// BulkImportModal.test.tsx
describe("BulkImportModal", () => {
  it("renders artifacts in table", () => {
    const artifacts = [
      { path: "1", type: "skill", name: "test", version: "latest" },
    ];
    render(
      <BulkImportModal
        artifacts={artifacts}
        open={true}
        onClose={() => {}}
        onImport={() => Promise.resolve()}
      />
    );
    expect(screen.getByText("test")).toBeInTheDocument();
  });

  it("selects artifacts for import", async () => {
    const artifacts = [
      { path: "1", type: "skill", name: "test1" },
      { path: "2", type: "skill", name: "test2" },
    ];
    render(
      <BulkImportModal
        artifacts={artifacts}
        open={true}
        onClose={() => {}}
        onImport={() => Promise.resolve()}
      />
    );
    const checkboxes = screen.getAllByRole("checkbox");
    await userEvent.click(checkboxes[1]); // Select first artifact
    expect(screen.getByText(/Import 1 Artifact/)).toBeInTheDocument();
  });
});
```

### Integration Tests (>70% Coverage)

**API Integration Tests** (`skillmeat/api/tests/`):

```python
def test_discovery_endpoint_success(client, temp_collection):
    """Test POST /artifacts/discover endpoint"""
    response = client.post("/api/v1/artifacts/discover")
    assert response.status_code == 200
    assert "artifacts" in response.json()

def test_bulk_import_endpoint_success(client, temp_collection):
    """Test POST /artifacts/discover/import endpoint"""
    request_data = {
        "artifacts": [
            {
                "source": "anthropics/skills/canvas",
                "artifact_type": "skill",
            }
        ]
    }
    response = client.post("/api/v1/artifacts/discover/import", json=request_data)
    assert response.status_code == 200
    assert response.json()["total_imported"] > 0

def test_metadata_endpoint_success(client):
    """Test GET /artifacts/metadata/github endpoint"""
    response = client.get("/api/v1/artifacts/metadata/github?source=anthropics/skills/canvas")
    assert response.status_code == 200
    assert "metadata" in response.json()

def test_parameter_update_endpoint(client, imported_artifact):
    """Test PUT /artifacts/{id}/parameters endpoint"""
    response = client.put(
        f"/api/v1/artifacts/{imported_artifact.id}/parameters",
        json={"parameters": {"tags": ["new-tag"]}}
    )
    assert response.status_code == 200
    assert response.json()["success"] is True
```

### E2E Tests (Full User Workflows)

**Discovery Flow E2E** (`skillmeat/web/e2e/discovery.spec.ts`):

```typescript
describe("Discovery Flow", () => {
  it("discovers and imports artifacts", async ({ page }) => {
    await page.goto("http://localhost:3000/manage");

    // Wait for discovery banner
    await expect(page.getByText(/Found .* Artifact/)).toBeVisible();

    // Click Review & Import
    await page.click("text=Review & Import");

    // Modal opens
    await expect(page.getByRole("dialog")).toBeVisible();

    // Select artifacts
    const checkboxes = await page.locator('input[type="checkbox"]').all();
    await checkboxes[0].click();

    // Click Import
    await page.click("text=Import");

    // Wait for success
    await expect(page.getByText(/imported successfully/)).toBeVisible();
  });
});
```

### Performance Tests

```python
def test_discovery_performance(large_collection):
    """Discovery scan completes <2 seconds for 50+ artifacts"""
    start = time.time()
    service = ArtifactDiscoveryService(large_collection.path)
    result = service.discover_artifacts()
    duration = time.time() - start

    assert duration < 2.0, f"Discovery took {duration}s (expected <2s)"

def test_metadata_fetch_performance():
    """Metadata fetch <1 second (cached)"""
    cache = MetadataCache()
    extractor = GitHubMetadataExtractor(cache)

    # First call (uncached)
    start = time.time()
    result1 = extractor.fetch_metadata("anthropics/skills/canvas")
    duration1 = time.time() - start

    # Second call (cached)
    start = time.time()
    result2 = extractor.fetch_metadata("anthropics/skills/canvas")
    duration2 = time.time() - start

    assert duration2 < 0.1, f"Cached fetch took {duration2}s (expected <0.1s)"
```

---

## Risk Mitigation Strategy

| Risk | Impact | Likelihood | Mitigation | Owner |
|------|--------|-----------|-----------|-------|
| GitHub API rate limiting | MEDIUM | MEDIUM | Implement cache (1h TTL), optional token auth, graceful fallback | Backend |
| Partial bulk import corruption | HIGH | LOW | Atomic transaction with rollback, validate all before import | Backend |
| Invalid artifacts crash scanner | MEDIUM | MEDIUM | Per-artifact error handling, skip invalid entries, detailed logging | Backend |
| User selects wrong artifacts | MEDIUM | MEDIUM | Clear preview table, explicit confirmation dialog, atomic rollback | Frontend |
| Metadata from GitHub incomplete | LOW | MEDIUM | Show "auto-populated" badge, allow user edits, manual override | Frontend |
| Large project discovery slow | MEDIUM | LOW | Incremental scanning, background jobs, cache results | Backend |
| Duplicate artifact imports | MEDIUM | MEDIUM | Duplicate detection, merge conflicts UI, per-artifact resolution | Backend |
| Non-standard GitHub formats break parser | MEDIUM | LOW | Strict format validation, clear error messages, manual fallback | Backend |

---

## Orchestration Quick Reference

Use the following Task() commands to delegate implementation work to subagents. Execute batches in order, with parallel execution within each batch.

### Batch 1: Database & Service Foundation (Phase 1)

Execute all tasks in parallel:

```text
Task("python-backend-engineer", "
  TASK SID-001: Create GitHub Metadata Extraction Service

  Create skillmeat/core/github_metadata.py with GitHubMetadataExtractor class.

  Requirements:
  - Parse user/repo/path format and HTTPS URLs
  - Fetch metadata from GitHub API and file content
  - Extract YAML frontmatter from SKILL.md/COMMAND.md
  - Cache responses with 1-hour TTL
  - Handle GitHub API rate limits and errors gracefully
  - Support optional GitHub token for higher rate limits

  Input schemas: GitHubSourceSpec, MetadataFetchRequest
  Output schemas: GitHubMetadata, MetadataFetchResponse

  Acceptance criteria:
  - Parses all standard GitHub URL formats
  - Fetches real metadata from GitHub API
  - Caches responses correctly
  - Errors don't block form submission (manual override)

  Estimate: 8 story points
")

Task("python-backend-engineer", "
  TASK SID-002: Create Artifact Discovery Service

  Create skillmeat/core/discovery.py with ArtifactDiscoveryService class.

  Requirements:
  - Scan .claude/artifacts/ directory recursively
  - Detect artifact types (skill, command, agent, hook, mcp)
  - Extract metadata from SKILL.md/COMMAND.md/AGENT.md frontmatter
  - Validate artifact structure and required files
  - Handle invalid artifacts gracefully (log, skip, continue)
  - Return structured DiscoveryResult with artifacts list and errors

  Input schemas: DiscoveryRequest
  Output schemas: DiscoveryResult, DiscoveredArtifact

  Acceptance criteria:
  - Discovers 100% of valid artifacts in .claude/
  - Handles invalid artifacts without crashing
  - Completes scan <2 seconds for 50+ artifacts
  - Extracts name, type, source, version, tags, description

  Estimate: 8 story points
")

Task("python-backend-engineer", "
  TASK SID-003: Implement Metadata Cache

  Create skillmeat/core/cache.py with MetadataCache class.

  Requirements:
  - In-memory cache with configurable TTL (default 1 hour)
  - Cache GitHub metadata responses by source key
  - Track cache hits/misses for analytics
  - Thread-safe operations
  - Optional persistent backend (not MVP)
  - Simple API: get(), set(), invalidate()

  Acceptance criteria:
  - Cache correctly stores and retrieves entries
  - TTL expiration works correctly
  - Thread-safe for concurrent requests
  - Cache hits reduce GitHub API calls

  Estimate: 3 story points
")

Task("backend-architect", "
  TASK SID-004: Create Discovery & Import Schemas

  Create/update skillmeat/api/schemas/artifacts.py with new schemas.

  New schemas needed:
  - DiscoveredArtifact
  - DiscoveryRequest, DiscoveryResult
  - BulkImportArtifact, BulkImportRequest
  - ImportResult, BulkImportResult
  - GitHubMetadata, MetadataFetchRequest, MetadataFetchResponse
  - ArtifactParameters, ParameterUpdateRequest, ParameterUpdateResponse

  Requirements:
  - Use Pydantic v2 syntax
  - Include examples in Config.json_schema_extra
  - Proper field validation (required, optional, constraints)
  - Consistent with existing ArtifactCreateRequest pattern

  Acceptance criteria:
  - All schemas properly typed and documented
  - Examples provided for all request/response types
  - Validation matches backend business logic

  Estimate: 5 story points
")

Task("python-backend-engineer", "
  TASK SID-005: Unit Tests: GitHub Metadata Service

  Create skillmeat/core/tests/test_github_metadata.py.

  Test coverage needed (>80%):
  - URL parsing: standard format, HTTPS, with version
  - Metadata fetching: successful fetch, GitHub API errors, rate limiting
  - Frontmatter extraction: valid YAML, missing fields, malformed
  - Caching: cache hit, cache miss, TTL expiration
  - Error scenarios: network errors, invalid JSON, timeouts

  Use pytest fixtures for mocking GitHub API responses.

  Acceptance criteria:
  - >80% code coverage
  - Tests for all public methods
  - Error scenarios covered
  - Mocks prevent real GitHub API calls in tests

  Estimate: 5 story points
")

Task("python-backend-engineer", "
  TASK SID-006: Unit Tests: Artifact Discovery Service

  Create skillmeat/core/tests/test_discovery_service.py.

  Test coverage needed (>80%):
  - Discovery: successful scan, empty directory, multiple artifacts
  - Type detection: skill, command, agent, hook, mcp
  - Metadata extraction: valid artifacts, missing files, incomplete metadata
  - Error handling: invalid artifacts, permission errors, filesystem errors
  - Performance: <2 seconds for 50+ artifacts

  Use pytest fixtures to create temporary test collections.

  Acceptance criteria:
  - >80% code coverage
  - Performance benchmark verified
  - All artifact types tested
  - Error scenarios handled gracefully

  Estimate: 5 story points
")
```

### Batch 2: API Endpoints & Integration (Phase 2)

Execute mostly sequential after Batch 1 completes, but tasks SID-012 can start once services are ready:

```text
Task("python-backend-engineer", "
  TASK SID-007: Implement Discovery Endpoint

  Add to skillmeat/api/routers/artifacts.py:

  @router.post('/discover', response_model=DiscoveryResult)
  async def discover_artifacts(
      request: DiscoveryRequest,
      artifact_mgr: ArtifactManagerDep
  ) -> DiscoveryResult:
      '''Scan .claude/ directory for existing artifacts.'''

  Implementation:
  - Create ArtifactDiscoveryService instance
  - Call discover_artifacts() method
  - Return DiscoveryResult with artifacts and errors
  - Log discovery results for analytics

  Acceptance criteria:
  - Endpoint returns proper HTTP status codes (200, 400, 401, 500)
  - DiscoveryResult includes all discovered artifacts
  - Errors reported per-artifact
  - Scan duration tracked

  Estimate: 5 story points
")

Task("python-backend-engineer", "
  TASK SID-008: Implement Bulk Import Endpoint

  Add to skillmeat/api/routers/artifacts.py:

  @router.post('/discover/import', response_model=BulkImportResult)
  async def bulk_import_artifacts(
      request: BulkImportRequest,
      artifact_mgr: ArtifactManagerDep
  ) -> BulkImportResult:
      '''Bulk import multiple artifacts with atomic transaction.'''

  Implementation:
  - Create ArtifactImporter instance
  - Validate all artifacts before import
  - Execute bulk_import() with atomic transaction
  - Return BulkImportResult with per-artifact status
  - Log import results for analytics

  Acceptance criteria:
  - Atomic transaction: all succeed or all fail
  - Per-artifact status in response
  - Error details for failed imports
  - Manifest and lock file updated correctly

  Estimate: 8 story points
")

Task("python-backend-engineer", "
  TASK SID-009: Implement GitHub Metadata Endpoint

  Add to skillmeat/api/routers/artifacts.py:

  @router.get('/metadata/github', response_model=MetadataFetchResponse)
  async def fetch_github_metadata(
      source: str = Query(...),
      artifact_mgr: ArtifactManagerDep = None
  ) -> MetadataFetchResponse:
      '''Fetch metadata from GitHub for given source.'''

  Implementation:
  - Create GitHubMetadataExtractor instance
  - Parse and validate source format
  - Call fetch_metadata() method
  - Return MetadataFetchResponse
  - Log metadata fetch results

  Acceptance criteria:
  - Validates GitHub source format
  - Returns metadata or error
  - Cache used for repeated requests
  - Handles GitHub API errors gracefully

  Estimate: 5 story points
")

Task("backend-architect", "
  TASK SID-010: Implement Parameter Edit Endpoint

  Add to skillmeat/api/routers/artifacts.py:

  @router.put('/{artifact_id}/parameters', response_model=ParameterUpdateResponse)
  async def update_artifact_parameters(
      artifact_id: str,
      request: ParameterUpdateRequest,
      artifact_mgr: ArtifactManagerDep
  ) -> ParameterUpdateResponse:
      '''Update artifact parameters after import.'''

  Implementation:
  - Parse artifact_id (type:name format)
  - Validate parameters with ParameterValidator
  - Update artifact in manifest and lock file
  - Return ParameterUpdateResponse with updated fields
  - Log parameter changes

  Acceptance criteria:
  - Validates source format before update
  - Checks version exists and accessible
  - Atomic transaction for manifest/lock updates
  - Returns clear error messages for validation failures

  Estimate: 5 story points
")

Task("python-backend-engineer", "
  TASK SID-011: Integration Tests: API Endpoints

  Create skillmeat/api/tests/test_discovery_endpoints.py.

  Test coverage needed (>70%):
  - Discovery endpoint: successful scan, empty directory, error handling
  - Bulk import: successful import, validation errors, atomic rollback
  - Metadata endpoint: successful fetch, cache hit, GitHub errors, rate limit
  - Parameter edit: successful update, validation errors, not found

  Use TestClient and mock services as needed.

  Acceptance criteria:
  - >70% endpoint coverage
  - All HTTP status codes tested
  - Request/response validation tested
  - Error scenarios covered

  Estimate: 5 story points
")

Task("backend-architect", "
  TASK SID-012: Error Handling & Validation

  Review and implement consistent error handling across all layers.

  Implementation:
  - Consistent error response format
  - User-friendly error messages
  - Proper HTTP status codes (400, 401, 404, 422, 500)
  - Validation consistency: frontend mirrors backend
  - Detailed error logging for debugging

  Validation rules:
  - Source format: user/repo/path[@version]
  - Version format: @latest, @v1.0.0, @abc1234, or omitted
  - Scope: 'user' or 'local'
  - Tags: non-empty list of strings
  - Artifact type: skill, command, agent, hook, mcp

  Acceptance criteria:
  - Error responses follow consistent format
  - All validation rules enforced
  - Clear error messages for common mistakes
  - Validation happens server-side

  Estimate: 5 story points
")
```

### Batch 3: Frontend Components (Phase 3)

Execute in parallel:

```text
Task("ui-engineer-enhanced", "
  TASK SID-013: Create Discovery Banner Component

  Create skillmeat/web/components/discovery/DiscoveryBanner.tsx.

  Component requirements:
  - Props: discoveredCount, onReview callback, dismissible flag
  - Display alert/banner with discovered count
  - 'Review & Import' button triggers onReview
  - Optional dismiss button to hide banner
  - Styling: use shadcn/ui Alert component
  - Accessible: proper ARIA labels, keyboard navigation

  Acceptance criteria:
  - Displays correctly with different discovery counts
  - Callback fires on button click
  - Dismissible functionality works
  - Accessible keyboard navigation

  Estimate: 3 story points
")

Task("ui-engineer-enhanced", "
  TASK SID-014: Create Bulk Import Modal/Table

  Create skillmeat/web/components/discovery/BulkImportModal.tsx.

  Component requirements:
  - Props: artifacts array, open bool, onClose callback, onImport callback
  - Table columns: checkbox, type, name, version, source, tags, edit button
  - Checkbox per row for selection
  - 'Select All / Deselect All' controls
  - Edit button opens parameter editor for that row
  - 'Import All' button imports selected artifacts
  - Loading state during import
  - Error toast if import fails
  - Success feedback after import

  Styling:
  - Use shadcn/ui Dialog, Table, Button, Checkbox
  - Responsive design
  - Accessible table navigation

  Acceptance criteria:
  - Renders all artifacts in table
  - Selection controls work
  - Import action calls onImport with selected artifacts
  - Loading and error states display correctly

  Estimate: 8 story points
")

Task("ui-engineer-enhanced", "
  TASK SID-015: Create Auto-Population Form Component

  Create skillmeat/web/components/discovery/AutoPopulationForm.tsx.

  Component requirements:
  - Props: artifactType, onImport callback
  - GitHub URL/source input field
  - Real-time validation feedback
  - Loading state during metadata fetch (spinner or skeleton)
  - Form fields auto-populated: name, description, author, topics, license
  - User can edit auto-populated fields
  - Submit button submits form with final values
  - Error handling if fetch fails (show error, allow manual entry)
  - Clear form after successful import

  Styling:
  - Use shadcn/ui Form, Input, Button, Skeleton
  - Clear visual feedback for loading state
  - Error messages in red

  Acceptance criteria:
  - URL input triggers metadata fetch
  - Metadata fetched correctly and auto-filled
  - User can edit auto-filled fields
  - Form submits with final values
  - Error handling works gracefully

  Estimate: 8 story points
")

Task("ui-engineer-enhanced", "
  TASK SID-016: Create Parameter Editor Modal

  Create skillmeat/web/components/discovery/ParameterEditorModal.tsx.

  Component requirements:
  - Props: artifact object, open bool, onClose callback, onSave callback
  - Form fields: source, version, scope (select), tags, aliases
  - Client-side validation with error messages
  - Save button calls onSave with parameter updates
  - Cancel button closes modal without saving
  - Loading state during save
  - Success/error feedback

  Styling:
  - Use shadcn/ui Dialog, Form, Input, Select, Button
  - Field validation error messages

  Acceptance criteria:
  - Form pre-populates with artifact data
  - Validation feedback on field blur
  - Save action calls onSave correctly
  - Modal closes after successful save
  - Cancel doesn't save changes

  Estimate: 5 story points
")

Task("frontend-developer", "
  TASK SID-017: Create React Query Hooks

  Create skillmeat/web/hooks/useDiscovery.ts (or split into multiple files).

  Hooks to implement:
  - useDiscovery(): discovery scan + bulk import
  - useGitHubMetadata(): fetch metadata from URL
  - useEditArtifactParameters(): update artifact parameters

  Each hook requirements:
  - Properly typed with TypeScript
  - Use React Query for async state management
  - Handle loading, error, success states
  - Return data, isLoading, error, mutate/mutation functions
  - Invalidate relevant queries on mutation success
  - Proper error handling and type-safe responses

  Acceptance criteria:
  - All hooks properly typed
  - Async operations handled with React Query
  - Query invalidation works correctly
  - Type-safe responses and errors

  Estimate: 5 story points
")

Task("frontend-developer", "
  TASK SID-018: Form Validation & Error States

  Implement consistent form validation across all components.

  Requirements:
  - Client-side validation using react-hook-form + Zod
  - Validation rules match backend rules
  - Real-time feedback during input
  - Clear error messages on field blur
  - Disabled submit button if validation fails
  - Loading states with spinners/skeletons
  - Error toasts for async operation failures
  - Success toasts for successful operations

  Validation rules:
  - Source: must be valid GitHub format (user/repo/path)
  - Version: optional, must start with @
  - Scope: must be 'user' or 'local'
  - Tags: list of non-empty strings
  - Artifact type: one of skill, command, agent, hook, mcp

  Acceptance criteria:
  - Client validation prevents invalid submissions
  - Error messages are clear and actionable
  - Loading states display appropriately
  - Success/error toasts show correctly

  Estimate: 5 story points
")

Task("frontend-developer", "
  TASK SID-019: Component Integration Tests

  Create skillmeat/web/tests/discovery.test.tsx.

  Test coverage needed (>70%):
  - DiscoveryBanner: renders with count, callback on click
  - BulkImportModal: renders table, selection works, import action
  - AutoPopulationForm: URL input, metadata fetch, form fill
  - ParameterEditorModal: form render, save action, validation

  Use React Testing Library and Vitest.
  Mock React Query with appropriate test setup.

  Acceptance criteria:
  - >70% component coverage
  - User interactions tested
  - Callback/mutation functions tested
  - Error states tested

  Estimate: 5 story points
")
```

### Batch 4: Page Integration & UX (Phase 4)

Execute sequentially as components become ready:

```text
Task("frontend-developer", "
  TASK SID-020: Integrate Discovery into /manage Page

  Update skillmeat/web/app/manage/page.tsx.

  Integration requirements:
  - On page load, call useDiscovery() to scan for artifacts
  - Show DiscoveryBanner when discoveredCount > 0
  - Click 'Review & Import' opens BulkImportModal
  - Modal shows discovered artifacts
  - User selects and imports
  - Success toast after import
  - Refresh artifact list in management page after import

  Implementation:
  - Use useDiscovery hook for discovery state
  - Conditional render DiscoveryBanner
  - Manage modal open/close state
  - Handle import success/error
  - Invalidate artifact list query after import

  Acceptance criteria:
  - Discovery runs on page load
  - Banner displays when artifacts found
  - Full workflow from discovery to import works
  - No regressions in existing /manage page functionality

  Estimate: 5 story points
")

Task("frontend-developer", "
  TASK SID-021: Integrate Auto-Population into Add Form

  Update artifact add form component (likely in entity management).

  Integration requirements:
  - GitHub source URL field with debounced fetch
  - While fetching, show loading state (spinner)
  - After fetch, auto-populate name, description, author, topics
  - User can edit auto-populated fields
  - Submit button imports with final values
  - Error toast if fetch fails, allow manual override
  - Clear form after successful import

  Implementation:
  - Add source field to existing add form
  - Use useGitHubMetadata hook for fetch
  - Debounce fetch on input change
  - Conditionally auto-fill fields based on metadata
  - Handle fetch errors gracefully

  Acceptance criteria:
  - URL input triggers metadata fetch
  - Auto-population works correctly
  - User can edit auto-populated values
  - Error handling graceful (don't block submission)
  - Successful import clears form

  Estimate: 5 story points
")

Task("ui-engineer-enhanced", "
  TASK SID-022: Integrate Parameter Editor into Entity Detail

  Update artifact detail page (skillmeat/web/app/manage/[type]/[name]/page.tsx).

  Integration requirements:
  - Add 'Edit Parameters' button in overview tab
  - Button click opens ParameterEditorModal
  - Modal allows editing source, version, scope, tags
  - Save button calls update API
  - Success toast after save
  - Refresh artifact detail after update
  - Error toast if update fails

  Implementation:
  - Add button to detail page
  - Use useEditArtifactParameters hook for mutation
  - Manage modal open/close state
  - Handle success/error responses
  - Invalidate artifact detail query after update

  Acceptance criteria:
  - Edit button visible and clickable
  - Modal opens/closes correctly
  - Save updates artifact parameters
  - Success/error feedback displayed
  - Detail page refreshes with updated values

  Estimate: 3 story points
")

Task("frontend-developer", "
  TASK SID-023: Polish Loading States & Error Messages

  Improve UX across discovery, auto-population, and parameter editing.

  Polish requirements:
  - Skeleton screens for table loading (BulkImportModal)
  - Spinner for metadata fetching
  - Clear error toasts with actionable messages
  - Rollback feedback if import partially fails
  - Consistent loading state styling
  - Accessible announcements for screen readers
  - Loading button states (disabled, spinner text)

  Implementation:
  - Add Skeleton components to tables
  - Add Spinner components during async operations
  - Create reusable toast utilities for errors
  - Test with screen reader

  Acceptance criteria:
  - Loading states display appropriate UI elements
  - Error messages are clear and actionable
  - Accessibility announcements working
  - Consistent styling across all loading states

  Estimate: 5 story points
")

Task("frontend-developer", "
  TASK SID-024: Analytics Instrumentation

  Add event tracking for discovery and auto-population features.

  Events to track:
  - discovery_scan: When discovery scan completes, count of artifacts found
  - auto_population_fetch: When metadata fetch succeeds/fails, source, duration
  - bulk_import: When bulk import succeeds/fails, count, duration
  - parameter_edit: When artifact parameters edited, fields changed
  - discovery_banner_view: When banner displayed
  - discovery_modal_open: When modal opened

  Implementation:
  - Use existing analytics SDK/library
  - Fire events at appropriate points in flow
  - Include relevant metadata (count, duration, source)
  - Log errors for failed operations

  Acceptance criteria:
  - All event types firing correctly
  - Event data includes relevant fields
  - No performance impact from tracking
  - Analytics dashboard can show metrics

  Estimate: 5 story points
")

Task("frontend-developer", "
  TASK SID-025: E2E Tests: Discovery Flow

  Create skillmeat/web/e2e/discovery.spec.ts.

  Test coverage needed:
  - User navigates to /manage
  - Discovery banner appears with artifact count
  - User clicks 'Review & Import'
  - Modal opens with table of artifacts
  - User selects artifacts via checkboxes
  - User clicks 'Import All'
  - Import completes, success toast appears
  - Artifacts appear in respective tabs

  Full user journey testing with Playwright/Cypress.

  Acceptance criteria:
  - Full discovery -> import flow tested
  - All UI elements properly selected and interacted with
  - Success criteria verified at end
  - Test passes consistently

  Estimate: 8 story points
")

Task("frontend-developer", "
  TASK SID-026: E2E Tests: Auto-Population Flow

  Create skillmeat/web/e2e/auto-population.spec.ts.

  Test coverage needed:
  - User navigates to add artifact form
  - User pastes GitHub URL in source field
  - Loading state shows while fetching metadata
  - Form auto-populates with fetched metadata
  - User edits some fields (optional)
  - User clicks 'Import'
  - Import completes, success toast appears
  - New artifact appears in list

  Full user journey testing with Playwright/Cypress.

  Acceptance criteria:
  - Full auto-population -> import flow tested
  - Metadata fetched and form filled correctly
  - User edits preserved if made
  - Success criteria verified at end
  - Test passes consistently

  Estimate: 8 story points
")
```

### Batch 5: Testing, Documentation & Deployment (Phase 5)

Execute in parallel where possible:

```text
Task("python-backend-engineer", "
  TASK SID-027: Performance Testing & Optimization

  Create performance benchmarks and optimize as needed.

  Benchmarks to verify:
  - Discovery scan <2 seconds for 50+ artifacts
  - Metadata fetch <1 second (cached)
  - Bulk import <3 seconds for 20 artifacts
  - GitHub API cache hit <100ms

  Implementation:
  - Create pytest performance tests with timing
  - Use large test collections for realistic scenarios
  - Profile code with cProfile if needed
  - Optimize slow paths (file I/O, API calls)
  - Document optimization techniques

  Acceptance criteria:
  - All performance benchmarks met
  - Optimization techniques documented
  - No performance regressions
  - Benchmarks automated in CI

  Estimate: 5 story points
")

Task("python-backend-engineer", "
  TASK SID-028: Error Scenario Testing

  Comprehensive testing of error scenarios.

  Scenarios to test:
  - GitHub API down or rate limited
  - Invalid artifacts in .claude/
  - Network timeouts during metadata fetch
  - Partial bulk import failure
  - Disk full during import
  - Corrupted manifest files
  - Permission errors

  Implementation:
  - Mock or simulate error conditions
  - Verify graceful error handling
  - Check error messages are helpful
  - Verify no data corruption on errors
  - Test rollback/recovery mechanisms

  Acceptance criteria:
  - All error scenarios handled gracefully
  - Error messages helpful and actionable
  - No data corruption or partial corruption
  - Recovery mechanisms work correctly

  Estimate: 5 story points
")

Task("ui-engineer-enhanced", "
  TASK SID-029: Accessibility Audit

  Verify accessibility of new components and flows.

  Audit checklist:
  - Modal keyboard navigation (Tab, Escape)
  - Table row selection keyboard accessible
  - Loading states announced for screen readers
  - Error messages in color + text
  - Button labels clear and descriptive
  - Form labels associated with inputs
  - Focus visible/indicated throughout

  Implementation:
  - Run axe accessibility checker
  - Test with keyboard navigation only
  - Test with screen reader (NVDA/JAWS)
  - Review against WCAG 2.1 AA standards
  - Document any accessibility issues

  Acceptance criteria:
  - No critical accessibility violations
  - Keyboard navigation works throughout
  - Screen reader announces loading states
  - All interactive elements keyboard accessible

  Estimate: 3 story points
")

Task("documentation-writer", "
  TASK SID-030: User Guide: Discovery

  Create user documentation for discovery feature.

  Documentation should cover:
  - What is artifact discovery
  - How discovery works (scans .claude/)
  - When discovery runs (on /manage load)
  - How to use bulk import
  - Editing parameters before import
  - Troubleshooting: artifacts not found, import fails
  - Best practices: what gets discovered, when to use

  Format: Markdown file in docs/guides/
  Include screenshots/screenshots where helpful.

  Acceptance criteria:
  - Documentation comprehensive and clear
  - Screenshots/examples included
  - Troubleshooting section helpful
  - Easy to follow for new users

  Estimate: 3 story points
")

Task("documentation-writer", "
  TASK SID-031: User Guide: Auto-Population

  Create user documentation for auto-population feature.

  Documentation should cover:
  - What is auto-population
  - Supported sources (GitHub primary)
  - How to paste GitHub URL
  - What metadata is auto-populated
  - Editing auto-populated fields
  - Manual override if auto-population fails
  - Troubleshooting: fetch fails, incomplete metadata
  - Best practices: what gets populated, accuracy

  Format: Markdown file in docs/guides/
  Include examples of common GitHub URLs.

  Acceptance criteria:
  - Documentation comprehensive and clear
  - Examples of GitHub URL formats included
  - Troubleshooting section helpful
  - Clear how to manually override

  Estimate: 3 story points
")

Task("documentation-writer", "
  TASK SID-032: API Documentation

  Document new API endpoints and schemas.

  Documentation should cover:
  - Endpoint overview and use cases
  - Request/response schemas
  - Example requests and responses
  - Error codes and meanings
  - Rate limiting and caching details
  - GitHub API dependencies

  Format: Update OpenAPI schema + markdown docs
  Include curl examples for testing.

  Acceptance criteria:
  - All 4 endpoints documented
  - Schemas clearly defined
  - Examples provided
  - Error codes explained
  - Ready for API users

  Estimate: 3 story points
")

Task("backend-architect", "
  TASK SID-033: Feature Flag Implementation

  Implement feature flags for gradual rollout.

  Feature flags needed:
  - ENABLE_AUTO_DISCOVERY: Toggle discovery feature
  - ENABLE_AUTO_POPULATION: Toggle metadata fetch
  - DISCOVERY_CACHE_TTL: Cache duration (default 3600)
  - GITHUB_TOKEN: Optional token for rate limits

  Implementation:
  - Add to APISettings configuration
  - Check flags in endpoint handlers
  - Return feature unavailable (501) if disabled
  - Update .env example with new settings
  - Document feature flag usage

  Acceptance criteria:
  - Feature flags properly configured
  - Endpoints check flags before executing
  - Graceful handling when disabled
  - Easy to toggle via environment

  Estimate: 5 story points
")

Task("backend-architect", "
  TASK SID-034: Monitoring & Error Tracking

  Set up monitoring for new features.

  Monitoring to implement:
  - Error tracking: Sentry/similar for exceptions
  - Performance metrics: discovery duration, metadata fetch time
  - Analytics events: discovery scans, bulk imports, edits
  - Alert thresholds: GitHub API rate limit approaching
  - Dashboard: summary of feature metrics

  Implementation:
  - Integrate error tracking SDK
  - Add performance timing instrumentation
  - Log analytics events at key points
  - Configure alert rules
  - Create monitoring dashboard

  Acceptance criteria:
  - Errors captured and tracked
  - Performance metrics visible
  - Analytics data collected
  - Alerts configured appropriately
  - Dashboard shows key metrics

  Estimate: 5 story points
")

Task("python-backend-engineer", "
  TASK SID-035: Final Integration & Smoke Tests

  Full system integration testing.

  Tests to run:
  - End-to-end: discovery -> bulk import complete flow
  - End-to-end: add form -> auto-population -> import complete flow
  - End-to-end: edit parameters on existing artifact
  - Data consistency: manifest/lock file consistent
  - No regressions: existing artifact features still work
  - Feature flags work correctly (enable/disable)
  - Analytics events firing correctly
  - Error tracking capturing errors

  Implementation:
  - Run comprehensive smoke test suite
  - Verify all features in real environment
  - Check for any data inconsistencies
  - Validate no regressions
  - Sign off for deployment

  Acceptance criteria:
  - All smoke tests pass
  - No data inconsistencies found
  - No regressions in existing features
  - Ready for production deployment

  Estimate: 5 story points
")
```

---

## Success Criteria & Definition of Done

### Functional Completeness

- [x] Auto-discovery scans .claude/ and finds all artifact types
- [x] Discovery modal shows table with 100% of artifacts found
- [x] Bulk import is atomic (all-or-nothing per batch)
- [x] Bulk import validates all entries before operation
- [x] GitHub URL parsing handles all standard formats
- [x] Metadata auto-population fills name, description, author, topics, license
- [x] Metadata errors don't block form submission (manual fallback)
- [x] Post-import parameter editing works for source, version, tags, scope
- [x] All parameters saved with atomic transaction
- [x] Discovery doesn't corrupt existing artifacts

### Technical Quality

- [x] All API endpoints follow REST conventions
- [x] All endpoints validate input and return proper HTTP status codes
- [x] Error messages are user-friendly and actionable
- [x] Metadata cache implements TTL correctly
- [x] GitHub API rate limiting handled gracefully
- [x] All parameters validated server-side
- [x] Frontend form validation matches backend validation
- [x] Loading states properly displayed during async operations
- [x] No regressions in existing artifact creation flow

### Testing Coverage

- [x] Unit tests for GitHub metadata extraction (>80% coverage)
- [x] Unit tests for discovery scan logic (>80% coverage)
- [x] Integration tests for bulk import workflow
- [x] E2E tests for discovery and auto-population flows
- [x] Error handling tests (GitHub API failures, invalid artifacts)
- [x] Performance tests (discovery < 2s, metadata fetch cached)
- [x] No regressions in existing artifact creation flow
- [x] Accessibility audit for forms and modals

### Documentation

- [x] User guide for discovery and auto-population features
- [x] API endpoint documentation
- [x] GitHub metadata schema documentation
- [x] Error code reference for troubleshooting

### Performance

- [x] Discovery scan completes <2 seconds for 50+ artifacts
- [x] Metadata fetch from GitHub <1 second per artifact (cached)
- [x] Bulk import validates and saves <3 seconds for 20+ artifacts
- [x] Form response to URL paste <500ms (with loading state)

### Deployment

- [x] Feature flags for gradual rollout (ENABLE_AUTO_DISCOVERY, ENABLE_AUTO_POPULATION)
- [x] Error tracking and monitoring configured
- [x] Analytics events instrumented
- [x] Comprehensive smoke tests pass
- [x] No data corruption or partial corruption
- [x] All acceptance criteria met

---

## Timeline & Resource Allocation

```
Week 1-1.5: Phase 1 (Data Layer & Services)
  Backend: SID-001, SID-002, SID-003 (parallel)
  Backend Architect: SID-004 (depends on above)
  Backend: SID-005, SID-006 (parallel, after services ready)
  Effort: 4 developers, 34 story points

Week 1.5-2.5: Phase 2 (API Endpoints)
  Backend: SID-007, SID-008, SID-009 (mostly sequential)
  Backend Architect: SID-010 (parallel with endpoints)
  Backend: SID-011 (after endpoints ready)
  Backend Architect: SID-012 (parallel, error handling)
  Effort: 2-3 developers, 33 story points

Week 2-3: Phase 3 (Frontend Components)
  UI Engineer: SID-013, SID-014, SID-015, SID-016 (parallel)
  Frontend Developer: SID-017, SID-018, SID-019 (parallel after API ready)
  Effort: 2 developers, 39 story points

Week 3-4: Phase 4 (Page Integration & UX)
  Frontend Developer: SID-020, SID-021, SID-025, SID-026 (mix of sequential/parallel)
  UI Engineer: SID-022
  Frontend Developer: SID-023, SID-024 (polish and analytics)
  Effort: 2 developers, 39 story points

Week 4.5-5.5: Phase 5 (Testing, Docs, Deployment)
  Backend: SID-027, SID-028
  UI Engineer: SID-029
  Documentation Writer: SID-030, SID-031, SID-032
  Backend Architect: SID-033, SID-034
  Backend: SID-035 (final integration)
  Effort: 5 developers, 37 story points

TOTAL: ~4-6 weeks, 95-110 story points, 5-6 developers
```

---

## Dependencies & Assumptions

### External Dependencies

**Libraries (Backend):**
- `pydantic` (v2): Schema validation
- `requests` or `httpx`: GitHub API client
- `pathlib`: Directory scanning
- `python-frontmatter` or `yaml`: Markdown metadata extraction

**Libraries (Frontend):**
- `@hookform/resolvers`: URL validation
- `zod`: Schema validation
- `axios` or `fetch`: GitHub API calls
- `@tanstack/react-query`: Server state management
- `shadcn/ui`: Component library

**External APIs:**
- GitHub REST API v3 (rate: 60 req/hr unauthenticated, 5000 req/hr authenticated)

### Internal Dependencies

**Feature Dependencies:**
- Entity Lifecycle Management PRD (form infrastructure, import logic)
- Web UI Consolidation PRD (entity detail page, table components)
- ArtifactManager (existing, used for import operations)

**Infrastructure:**
- FastAPI routers and middleware (existing)
- Collection filesystem structure (existing)
- Manifest and lock file managers (existing)

### Assumptions

- Users have internet access for GitHub API calls
- GitHub URLs follow standard format: `owner/repo/path[@version]`
- `.claude/` directory structure is standard (skills/, commands/, agents/, etc.)
- Artifacts in `.claude/` are valid (basic validation done)
- Users prefer web UI import flow over CLI
- Metadata from GitHub is reasonably complete

---

## Appendices

### A. File Locations & Changes Summary

**New Files:**
```
skillmeat/core/discovery.py               - ArtifactDiscoveryService
skillmeat/core/github_metadata.py         - GitHubMetadataExtractor
skillmeat/core/cache.py                   - MetadataCache
skillmeat/core/importer.py                - ArtifactImporter
skillmeat/core/parameters.py              - ParameterValidator
skillmeat/core/tests/test_discovery_service.py
skillmeat/core/tests/test_github_metadata.py
skillmeat/api/tests/test_discovery_endpoints.py

skillmeat/web/components/discovery/DiscoveryBanner.tsx
skillmeat/web/components/discovery/BulkImportModal.tsx
skillmeat/web/components/discovery/BulkImportParameterEditor.tsx
skillmeat/web/components/discovery/AutoPopulationForm.tsx
skillmeat/web/components/discovery/ParameterEditorModal.tsx
skillmeat/web/hooks/useDiscovery.ts
skillmeat/web/hooks/useGitHubMetadata.ts
skillmeat/web/hooks/useEditArtifactParameters.ts
skillmeat/web/tests/discovery.test.tsx
skillmeat/web/e2e/discovery.spec.ts
skillmeat/web/e2e/auto-population.spec.ts

docs/guides/discovery-guide.md
docs/guides/auto-population-guide.md
docs/api/discovery-endpoints.md
```

**Modified Files:**
```
skillmeat/api/routers/artifacts.py        - Add 4 new endpoints
skillmeat/api/schemas/artifacts.py        - Add new schema models
skillmeat/web/app/manage/page.tsx         - Integrate discovery banner
skillmeat/web/app/manage/[type]/[name]/page.tsx - Integrate parameter editor
skillmeat/api/config.py                   - Add feature flag settings
```

### B. Code Examples

**Discovery Service Usage:**
```python
from skillmeat.core.discovery import ArtifactDiscoveryService

service = ArtifactDiscoveryService(Path.home() / ".skillmeat" / "collection")
result = service.discover_artifacts()

for artifact in result.artifacts:
    print(f"{artifact.type}: {artifact.name}")
```

**GitHub Metadata Extraction:**
```python
from skillmeat.core.github_metadata import GitHubMetadataExtractor
from skillmeat.core.cache import MetadataCache

cache = MetadataCache(ttl_seconds=3600)
extractor = GitHubMetadataExtractor(cache)

metadata = extractor.fetch_metadata("anthropics/skills/canvas-design")
print(f"Title: {metadata.title}")
print(f"Description: {metadata.description}")
```

**Bulk Import:**
```python
from skillmeat.core.importer import ArtifactImporter

importer = ArtifactImporter(artifact_manager)
request = BulkImportRequest(artifacts=[
    BulkImportArtifact(
        source="anthropics/skills/canvas",
        artifact_type="skill",
        name="canvas",
        tags=["design"]
    )
])

result = importer.bulk_import(request)
print(f"Imported: {result.total_imported}, Failed: {result.total_failed}")
```

---

## Deployment Checklist

- [ ] All code reviewed and approved
- [ ] All tests passing (unit, integration, E2E)
- [ ] Performance benchmarks met
- [ ] No data corruption found in testing
- [ ] Feature flags configured and tested
- [ ] Error tracking configured
- [ ] Analytics events verified
- [ ] Documentation complete and published
- [ ] Accessibility audit passed
- [ ] Smoke tests pass in staging
- [ ] Gradual rollout plan prepared
- [ ] Rollback plan prepared
- [ ] Monitoring dashboard live
- [ ] Team trained on new features
- [ ] User communication prepared

---

**Implementation Plan Status:** Ready for execution

**Created:** 2025-11-30

**Last Updated:** 2025-11-30

**Related Documents:**
- PRD: `/docs/project_plans/PRDs/enhancements/smart-import-discovery-v1.md`
- Progress Tracking: (to be created in `.claude/progress/smart-import-discovery-v1/`)
- API Docs: (to be created after implementation)

---

*This implementation plan is designed for AI agent execution with clear task breakdowns, assigned owners, and parallel execution opportunities within each phase.*
