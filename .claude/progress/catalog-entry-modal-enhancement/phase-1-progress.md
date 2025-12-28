---
type: progress
prd: "catalog-entry-modal-enhancement"
phase: 1
title: "Backend File Fetching"
status: pending
progress: 0
total_tasks: 8
completed_tasks: 0
blocked_tasks: 0
created: 2025-12-28
updated: 2025-12-28

tasks:
  - id: "TASK-1.1"
    title: "Add get_file_tree() to GitHubClient"
    status: "pending"
    priority: "high"
    estimate: "2 pts"
    assigned_to: ["python-backend-engineer"]
    dependencies: []
    acceptance: "Method returns list of file paths, types, sizes from GitHub Tree API. Handles recursive trees."
    files: ["skillmeat/core/marketplace/github_scanner.py"]

  - id: "TASK-1.2"
    title: "Add get_file_content() to GitHubClient"
    status: "pending"
    priority: "high"
    estimate: "2 pts"
    assigned_to: ["python-backend-engineer"]
    dependencies: []
    acceptance: "Method returns file content (base64-decoded), encoding, size, SHA from GitHub Contents API."
    files: ["skillmeat/core/marketplace/github_scanner.py"]

  - id: "TASK-1.5"
    title: "Implement backend caching layer"
    status: "pending"
    priority: "high"
    estimate: "2 pts"
    assigned_to: ["python-backend-engineer"]
    dependencies: []
    acceptance: "LRU cache with max 1000 entries. TTL: 1hr (trees), 2hr (contents). Keys: tree:{source_id}:{artifact_path}:{sha}."
    files: ["skillmeat/api/utils/cache.py"]

  - id: "TASK-1.3"
    title: "Create file tree endpoint"
    status: "pending"
    priority: "high"
    estimate: "3 pts"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["TASK-1.1", "TASK-1.5"]
    acceptance: "GET /marketplace/sources/{id}/artifacts/{path}/files returns cached file tree DTO."
    files: ["skillmeat/api/routers/marketplace_sources.py", "skillmeat/api/schemas/marketplace.py"]

  - id: "TASK-1.4"
    title: "Create file content endpoint"
    status: "pending"
    priority: "high"
    estimate: "3 pts"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["TASK-1.2", "TASK-1.5"]
    acceptance: "GET /marketplace/sources/{id}/artifacts/{path}/files/{file_path} returns cached content DTO."
    files: ["skillmeat/api/routers/marketplace_sources.py", "skillmeat/api/schemas/marketplace.py"]

  - id: "TASK-1.6"
    title: "Add rate limit detection"
    status: "pending"
    priority: "medium"
    estimate: "1 pt"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["TASK-1.3", "TASK-1.4"]
    acceptance: "Detect GitHub HTTP 403 with X-RateLimit-Remaining: 0. Return HTTP 429 with Retry-After header."
    files: ["skillmeat/api/routers/marketplace_sources.py"]

  - id: "TASK-1.7"
    title: "Unit tests for file endpoints"
    status: "pending"
    priority: "medium"
    estimate: "1 pt"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["TASK-1.3", "TASK-1.4", "TASK-1.6"]
    acceptance: "Test happy path, 404 errors, rate limits, cache hits/misses. Coverage >80%."
    files: ["tests/api/routers/test_marketplace_sources.py"]

  - id: "TASK-1.8"
    title: "Update OpenAPI spec"
    status: "pending"
    priority: "low"
    estimate: "1 pt"
    assigned_to: ["documentation-writer"]
    dependencies: ["TASK-1.3", "TASK-1.4"]
    acceptance: "Add /files and /files/{file_path} endpoints to OpenAPI schema with request/response models."
    files: ["skillmeat/api/server.py"]

parallelization:
  batch_1: ["TASK-1.1", "TASK-1.2", "TASK-1.5"]
  batch_2: ["TASK-1.3", "TASK-1.4"]
  batch_3: ["TASK-1.6", "TASK-1.7", "TASK-1.8"]

quality_gate:
  owner: "python-backend-engineer"
  criteria:
    - "All unit tests pass (>80% coverage)"
    - "OpenAPI spec validates (no schema errors)"
    - "Rate limit handling tested with mocked GitHub 403 responses"
    - "Backend cache hit rate >70% in local testing"
    - "No security vulnerabilities (path traversal, injection)"

blockers: []

notes: []
---

# Phase 1: Backend File Fetching

**Goal**: Enable GitHub file tree and content fetching with caching layer.

**Duration**: 3 days | **Effort**: 13 story points

## Orchestration Quick Reference

### Batch 1 (Parallel - No Dependencies)

```
Task("python-backend-engineer", "TASK-1.1: Add get_file_tree() method to GitHubScanner class in skillmeat/core/marketplace/github_scanner.py. Use GitHub Tree API (/repos/{owner}/{repo}/git/trees/{sha}?recursive=1). Return list of {path, type, size}. Handle rate limits.")

Task("python-backend-engineer", "TASK-1.2: Add get_file_content() method to GitHubScanner class. Use GitHub Contents API (/repos/{owner}/{repo}/contents/{path}?ref={sha}). Decode base64 content. Return {content, encoding, size, sha}.")

Task("python-backend-engineer", "TASK-1.5: Implement backend caching layer in skillmeat/api/utils/cache.py. Extend CacheManager for file content caching. LRU with max 1000 entries. TTL: 1hr (trees), 2hr (contents). Key format: tree:{source_id}:{artifact_path}:{sha}, content:{source_id}:{artifact_path}:{file_path}:{sha}.")
```

### Batch 2 (After Batch 1)

```
Task("python-backend-engineer", "TASK-1.3: Create GET /marketplace/sources/{id}/artifacts/{path}/files endpoint in skillmeat/api/routers/marketplace_sources.py. Call GitHubScanner.get_file_tree(). Return cached DTO with file list. Add Pydantic schemas to skillmeat/api/schemas/marketplace.py.")

Task("python-backend-engineer", "TASK-1.4: Create GET /marketplace/sources/{id}/artifacts/{path}/files/{file_path} endpoint. Call GitHubScanner.get_file_content(). Return cached DTO with file content. Handle path encoding for nested files.")
```

### Batch 3 (After Batch 2)

```
Task("python-backend-engineer", "TASK-1.6: Add rate limit detection to file endpoints. Detect GitHub HTTP 403 with X-RateLimit-Remaining: 0. Return HTTP 429 with Retry-After header calculated from X-RateLimit-Reset.")

Task("python-backend-engineer", "TASK-1.7: Write unit tests for file endpoints in tests/api/routers/test_marketplace_sources.py. Test: happy path file tree fetch, happy path content fetch, 404 for missing file, rate limit 429 response, cache hit scenario. Coverage >80%.")

Task("documentation-writer", "TASK-1.8: Update OpenAPI documentation. Ensure new /files endpoints appear in /api/v1/docs with proper request/response schemas and examples.")
```

## Key Files

| File | Purpose |
|------|---------|
| `skillmeat/core/marketplace/github_scanner.py` | Add get_file_tree(), get_file_content() methods |
| `skillmeat/api/routers/marketplace_sources.py` | Add file tree and content endpoints |
| `skillmeat/api/schemas/marketplace.py` | Add FileTreeResponse, FileContentResponse DTOs |
| `skillmeat/api/utils/cache.py` | Extend CacheManager for file caching |
| `tests/api/routers/test_marketplace_sources.py` | Unit tests for new endpoints |

## Acceptance Criteria

- [ ] GitHubScanner can fetch file trees and individual file contents
- [ ] Backend cache reduces GitHub API calls by 70%+ for repeated requests
- [ ] Rate limit errors (HTTP 403) are detected and handled gracefully
- [ ] All endpoints return proper DTOs (Pydantic models)
- [ ] Unit tests achieve >80% coverage for new code
- [ ] OpenAPI spec updated with new endpoints
