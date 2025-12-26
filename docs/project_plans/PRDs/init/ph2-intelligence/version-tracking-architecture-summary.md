# Artifact Version Tracking - Architecture Summary

**Decision Date**: 2025-11-20
**Status**: Approved - Ready for Implementation
**Phase**: Phase 2 Intelligence

## Executive Summary

This document summarizes the architectural decisions and design for implementing comprehensive artifact version tracking and visualization in SkillMeat. The system will enable users to track modifications to deployed artifacts, visualize version relationships across projects, and make informed decisions about syncing changes.

## Core Architecture Decisions

### 1. Storage Strategy: TOML-First Approach

**Decision**: Use enhanced TOML storage for MVP, with SQLite migration path for scale.

**Rationale**:
- Maintains consistency with existing storage patterns
- Human-readable and inspectable
- No new dependencies for MVP
- Easy migration path to database if performance requires

**Implementation**:
- Extend `.skillmeat-deployed.toml` with version tracking fields
- Store version lineage as array of snapshots
- Compute content hashes on-demand for modification detection

### 2. Data Model: Content Hash-Based Versioning

**Decision**: Use SHA-256 content hashing for version identification and change detection.

**Key Models**:
```python
Deployment:
  - deployed_sha: str          # SHA at deployment time
  - current_sha: Optional[str] # Current SHA (computed)
  - local_modifications: bool  # Modification flag
  - version_lineage: List      # History of changes

ArtifactVersion:
  - content_sha: str           # Unique version identifier
  - parent_sha: Optional[str]  # Link to parent version
  - location_type: Literal["collection", "project"]

VersionGraphNode:
  - version: ArtifactVersion
  - children: List[VersionGraphNode]
  - metadata: Dict

VersionGraph:
  - root: VersionGraphNode     # Collection version (canonical)
  - statistics: Dict           # Aggregated stats
```

**Why Content Hashing**:
- Deterministic and repeatable
- Detects all content changes
- No dependency on timestamps (unreliable)
- Enables deduplication
- Standard cryptographic hashing (SHA-256)

### 3. Modification Detection: On-Demand + Lazy Evaluation

**Decision**: Check for modifications on-demand, with caching and periodic refresh options.

**Trigger Points**:
1. API read (when project details requested)
2. Explicit check via `/projects/{id}/check-modifications`
3. CLI commands (`skillmeat status`, `skillmeat sync --check`)
4. Optional background job (Phase 3)

**Performance Optimization**:
- Cache results for 5 minutes
- Debounce checks (max 1/minute per project)
- Parallel processing for multiple artifacts
- Skip unchanged files using metadata (timestamp + size)

### 4. Version Graph: Tree Structure with Orphan Handling

**Decision**: Represent versions as a tree rooted at the collection artifact, with orphan nodes for deployments without parent.

**Graph Structure**:
```
Collection (root)
├─ Project A (modified)
│  └─ [SHA: abc123 → def456]
├─ Project B (synced)
│  └─ [SHA: abc123 → abc123]
└─ Project C (modified)
   └─ [SHA: abc123 → ghi789]

Orphaned:
└─ Project D (no parent in collection)
   └─ [SHA: jkl012]
```

**Why Trees**:
- Natural parent-child relationship
- Easy traversal and statistics computation
- Scalable to hundreds of deployments
- Clear visualization path

### 5. API Design: RESTful with Graph Endpoints

**New Endpoints**:

#### Check Modifications
```
POST /api/v1/projects/{project_id}/check-modifications
```
Scans all deployments in a project and updates modification status.

#### Get Version Graph
```
GET /api/v1/artifacts/{artifact_id}/version-graph?collection={name}
```
Returns complete version tree for an artifact.

#### Enhanced Artifact Response
```
GET /api/v1/artifacts/{artifact_id}?include_deployments=true
```
Adds deployment statistics to artifact detail.

**Design Principles**:
- RESTful resource-based URLs
- Cursor-based pagination where needed
- Caching headers (Cache-Control, ETag)
- Rate limiting (1 req/min for heavy operations)
- Standard error responses (ErrorResponse envelope)

### 6. Frontend State: React Query + Zustand

**Decision**: Use React Query for server state, Zustand for UI state.

**React Query** (Server State):
- Version graphs (5-minute stale time)
- Modification checks (1-minute stale time)
- Deployment lists
- Automatic refetch on window focus
- Optimistic updates

**Zustand** (UI State):
- Selected node in version tree
- Expanded/collapsed nodes
- View mode (tree/list/graph)
- Filter settings
- Persisted in localStorage

**Why This Split**:
- Clear separation of concerns
- React Query handles caching, refetch, errors
- Zustand handles ephemeral UI state
- Minimal boilerplate
- Type-safe

### 7. Visualization: Tree View as Primary, Graph as Enhancement

**Decision**: Implement tree view first (MVP), add graph visualization later (Phase 3).

**Tree View Features**:
- Expandable/collapsible nodes
- Status badges (modified/synced/outdated)
- Color coding (yellow=modified, green=synced, red=outdated)
- Hover tooltips (SHA, timestamps, project info)
- Search/filter
- Export to JSON/CSV

**Future Graph View** (Phase 3):
- D3.js or Vis.js network diagram
- Interactive force-directed layout
- Zoom/pan/drag
- Node clustering for large graphs

**Why Tree First**:
- Simpler to implement
- Better for linear relationships
- More familiar UX pattern
- Sufficient for most use cases (1 artifact → N projects)

## Critical Design Patterns

### Pattern 1: Content Hash as Immutable Version ID

```python
def compute_content_hash(path: Path) -> str:
    """Compute SHA-256 hash of all content in path."""
    hasher = hashlib.sha256()
    for file_path in sorted(path.rglob("*")):
        if file_path.is_file():
            hasher.update(file_path.read_bytes())
    return hasher.hexdigest()
```

**Benefits**:
- Content changes always detected
- No false positives from timestamp updates
- Deduplication possible (same hash = same content)
- Cryptographically secure

### Pattern 2: Version Lineage as Audit Trail

```toml
[[deployed.version_lineage]]
sha = "abc123"
timestamp = "2025-11-20T10:30:00Z"
note = "Initial deployment"

[[deployed.version_lineage]]
sha = "def456"
timestamp = "2025-11-20T15:45:00Z"
note = "Local modifications detected"
```

**Benefits**:
- Full history of version changes
- Rollback capability (future)
- Audit trail for compliance
- Debug aid for troubleshooting

### Pattern 3: Lazy Graph Construction

```python
def build_graph(artifact_name, artifact_type):
    # Only build graph when explicitly requested
    # Cache result for 5 minutes
    # Parallel scan of projects
    # Early exit if no deployments found
```

**Benefits**:
- No background overhead
- Fast for simple queries
- Scales to large project counts
- Cacheable

### Pattern 4: Optimistic UI Updates

```typescript
const { mutate: checkModifications } = useMutation({
  mutationFn: () => checkProjectModifications(projectId),
  onMutate: () => {
    // Show loading state immediately
    queryClient.setQueryData(
      versionKeys.projectModifications(projectId),
      (old) => ({ ...old, checking: true })
    )
  },
  onSuccess: (data) => {
    // Update cache with new data
    queryClient.setQueryData(
      versionKeys.projectModifications(projectId),
      data
    )
  }
})
```

**Benefits**:
- Instant feedback
- Better perceived performance
- Graceful error handling
- Standard React Query pattern

## Security Considerations

### Path Traversal Prevention

All artifact names validated in `Artifact.__post_init__()`:
```python
if "/" in self.name or "\\" in self.name:
    raise ValueError("Invalid artifact name")
if ".." in self.name:
    raise ValueError("Invalid artifact name")
```

### Authentication & Authorization

- All API endpoints require API key
- Rate limiting on heavy operations
- User-scoped data access
- No cross-user data leakage

### Content Hash Integrity

- SHA-256 is cryptographically secure
- Collision probability negligible
- Tamper detection built-in
- No plaintext storage of sensitive data

## Performance Characteristics

### Time Complexity

| Operation | Complexity | Target |
|-----------|-----------|--------|
| Compute artifact hash | O(n) files | <50ms |
| Check single deployment | O(1) | <10ms |
| Check all deployments (project) | O(m) artifacts | <100ms |
| Build version graph | O(p) projects | <500ms |
| Render version tree (UI) | O(n) nodes | <200ms |

### Space Complexity

| Data | Size | Storage |
|------|------|---------|
| Deployment record | ~1KB | TOML file |
| Version lineage entry | ~100B | TOML array |
| Version graph (100 projects) | ~50KB | Memory cache |
| UI state | ~5KB | localStorage |

### Scaling Limits

- **Sweet spot**: 1-100 projects
- **Acceptable**: 100-1000 projects (with indexing)
- **Requires enhancement**: 1000+ projects (SQLite migration)

## Migration Strategy

### Phase 1: Backward-Compatible Extension

1. Add new fields to `Deployment` with Optional types
2. Existing TOML files auto-migrate on read
3. Write new files with v2 format
4. Backup original files before migration

### Phase 2: Data Enrichment

1. Compute initial `current_sha` for existing deployments
2. Set `deployed_sha = collection_sha` (rename)
3. Initialize empty version lineage
4. Run modification check to populate current state

### Phase 3: SQLite Migration (If Needed)

1. Export TOML to SQLite database
2. Maintain dual read path (TOML + SQLite)
3. Gradually migrate queries to SQLite
4. Deprecate TOML for version tracking
5. Keep TOML for deployment metadata

## Testing Strategy

### Unit Tests (90%+ Coverage)

- Data model serialization/deserialization
- Version graph construction logic
- Modification detection algorithms
- Content hash computation
- API endpoint handlers

### Integration Tests (80%+ Coverage)

- End-to-end deployment → modification → detection flow
- API contracts and error handling
- Database operations and migrations
- Cross-component interactions

### Performance Tests

- Version graph with 100 projects (<500ms)
- Modification check on 50 artifacts (<5s)
- Concurrent API requests (10 simultaneous)
- Memory leak detection (no leaks)

### UI Tests

- Component rendering
- User interactions
- Visual regression
- Accessibility (WCAG 2.1 AA)

## Risks and Mitigations

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Performance degradation (many projects) | High | Medium | Caching, lazy loading, parallel processing, SQLite migration path |
| False positives in modification detection | High | Low | Content hashing is deterministic, comprehensive testing |
| Complex UI confuses users | Medium | Medium | User testing, tooltips, progressive disclosure, documentation |
| Migration breaks existing data | Critical | Low | Backup strategy, dry-run mode, rollback plan, extensive testing |
| Race conditions (concurrent checks) | Medium | Medium | File locking, atomic updates, debouncing, idempotent operations |

## Success Metrics

### Functional Requirements

- [ ] 99%+ accuracy in modification detection
- [ ] Version graph generation <500ms (100 projects)
- [ ] UI rendering <200ms
- [ ] Zero data loss during migration
- [ ] All API endpoints functional

### User Experience

- [ ] Beta user satisfaction >8/10
- [ ] Feature adoption >70% within 1 month
- [ ] Support tickets <5 per week
- [ ] Documentation completeness score >90%

### Technical Quality

- [ ] Unit test coverage >90%
- [ ] Integration test coverage >80%
- [ ] Zero critical bugs
- [ ] Accessibility WCAG 2.1 AA compliant
- [ ] API response time p95 <500ms

## Next Steps for Implementation

### Immediate (Week 1)

1. **Extend Deployment Model** → `backend-typescript-architect`
2. **Create Version Models** → `backend-typescript-architect`
3. **Migration Script** → `data-layer-expert`
4. **Update DeploymentTracker** → `data-layer-expert`

### Week 2

1. **Modification Detection** → `backend-typescript-architect`
2. **Version Graph Builder** → `backend-typescript-architect`

### Week 3

1. **API Schemas** → `backend-typescript-architect`
2. **API Endpoints** → `backend-typescript-architect`

### Week 4

1. **API Client & Hooks** → `frontend-architect`
2. **UI Components** → `ui-engineer`
3. **Integration** → `ui-engineer`

### Week 5

1. **Testing** → `debugger`
2. **Documentation** → `documentation-writer` (Haiku 4.5)
3. **Beta Testing** → `QA team`

## References

### Documentation

- **ADR-004**: `/Users/miethe/dev/homelab/development/skillmeat/docs/dev/architecture/decisions/004-artifact-version-tracking.md`
- **Implementation Plan**: `/Users/miethe/dev/homelab/development/skillmeat/docs/project_plans/ph2-intelligence/artifact-version-tracking-implementation-plan.md`

### Existing Code

- **Deployment Tracking**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/storage/deployment.py`
- **Artifact Models**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/core/artifact.py`
- **API Schemas**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/schemas/`

### Related Features

- Phase 1 Deployment System
- Phase 2 Diff Engine
- Phase 2 Smart Updates
- Phase 3 Web Interface

---

**Approval**: Lead Architect
**Date**: 2025-11-20
**Status**: Ready for Specialist Delegation
