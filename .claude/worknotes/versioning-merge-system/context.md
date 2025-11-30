# Context: Versioning & Merge System Implementation

**Date**: 2025-11-30
**PRD**: `/docs/project_plans/PRDs/enhancements/versioning-merge-system-v1.md`
**Implementation Plan**: `/docs/project_plans/implementation_plans/enhancements/versioning-merge-system-v1.md`
**Progress Tracking**: `.claude/progress/versioning-merge-system/all-phases-progress.md`

---

## Feature Overview

**Versioning & Merge System** provides robust artifact version management with intelligent three-way merge capabilities for the SkillMeat artifact collection manager.

### Core Capabilities

1. **Version History & Rollback**
   - Per-artifact version snapshots (not just collection-level)
   - Complete lineage from source to deployment
   - One-click rollback to any prior version
   - Preservation of subsequent non-conflicting changes during rollback

2. **Smart Three-Way Merge**
   - Automatic detection of local vs. upstream changes
   - Auto-merge of non-conflicting changes
   - Clear conflict detection (only true conflicts require user input)
   - Line-level merge for text files, file-level for binary

3. **Clear Visual Feedback**
   - Color-coded diff: Green (upstream only), Blue (local only), Red (conflicts)
   - Change type labels: "local change", "upstream update", "conflict"
   - Merge statistics: "{N} auto-merged, {M} conflicts, {K} unchanged"

4. **Cross-Level Sync Support**
   - Source → Collection merge (upstream pull)
   - Collection → Project merge (deploy with merge preview)
   - Project → Collection merge (pull local changes back)

---

## Technical Architecture Overview

### Storage Strategy (Phases 1-3)

**Directory Structure**:
```
~/.skillmeat/collection/artifacts/[name]/
├── latest/              # Current working version
│   ├── skill.py
│   ├── skill.md
│   └── ...
├── versions/
│   ├── v1-{hash}/       # Snapshot of version 1
│   │   ├── skill.py
│   │   ├── skill.md
│   │   └── ...
│   ├── v2-{hash}/
│   └── ...
└── .version.toml        # Version metadata (TOML)
```

**Version Metadata (TOML)**:
- `id`: Version identifier (v{n}-{hash})
- `timestamp`: When version was created (ISO 8601)
- `hash`: Content hash (SHA256) for deduplication
- `source`: Where version came from (source, upstream, deploy, merge, rollback)
- `files_changed`: List of modified files
- `change_summary`: Human-readable description
- `parent_versions`: For merge tracking (optional)
- `performed_by`: User/agent who created version (optional)

### Merge Engine (Phase 5)

**Three-Way Merge Algorithm**:
```
Inputs:  base (common ancestor), ours (local), theirs (remote)
Outputs: merged_files[], conflicts[], non_conflicts[]

Cases:
1. No changes in any direction → non_conflict
2. Only theirs changed → auto-merge with theirs
3. Only we changed → auto-merge with ours
4. Both changed → attempt line-level merge
   - Success: auto-merged
   - Failure: conflict (conflict markers)
```

**Change Classification**:
- `upstream_only`: File changed in theirs but not in ours → auto-merge
- `local_only`: File changed in ours but not in theirs → auto-merge
- `conflict`: File changed in both but different ways → user resolution needed
- `unchanged`: No changes in any direction → skip

### API Layer (Phase 7)

**Version Management Endpoints**:
- `GET /api/v1/artifacts/{id}/versions` → List all versions with pagination
- `GET /api/v1/artifacts/{id}/versions/{version_id}` → Get version metadata
- `GET /api/v1/artifacts/{id}/versions/{version_id}/files` → Get version content
- `GET /api/v1/artifacts/{id}/versions/{v1}/diff/{v2}` → Compare two versions
- `POST /api/v1/artifacts/{id}/versions/{version_id}/restore` → Restore to version

**Merge Endpoints**:
- `POST /api/v1/artifacts/{id}/merge/analyze` → Three-way merge analysis
- `POST /api/v1/artifacts/{id}/merge/preview` → Preview without applying
- `POST /api/v1/artifacts/{id}/merge/apply` → Apply merge with resolutions

### Frontend Components (Phases 8-9)

**History Tab**:
- `VersionTimeline`: Chronological list with metadata, actions
- `VersionContentViewer`: Read-only file viewer for past versions
- `VersionComparisonView`: Side-by-side diff between any two versions
- Restore button with confirmation dialog

**Merge UI**:
- `ColoredDiffViewer`: Three-way diff with color coding
- `MergePreview`: Shows what will merge before applying
- `MergeWorkflow`: Step-by-step guided workflow
- `ConflictResolver`: Integration with existing conflict resolver component

---

## Key Technical Decisions

### 1. Directory-Based Snapshots (Not Delta-Based)

**Why**: Simplicity, debuggability, no external dependencies
- Users can directly inspect versions on disk
- Git history integration not required
- Fast for typical artifact sizes (<10MB)
- Trade-off: Higher disk usage vs. simplicity

**Mitigation**: Compression (gzip/bzip2) + retention policies

### 2. Content-Addressed Version IDs

**Why**: Deterministic identification, idempotent, enables deduplication

Format: `v{n}-{hash}` where hash is first 8 chars of SHA256
- Sortable by version number
- Unique by content hash
- Enables tamper detection

### 3. Line-Level Merge for Text, File-Level for Binary

**Why**: Supports auto-merge of non-conflicting changes while handling binary safely

- Text files: Use line-level three-way merge (difflib-based)
- Binary files: Accept ours or theirs (no merge attempt)

### 4. Atomic Merge & Rollback Operations

**Why**: Prevents partial updates, no corruption on failure

- All-or-nothing semantics
- Simple recovery: retry entire operation
- No need for complex undo mechanisms

### 5. Automatic Version Capture on Sync/Deploy

**Why**: Complete audit trail, no user action required

- Triggered on successful sync/deploy
- Preserves full lineage
- Enables rollback from any state

---

## Dependencies & Constraints

### External Constraints
- **Python**: 3.9+ (existing requirement)
- **Existing Components**: conflict-resolver.tsx (reuse), DiffResult model (enhance)
- **Libraries**: Standard library sufficient (difflib, pathlib, toml/tomli)

### Internal Dependencies

**Sequence** (strict bottom-up architecture):
1. **Phase 1**: Storage infrastructure (foundation)
2. **Phase 2**: Repository CRUD (data access layer)
3. **Phase 3**: Repository comparisons (read operations)
4. **Phase 4**: Service layer - version management
5. **Phase 5**: Service layer - merge engine (builds on Phase 3)
6. **Phase 6**: Rollback & orchestration (combines Phase 4 & 5)
7. **Phase 7**: API layer (exposes Phase 4-6)
8. **Phase 8-9**: Frontend (consumes Phase 7 APIs)
9. **Phase 10**: Sync integration (wires Phase 7 into existing workflows)

**Critical Path**: Phase 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8/9 (parallel) → 10

### Risks & Mitigations

| Risk | Impact | Likelihood | Mitigation |
|------|--------|-----------|-----------|
| Merge algorithm incorrect → corrupt artifact | HIGH | LOW | Atomic operations, 50+ test scenarios, code review |
| Version storage bloats disk | MEDIUM | MEDIUM | Compression, retention policies (keep last 50 or 90 days) |
| Three-way merge confuses users | MEDIUM | MEDIUM | Color coding + labels, guided workflow, user testing |
| Large version histories slow UI | MEDIUM | LOW | Pagination, virtual scrolling, lazy loading |
| Rollback conflicts with later changes | HIGH | LOW | Rollback conflict detection, user confirmation |
| User accidentally restores wrong version | MEDIUM | MEDIUM | Confirmation dialog, clear version info, undo support |

---

## Feature Flags for Rollout

```python
# Core features
ENABLE_VERSION_HISTORY = True          # Per-artifact versioning
ENABLE_THREE_WAY_MERGE = True          # Smart merge algorithm
ENABLE_AUTO_MERGE = True               # Auto-merge non-conflicts

# UI features
ENABLE_MERGE_UI = True                 # Show merge workflow in UI
ENABLE_HISTORY_TAB = True              # Show History tab in modal

# Storage & retention
VERSION_RETENTION_DAYS = 90            # Keep versions for N days
VERSION_RETENTION_COUNT = 50           # Or keep last N versions
VERSION_COMPRESSION = "gzip"           # gzip, bzip2, or none

# Performance
VERSION_PAGE_SIZE = 20                 # Pagination size for lists
MERGE_TIMEOUT_SECONDS = 30             # Max time for merge operation
```

---

## Success Criteria (High-Level)

### Functional
- ✓ Per-artifact version snapshots created on sync/deploy
- ✓ History tab displays all versions chronologically
- ✓ Users can restore any prior version with one click
- ✓ Three-way merge detects changes in all directions
- ✓ Auto-merge handles non-conflicting changes
- ✓ Color-coded diff clearly shows local vs. upstream changes
- ✓ All sync directions (upstream, collection, project) support merge

### Performance
- ✓ Version history retrieval: <500ms for 100 versions
- ✓ Three-way merge: <2s for 10MB artifact
- ✓ Rollback: <1s (excluding I/O)
- ✓ Merge apply: <5s including storage

### Quality
- ✓ Unit test coverage: >85% across all layers
- ✓ 50+ merge algorithm test scenarios
- ✓ E2E tests for critical user paths
- ✓ No regressions in existing sync functionality
- ✓ WCAG 2.1 AA accessibility

---

## Session Handoff Notes

### For Incoming Agents

1. **Read the PRD First**: `/docs/project_plans/PRDs/enhancements/versioning-merge-system-v1.md`
   - Comprehensive problem context
   - User stories and journeys
   - All requirements and acceptance criteria

2. **Review Implementation Plan**: `/docs/project_plans/implementation_plans/enhancements/versioning-merge-system-v1.md`
   - Phase-by-phase breakdown
   - Detailed task descriptions with acceptance criteria
   - Task estimates and dependencies

3. **Check Progress File**: `.claude/progress/versioning-merge-system/all-phases-progress.md`
   - Current phase and task status
   - Which tasks are ready to start
   - Parallelization opportunities
   - Orchestration Quick Reference with Task() commands

4. **Architecture References**
   - Storage: `skillmeat/storage/snapshot.py` (extend for per-artifact)
   - Sync: `skillmeat/core/sync.py` (integrate three-way merge)
   - Diff: `skillmeat/models.py` (enhance DiffResult for three-way)
   - Conflict resolver: `skillmeat/web/components/collection/conflict-resolver.tsx` (reuse)

### Parallelization Opportunities

**After Phase 3 complete**:
- Phase 4 and 5 can run in parallel (service layer)
- Both depend on repository comparisons, not on each other

**After Phase 7 complete**:
- Phase 8 and 9 can run in parallel (frontend)
- Both depend on API contracts, not on each other

**During Phase 10**:
- Phase 11 (testing & documentation) can run in parallel
- Testing for Phase 10 code can proceed while integration continues

### Common Pitfalls to Avoid

1. **Don't skip Phase 1**: Storage design is foundation for everything
2. **Don't merge before Phase 3**: Merge engine depends on repository comparisons
3. **Don't wire sync (Phase 10) before Phase 9**: Need complete merge UI first
4. **Don't skip test scenarios**: 50+ merge test cases required for Phase 5 quality gate
5. **Don't create merge without rollback support**: Phase 6 rollback must be complete

### Communication Points

- **Phase 1 approval**: Confirm storage structure with data-layer-expert
- **Phase 5 review**: 50+ merge test scenarios reviewed by backend-architect
- **Phase 7 review**: OpenAPI spec reviewed before SDK generation
- **Phase 9 review**: ColoredDiffViewer UX reviewed with ui-engineer-enhanced
- **Phase 10 review**: Sync integration tested with existing workflows
- **Phase 11 review**: All documentation reviewed by documentation-writer

---

## Useful References

### Three-Way Merge Resources
- Git merge-base and three-way merge semantics
- Mercurial conflict markers format
- Python difflib module (already in stdlib)

### Storage References
- Content-addressed storage (CAS) concepts
- TOML configuration format
- Atomic file operations

### API Design References
- RESTful API conventions (existing in codebase)
- OpenAPI 3.0 specification
- Error response standardization

### Frontend References
- React components in `skillmeat/web/components/`
- Radix UI components (already in use)
- shadcn/ui patterns (already in use)

---

**Created**: 2025-11-30
**Last Updated**: 2025-11-30
**Status**: Ready for implementation
