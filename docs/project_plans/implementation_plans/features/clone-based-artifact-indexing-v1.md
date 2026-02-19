---
title: 'Implementation Plan: Clone-Based Artifact Indexing'
description: Hybrid sparse clone strategy to reduce GitHub API rate limit exhaustion
  during artifact metadata extraction
audience:
- ai-agents
- developers
- product-managers
tags:
- implementation
- marketplace
- optimization
- github-integration
created: 2026-01-24
updated: '2026-02-07'
category: product-planning
status: completed
related:
- /docs/project_plans/SPIKEs/clone-based-artifact-indexing-spike.md
schema_version: 2
doc_type: implementation_plan
feature_slug: clone-based-artifact-indexing
prd_ref: null
---

# Implementation Plan: Clone-Based Artifact Indexing

**Plan ID**: `IMPL-2026-01-24-CLONE-ARTIFACT-INDEXING`
**Date**: 2026-01-24
**Author**: Implementation Planner (Orchestrator)
**Related SPIKE**: `/docs/project_plans/SPIKEs/clone-based-artifact-indexing-spike.md`

**Complexity**: Large (L)
**Total Estimated Effort**: 55-65 story points
**Target Timeline**: 2 weeks (10 business days)

---

## Executive Summary

This implementation plan addresses GitHub API rate limit exhaustion during artifact metadata extraction by introducing a hybrid sparse clone strategy. Rather than making individual API calls for each artifact manifest file, the system will intelligently select between three strategies: direct API calls for small operations (<3 artifacts), sparse manifest cloning for medium operations (3-20 artifacts), and sparse directory cloning for large operations (>20 artifacts).

The solution maintains zero API calls for full-repository clones (only clones artifact directories), introduces a `CloneTarget` dataclass for rapid re-indexing with cached configuration, and enables optional deep indexing for enhanced full-text search. Implementation follows MeatyPrompts layered architecture with database foundation first, progressing through core logic, API exposure, and comprehensive testing.

---

## Implementation Strategy

### Architecture Sequence

Following MeatyPrompts layered architecture in strict order:

1. **Database Layer** - Migrations, schema updates, FTS5 configuration
2. **Core Layer** - CloneTarget dataclass, metadata computation, extraction logic
3. **Service/Repository Layer** - Clone orchestration, manifest extraction, caching
4. **API Layer** - Router enhancements, response schemas, deep indexing toggles
5. **Testing Layer** - Unit, integration, performance benchmarks
6. **Documentation Layer** - API docs, migration guides, troubleshooting

### Parallel Work Opportunities

- **DB Migrations + Core Dataclass** (Phase 1): Can start DB migration work while designing CloneTarget serialization
- **Manifest Extractors** (Phase 2): Each artifact type extractor can be developed independently and tested in isolation
- **Testing Infrastructure** (Phase 3+): Setup fixtures and helpers early for all phases to use
- **Documentation**: Can be drafted while implementation proceeds, finalized at end

### Critical Path

1. Database migrations must complete before any code reads/writes new fields
2. CloneTarget dataclass must exist before extraction logic can use it
3. Clone strategy selection logic must be solid before deep indexing features
4. Integration tests must verify all strategies work before deployment

---

## Phase Breakdown

### Phase 1: Database & Core Foundation (2-3 days)

**Duration**: 2-3 days
**Dependencies**: None (project must have git and Python 3.9+)
**Assigned Subagent(s)**: data-layer-expert, python-backend-engineer
**Parallel Work**: Yes - can start Phase 2 design while migrations run

#### 1.1 Database Migrations

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Dependencies |
|---------|-----------|-------------|-------------------|----------|-------------|--------------|
| DB-101 | Create Alembic migration | Add clone_target_json, deep_indexing fields to MarketplaceSource; add deep_search_text fields to MarketplaceCatalogEntry | Migration runs cleanly forward/backward on test DB | 2 pts | data-layer-expert | None |
| DB-102 | Update FTS5 schema | Drop and recreate catalog_fts virtual table with deep_search_text column; add tokenization config | FTS5 table has all columns, full-text indexing works | 2 pts | data-layer-expert | DB-101 |
| DB-103 | Add webhook pre-wiring | Add webhook_secret and last_webhook_event_at fields to MarketplaceSource (for future use, nullable) | Fields exist and are properly indexed | 1 pt | data-layer-expert | DB-101 |

#### 1.2 CloneTarget Dataclass & Serialization

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Dependencies |
|---------|-----------|-------------|-------------------|----------|-------------|--------------|
| CORE-101 | Create CloneTarget dataclass | Implement `skillmeat/core/clone_target.py` with dataclass for strategy, sparse_patterns, artifacts_root, artifact_paths, tree_sha, computed_at | Dataclass can serialize/deserialize from JSON; all fields properly typed | 2 pts | python-backend-engineer | None |
| CORE-102 | Add to MarketplaceSource model | Update SQLAlchemy model with `clone_target_json` property, add `clone_target` property for deserialization | Model tests pass, can read/write CloneTarget from DB | 2 pts | data-layer-expert | DB-101, CORE-101 |
| CORE-103 | Implement compute_clone_metadata() | Create function to compute artifacts_root, sparse_patterns from DetectedArtifact list; handle edge cases (no artifacts, scattered paths) | Function tested with various artifact distributions; returns valid dict | 2 pts | python-backend-engineer | CORE-101 |

#### 1.3 Phase 1 Quality Gates

- [ ] Alembic migrations run cleanly forward and backward
- [ ] FTS5 table schema validated with SQLite inspection
- [ ] CloneTarget serializes/deserializes without data loss
- [ ] compute_clone_metadata() handles empty/single/multiple artifacts correctly
- [ ] Unit tests for CloneTarget pass (>80% coverage)
- [ ] No breaking changes to existing MarketplaceCatalogEntry reads

**Phase 1 Total**: 11 story points

---

### Phase 2: Universal Clone Infrastructure (3-4 days)

**Duration**: 3-4 days
**Dependencies**: Phase 1 complete
**Assigned Subagent(s)**: python-backend-engineer, backend-architect
**Parallel Work**: Manifest extractors can be worked on independently

#### 2.1 Clone Orchestration & Strategy Selection

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Dependencies |
|---------|-----------|-------------|-------------------|----------|-------------|--------------|
| CLONE-101 | Implement select_indexing_strategy() | Create function to choose api/sparse_manifest/sparse_directory based on artifact count and configuration; document thresholds | Function returns correct strategy for all scenarios; matches SPIKE requirements | 2 pts | python-backend-engineer | CORE-103 |
| CLONE-102 | Implement get_sparse_checkout_patterns() | Generate sparse-checkout patterns for each strategy; handle multi-root cases; ensure no full-repo cloning | Patterns tested with actual git commands; cover all artifact types | 2 pts | python-backend-engineer | CORE-101 |
| CLONE-103 | Refactor _clone_repo_sparse() | Update existing clone function to accept pattern list, strategy selector; add error handling and logging | Clones complete successfully for various pattern sets; proper cleanup on error | 3 pts | python-backend-engineer | CLONE-101, CLONE-102 |

#### 2.2 Manifest Extraction - All Types

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Dependencies |
|---------|-----------|-------------|-------------------|----------|-------------|--------------|
| MANIFEST-101 | Create skillmeat/core/manifest_extractors.py | Implement extractors for SKILL.md, command.yaml, agent.yaml, hook.yaml, mcp.json; handle parse errors gracefully | All extractors tested with real-world manifests; return standardized metadata dict | 4 pts | python-backend-engineer | None |
| MANIFEST-102 | Implement _extract_all_manifests_batch() | Batch extraction from cloned directory; support both API fallback and local filesystem read | Function reads all manifest files efficiently; handles missing files without crashing | 3 pts | python-backend-engineer | MANIFEST-101, CLONE-103 |
| MANIFEST-103 | Add type-specific parsers | Implement YAML parser for commands/agents/hooks, JSON parser for mcp, markdown frontmatter for skills | Parsers extract title, description, tags for each type; tests pass | 3 pts | python-backend-engineer | MANIFEST-101 |

#### 2.3 Integration with Existing Flow

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Dependencies |
|---------|-----------|-------------|-------------------|----------|-------------|--------------|
| INTEGRATE-101 | Update _perform_scan() to use CloneTarget | Modify scan flow to compute and persist CloneTarget; select strategy; execute appropriate indexing path | Scan completes for all artifact types; CloneTarget stored correctly | 3 pts | python-backend-engineer | CLONE-101, MANIFEST-102 |
| INTEGRATE-102 | Add differential re-indexing logic | Implement should_reindex(), get_changed_artifacts() using CloneTarget.tree_sha; skip unnecessary clones | Re-indexing avoids cloning when tree unchanged; only processes modified artifacts | 2 pts | python-backend-engineer | CORE-101 |

#### 2.4 Phase 2 Quality Gates

- [ ] All manifest extractors tested with real manifests from artifact repos
- [ ] _clone_repo_sparse() successfully clones with varied pattern lists
- [ ] Differential re-indexing correctly detects tree changes
- [ ] Integration tests show rate limit calls reduced from O(n) to O(1) or O(log n)
- [ ] All 5 artifact types (skill, command, agent, hook, mcp) extracted successfully
- [ ] Temp files properly cleaned up after clone operations
- [ ] Code coverage >80% for new functions

**Phase 2 Total**: 22 story points

---

### Phase 3: Optimization & Observability (2-3 days)

**Duration**: 2-3 days
**Dependencies**: Phase 2 complete
**Assigned Subagent(s)**: python-backend-engineer, backend-architect

#### 3.1 Performance & Metrics

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Dependencies |
|---------|-----------|-------------|-------------------|----------|-------------|--------------|
| METRICS-101 | Add timing instrumentation | Instrument clone, extraction, storage operations with OpenTelemetry; log strategy selection | Metrics available for all operations; can trace slow paths | 2 pts | python-backend-engineer | INTEGRATE-101 |
| METRICS-102 | Implement API call counter | Track GitHub API calls per scan; emit metrics/logs showing reduction | Logs show X API calls for Y artifacts (validates hybrid approach) | 2 pts | python-backend-engineer | METRICS-101 |
| METRICS-103 | Performance validation | Benchmark with 100-artifact repo; verify <60 second indexing, <10 API calls | Benchmark results documented; performance targets met | 2 pts | python-backend-engineer | METRICS-101 |

#### 3.2 Robustness & Error Handling

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Dependencies |
|---------|-----------|-------------|-------------------|----------|-------------|--------------|
| ROBUST-101 | Add clone timeout handling | Implement timeout for clone operations; graceful fallback to API if clone fails | Clone timeout tested; fallback works without crashing | 2 pts | python-backend-engineer | CLONE-103 |
| ROBUST-102 | Implement git availability check | Detect missing git at startup; warn user; allow API-only mode | Application starts without git (with warning); API mode works | 1 pt | python-backend-engineer | CLONE-101 |
| ROBUST-103 | Add disk space validation | Check available space before cloning; abort if insufficient space available | Disk check runs before clone; error message clear | 1 pt | python-backend-engineer | CLONE-103 |

#### 3.3 Phase 3 Quality Gates

- [ ] Performance benchmark meets <60 second target for 100-artifact repos
- [ ] API call count <10 for all scenarios
- [ ] All error paths logged with actionable messages
- [ ] Graceful fallback to API when clone fails
- [ ] Metrics clearly show strategy selection for each scan
- [ ] OpenTelemetry instrumentation complete

**Phase 3 Total**: 12 story points

---

### Phase 4: Deep Indexing (1-2 days)

**Duration**: 1-2 days
**Dependencies**: Phase 3 complete
**Assigned Subagent(s)**: python-backend-engineer, backend-architect

#### 4.1 Deep Index Infrastructure

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Dependencies |
|---------|-----------|-------------|-------------------|----------|-------------|--------------|
| DEEP-101 | Implement extract_deep_search_text() | Extract searchable text from all artifact files; filter by type (*.md, *.yaml, *.py, *.ts, etc.); skip large files | Text extraction works for all file types; returns normalized, searchable text | 2 pts | python-backend-engineer | MANIFEST-101 |
| DEEP-102 | Implement get_deep_sparse_patterns() | Generate patterns for full artifact directory clone | Patterns tested with large repos; clones only artifact dirs, not codebase | 1 pt | python-backend-engineer | CLONE-102 |
| DEEP-103 | Add deep_indexing_enabled flag logic | Update scan flow to clone full artifact directories when flag=true; extract deep_search_text | Deep indexing optional and toggleable; correctly populates database fields | 2 pts | python-backend-engineer | DEEP-101, DEEP-102 |

#### 4.2 API Exposure

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Dependencies |
|---------|-----------|-------------|-------------------|----------|-------------|--------------|
| API-401 | Update SourceCreateRequest schema | Add deep_indexing_enabled boolean field with description | Field accepted in POST /marketplace/sources; defaults to false | 1 pt | python-backend-engineer | DEEP-103 |
| API-402 | Update search response schema | Add deep_match boolean and matched_file string to search results | Search results indicate whether match came from deep index | 1 pt | python-backend-engineer | API-401 |
| API-403 | Update FTS5 search query | Include deep_search_text in full-text search; rank deep matches differently | Searches that match deep_search_text return results; ranking is sensible | 2 pts | python-backend-engineer | API-402 |

#### 4.3 Phase 4 Quality Gates

- [ ] Deep indexing extracts text from all supported file types
- [ ] Large files (>100KB) properly skipped
- [ ] FTS5 searches include deep_search_text results
- [ ] deep_match flag correctly set in responses
- [ ] Performance impact of deep indexing measured and acceptable
- [ ] Backward compatibility maintained (default deep_indexing_enabled=false)

**Phase 4 Total**: 9 story points

---

### Phase 5: Testing & Benchmarks (2 days)

**Duration**: 2 days
**Dependencies**: Phases 1-4 complete
**Assigned Subagent(s)**: python-backend-engineer, testing-specialist, backend-architect

#### 5.1 Unit Testing

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Dependencies |
|---------|-----------|-------------|-------------------|----------|-------------|--------------|
| TEST-501 | Unit tests: CloneTarget | Test serialization, deserialization, edge cases | 100% code coverage; all edge cases pass | 2 pts | python-backend-engineer | CORE-101 |
| TEST-502 | Unit tests: Metadata computation | Test compute_clone_metadata() with various artifact distributions | Tests cover: empty list, single artifact, scattered paths, common roots | 2 pts | python-backend-engineer | CORE-103 |
| TEST-503 | Unit tests: Strategy selection | Test select_indexing_strategy() with various artifact counts and configs | All threshold conditions tested; strategy selection deterministic | 2 pts | python-backend-engineer | CLONE-101 |
| TEST-504 | Unit tests: Manifest extractors | Test all 5 extractors with real-world manifests and edge cases | 100% code coverage; error handling tested | 3 pts | python-backend-engineer | MANIFEST-101 |

#### 5.2 Integration Testing

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Dependencies |
|---------|-----------|-------------|-------------------|----------|-------------|--------------|
| TEST-505 | Integration: Clone strategies | Test each strategy (api, sparse_manifest, sparse_directory) with real test repos | All strategies successfully clone and extract metadata | 3 pts | python-backend-engineer | INTEGRATE-101 |
| TEST-506 | Integration: End-to-end scan | Test complete scan flow from detection to database update | Scan completes successfully; all artifact metadata stored correctly | 2 pts | python-backend-engineer | INTEGRATE-101 |
| TEST-507 | Integration: Differential re-indexing | Test re-scan with unchanged and changed trees | Unchanged trees skip clone; changed trees re-index correctly | 2 pts | python-backend-engineer | INTEGRATE-102 |

#### 5.3 Performance Benchmarking

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Dependencies |
|---------|-----------|-------------|-------------------|----------|-------------|--------------|
| TEST-508 | Benchmark: 100-artifact repo | Index large repo; measure time, API calls, disk usage | <60 seconds total, <10 API calls, <500MB disk | 2 pts | python-backend-engineer | METRICS-103 |
| TEST-509 | Benchmark: API call reduction | Compare before/after: O(n) API calls vs O(1) | Measurements documented; reduction validated | 1 pt | python-backend-engineer | METRICS-102 |
| TEST-510 | Stress test: Edge cases | Test with private repos (auth), rate-limited repos, very large repos | Graceful fallback/error handling; no crashes | 2 pts | python-backend-engineer | ROBUST-101 |

#### 5.4 Phase 5 Quality Gates

- [ ] All unit tests pass; >80% code coverage
- [ ] All integration tests pass
- [ ] Benchmarks show <60 second indexing for 100-artifact repo
- [ ] API call reduction verified (minimum 90% reduction from baseline)
- [ ] No crashes or hangs in edge case testing
- [ ] Performance metrics meet or exceed targets

**Phase 5 Total**: 22 story points

---

## Risk Mitigation

### Technical Risks

| Risk | Impact | Likelihood | Mitigation Strategy |
|------|--------|------------|-------------------|
| Git not available in production | High | Medium | Check at startup, emit clear warning, allow API-only fallback mode |
| Clone timeout on massive repos | Medium | Medium | Implement configurable timeout (default 5 min), fallback to API if exceeded |
| Private repo authentication failure | High | Low | Validate GitHub token before clone, use token from central GitHubClient |
| Disk space exhaustion | Medium | Low | Check available disk before clone, abort with clear error if insufficient |
| Manifest format inconsistency | Low | Medium | Flexible parsing with sensible defaults; log parsing errors; use API fallback if parse fails |
| Sparse-checkout not supported | Low | Low | Detect git version at startup; fail gracefully with clear error message |
| Rate limit still exceeded in edge cases | Medium | Low | Maintain fallback to API for small operations; monitor metrics in production |
| Deep indexing file size explosion | Medium | Medium | Implement file size limits (100KB default), skip binary files, truncate large text files |
| Database migration rollback issues | High | Low | Test migrations on staging with real data before production; maintain backward compatibility |
| Concurrent scan operations | Medium | Low | Implement file-level locking for temp directories; use database transactions |

### Schedule Risks

| Risk | Impact | Likelihood | Mitigation Strategy |
|------|--------|------------|-------------------|
| Phase 2 manifests more complex than estimated | Medium | Medium | Start with skills (simplest), add others incrementally; spike on complex types early |
| Performance benchmarks not met | High | Medium | Early benchmark validation in Phase 3; adjust thresholds/strategy if needed |
| Database migration compatibility issues | High | Low | Test on all supported databases early; maintain staging environment for testing |
| Testing uncovers major design flaws | High | Medium | Comprehensive design review at end of Phase 1; early integration test in Phase 2 |

---

## Resource Requirements

### Team Composition

| Role | Phases | Time | Notes |
|------|--------|------|-------|
| data-layer-expert | 1 | 3 days | Database migrations, FTS5 schema, model updates |
| python-backend-engineer | 1-5 | 2 weeks | Core implementation, testing, refinement |
| backend-architect | 2-4 | 1 week part-time | Design review, complex logic, optimization decisions |
| testing-specialist | 5 | 3 days | Test infrastructure, benchmark harness |

### Skill Requirements

- Python 3.9+, FastAPI, SQLAlchemy, Alembic
- Git operations, subprocess management, file I/O
- YAML/JSON/Markdown parsing
- SQLite FTS5 configuration
- GitHub API (via existing GitHubClient wrapper)

### Environment Requirements

- Git binary (check at startup, not available in serverless)
- Temporary directory with write access (at least 1GB)
- GitHub token (for private repo support)

---

## Key Files & Locations

### Files to Create

| File Path | Purpose | Phase |
|-----------|---------|-------|
| `skillmeat/core/clone_target.py` | CloneTarget dataclass and serialization | 1 |
| `skillmeat/core/manifest_extractors.py` | Type-specific manifest parsers | 2 |
| `skillmeat/api/migrations/add_clone_target_fields.py` | Alembic migration | 1 |
| `skillmeat/api/migrations/add_deep_search_to_fts5.py` | FTS5 update migration | 1 |

### Files to Modify

| File Path | Change Scope | Phase |
|-----------|-------------|-------|
| `skillmeat/api/models/marketplace.py` | Add fields to MarketplaceSource, MarketplaceCatalogEntry | 1 |
| `skillmeat/api/routers/marketplace_sources.py` | Lines 655-929 (scan flow), add strategy selection, update _perform_scan() | 2-4 |
| `skillmeat/api/schemas/marketplace.py` | Add deep_indexing_enabled, deep_match fields | 4 |

### Testing

| File Path | Purpose | Phase |
|-----------|---------|-------|
| `skillmeat/api/tests/test_clone_target.py` | Unit tests for CloneTarget | 5 |
| `skillmeat/api/tests/test_manifest_extractors.py` | Unit tests for extractors | 5 |
| `skillmeat/api/tests/test_clone_strategies.py` | Integration tests for clone strategies | 5 |
| `skillmeat/api/tests/fixtures/artifacts/` | Test artifact repositories | 5 |

---

## Success Metrics

### Delivery Metrics

- On-time delivery (±1 day)
- All phases pass quality gates
- Code coverage >80% for new code
- Zero P0/P1 bugs in first week of deployment

### Technical Metrics

- GitHub API calls reduced by 90%+ for large repos
- 100-artifact repo indexing completes in <60 seconds
- Disk usage <500MB per clone operation
- 99%+ success rate for public repos

### User-Facing Metrics

- No increase in error rates from scan operations
- Improved performance visible in UI (faster source import)
- Deep indexing improves search quality (tracked via search analytics)

---

## Communication Plan

- **Daily standups**: 15 min sync on blockers
- **Phase reviews**: 30 min gate review at end of each phase
- **Weekly status**: Summary of progress, blockers, next week's focus
- **Stakeholder update**: Bi-weekly executive summary

---

## Post-Implementation

### Launch Checklist

- [ ] All tests passing in CI/CD
- [ ] Performance benchmarks documented and approved
- [ ] Staging environment mirrors production
- [ ] Rollback procedure documented and tested
- [ ] Monitoring dashboards created
- [ ] Runbook for troubleshooting written

### Monitoring

- Track GitHub API call counts per source
- Monitor clone operation success rates
- Alert on performance regressions (>60 second scans)
- Track disk usage of temp directories
- Monitor error rates by artifact type

### Future Enhancements

1. **Webhook Integration** (Phase 4 pre-wired): Auto-reindex on GitHub push events
2. **Artifact Caching**: Cache extracted metadata for faster re-indexing
3. **Parallel Cloning**: Support concurrent clone operations for multiple sources
4. **Advanced Deep Indexing**: Include Jupyter notebooks, compiled artifacts
5. **Search Ranking**: Improve FTS5 ranking based on file type matches

---

## Decision Log

### D1: Threshold Values

**Decision**: Use 3 artifacts as threshold for clone vs API (validated via benchmarks in Phase 3)

**Rationale**:
- <3 artifacts: API overhead minimal (<100ms), clone overhead not worth it
- 3-20 artifacts: Clone manifests faster than individual API calls
- >20 artifacts: Sparse directory clone most efficient

**Alternative Considered**: Dynamic threshold based on GitHub response times. Rejected: adds complexity, 3 is reasonable default.

### D2: Clone Caching Strategy

**Decision**: Cache CloneTarget configuration (not cloned files)

**Rationale**:
- Cloned files are transient; caching adds complexity
- CloneTarget contains all info needed to re-sync quickly
- Enables rapid differential re-indexing

**Alternative Considered**: Full clone caching. Rejected: disk overhead, invalidation complexity.

### D3: Sparse vs Full Clone

**Decision**: Always use sparse-checkout (never clone full repo)

**Rationale**:
- Minimal bandwidth and disk usage
- Works with all artifact types
- Critical for repos with artifacts in `.claude/` subdirectories

**Alternative Considered**: Archive download. Rejected: GitHub doesn't support for public repos.

### D4: Deep Indexing Opt-In

**Decision**: Deep indexing defaults to false, toggleable per source

**Rationale**:
- Adds overhead; users should opt-in
- Enables experimentation without affecting all users
- Can be enabled globally later if proven valuable

---

## Glossary

| Term | Definition |
|------|-----------|
| **CloneTarget** | Structured configuration containing strategy, patterns, tree_sha for rapid re-indexing |
| **Sparse Checkout** | Git feature to clone only specified files/directories |
| **Sparse Manifest** | Strategy: clone only manifest files (SKILL.md, command.yaml, etc.) |
| **Sparse Directory** | Strategy: clone artifact directories only (e.g., `.claude/skills/**`) |
| **Deep Indexing** | Optional: index full artifact content for enhanced full-text search |
| **Tree SHA** | Git commit SHA of the repository tree; used for change detection |

---

## References

- SPIKE Document: `/docs/project_plans/SPIKEs/clone-based-artifact-indexing-spike.md`
- Git Sparse Checkout: https://git-scm.com/docs/git-sparse-checkout
- GitHub Rate Limits: https://docs.github.com/en/rest/rate-limit
- SQLite FTS5: https://www.sqlite.org/fts5.html
- Current Implementation: `skillmeat/api/routers/marketplace_sources.py` (lines 655-929)

---

## Appendix: Task Summary

### By Phase

| Phase | Tasks | Story Points | Duration |
|-------|-------|--------------|----------|
| 1: Foundation | 9 | 11 | 2-3 days |
| 2: Universal Clone | 12 | 22 | 3-4 days |
| 3: Optimization | 8 | 12 | 2-3 days |
| 4: Deep Indexing | 6 | 9 | 1-2 days |
| 5: Testing | 10 | 22 | 2 days |
| **TOTAL** | **45** | **76** | **10-14 days** |

*Note: Aggressive estimate 55-65 points accounts for integration complexity; conservative estimate 65-75 points recommended.*

### Critical Path Dependencies

```
Phase 1 (DB + CloneTarget)
  ↓
Phase 2 (Clone Infrastructure + Manifest Extraction)
  ↓
Phase 3 (Optimization + Robustness)
  ├→ Phase 4 (Deep Indexing) [can start after INTEGRATE-101]
  ↓
Phase 5 (Testing)
```

---

**Implementation Plan Version**: 1.0
**Last Updated**: 2026-01-24
**Status**: Ready for Review

