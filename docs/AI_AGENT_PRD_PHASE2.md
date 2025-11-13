# SkillMeat Phase 2 PRD: Intelligence & Sync
## Product Requirements Document for AI Agent Implementation

**Version:** 2.0
**Date:** 2025-11-09
**Target:** AI Agent Teams
**Duration:** 6 weeks (Weeks 9-14)
**Status:** Ready for Implementation

---

## Executive Summary

This PRD defines Phase 2 of SkillMeat, focusing on **Intelligence & Sync** features that transform the collection manager into a bidirectional, intelligent system. This document is optimized for AI agent teams working in parallel.

**Key Deliverables:**
- Cross-project search and discovery
- Smart updates with three-way merge
- Bidirectional sync (project → collection)
- Usage analytics and insights

**Prerequisites:** Complete F1.5 (update execution) from Phase 1 before starting Phase 2.

---

## Phase 1 Status: 85% Complete

### Critical Gap to Address First

**F1.5 Upstream Tracking - Update Execution NOT IMPLEMENTED**

**Current State:**
- ✅ `check_updates()` works - detects available updates
- ❌ `update()` raises `NotImplementedError`
- ❌ Cannot apply updates from upstream

**Required Before Phase 2:**
```python
# Location: skillmeat/core/artifact.py line 559
def update(self, artifact_name: str, collection_name: str, strategy: str = "prompt") -> Artifact:
    """Update artifact from upstream."""
    # IMPLEMENT THIS:
    # 1. Fetch latest version from upstream
    # 2. Check for local modifications
    # 3. Apply update strategy (prompt/overwrite/merge)
    # 4. Update collection and lock file
    # 5. Return updated artifact
```

**Estimated Effort:** 2-3 days
**Priority:** CRITICAL - Blocks Phase 2 smart updates

---

## Phase 2 Features Overview

### F2.1: Cross-Project Search
**Value:** Discover artifacts across all collections and projects
**Use Case:** "Where did I use that security scanning agent?"

### F2.2: Usage Analytics
**Value:** Understand which artifacts are valuable, which are unused
**Use Case:** "Which commands do I actually use? Clean up clutter"

### F2.3: Smart Updates
**Value:** Merge upstream changes with local modifications
**Use Case:** "Get updates without losing my customizations"

### F2.4: Collection Sync
**Value:** Pull project improvements back to collection
**Use Case:** "I improved this in my project, add it to collection"

---

## Agent Assignments & Parallelization

### Agent 1: Diff & Merge Specialist
**Duration:** Weeks 9-12 (4 weeks)
**Focus:** Core diff and merge algorithms
**Dependencies:** None (standalone utilities)

**Deliverables:**
- `skillmeat/utils/diff.py` (~300 LOC)
- `skillmeat/core/merge.py` (~250 LOC)
- Three-way merge with conflict detection
- CLI `diff` command
- Test suite (test_diff.py, test_merge.py)

**Tasks:**
1. Week 9: Implement DiffEngine
   - File diff using difflib.unified_diff()
   - Directory diff with recursion
   - Rich formatting for terminal display
2. Week 10: Three-way diff foundation
   - Detect auto-mergeable changes
   - Identify conflicts
3. Week 11: MergeEngine implementation
   - Three-way merge algorithm
   - Conflict marker generation
4. Week 12: Conflict resolution UI
   - Interactive editor integration
   - Validation and testing

### Agent 2: Search & Discovery
**Duration:** Weeks 9-10 (2 weeks)
**Focus:** Search functionality
**Dependencies:** None (read-only operations)

**Deliverables:**
- `skillmeat/core/search.py` (~350 LOC)
- Search collection and projects
- Duplicate detection
- CLI search commands
- Test suite (test_search.py)

**Tasks:**
1. Week 9: SearchManager implementation
   - Content search (try ripgrep, fallback to Python)
   - Metadata search (tags, description)
   - Result ranking and scoring
2. Week 10: Advanced features
   - Cross-project search
   - Duplicate detection algorithm
   - Fuzzy matching
   - CLI integration

### Agent 3: Sync & Updates
**Duration:** Weeks 11-13 (3 weeks)
**Focus:** Bidirectional sync and smart updates
**Dependencies:** DiffEngine (from Agent 1)

**Deliverables:**
- `skillmeat/core/sync.py` (~400 LOC)
- Enhanced update implementation
- Bidirectional sync logic
- CLI sync commands
- Test suite (test_sync.py)

**Tasks:**
1. Week 11: Complete F1.5 update execution
   - Implement ArtifactManager.update()
   - Integrate with MergeEngine
   - Handle update strategies
2. Week 12: Smart update workflow
   - Preview updates with diff
   - Interactive strategy selection
   - Rollback on failure
3. Week 13: SyncManager implementation
   - Detect project modifications
   - Pull changes to collection
   - Sync strategies (overwrite/merge/fork)

### Agent 4: Analytics & Integration
**Duration:** Weeks 13-14 (2 weeks)
**Focus:** Analytics system and final integration
**Dependencies:** All other modules

**Deliverables:**
- `skillmeat/core/analytics.py` (~300 LOC)
- SQLite analytics database
- Usage reports and insights
- Integration tests
- Documentation updates

**Tasks:**
1. Week 13: AnalyticsManager
   - SQLite schema setup
   - Event tracking system
   - Statistics computation
2. Week 14: Integration & polish
   - Analytics CLI commands
   - End-to-end integration tests
   - Documentation updates
   - Performance validation

---

## Technical Specifications

### New Modules Structure

```
skillmeat/
├── core/
│   ├── search.py         # NEW - Agent 2
│   ├── merge.py          # NEW - Agent 1
│   ├── sync.py           # ENHANCE - Agent 3 (currently empty)
│   └── analytics.py      # NEW - Agent 4
└── utils/
    └── diff.py           # NEW - Agent 1
```

### Data Models

#### DiffResult
```python
@dataclass
class DiffResult:
    files_added: List[str]
    files_removed: List[str]
    files_modified: List[FileDiff]
    total_additions: int
    total_deletions: int
    is_identical: bool

@dataclass
class FileDiff:
    path: str
    additions: int
    deletions: int
    diff_text: str  # Unified diff format
```

#### SearchResult
```python
@dataclass
class SearchResult:
    artifact: Artifact
    match_type: MatchType  # METADATA, CONTENT, TAG
    match_location: str
    match_line: Optional[int]
    context: str
    score: float
```

#### SyncStrategy & Result
```python
class SyncStrategy(str, Enum):
    OVERWRITE = "overwrite"
    MERGE = "merge"
    FORK = "fork"
    PROMPT = "prompt"

@dataclass
class SyncResult:
    success: bool
    artifact_name: str
    changes_applied: bool
    conflicts: List[str]
    diff_summary: Optional[DiffResult]
```

#### Analytics Models
```python
@dataclass
class ArtifactStats:
    name: str
    deploy_count: int
    project_count: int
    last_deployed: Optional[datetime]
    modification_rate: float

@dataclass
class UsageReport:
    period_days: int
    total_deployments: int
    most_used: List[Tuple[str, int]]
    never_used: List[str]
```

### Database Schema (SQLite)

```sql
CREATE TABLE artifact_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    artifact_name TEXT NOT NULL,
    artifact_type TEXT NOT NULL,
    event_type TEXT NOT NULL,  -- 'deploy', 'update', 'remove'
    project_path TEXT,
    collection_name TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE deployment_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    artifact_name TEXT NOT NULL,
    project_path TEXT NOT NULL,
    event_type TEXT NOT NULL,  -- 'initial', 'modify', 'sync'
    modification_detected BOOLEAN DEFAULT 0,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_artifact_events_name ON artifact_events(artifact_name);
CREATE INDEX idx_deployment_events_artifact ON deployment_events(artifact_name);
```

---

## API Specifications for Agents

### DiffEngine API (Agent 1)

```python
class DiffEngine:
    @staticmethod
    def diff_files(file1: Path, file2: Path, context_lines: int = 3) -> FileDiff:
        """Generate unified diff between two files using difflib."""

    @staticmethod
    def diff_directories(dir1: Path, dir2: Path,
                        ignore_patterns: Optional[List[str]] = None) -> DiffResult:
        """Recursively compare directories."""

    @staticmethod
    def three_way_diff(base: Path, local: Path, remote: Path) -> ThreeWayDiffResult:
        """Perform three-way diff for merge analysis."""

    @staticmethod
    def format_unified(diff_result: DiffResult) -> str:
        """Format as unified diff."""

    @staticmethod
    def format_rich(diff_result: DiffResult) -> rich.Text:
        """Format with Rich for terminal display."""
```

**Implementation Notes:**
- Use `difflib.unified_diff()` for text files
- Handle binary files (skip with message)
- Respect .gitignore patterns in directory diff
- Generate addition/deletion statistics

### SearchManager API (Agent 2)

```python
class SearchManager:
    def __init__(self, config: ConfigManager):
        self.config = config
        self.use_ripgrep = shutil.which("rg") is not None

    def search_collection(self, query: str,
                         scope: SearchScope = SearchScope.ALL) -> List[SearchResult]:
        """Search within collection artifacts."""

    def search_projects(self, query: str,
                       project_paths: Optional[List[Path]] = None) -> List[SearchResult]:
        """Search deployed artifacts in projects."""

    def find_duplicates(self, similarity_threshold: float = 0.95) -> List[Tuple[Artifact, Artifact, float]]:
        """Find duplicate or similar artifacts by content hash."""
```

**Implementation Notes:**
- Try `subprocess` call to `rg` if available
- Fallback to Python `re` + `Path.rglob()`
- Cache results for 60 seconds
- Limit to 100 results by default

### MergeEngine API (Agent 1)

```python
class MergeEngine:
    def __init__(self, diff_engine: DiffEngine):
        self.diff_engine = diff_engine

    def can_auto_merge(self, base: Path, local: Path, remote: Path) -> bool:
        """Check if automatic merge is possible without conflicts."""

    def merge(self, base: Path, local: Path, remote: Path,
             strategy: MergeStrategy = MergeStrategy.AUTO) -> MergeResult:
        """Perform three-way merge."""

    def create_conflict_markers(self, base: Path, local: Path,
                               remote: Path, output: Path) -> None:
        """Generate file with Git-style conflict markers."""
```

**Merge Algorithm:**
```
1. diff_local = diff(base, local)
2. diff_remote = diff(base, remote)
3. For each chunk:
   a. If only local changed: apply local
   b. If only remote changed: apply remote
   c. If both changed identically: apply once
   d. If both changed differently: CONFLICT
4. If no conflicts: auto-merge success
5. If conflicts: generate conflict markers
```

### SyncManager API (Agent 3)

```python
class SyncManager:
    def __init__(self, collection_mgr: CollectionManager):
        self.collection_mgr = collection_mgr
        self.diff_engine = DiffEngine()

    def detect_changes(self, project_path: Path) -> List[ArtifactChange]:
        """Detect all modified artifacts in project by comparing hashes."""

    def sync_from_project(self, artifact_name: str, artifact_type: ArtifactType,
                         project_path: Path,
                         strategy: SyncStrategy = SyncStrategy.PROMPT) -> SyncResult:
        """Pull changes from project to collection."""

    def preview_sync(self, artifact_name: str, project_path: Path) -> SyncPreview:
        """Show diff before syncing."""
```

**Sync Workflow:**
```
1. Read .skillmeat-deployed.toml
2. For each artifact, compare current hash vs deployment SHA
3. If different: mark as modified
4. User selects artifact to sync
5. Show diff (collection vs project)
6. User chooses strategy
7. Apply strategy
8. Update collection manifest and lock
```

### AnalyticsManager API (Agent 4)

```python
class AnalyticsManager:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self._init_schema()

    def track_event(self, event_type: EventType, artifact_name: str, **kwargs) -> None:
        """Record analytics event."""

    def get_usage_report(self, days: int = 30) -> UsageReport:
        """Generate usage summary for period."""

    def suggest_cleanup(self, unused_threshold_days: int = 90) -> List[str]:
        """Suggest artifacts for removal based on usage."""
```

**Event Types:**
- `DEPLOY`: Artifact deployed to project
- `UPDATE`: Artifact updated from upstream
- `MODIFY`: Deployed artifact modified
- `SYNC`: Artifact synced back to collection
- `REMOVE`: Artifact removed

---

## CLI Commands Specification

### New Commands for Phase 2

```bash
# Diff commands
skillmeat diff <artifact> [project-path]     # Show diff between collection and project
skillmeat diff <artifact> --upstream         # Show diff between local and upstream

# Search commands
skillmeat search <query>                     # Search in collection
skillmeat search <query> --projects          # Search across projects
skillmeat find-duplicates                    # Find duplicate artifacts

# Enhanced update (F1.5 completion)
skillmeat update <artifact>                  # Smart update with merge
skillmeat update <artifact> --strategy merge # Specify strategy
skillmeat update --all                       # Update all outdated

# Sync commands
skillmeat sync check                         # List modified artifacts in projects
skillmeat sync pull <artifact> --from <project>  # Pull changes to collection
skillmeat sync preview <artifact> <project>  # Preview sync diff

# Analytics commands
skillmeat analytics                          # Show overall usage stats
skillmeat analytics <artifact>               # Show artifact-specific stats
skillmeat analytics --export output.json    # Export analytics data
```

---

## Testing Requirements

### Test Coverage Target: >75% for new modules

### Unit Tests Required

**test_diff.py** (~200 LOC)
- Identical files → no diff
- File with additions/deletions/modifications
- Directory comparison
- Binary file handling
- Three-way diff scenarios

**test_search.py** (~150 LOC)
- Exact match in metadata
- Regex match in content
- Fuzzy matching
- Cross-project search
- Performance with 100+ artifacts

**test_merge.py** (~250 LOC)
- Auto-merge (no conflicts)
- Local-only changes
- Remote-only changes
- Conflicting changes
- Conflict marker generation

**test_sync.py** (~200 LOC)
- Detect modifications
- Pull clean changes
- Handle merge conflicts
- Preview functionality
- Strategy selection

**test_analytics.py** (~150 LOC)
- Track events
- Generate reports
- Calculate statistics
- Export/import data

### Integration Tests Required

**test_update_flow.py**
- Deploy → modify → upstream updates → update triggers merge → resolve conflicts

**test_sync_flow.py**
- Deploy → improve in project → detect → preview → pull to collection → redeploy

**test_search_across_projects.py**
- Search finds artifacts in multiple locations
- Duplicate detection works

### Performance Benchmarks

| Operation | Target | Test Method |
|-----------|--------|-------------|
| Search 100 artifacts | <1s | Time `search_collection()` |
| Diff large file (1000 lines) | <500ms | Time `diff_files()` |
| Sync check 10 projects | <3s | Time `detect_changes()` |
| Analytics query | <100ms | Time `get_usage_report()` |

---

## Implementation Timeline

### Week 9: Diff Foundation
**Agent 1 Focus**
- Day 1-2: DiffEngine implementation
- Day 3: CLI diff command
- Day 4-5: Three-way diff foundation

**Agent 2 Focus**
- Day 1-3: SearchManager implementation
- Day 4-5: CLI search commands

**Milestone:** Diff and search functional

### Week 10: Search & Discovery
**Agent 2 Focus**
- Day 1-2: Cross-project search
- Day 3-5: Duplicate detection

**Agent 1 Focus**
- Testing and refinement

**Milestone:** Search complete, ready for integration

### Week 11: Merge Engine
**Agent 1 Focus**
- Day 1-3: MergeEngine implementation
- Day 4-5: Auto-merge detection

**Agent 3 Focus**
- Day 1-2: F1.5 update execution basic implementation
- Day 3-5: Integrate with MergeEngine

**Milestone:** Merge engine working, update execution started

### Week 12: Smart Updates
**Agent 3 Focus**
- Day 1-3: Complete update command with merge support
- Day 4-5: Interactive conflict resolution

**Agent 1 Focus**
- Conflict resolution UI
- Testing edge cases

**Milestone:** Smart updates fully functional

### Week 13: Bidirectional Sync
**Agent 3 Focus**
- Day 1-3: SyncManager implementation
- Day 4-5: Sync CLI commands

**Agent 4 Focus**
- Day 1-2: Analytics schema setup
- Day 3-5: AnalyticsManager core implementation

**Milestone:** Sync working, analytics started

### Week 14: Analytics & Polish
**Agent 4 Focus**
- Day 1-2: Analytics CLI commands
- Day 3-4: Integration testing
- Day 5: Documentation updates

**All Agents:**
- Code review and cleanup
- Performance testing
- Documentation review

**Milestone:** Phase 2 complete and ready for release

---

## Success Criteria

### Feature Completeness
- ✅ F2.1: Cross-project search works
- ✅ F2.2: Usage analytics tracks events
- ✅ F2.3: Smart updates with merge
- ✅ F2.4: Bidirectional sync functional

### Quality Gates
- Test coverage >75% for new modules
- All integration tests passing
- Performance benchmarks met
- No critical bugs
- Documentation complete

### User Acceptance
- Can search and find artifacts across projects
- Can update with local modifications safely
- Can pull improvements back to collection
- Can view usage statistics
- Conflict resolution is clear and intuitive

---

## Risk Mitigation

### High-Risk Areas

**1. Merge Algorithm Correctness**
- **Risk:** Merge corrupts artifacts
- **Mitigation:**
  - Always create snapshot before merge
  - Extensive test suite with edge cases
  - Show preview before applying
  - Atomic operations with rollback

**2. Sync State Consistency**
- **Risk:** Collection and project states diverge
- **Mitigation:**
  - Use lock files during sync
  - Validate before and after
  - Provide `skillmeat doctor` command to fix issues

**3. Performance with Large Collections**
- **Risk:** Search/sync slow with 100+ artifacts
- **Mitigation:**
  - Add indexing if needed
  - Lazy loading
  - Progress indicators
  - Cancellation support

### Medium-Risk Areas

**4. Cross-Platform Compatibility**
- **Risk:** Windows path handling breaks
- **Mitigation:**
  - Use pathlib consistently
  - Test on Windows CI
  - Platform-specific handling where needed

**5. User Workflow Complexity**
- **Risk:** Too many prompts confuse users
- **Mitigation:**
  - Sensible defaults
  - `--yes` flags for automation
  - Clear, actionable messages

---

## Agent Communication Protocol

### Handoff Points

**Week 10 End:**
- Agent 1 → Agent 3: DiffEngine API ready
- Agent 2: SearchManager standalone complete

**Week 12 End:**
- Agent 1 → Agent 3: MergeEngine API ready
- Agent 3: Update implementation ready for integration

**Week 13 End:**
- Agent 3 → Agent 4: SyncManager API ready
- All: Ready for integration testing

### Shared Resources

**Test Fixtures:**
```
tests/fixtures/phase2/
├── sample_skills/
├── sample_commands/
├── sample_agents/
├── modified_versions/
└── conflict_scenarios/
```

**Documentation Templates:**
- API documentation format
- Test documentation format
- User guide format

### Coordination Meetings (Async)

- **Monday:** Week kickoff, task alignment
- **Wednesday:** Mid-week sync, blocker resolution
- **Friday:** Progress review, next week preview

---

## Documentation Requirements

### For Each Module

**Agent Deliverables:**
1. **Module documentation** - Docstrings with examples
2. **API reference** - All public methods documented
3. **Test documentation** - What scenarios are covered
4. **User guide** - How to use new features

### Final Documentation (Agent 4)

- `docs/phase2-features.md` - Overview
- `docs/guides/searching.md` - Search guide
- `docs/guides/updating-safely.md` - Update guide
- `docs/guides/syncing-changes.md` - Sync guide
- `docs/guides/using-analytics.md` - Analytics guide
- Update `docs/commands.md` with new commands
- Update `README.md` with Phase 2 highlights

---

## Definition of Done

### For Each Feature

- [ ] Code implemented with type hints
- [ ] Unit tests written and passing (>75% coverage)
- [ ] Integration tests passing
- [ ] Documentation complete
- [ ] Code reviewed (by other agent if possible)
- [ ] Performance benchmarks met
- [ ] CLI help text written

### For Phase 2 Release

- [ ] All four features complete
- [ ] F1.5 gap closed (update execution)
- [ ] All tests passing (unit + integration)
- [ ] Performance targets met
- [ ] Documentation comprehensive
- [ ] Migration guide for Phase 1 → Phase 2
- [ ] CHANGELOG.md updated
- [ ] Version bumped to 0.2.0-alpha

---

## Appendix: Quick Reference

### Agent Workload Summary

| Agent | Weeks | Focus | LOC | Tests | Priority |
|-------|-------|-------|-----|-------|----------|
| Agent 1 | 9-12 (4w) | Diff & Merge | ~550 | ~450 | High |
| Agent 2 | 9-10 (2w) | Search | ~350 | ~150 | Medium |
| Agent 3 | 11-13 (3w) | Sync & Updates | ~600 | ~200 | High |
| Agent 4 | 13-14 (2w) | Analytics | ~300 | ~150 | Medium |

### Critical Path

```
Week 9: Agent 1 (DiffEngine) + Agent 2 (SearchManager)
  ↓
Week 10: Agent 1 (Three-way diff) + Agent 2 (Complete)
  ↓
Week 11: Agent 1 (MergeEngine) + Agent 3 starts (needs DiffEngine)
  ↓
Week 12: Agent 3 (Update + Sync) depends on MergeEngine
  ↓
Week 13: Agent 3 (Complete) + Agent 4 starts
  ↓
Week 14: Agent 4 (Integration) needs all modules
```

### Key Dependencies

- Agent 3 depends on Agent 1 (DiffEngine, MergeEngine)
- Agent 4 depends on all agents (integration testing)
- No other blocking dependencies

---

**Document Status:** Ready for Agent Team Implementation
**Next Action:** Assign agents to workstreams and begin Week 9
**Contact:** Technical lead for questions and coordination

**END OF PRD**
