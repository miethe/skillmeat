---
type: progress
prd: clone-based-artifact-indexing
phase: 5
title: Testing & Benchmarks
status: completed
started: null
updated: '2026-01-25'
completion: 0
total_tasks: 12
completed_tasks: 12
tasks:
- id: TEST-101
  title: Unit tests for CloneTarget serialization
  description: Test CloneTarget dataclass serialization/deserialization, edge cases
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies: []
  model: sonnet
  estimated_time: 1h
  story_points: 2
  acceptance_criteria:
  - 100% code coverage for CloneTarget class
  - Test to_json() and from_json() round-trip
  - Test with all strategy types
  - Test with empty lists, None values
  - Test datetime handling with timezone
- id: TEST-102
  title: Unit tests for compute_clone_metadata()
  description: Test metadata computation with various artifact distributions
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies: []
  model: sonnet
  estimated_time: 1h
  story_points: 2
  acceptance_criteria:
  - Test empty artifact list
  - Test single artifact
  - Test multiple artifacts with common root
  - Test scattered artifacts (no common root)
  - Test nested paths (.claude/skills/foo/bar)
- id: TEST-103
  title: Unit tests for strategy selection
  description: Test select_indexing_strategy() with various artifact counts and configs
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies: []
  model: sonnet
  estimated_time: 1h
  story_points: 2
  acceptance_criteria:
  - Test <3 artifacts returns 'api'
  - Test 3-20 artifacts returns 'sparse_manifest'
  - Test >20 artifacts with root returns 'sparse_directory'
  - Test >20 scattered returns 'sparse_manifest'
  - Strategy selection is deterministic
- id: TEST-104
  title: Unit tests for manifest extractors
  description: Test all 5 extractors with real-world manifests and edge cases
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies: []
  model: opus
  estimated_time: 2h
  story_points: 3
  acceptance_criteria:
  - Test skill extractor with valid/invalid SKILL.md
  - Test command/agent/hook extractors with .yaml and .yml
  - Test MCP extractor with mcp.json and package.json fallback
  - Test missing frontmatter handling
  - Test malformed YAML/JSON handling
  - 100% code coverage
- id: TEST-105
  title: Integration tests for sparse_manifest strategy
  description: End-to-end test of sparse_manifest clone and extraction
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies: []
  model: opus
  estimated_time: 2h
  story_points: 3
  acceptance_criteria:
  - Test with real test repository (can use anthropics/quickstarts)
  - Verify only manifest files are cloned
  - Verify all artifact types extracted correctly
  - Verify temp directory cleaned up
  - Test with GitHub token (authenticated)
- id: TEST-106
  title: Integration tests for sparse_directory strategy
  description: End-to-end test of sparse_directory clone for large repos
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies: []
  model: opus
  estimated_time: 2h
  story_points: 3
  acceptance_criteria:
  - Test with repository containing >20 artifacts
  - Verify only artifact directories cloned (not full repo)
  - Verify extraction works from cloned directories
  - Measure and log clone/extraction time
  - Verify temp directory cleaned up
- id: TEST-107
  title: Integration tests for API fallback
  description: Test graceful fallback when clone fails or times out
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies: []
  model: sonnet
  estimated_time: 1.5h
  story_points: 2
  acceptance_criteria:
  - Test fallback when git not available
  - Test fallback on clone timeout
  - Test fallback on clone error (e.g., auth failure)
  - Verify scan still completes via API
  - Verify warning logged on fallback
- id: TEST-108
  title: E2E test for full scan flow
  description: Complete end-to-end test from source creation through scan to search
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies: []
  model: opus
  estimated_time: 2h
  story_points: 2
  acceptance_criteria:
  - Create source via API
  - Trigger scan
  - Verify artifacts indexed
  - Verify CloneTarget stored
  - Search for indexed artifacts
  - Verify search results correct
- id: TEST-109
  title: 'Performance benchmark: 100 artifacts in <60s'
  description: Benchmark indexing performance with large repository
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies: []
  model: opus
  estimated_time: 2h
  story_points: 2
  acceptance_criteria:
  - Create or use test repo with 100+ artifacts
  - Full scan completes in <60 seconds
  - Results logged with timing breakdown
  - Benchmark reproducible
- id: TEST-110
  title: 'Performance benchmark: <10 API calls'
  description: Verify API call reduction from O(n) to O(1)
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies: []
  model: sonnet
  estimated_time: 1h
  story_points: 1
  acceptance_criteria:
  - Track API calls during 50+ artifact scan
  - Total API calls <10 (tree fetch + metadata)
  - Compare with baseline (O(n) calls)
  - Document reduction percentage
- id: TEST-111
  title: Deep indexing integration tests
  description: Test deep indexing feature end-to-end
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies: []
  model: sonnet
  estimated_time: 1.5h
  story_points: 2
  acceptance_criteria:
  - Test with deep_indexing_enabled=true
  - Verify full artifact directories cloned
  - Verify deep_search_text populated
  - Search finds results in deep content
  - Verify deep_match flag set correctly
- id: TEST-112
  title: Stress tests for edge cases
  description: Test with private repos, rate-limited scenarios, very large repos
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies: []
  model: opus
  estimated_time: 2h
  story_points: 2
  acceptance_criteria:
  - Test with private repo (requires auth)
  - Test behavior when rate limited
  - Test with very large repo (>1GB)
  - Graceful handling (no crashes)
  - Appropriate error messages
parallelization:
  batch_1:
  - TEST-101
  - TEST-102
  - TEST-103
  batch_2:
  - TEST-104
  - TEST-105
  - TEST-106
  - TEST-107
  batch_3:
  - TEST-108
  - TEST-109
  - TEST-110
  - TEST-111
  - TEST-112
  critical_path:
  - TEST-104
  - TEST-105
  - TEST-109
  estimated_total_time: 18h
blockers: []
quality_gates:
- All unit tests pass with >80% code coverage
- All integration tests pass
- Benchmarks show <60 second indexing for 100-artifact repo
- API call reduction verified (minimum 90% reduction from baseline)
- No crashes or hangs in edge case testing
- Performance metrics meet or exceed targets
in_progress_tasks: 0
blocked_tasks: 0
progress: 100
schema_version: 2
doc_type: progress
feature_slug: clone-based-artifact-indexing
---

# Phase 5: Testing & Benchmarks

**Plan:** `docs/project_plans/implementation_plans/features/clone-based-artifact-indexing-v1.md`
**SPIKE:** `docs/project_plans/SPIKEs/clone-based-artifact-indexing-spike.md`
**Status:** Pending
**Story Points:** 22 total
**Duration:** 2 days
**Dependencies:** Phases 1-4 complete

## Orchestration Quick Reference

**Batch 1** (Parallel - 3h estimated):
- TEST-101 -> `python-backend-engineer` (sonnet) - CloneTarget serialization tests
- TEST-102 -> `python-backend-engineer` (sonnet) - compute_clone_metadata() tests
- TEST-103 -> `python-backend-engineer` (sonnet) - Strategy selection tests

**Batch 2** (After Batch 1 - 7.5h estimated):
- TEST-104 -> `python-backend-engineer` (opus) - Manifest extractor tests
- TEST-105 -> `python-backend-engineer` (opus) - sparse_manifest integration tests
- TEST-106 -> `python-backend-engineer` (opus) - sparse_directory integration tests
- TEST-107 -> `python-backend-engineer` (sonnet) - API fallback tests

**Batch 3** (After Batch 2 - 8.5h estimated):
- TEST-108 -> `python-backend-engineer` (opus) - E2E scan flow test
- TEST-109 -> `python-backend-engineer` (opus) - 100 artifact benchmark
- TEST-110 -> `python-backend-engineer` (sonnet) - API call reduction benchmark
- TEST-111 -> `python-backend-engineer` (sonnet) - Deep indexing integration tests
- TEST-112 -> `python-backend-engineer` (opus) - Edge case stress tests

### Task Delegation Commands

**Batch 1:**
```
Task("python-backend-engineer", "TEST-101: Unit tests for CloneTarget serialization

Create skillmeat/api/tests/test_clone_target.py.

Tests:
1. test_clone_target_to_json(): Verify JSON output structure
2. test_clone_target_from_json(): Verify deserialization
3. test_clone_target_roundtrip(): to_json() -> from_json() preserves data
4. test_clone_target_with_all_strategies(): Test each strategy type
5. test_clone_target_empty_lists(): Handle empty patterns/paths
6. test_clone_target_datetime_timezone(): Verify timezone handling

Use pytest. Target 100% coverage of CloneTarget class.", model="sonnet")

Task("python-backend-engineer", "TEST-102: Unit tests for compute_clone_metadata()

Add to skillmeat/api/tests/test_clone_target.py.

Tests:
1. test_compute_empty_list(): Returns empty/None values
2. test_compute_single_artifact(): dirname as root
3. test_compute_common_root(): Multiple artifacts with shared parent
4. test_compute_scattered(): No common root, returns appropriate patterns
5. test_compute_nested_paths(): Deep nesting like .claude/skills/foo/bar
6. test_compute_mixed_types(): Multiple artifact types

Mock DetectedArtifact with different path configurations.", model="sonnet")

Task("python-backend-engineer", "TEST-103: Unit tests for strategy selection

Add to skillmeat/api/tests/test_clone_target.py.

Tests:
1. test_strategy_api_for_few_artifacts(): <3 returns 'api'
2. test_strategy_sparse_manifest_medium(): 3-20 returns 'sparse_manifest'
3. test_strategy_sparse_directory_large(): >20 with root returns 'sparse_directory'
4. test_strategy_sparse_manifest_scattered(): >20 scattered returns 'sparse_manifest'
5. test_strategy_is_deterministic(): Same input always same output
6. test_strategy_boundary_conditions(): Test exactly 3 and 20 artifacts

Use parameterized tests for various counts.", model="sonnet")
```

**Batch 2:**
```
Task("python-backend-engineer", "TEST-104: Unit tests for manifest extractors

Create skillmeat/api/tests/test_manifest_extractors.py.

Tests for each extractor:

Skill (extract_skill_manifest):
- test_skill_valid_frontmatter(): Standard SKILL.md
- test_skill_missing_frontmatter(): No --- delimiters
- test_skill_malformed_yaml(): Invalid YAML syntax

Command (extract_command_manifest):
- test_command_yaml(): command.yaml parsing
- test_command_yml(): command.yml variant
- test_command_md_fallback(): COMMAND.md fallback

Agent/Hook: Similar pattern

MCP (extract_mcp_manifest):
- test_mcp_json(): mcp.json parsing
- test_mcp_package_fallback(): package.json fallback
- test_mcp_malformed_json(): Invalid JSON

Use tmp_path fixture for test files. Target 100% coverage.")

Task("python-backend-engineer", "TEST-105: Integration tests for sparse_manifest strategy

Create skillmeat/api/tests/test_clone_strategies.py.

Test flow:
1. Use real test repo (anthropics/quickstarts or similar)
2. Create source with 5-10 artifacts
3. Trigger scan
4. Verify strategy selected is 'sparse_manifest'
5. Verify only manifest files in temp directory
6. Verify all metadata extracted correctly
7. Verify temp directory cleaned up
8. Run with GITHUB_TOKEN if available

Mark as integration test (slower, requires network).")

Task("python-backend-engineer", "TEST-106: Integration tests for sparse_directory strategy

Add to skillmeat/api/tests/test_clone_strategies.py.

Test flow:
1. Use or create test repo with >20 artifacts
2. Artifacts should share common root (e.g., .claude/)
3. Trigger scan
4. Verify strategy is 'sparse_directory'
5. Verify only artifact root cloned (not full repo)
6. Measure and log: clone_time, extraction_time, total_time
7. Verify cleanup

May need to create test fixtures with many dummy artifacts.")

Task("python-backend-engineer", "TEST-107: Integration tests for API fallback

Add to skillmeat/api/tests/test_clone_strategies.py.

Tests:
1. test_fallback_git_unavailable(): Mock git not found
2. test_fallback_clone_timeout(): Mock subprocess timeout
3. test_fallback_clone_error(): Mock clone failure (auth error)
4. test_fallback_completes_scan(): Verify scan succeeds via API
5. test_fallback_logs_warning(): Check for warning log

Mock subprocess and shutil as needed.", model="sonnet")
```

**Batch 3:**
```
Task("python-backend-engineer", "TEST-108: E2E test for full scan flow

Create skillmeat/api/tests/test_scan_e2e.py.

Full flow test:
1. POST /marketplace/sources with real GitHub repo
2. POST /marketplace/sources/{id}/scan
3. Wait for scan completion
4. GET /marketplace/sources/{id} - verify clone_target populated
5. GET /marketplace/catalog?source_id={id} - verify artifacts indexed
6. GET /marketplace/search?q=<query> - verify search works
7. Verify artifact metadata (title, description, tags) correct

Use pytest-asyncio for async tests. Mark as E2E/slow.")

Task("python-backend-engineer", "TEST-109: Performance benchmark: 100 artifacts in <60s

Create skillmeat/api/tests/benchmarks/test_performance.py.

Benchmark:
1. Create/use test repo with 100+ artifacts
   - Can generate fixtures or use known large repo
2. Time full scan operation
3. Break down: detection, strategy_selection, clone, extraction, storage
4. Assert total time <60 seconds
5. Log detailed timing report

Use pytest-benchmark if available. Run as separate benchmark suite.
Store results for regression tracking.")

Task("python-backend-engineer", "TEST-110: Performance benchmark: <10 API calls

Add to skillmeat/api/tests/benchmarks/test_performance.py.

Test:
1. Instrument GitHubClient to count API calls
2. Run scan on 50+ artifact repo
3. Count total API calls
4. Assert count <10
5. Compare with baseline (would be ~50+ without optimization)
6. Calculate and log reduction percentage

Document: 'API calls reduced from {baseline} to {actual} ({percent}% reduction)'", model="sonnet")

Task("python-backend-engineer", "TEST-111: Deep indexing integration tests

Create skillmeat/api/tests/test_deep_indexing.py.

Tests:
1. test_deep_index_enabled(): Source with deep_indexing_enabled=True
2. test_full_directory_cloned(): Verify all files in artifact dir cloned
3. test_deep_search_text_populated(): Check database field
4. test_search_finds_deep_content(): Query that matches deep content
5. test_deep_match_flag(): Response has deep_match=True
6. test_default_disabled(): Verify off by default

Use small test artifacts with known content for assertions.", model="sonnet")

Task("python-backend-engineer", "TEST-112: Stress tests for edge cases

Create skillmeat/api/tests/test_stress.py.

Tests (mark as slow/optional):
1. test_private_repo_with_auth(): Requires GITHUB_TOKEN
2. test_rate_limit_handling(): Mock 429 responses
3. test_large_repo(): Repo with >1GB of code (but sparse clone)
4. test_concurrent_scans(): Multiple sources scanned simultaneously
5. test_disk_full_handling(): Mock disk space check failure

Each should not crash. Verify appropriate error handling and logging.
Some tests may be skipped if environment not configured.")
```

---

## Test Fixtures Setup

Create test artifacts in `skillmeat/api/tests/fixtures/artifacts/`:

```
fixtures/artifacts/
  skill-valid/
    SKILL.md          # Valid skill with frontmatter
  skill-no-frontmatter/
    SKILL.md          # Missing --- delimiters
  command-yaml/
    command.yaml      # Valid command
  agent-yml/
    agent.yml         # Valid agent
  mcp-json/
    mcp.json          # Valid MCP
  hook-yaml/
    hook.yaml         # Valid hook
```

---

## Success Criteria

- [ ] All unit tests pass with >80% code coverage
- [ ] All integration tests pass
- [ ] Benchmarks show <60 second indexing for 100-artifact repo
- [ ] API call reduction verified (minimum 90% reduction from baseline)
- [ ] No crashes or hangs in edge case testing
- [ ] Performance metrics meet or exceed targets

---

## Work Log

[Session entries will be added as tasks complete]

---

## Decisions Log

[Architectural decisions will be logged here]

---

## Files Changed

[Will be tracked as implementation progresses]
