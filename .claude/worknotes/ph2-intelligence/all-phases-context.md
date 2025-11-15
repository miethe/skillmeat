# Phase 2 Intelligence - All Phases Context

**Purpose**: Token-efficient context for resuming work across AI turns for the entire PRD implementation

**Last Updated**: 2025-11-15

---

## Current State

**Branch**: `claude/phase2-intelligence-execution-014j6zeEN1wrTPbvY7J27o1w`
**Last Commit**: 159395c feat: implement upstream update execution
**Current Phase**: Phase 0 (Upstream Update Execution)
**Current Task**: Setting up tracking infrastructure

---

## Architecture Overview

Phase 2 builds on the existing SkillMeat collection core with four major subsystems:

1. **Diff/Merge Layer** (`skillmeat/core/diff_engine.py`, `merge_engine.py`)
   - Three-way diff for base/local/remote comparisons
   - Auto-merge with conflict detection
   - Git-style conflict markers

2. **Search Layer** (`skillmeat/core/search_manager.py`)
   - Metadata + content search with ripgrep acceleration
   - Cross-project indexing with caching
   - Similarity-based duplicate detection

3. **Sync Layer** (`skillmeat/core/sync_manager.py`)
   - Bi-directional project ↔ collection sync
   - Drift detection via `.skillmeat-deployed.toml`
   - Three strategies: overwrite/merge/fork

4. **Analytics Layer** (`skillmeat/storage/analytics_db.py`, `core/analytics_manager.py`)
   - SQLite event storage with WAL mode
   - Usage tracking for deploy/update/sync/remove
   - Reports: most/least used, cleanup suggestions

---

## Key Patterns & Standards

### SkillMeat Architecture (from CLAUDE.md)
- **Package Structure**: `skillmeat/` replaces `skillman/`
- **Data Models**: Artifact, Manifest, LockFile, SkillMetadata in `models.py`
- **GitHub Integration**: SkillSpec parsing (`user/repo/path[@version]`), GitHubClient
- **CLI Framework**: Click-based with Rich output (ASCII-compatible, no Unicode)
- **Atomic Operations**: Temp directories + atomic moves
- **Python Compatibility**: 3.9+ with conditional `tomllib`/`tomli` imports

### Testing Standards
- **Coverage Target**: ≥75% for new modules
- **Integration Tests**: Run in CI <5min
- **Fixtures**: Reusable under `tests/fixtures/phase2/`
- **Performance Assertions**: Diff <2s, Search <3s, Sync preview <4s

### Security & Safety
- **Temp File Cleanup**: Always clean on error
- **Analytics Opt-Out**: Must be functional and documented
- **PII Redaction**: User paths redacted in logs
- **Atomic Manifest Updates**: Temp file swap with fsync

---

## Critical Dependencies

### Phase Dependencies
- **Phase 0** → Phase 1: DiffEngine stub needed for strategy execution
- **Phase 1** → Phase 3: MergeEngine required for smart updates
- **Phase 3** → Phase 4: Sync events feed analytics
- **All Phases** → Phase 5: Integration tests require all modules
- **Phase 5** → Phase 6: Documentation needs complete implementation

### Module Dependencies
```
ArtifactManager.update
  ↓ requires
DiffEngine → MergeEngine
  ↓ used by
SyncManager → AnalyticsManager
```

---

## Environment Setup

### Current Development Environment
```bash
# Install in development mode
pip install -e ".[dev]"
# Or with uv (recommended)
uv tool install --editable .

# Run tests
pytest -v --cov=skillman --cov-report=xml

# Type checking
mypy skillman --ignore-missing-imports

# Format
black skillman
```

### Key Files Reference
- **Config**: `skillmeat/config.py` (ConfigManager, ~/.skillman/config.toml)
- **Models**: `skillmeat/models.py` (Skill, Manifest, LockFile, Metadata)
- **CLI**: `skillmeat/cli.py` (Click commands with Rich output)
- **GitHub**: `skillmeat/github.py` (SkillSpec, GitHubClient, SkillValidator)
- **Installer**: `skillmeat/installer.py` (SkillInstaller, atomic operations)

---

## Implementation Notes

### Subagent Delegation Strategy
Per command requirements, ALL implementation work must be delegated to specialized subagents:

- **python-backend-engineer**: Core Python logic, managers, utilities
- **backend-architect**: Design decisions, three-way diff, merge strategies
- **cli-engineer**: CLI commands, UX, Rich formatting
- **test-engineer**: Unit/integration tests, fixtures
- **data-layer-expert**: SQLite schema, migrations, analytics storage
- **search-specialist**: Search algorithms, indexing, duplicate detection
- **documentation-writer**: ALL documentation (guides, references, README)

### Documentation Restrictions
- **ONLY** ai-artifacts-engineer (documentation-writer) creates docs
- **NO** reports, summaries, or ad-hoc documentation
- **EXCEPTION**: Brief observation notes in `.claude/worknotes/observations/`

---

## Known Constraints & Gotchas

### From CLAUDE.md
1. **Python Version**: 3.9+ required; use conditional imports for `tomllib`
2. **Rich Output**: ASCII-compatible only, no Unicode box-drawing
3. **Atomic Operations**: Always use temp directories + atomic moves
4. **GitHub Rate Limits**: Encourage token usage for private repos
5. **Scopes**: User scope (~/.claude/skills/user/) vs local (./.claude/skills/)

### Performance Targets (PRD)
- Diff operations: <2s for 500 files
- Search operations: <3s for 500 artifacts
- Sync preview: <4s for 500 artifacts
- Analytics aggregations: <500ms for 10k events

### Security Checklist Items
- [ ] Temp files cleaned on error
- [ ] Analytics opt-out functional
- [ ] Logs redact user paths
- [ ] Manifest updates atomic (temp swap + fsync)
- [ ] No PII in telemetry

---

## Phase-Specific Context

### Phase 0: Upstream Update Execution
**Status**: Starting
**Key Deliverable**: Working `skillmeat update <artifact>` command

**Implementation Notes**:
- Closes F1.5 gap from Phase 1
- DiffEngine stub sufficient for initial strategies
- Must handle rollback on failure
- Strategy flag: `--strategy=overwrite|merge|prompt` (default: prompt)

**Files Expected**:
- skillmeat/core/artifact_manager.py (update methods)
- tests/test_update_flow.py

---

### Phase 1: Diff & Merge Foundations
**Status**: Pending Phase 0
**Key Deliverable**: DiffEngine + MergeEngine with CLI

**Implementation Notes**:
- DiffEngine handles text/binary files
- Three-way diff for base/local/remote
- Git-style conflict markers
- Handoff to Phase 3 for sync integration

**Critical Path**: Phase 3 (Sync) blocks on MergeEngine completion

---

### Phase 2: Search & Discovery
**Status**: Pending (parallel with Phase 1)
**Key Deliverable**: SearchManager + CLI commands

**Implementation Notes**:
- No blocking dependencies (read-only operations)
- Ripgrep acceleration optional (fallback to Python)
- Cross-project indexing with 60s TTL caching
- Duplicate detection: similarity threshold 0.85

**Parallel Work**: Can start alongside Phase 1

---

### Phase 3: Smart Updates & Sync
**Status**: Pending Phases 0 & 1
**Key Deliverable**: Bi-directional sync with strategies

**Implementation Notes**:
- Requires MergeEngine from Phase 1
- `.skillmeat-deployed.toml` tracks deployment state
- Three strategies: overwrite/merge/fork
- Dry-run support required

**Critical Path**: Blocks Phase 4 (Analytics needs sync events)

---

### Phase 4: Analytics & Insights
**Status**: Pending Phase 3
**Key Deliverable**: SQLite analytics with usage reports

**Implementation Notes**:
- WAL mode for concurrent access
- Event buffering with retry on failure
- Opt-out mechanism required
- Retention policy: configurable (default 90 days)

---

### Phase 5: Verification & Hardening
**Status**: Pending Phases 1-4
**Key Deliverable**: Integration tests + performance benchmarks

**Implementation Notes**:
- 500-artifact fixture dataset
- Integration tests run in CI <5min
- Performance benchmarks validate PRD targets
- Security checklist must be signed

---

### Phase 6: Documentation & Release
**Status**: Pending all prior phases
**Key Deliverable**: Complete docs + 0.2.0-alpha release

**Implementation Notes**:
- Four new guides (searching, updating, syncing, analytics)
- CHANGELOG with issue references
- Version bump in pyproject.toml
- Release tag: v0.2.0-alpha

---

## Session History

### 2025-11-15 - Session 1
**Focus**: Phase 0 remediation + Phase 1 kickoff

**Completed**:
- ✅ Created tracking infrastructure
- ✅ Validated Phase 0 (70% → 85% complete)
- ✅ Completed Phase 0 remediation:
  - test_update_flow.py integration suite (6 tests, 87% coverage)
  - DiffEngine stub for Phase 1
  - Atomic write fsync
  - Snapshot error logging
- ✅ Documented Phase 0 decision (functionally complete with known limitation)
- ✅ Implemented P1-001: DiffEngine scaffolding (exceeds performance requirements)

**Phase Status**:
- Phase 0: ✅ Functionally complete (snapshot-based recovery)
- Phase 1 P1-001: ✅ Complete (DiffEngine implemented)
- Phase 1 P1-002: ⏳ Next (Three-way diff)

**Commits**:
- 84a08e1: Phase 0 remediation (tests + infrastructure)
- 8faff78: Phase 0 completion decision
- 7afead1: P1-001 DiffEngine implementation

**Next Session**: Continue Phase 1 with P1-002 (Three-Way Diff) to python-backend-engineer

---

## Quick Reference Commands

```bash
# Run specific test
pytest tests/test_cli_core.py::test_function -v

# Full test suite with coverage
pytest -v --cov=skillman --cov-report=xml

# Code quality checks (pre-commit)
black skillman && \
  flake8 skillman --count --select=E9,F63,F7,F82 --show-source --statistics && \
  mypy skillman --ignore-missing-imports

# Build and check package
python -m build
twine check dist/*
```

---

## Open Questions & Decisions Needed

(None yet - will be populated during implementation)

---

## Handoff Notes Between Phases

(Will be populated as phases complete)

### Phase 0 → Phase 1
(Pending)

### Phase 1 → Phase 3
(Pending - DiffEngine/MergeEngine APIs)

### Phase 3 → Phase 4
(Pending - Sync event schema)
