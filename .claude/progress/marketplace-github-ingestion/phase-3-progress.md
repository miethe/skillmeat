---
type: progress
prd: marketplace-github-ingestion
phase: 3
title: Service Layer
status: planning
started: null
completed: null
overall_progress: 0
completion_estimate: on-track
total_tasks: 7
completed_tasks: 0
in_progress_tasks: 0
blocked_tasks: 0
at_risk_tasks: 0
owners:
- backend-architect
contributors:
- python-backend-engineer
tasks:
- id: SVC-001
  description: DTOs and service models for marketplace sources and catalog entries
  status: pending
  assigned_to:
  - python-backend-engineer
  dependencies:
  - REPO-004
  estimated_effort: 2pts
  priority: high
- id: SVC-002
  description: Heuristic detector for artifact discovery (directory hints, file patterns,
    scoring)
  status: pending
  assigned_to:
  - backend-architect
  dependencies:
  - SVC-001
  estimated_effort: 5pts
  priority: high
- id: SVC-003
  description: GitHub scanning service (clone/API, file traversal, metadata extraction)
  status: pending
  assigned_to:
  - backend-architect
  dependencies:
  - SVC-002
  estimated_effort: 5pts
  priority: high
- id: SVC-004
  description: README link harvester for secondary repo discovery (dedup, cycle guard,
    depth limit)
  status: pending
  assigned_to:
  - python-backend-engineer
  dependencies:
  - SVC-003
  estimated_effort: 3pts
  priority: medium
- id: SVC-005
  description: Catalog diff engine to detect new/updated/removed entries (commit hash,
    file checksum)
  status: pending
  assigned_to:
  - backend-architect
  dependencies:
  - SVC-004
  estimated_effort: 3pts
  priority: high
- id: SVC-006
  description: Import coordinator to map upstream artifacts to collection and mark
    as imported
  status: pending
  assigned_to:
  - python-backend-engineer
  dependencies:
  - SVC-005
  estimated_effort: 3pts
  priority: high
- id: SVC-007
  description: Error handling, observability, and logging for marketplace operations
  status: pending
  assigned_to:
  - backend-architect
  dependencies:
  - SVC-006
  estimated_effort: 2pts
  priority: medium
parallelization:
  batch_1:
  - SVC-001
  batch_2:
  - SVC-002
  batch_3:
  - SVC-003
  batch_4:
  - SVC-004
  batch_5:
  - SVC-005
  batch_6:
  - SVC-006
  batch_7:
  - SVC-007
  critical_path:
  - SVC-001
  - SVC-002
  - SVC-003
  - SVC-004
  - SVC-005
  - SVC-006
  - SVC-007
  estimated_total_time: 23h
blockers: []
success_criteria:
- DTOs properly define marketplace data contracts
- Heuristic detector accurately identifies artifacts with confidence scoring
- GitHub scanning handles both API and clone methods with rate limiting
- README link harvester safely explores secondary repos with cycle protection
- Catalog diff engine correctly identifies status changes
- Import coordinator maps upstream to local artifacts consistently
- Error handling surfaces meaningful messages to users
- Structured logging enables observability and debugging
files_modified:
- skillmeat/core/schemas/marketplace.py
- skillmeat/core/services/marketplace_heuristic.py
- skillmeat/core/services/github_scanner.py
- skillmeat/core/services/readme_harvester.py
- skillmeat/core/services/catalog_diff.py
- skillmeat/core/services/marketplace_importer.py
- skillmeat/core/observability/marketplace_metrics.py
- tests/unit/services/test_marketplace_services.py
schema_version: 2
doc_type: progress
feature_slug: marketplace-github-ingestion
---

# Phase 3: Service Layer

**Status:** Planning | **Owner:** backend-architect | **Est. Effort:** 23 pts (23h)

## Overview

Build the core business logic for marketplace GitHub ingestion. This phase implements heuristic detection, GitHub scanning, README harvesting, catalog diffing, and import coordination. These services orchestrate the marketplace workflow and provide the foundation for API endpoints.

## Orchestration Quick Reference

**Critical Path:** SVC-001 → SVC-002 → SVC-003 → SVC-004 → SVC-005 → SVC-006 → SVC-007 (mostly sequential)

### Task Delegation Commands

```
Task("python-backend-engineer", "SVC-001: Create DTOs and Pydantic models: (1) MarketplaceSourceCreate/Update with repo_url, branch, root_hint, manual_map, (2) MarketplaceCatalogEntryCreate with artifact_type, path, upstream_url, confidence_score, (3) CatalogStatus enum (new/updated/removed/unchanged), (4) ScanResult with entries list and error summary. Include validators for URLs and paths.")

Task("backend-architect", "SVC-002: Implement HeuristicDetector service to score artifact likelihood: (1) Directory hints (skills/, agents/, .claude/commands/, etc.) with weights, (2) File pattern hints (skill*.md, manifest.yaml, etc.), (3) Scoring algorithm: dir_match (40%) + manifest (30%) + extension (20%) - depth_penalty (10%), (4) Return list of CatalogEntry with confidence 0-100, (5) Scan from root_hint or repo root. Include tests on messy repos.")

Task("backend-architect", "SVC-003: Create GitHubScanner service to fetch and traverse repos: (1) Support shallow clone (depth=1) for speed, (2) Fallback to API contents/ for rate-limit compliance, (3) Traverse directory tree respecting root_hint, (4) Extract file metadata (path, size, sha), (5) Apply heuristic detector to results, (6) Implement timeouts (60s) and size caps (500MB), (7) Cache clone results, (8) Handle private repos with PAT. Include rate-limit backoff and error logging.")

Task("python-backend-engineer", "SVC-004: Implement ReadmeHarvester to extract GitHub links from README files: (1) Parse README.md and variants, (2) Extract github.com URLs with regex, (3) Deduplicate and filter non-GitHub links, (4) Guard against cycles using visited set, (5) Limit depth to 1 and cap total repos to 5 per source, (6) Return list of repo URLs for enqueuing secondary scans. Include test with real READMEs.")

Task("backend-architect", "SVC-005: Build CatalogDiffEngine to detect changes between scans: (1) Compare new scan results to previous catalog entries, (2) Status logic: if entry missing → removed, if new path → new, if path exists but commit/checksum differs → updated, else unchanged, (3) Store upstream commit sha and file checksum in entries, (4) Return diff summary with counts by status, (5) Handle partial rescans gracefully. Include edge cases (path moves, renames).")

Task("python-backend-engineer", "SVC-006: Create ImportCoordinator to handle artifact imports: (1) Map upstream artifact (source_id, type, path, upstream_url) to collection artifact, (2) Validate artifact is importable (has valid manifest), (3) Mark entry as imported with timestamp, (4) Handle single and bulk imports, (5) Conflict resolution for duplicate names (prompt vs auto-suffix), (6) Return import result with success/error counts. Include dry-run mode.")

Task("backend-architect", "SVC-007: Implement error handling and observability: (1) Custom exceptions for scan failures, rate limits, invalid sources, (2) Structured logging with context (source_id, scan_duration, entry_count), (3) Metrics: scan_duration_ms, entries_by_type, confidence_distribution, error_rates, (4) User-friendly error messages for UI, (5) Retry logic with exponential backoff for transient failures. Include observability hooks for APM integration.")
```

## Success Criteria

| Criteria | Details |
|----------|---------|
| **DTOs** | All marketplace models properly defined and validated |
| **Detection** | Heuristic detector scores artifacts accurately on test repos |
| **Scanning** | GitHub scanner handles public/private repos with rate limiting |
| **Harvesting** | README harvester extracts links safely with cycle protection |
| **Diffing** | Catalog diff engine correctly identifies new/updated/removed entries |
| **Importing** | Artifacts imported with correct status tracking |
| **Observability** | Metrics and logs enable debugging and monitoring |
| **Error Handling** | User-friendly error messages for all failure modes |

## Tasks

| Task ID | Description | Agent | Status | Dependencies | Est. |
|---------|-------------|-------|--------|--------------|------|
| SVC-001 | DTOs and service models | python-backend-engineer | ⏳ Pending | REPO-004 | 2pts |
| SVC-002 | Heuristic detector service | backend-architect | ⏳ Pending | SVC-001 | 5pts |
| SVC-003 | GitHub scanning service | backend-architect | ⏳ Pending | SVC-002 | 5pts |
| SVC-004 | README link harvester | python-backend-engineer | ⏳ Pending | SVC-003 | 3pts |
| SVC-005 | Catalog diff engine | backend-architect | ⏳ Pending | SVC-004 | 3pts |
| SVC-006 | Import coordinator service | python-backend-engineer | ⏳ Pending | SVC-005 | 3pts |
| SVC-007 | Error handling and observability | backend-architect | ⏳ Pending | SVC-006 | 2pts |

## Blockers

None identified.

## Next Session Agenda

1. Begin SVC-001 once REPO phase completes
2. Implement heuristic detector with test repos
3. Build GitHub scanner with rate-limit handling
4. Add README harvester for secondary discovery
5. Implement catalog diff logic
6. Create import coordinator with conflict handling
7. Add comprehensive observability and error handling
