---
prd: collection-artifact-refresh
phase: 1
title: 'Phase 1: Core Refresh Infrastructure'
description: Data models, core CollectionRefresher implementation, and unit tests
parallelization:
  batch_1:
    description: Data models and enums
    tasks:
    - BE-101
    - BE-102
    - BE-103
    - BE-104
  batch_2:
    description: Core CollectionRefresher methods (independent)
    tasks:
    - BE-105
    - BE-106
    - BE-107
    - BE-108
    - BE-109
  batch_3:
    description: Orchestrator methods (depends on batch_2)
    tasks:
    - BE-110
  batch_4:
    description: Integration methods (depends on BE-110)
    tasks:
    - BE-111
    - BE-112
  batch_5:
    description: Unit tests (depends on implementation)
    tasks:
    - BE-113
    - BE-114
    - BE-115
    - BE-116
    - BE-117
    - BE-118
tasks:
- id: BE-101
  title: Create RefreshEntryResult dataclass
  description: Define dataclass to hold refresh result for a single artifact
  story_points: 0.5
  assigned_to: python-backend-engineer
  section: 1.1 Data Models
  status: completed
  dependencies: []
  notes: 'Fields:

    - name: str

    - success: bool

    - changes_detected: dict[str, Any]

    - error: str | None

    - metadata_updated: dict[str, Any]

    '
- id: BE-102
  title: Create RefreshResult dataclass
  description: Define dataclass to aggregate results from collection refresh
  story_points: 0.5
  assigned_to: python-backend-engineer
  section: 1.1 Data Models
  status: completed
  dependencies:
  - BE-101
  notes: 'Fields:

    - entries: list[RefreshEntryResult]

    - refresh_mode: RefreshMode

    - total_artifacts: int

    - artifacts_updated: int

    - artifacts_failed: int

    - errors: list[str]

    - started_at: datetime

    - completed_at: datetime

    '
- id: BE-103
  title: Create RefreshMode enum
  description: Define enum for refresh operation modes
  story_points: 0.25
  assigned_to: python-backend-engineer
  section: 1.1 Data Models
  status: completed
  dependencies: []
  notes: 'Modes:

    - DETECT_ONLY

    - AUTO_UPDATE

    - INTERACTIVE

    '
- id: BE-104
  title: Define field mapping config
  description: Create field mapping configuration for artifact metadata updates
  story_points: 0.25
  assigned_to: python-backend-engineer
  section: 1.1 Data Models
  status: completed
  dependencies: []
  notes: 'Map upstream fields to artifact properties:

    - description

    - version

    - tags

    - keywords

    - updated_at

    - license

    '
- id: BE-105
  title: Create CollectionRefresher class skeleton
  description: Initialize CollectionRefresher with dependencies and configuration
  story_points: 0.5
  assigned_to: python-backend-engineer
  section: 1.2 Core Implementation
  status: completed
  dependencies: []
  notes: 'Location: skillmeat/core/refresh.py

    Constructor params:

    - github_client: GitHubClient

    - artifact_repo: ArtifactRepository

    - field_mapping: dict

    - logger: Logger

    '
- id: BE-106
  title: Implement _parse_source_spec()
  description: Parse artifact source specifications into owner/repo/path format
  story_points: 0.75
  assigned_to: python-backend-engineer
  section: 1.2 Core Implementation
  status: completed
  dependencies: []
  notes: 'Parse format: "owner/repo/path/to/artifact[@version]"

    Return: (owner, repo, artifact_path, version_spec)

    Handle edge cases: missing owner, invalid format, version variants

    '
- id: BE-107
  title: Implement _fetch_upstream_metadata()
  description: Fetch metadata from upstream GitHub repository
  story_points: 1.0
  assigned_to: python-backend-engineer
  section: 1.2 Core Implementation
  status: completed
  dependencies: []
  notes: 'Uses GitHubClient to fetch:

    - METADATA.md or artifact definition

    - Version info from tags/releases

    - Last updated timestamp

    Error handling: API errors, missing files, invalid metadata

    Returns: dict with upstream fields

    '
- id: BE-108
  title: Implement _detect_changes()
  description: Compare upstream metadata against stored artifact metadata
  story_points: 0.75
  assigned_to: python-backend-engineer
  section: 1.2 Core Implementation
  status: completed
  dependencies: []
  notes: 'Fields to compare:

    - description

    - version

    - tags

    - keywords

    - updated_at

    Returns: dict of detected changes with before/after values

    '
- id: BE-109
  title: Implement _apply_updates()
  description: Apply detected changes to artifact metadata
  story_points: 0.75
  assigned_to: python-backend-engineer
  section: 1.2 Core Implementation
  status: completed
  dependencies: []
  notes: 'Update logic:

    - Apply field mappings

    - Update artifact in repository

    - Track what was changed

    - Handle conflicts (user edits vs upstream)

    Returns: dict of applied updates

    '
- id: BE-110
  title: Implement refresh_metadata()
  description: Orchestrate refresh for single artifact (fetch → detect → apply)
  story_points: 1.5
  assigned_to: python-backend-engineer
  section: 1.2 Core Implementation
  status: completed
  dependencies:
  - BE-106
  - BE-107
  - BE-108
  - BE-109
  notes: 'Workflow:

    1. Parse source spec

    2. Fetch upstream metadata

    3. Detect changes

    4. Apply updates (if not DETECT_ONLY mode)

    5. Return RefreshEntryResult

    Handle errors gracefully with logging

    '
- id: BE-111
  title: Implement refresh_collection()
  description: Refresh all artifacts in collection with parallelization
  story_points: 1.0
  assigned_to: python-backend-engineer
  section: 1.2 Core Implementation
  status: completed
  dependencies:
  - BE-110
  notes: 'Process all artifacts in collection:

    - Get all artifacts from repository

    - Call refresh_metadata for each

    - Use ThreadPoolExecutor for parallelization (5 workers)

    - Aggregate results into RefreshResult

    - Track timing and metrics

    '
- id: BE-112
  title: Add error handling and logging
  description: Add comprehensive error handling and structured logging to refresh
    flow
  story_points: 0.75
  assigned_to: python-backend-engineer
  section: 1.2 Core Implementation
  status: completed
  dependencies:
  - BE-110
  - BE-111
  notes: 'Logging levels:

    - INFO: refresh start/complete, summary stats

    - DEBUG: per-artifact progress, field changes

    - ERROR: API failures, parsing errors, update failures

    Exception handling:

    - GitHubClientError → log and record in result

    - ValidationError → skip artifact, log warning

    - Unexpected errors → log and continue

    '
- id: BE-113
  title: Unit tests for _parse_source_spec()
  description: Test artifact source parsing with various formats
  story_points: 1.0
  assigned_to: python-backend-engineer
  section: 1.3 Unit Tests
  status: completed
  dependencies:
  - BE-106
  notes: 'Test cases:

    - Valid format: owner/repo/path[@version]

    - With version tag

    - With version SHA

    - Missing version (defaults to latest)

    - Invalid formats (missing owner, invalid characters)

    - Edge cases (nested paths, numeric names)

    '
- id: BE-114
  title: Unit tests for _detect_changes()
  description: Test change detection logic
  story_points: 1.0
  assigned_to: python-backend-engineer
  section: 1.3 Unit Tests
  status: completed
  dependencies:
  - BE-108
  notes: 'Test cases:

    - No changes detected

    - Single field changed

    - Multiple fields changed

    - New fields in upstream

    - Removed fields

    - Version updates

    - Timestamp updates

    '
- id: BE-115
  title: Unit tests for _apply_updates()
  description: Test metadata update application
  story_points: 1.0
  assigned_to: python-backend-engineer
  section: 1.3 Unit Tests
  status: completed
  dependencies:
  - BE-109
  notes: 'Test cases:

    - Apply single field update

    - Apply multiple field updates

    - Field mapping correctness

    - Conflict handling (user edits)

    - Verify database persistence

    - Rollback on error

    '
- id: BE-116
  title: Unit tests for refresh_metadata()
  description: Test single artifact refresh orchestration
  story_points: 1.5
  assigned_to: python-backend-engineer
  section: 1.3 Unit Tests
  status: completed
  dependencies:
  - BE-110
  notes: 'Test cases:

    - Successful refresh with changes

    - Successful refresh without changes

    - DETECT_ONLY mode (no updates applied)

    - AUTO_UPDATE mode (updates applied)

    - GitHub API errors handled gracefully

    - Invalid source spec handling

    - RefreshEntryResult structure validation

    '
- id: BE-117
  title: Unit tests for refresh_collection()
  description: Test collection-wide refresh with parallelization
  story_points: 1.5
  assigned_to: python-backend-engineer
  section: 1.3 Unit Tests
  status: completed
  dependencies:
  - BE-111
  notes: 'Test cases:

    - Refresh empty collection

    - Refresh single artifact

    - Refresh multiple artifacts

    - Partial failures (some succeed, some fail)

    - Parallelization working correctly

    - Result aggregation

    - Timing metrics captured

    '
- id: BE-118
  title: Mock GitHub API tests
  description: Test GitHub API interactions with mocked responses
  story_points: 1.0
  assigned_to: python-backend-engineer
  section: 1.3 Unit Tests
  status: completed
  dependencies:
  - BE-107
  - BE-110
  notes: 'Mock scenarios:

    - Successful metadata fetch

    - Missing METADATA.md file

    - GitHub API rate limit error

    - GitHub API authentication error

    - Network timeout

    - Malformed JSON response

    - Use unittest.mock.patch for GitHubClient

    '
summary: '**Phase 1: Core Refresh Infrastructure**


  This phase establishes the foundation for the collection refresh system:


  1. **Data Models** - Define core dataclasses and enums for representing refresh
  operations

  2. **Core Implementation** - Build CollectionRefresher with individual refresh methods

  3. **Unit Tests** - Comprehensive test coverage for all implementation


  Total Story Points: 18.0 points

  Estimated Duration: 5-7 days


  **Success Criteria**:

  - All data models defined and type-safe

  - CollectionRefresher fully implemented with all methods

  - Unit tests pass with >80% statement coverage

  - Error handling in place for all API interactions

  - Logging structured and informative

  '
total_tasks: 18
completed_tasks: 18
in_progress_tasks: 0
blocked_tasks: 0
progress: 100
status: completed
updated: '2026-01-21'
---

## Phase Status

**Current Phase**: 1 of 3
**Overall Progress**: 0% (pending)
**Started**: Not yet
**Estimated Completion**: TBD

## Batch Execution Plan

### Batch 1: Data Models (Est. 1 day)
All tasks are independent. Execute in parallel:
- BE-101, BE-102, BE-103, BE-104

**Execution**: Single parallel delegation to python-backend-engineer

### Batch 2: Core Methods (Est. 2-3 days)
All independent core methods. Execute in parallel:
- BE-105, BE-106, BE-107, BE-108, BE-109

**Execution**: Single parallel delegation to python-backend-engineer

### Batch 3: Orchestrator (Est. 1-2 days)
Single method that depends on Batch 2:
- BE-110

**Execution**: Wait for Batch 2 completion, then delegate

### Batch 4: Integration (Est. 1-2 days)
Methods that depend on BE-110:
- BE-111, BE-112

**Execution**: Wait for Batch 3 completion, then parallel delegation

### Batch 5: Tests (Est. 2-3 days)
All tests can run after their implementation dependencies:
- BE-113, BE-114, BE-115, BE-116, BE-117, BE-118

**Execution**: Wait for all implementation complete, then parallel delegation

## Notes

- All tasks assigned to `python-backend-engineer` agent
- Backend infrastructure is well-defined; implementation is straightforward
- Emphasis on error handling and logging given GitHub API integration
- MockGitHubClient approach recommended for tests to avoid rate limiting
- Consider using `pytest-asyncio` if async methods are needed later
