# Artifact Version Tracking - Implementation Plan

**Status**: Ready for Implementation
**Priority**: High
**Phase**: Phase 2 Intelligence
**Estimated Duration**: 5 weeks
**Target Completion**: 2025-12-25

## Overview

Implement comprehensive version tracking and visualization for artifacts deployed across projects. This enables users to:
- See which projects have modified versions of their collection artifacts
- Visualize version relationships in a tree/graph view
- Automatically detect when deployed artifacts are modified
- Track version lineage and history
- Make informed decisions about syncing changes

## Prerequisites

- Phase 1 MVP completed (Collection management, deployment system)
- Existing deployment tracking via `.skillmeat-deployed.toml`
- Content hashing utility in place (`compute_content_hash`)
- API and web interface functional

## Architecture Reference

See ADR-004: `/Users/miethe/dev/homelab/development/skillmeat/docs/architecture/decisions/004-artifact-version-tracking.md`

## Work Breakdown

### Sprint 1: Data Model Enhancement (Week 1)

#### Task 1.1: Extend Deployment Model

**File**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/core/deployment.py`

**Changes**:
```python
@dataclass
class Deployment:
    # Existing fields (keep)
    artifact_name: str
    artifact_type: str
    from_collection: str
    deployed_at: datetime
    artifact_path: Path
    local_modifications: bool

    # RENAME for clarity
    deployed_sha: str  # Renamed from collection_sha

    # NEW fields
    current_sha: Optional[str] = None
    last_modification_check: Optional[datetime] = None
    modification_detected_at: Optional[datetime] = None
    parent_collection_path: Optional[str] = None
    version_lineage: List[Dict[str, Any]] = field(default_factory=list)
```

**Acceptance Criteria**:
- [ ] New fields added to `Deployment` dataclass
- [ ] `to_dict()` and `from_dict()` methods updated
- [ ] Backward compatibility maintained (old TOML files still load)
- [ ] Unit tests for serialization/deserialization
- [ ] Migration script for existing deployments

**Estimated Effort**: 1 day

---

#### Task 1.2: Create Version Tracking Models

**File**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/models.py`

**Add**:
- `ArtifactVersion` dataclass
- `VersionGraphNode` dataclass
- `VersionGraph` dataclass

**Acceptance Criteria**:
- [ ] All three models implemented with full type hints
- [ ] `VersionGraphNode.modification_count` property works recursively
- [ ] `VersionGraph.get_all_nodes()` flattens tree correctly
- [ ] Unit tests for graph traversal and statistics
- [ ] Documentation strings for all public methods

**Estimated Effort**: 1.5 days

---

#### Task 1.3: Migration Script

**File**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/storage/migration.py` (new)

**Create migration utility**:
```python
def migrate_deployment_tracking_v1_to_v2(project_path: Path) -> bool:
    """Migrate v1 deployment tracking to v2 with version fields."""
    # Read existing deployments
    # Add new fields with defaults
    # Rename collection_sha to deployed_sha
    # Compute initial current_sha
    # Write back with version lineage entry
```

**Acceptance Criteria**:
- [ ] Safely migrates all existing `.skillmeat-deployed.toml` files
- [ ] Handles missing files gracefully
- [ ] Backs up original file before migration
- [ ] Logs migration results
- [ ] Dry-run mode for testing

**Estimated Effort**: 1.5 days

---

#### Task 1.4: Update DeploymentTracker

**File**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/storage/deployment.py`

**Update existing methods**:
- `record_deployment()`: Set all new fields during deployment
- `write_deployments()`: Use new field names in TOML
- `read_deployments()`: Handle both old and new formats

**Acceptance Criteria**:
- [ ] New deployments use v2 format
- [ ] Old deployments auto-migrate on read
- [ ] Tests verify backward compatibility
- [ ] Integration tests with actual TOML files

**Estimated Effort**: 1 day

---

### Sprint 2: Core Logic Implementation (Week 2)

#### Task 2.1: Modification Detection

**File**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/storage/deployment.py`

**Implement**:
```python
@staticmethod
def compute_deployment_hash(project_path: Path, deployment: Deployment) -> str:
    """Compute current content hash for deployed artifact."""

@staticmethod
def check_and_update_modifications(project_path: Path) -> List[Deployment]:
    """Check all deployments for modifications and update tracking."""

@staticmethod
def get_modified_deployments(project_path: Path) -> List[Deployment]:
    """Get list of deployments with local modifications."""
```

**Acceptance Criteria**:
- [ ] Accurate SHA comparison (no false positives)
- [ ] Updates `local_modifications`, `current_sha`, timestamps correctly
- [ ] Handles missing artifacts gracefully
- [ ] Atomic updates to TOML file
- [ ] Performance: <100ms per artifact
- [ ] Unit tests with mock filesystem
- [ ] Integration tests with real deployments

**Estimated Effort**: 2 days

---

#### Task 2.2: Version Graph Builder

**File**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/core/version_tracker.py` (new)

**Implement**:
```python
class VersionGraphBuilder:
    def __init__(self, collection_mgr: CollectionManager):
        self.collection_mgr = collection_mgr

    def build_graph(
        self,
        artifact_name: str,
        artifact_type: ArtifactType,
        collection_name: Optional[str] = None
    ) -> VersionGraph:
        """Build complete version graph for artifact."""

    def _find_collection_version(self, ...) -> Optional[VersionGraphNode]:
        """Find artifact in collection as root node."""

    def _discover_projects(self) -> List[Path]:
        """Find all projects with deployments."""

    def _build_project_node(
        self,
        project_path: Path,
        deployment: Deployment
    ) -> VersionGraphNode:
        """Build node for deployed artifact instance."""

    def get_deployment_statistics(
        self,
        artifact_name: str,
        artifact_type: ArtifactType
    ) -> Dict[str, Any]:
        """Get deployment stats for artifact."""
```

**Acceptance Criteria**:
- [ ] Correctly builds graph with collection as root
- [ ] Finds all deployed instances across projects
- [ ] Computes modification status for each node
- [ ] Handles orphaned deployments (no collection parent)
- [ ] Performance: <500ms for 100 projects
- [ ] Unit tests with fixture projects
- [ ] Integration tests with real collection

**Estimated Effort**: 3 days

---

### Sprint 3: API Endpoints (Week 3)

#### Task 3.1: Version Schemas

**File**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/schemas/versions.py` (new)

**Create**:
- `ArtifactVersionInfo` schema
- `VersionGraphNodeResponse` schema
- `VersionGraphResponse` schema
- `ModificationCheckResponse` schema
- `DeploymentModificationStatus` schema

**Acceptance Criteria**:
- [ ] All schemas have complete Pydantic models
- [ ] OpenAPI examples provided
- [ ] Type validation works correctly
- [ ] JSON serialization tested
- [ ] Documentation strings complete

**Estimated Effort**: 1 day

---

#### Task 3.2: Modification Check Endpoint

**File**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/routers/projects.py`

**Add**:
```python
@router.post(
    "/{project_id}/check-modifications",
    response_model=ModificationCheckResponse,
    summary="Check project for artifact modifications",
)
async def check_project_modifications(
    project_id: str,
    token: TokenDep,
) -> ModificationCheckResponse:
    """Check all deployments in project for local modifications."""
```

**Acceptance Criteria**:
- [ ] Endpoint checks all deployments
- [ ] Returns accurate modification status
- [ ] Updates deployment tracking file
- [ ] Proper error handling
- [ ] Authentication required
- [ ] Rate limited (1 req/min per project)
- [ ] OpenAPI documentation
- [ ] Integration tests

**Estimated Effort**: 1.5 days

---

#### Task 3.3: Version Graph Endpoint

**File**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/routers/artifacts.py`

**Add**:
```python
@router.get(
    "/{artifact_id}/version-graph",
    response_model=VersionGraphResponse,
    summary="Get artifact version graph",
)
async def get_artifact_version_graph(
    artifact_id: str,
    artifact_mgr: ArtifactManagerDep,
    collection_mgr: CollectionManagerDep,
    token: TokenDep,
    collection: Optional[str] = Query(None),
) -> VersionGraphResponse:
    """Get complete version graph showing all deployments."""
```

**Acceptance Criteria**:
- [ ] Builds version graph using `VersionGraphBuilder`
- [ ] Returns tree structure with all nodes
- [ ] Includes deployment statistics
- [ ] Proper error handling
- [ ] Cached response (5-minute TTL)
- [ ] Authentication required
- [ ] OpenAPI documentation
- [ ] Integration tests

**Estimated Effort**: 1.5 days

---

#### Task 3.4: Enhanced Artifact Endpoint

**File**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/routers/artifacts.py`

**Modify** `artifact_to_response()`:
```python
def artifact_to_response(artifact, include_deployment_stats=False) -> ArtifactResponse:
    # Existing logic...

    if include_deployment_stats:
        # Add deployment_stats field
        graph_builder = VersionGraphBuilder(collection_mgr)
        stats = graph_builder.get_deployment_statistics(
            artifact.name,
            artifact.type
        )
        # Include in response
```

**Update** `GET /artifacts/{artifact_id}`:
- Add query param `?include_deployments=true`
- Conditionally include deployment statistics

**Acceptance Criteria**:
- [ ] Query param controls inclusion
- [ ] Statistics accurate
- [ ] Performance acceptable (<200ms additional)
- [ ] Backward compatible (default: no stats)
- [ ] Unit tests
- [ ] Integration tests

**Estimated Effort**: 1 day

---

### Sprint 4: Frontend Implementation (Week 4)

#### Task 4.1: API Client Functions

**File**: `/Users/miethe/dev/homelab/development/skillmeat/web/src/lib/api/versions.ts` (new)

**Implement**:
```typescript
export async function fetchVersionGraph(
  artifactId: string,
  collection?: string
): Promise<VersionGraphResponse> {}

export async function checkProjectModifications(
  projectId: string
): Promise<ModificationCheckResponse> {}

export async function fetchModifiedArtifacts(
  projectId: string
): Promise<DeploymentModificationStatus[]> {}
```

**Acceptance Criteria**:
- [ ] Type-safe API calls
- [ ] Error handling with ErrorResponse
- [ ] Auth token included
- [ ] Unit tests with MSW

**Estimated Effort**: 0.5 days

---

#### Task 4.2: React Query Hooks

**File**: `/Users/miethe/dev/homelab/development/skillmeat/web/src/hooks/useVersionTracking.ts` (new)

**Implement**:
```typescript
export function useVersionGraph(artifactId: string, collection?: string) {}
export function useProjectModifications(projectId: string) {}
export function useCheckModifications(projectId: string) {}
```

**Acceptance Criteria**:
- [ ] Proper cache keys
- [ ] 5-minute stale time for graphs
- [ ] 1-minute stale time for modifications
- [ ] Automatic refetch on window focus
- [ ] Optimistic updates
- [ ] Error handling

**Estimated Effort**: 1 day

---

#### Task 4.3: Zustand Store

**File**: `/Users/miethe/dev/homelab/development/skillmeat/web/src/stores/versionVisualizationStore.ts` (new)

**Implement**:
```typescript
interface VersionVisualizationStore {
  selectedNode: string | null
  expandedNodes: Set<string>
  highlightModified: boolean
  viewMode: 'tree' | 'list' | 'graph'
  actions: {...}
}
```

**Acceptance Criteria**:
- [ ] State persisted in localStorage
- [ ] Actions properly typed
- [ ] Immutable updates
- [ ] DevTools integration
- [ ] Unit tests

**Estimated Effort**: 0.5 days

---

#### Task 4.4: VersionTreeView Component

**File**: `/Users/miethe/dev/homelab/development/skillmeat/web/src/components/versions/VersionTreeView.tsx` (new)

**Component Structure**:
```tsx
<VersionTreeView
  artifactName="pdf-processor"
  artifactType="skill"
  collection="default"
/>
```

**Features**:
- Expandable/collapsible tree
- Status badges (modified/synced/outdated)
- Hover tooltips with SHA, timestamps
- Click to view details
- Search/filter nodes
- Export to JSON/CSV

**Acceptance Criteria**:
- [ ] Renders tree correctly
- [ ] Handles large trees (100+ nodes)
- [ ] Accessible (keyboard nav)
- [ ] Responsive design
- [ ] Loading states
- [ ] Error states
- [ ] Unit tests
- [ ] Storybook stories

**Estimated Effort**: 2 days

---

#### Task 4.5: ModificationBadge Component

**File**: `/Users/miethe/dev/homelab/development/skillmeat/web/src/components/versions/ModificationBadge.tsx` (new)

**Component Structure**:
```tsx
<ModificationBadge
  totalDeployments={5}
  modifiedCount={2}
  size="sm"
/>
```

**Renders**: `[Modified in 2/5]` or `[All Synced]`

**Acceptance Criteria**:
- [ ] Correct badge text
- [ ] Color coding (yellow=modified, green=synced)
- [ ] Size variants (sm/md/lg)
- [ ] Tooltip with details
- [ ] Accessible
- [ ] Unit tests
- [ ] Storybook stories

**Estimated Effort**: 0.5 days

---

#### Task 4.6: Integration with Artifact Detail View

**File**: `/Users/miethe/dev/homelab/development/skillmeat/web/src/pages/artifacts/[id].tsx`

**Add**:
- "Version History" tab
- `<VersionTreeView>` component
- "Check for Modifications" button
- Deployment statistics panel

**Acceptance Criteria**:
- [ ] Tab navigation works
- [ ] Version tree renders
- [ ] Statistics displayed
- [ ] Actions trigger API calls
- [ ] Loading/error states
- [ ] Responsive layout

**Estimated Effort**: 1.5 days

---

#### Task 4.7: Integration with Project Detail View

**File**: `/Users/miethe/dev/homelab/development/skillmeat/web/src/pages/projects/[id].tsx`

**Add**:
- "Modified Artifacts" section
- List of modified deployments
- "Check All" button
- Individual "View Changes" links

**Acceptance Criteria**:
- [ ] Modified artifacts highlighted
- [ ] Check button triggers API
- [ ] Results update UI
- [ ] Links to artifact detail
- [ ] Loading/error states

**Estimated Effort**: 1 day

---

### Sprint 5: Polish & Testing (Week 5)

#### Task 5.1: Performance Testing

**Create**: `/Users/miethe/dev/homelab/development/skillmeat/tests/performance/test_version_tracking.py`

**Test Scenarios**:
1. Version graph for 100 deployments
2. Modification check on 50 artifacts
3. Concurrent API requests (10 simultaneous)
4. Large project scan (1000 projects)

**Acceptance Criteria**:
- [ ] Version graph <500ms (100 projects)
- [ ] Modification check <100ms/artifact
- [ ] API response <200ms (cached)
- [ ] UI rendering <200ms
- [ ] Memory usage <100MB
- [ ] No memory leaks

**Estimated Effort**: 1.5 days

---

#### Task 5.2: Integration Tests

**Create**: `/Users/miethe/dev/homelab/development/skillmeat/tests/integration/test_version_tracking_flow.py`

**Test Flows**:
1. Deploy artifact → Modify → Detect modification
2. Build version graph with modified instances
3. Check modifications via API
4. View version graph in UI

**Acceptance Criteria**:
- [ ] End-to-end tests pass
- [ ] API contract tests pass
- [ ] UI tests with Playwright
- [ ] Error scenarios covered
- [ ] Coverage >90%

**Estimated Effort**: 2 days

---

#### Task 5.3: Documentation

**Create/Update**:
- `/Users/miethe/dev/homelab/development/skillmeat/docs/guides/version-tracking.md`
- `/Users/miethe/dev/homelab/development/skillmeat/docs/api/version-endpoints.md`
- Update quickstart guide
- Update architecture diagrams

**Content**:
- User guide with screenshots
- API reference with examples
- Architecture diagrams
- Troubleshooting guide
- FAQ

**Acceptance Criteria**:
- [ ] User guide complete
- [ ] API docs accurate
- [ ] Diagrams updated
- [ ] Examples tested
- [ ] Reviewed by team

**Estimated Effort**: 1.5 days

---

#### Task 5.4: Beta Testing

**Activities**:
1. Deploy to staging environment
2. Invite 5-10 beta testers
3. Collect feedback via survey
4. Monitor usage analytics
5. Fix critical bugs

**Acceptance Criteria**:
- [ ] Staging deployment successful
- [ ] Beta users onboarded
- [ ] Feedback collected (>80% response rate)
- [ ] User satisfaction >8/10
- [ ] Critical bugs fixed

**Estimated Effort**: 2 days (async)

---

## Dependencies and Sequencing

### Critical Path

```
Task 1.1 → Task 1.2 → Task 1.3 → Task 1.4
                              ↓
                         Task 2.1 → Task 2.2
                                       ↓
                         Task 3.1 → Task 3.2, 3.3, 3.4
                                       ↓
                         Task 4.1 → Task 4.2 → Task 4.3
                                       ↓
                         Task 4.4, 4.5 → Task 4.6, 4.7
                                       ↓
                         Task 5.1 → Task 5.2 → Task 5.3 → Task 5.4
```

### Parallel Work Opportunities

- Tasks 3.2, 3.3, 3.4 can be done in parallel (different endpoints)
- Tasks 4.4, 4.5 can be done in parallel (independent components)
- Tasks 4.6, 4.7 can be done in parallel (different pages)
- Task 5.3 can start during Task 5.2

## Resource Allocation

### Backend Developer (Full-time)

- Sprint 1: Tasks 1.1, 1.2, 1.3, 1.4
- Sprint 2: Tasks 2.1, 2.2
- Sprint 3: Tasks 3.1, 3.2, 3.3, 3.4
- Sprint 5: Tasks 5.1, 5.2

**Total**: 15 days backend work

### Frontend Developer (Full-time)

- Sprint 4: Tasks 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7
- Sprint 5: Task 5.3 (docs for UI)

**Total**: 7 days frontend work

### Documentation Writer (Part-time, 50%)

- Sprint 5: Task 5.3

**Total**: 1.5 days documentation work

### QA Engineer (Part-time, 50%)

- Sprint 5: Tasks 5.1, 5.2, 5.4

**Total**: 3 days QA work

## Testing Strategy

### Unit Tests

- All data models
- Version graph builder logic
- Modification detection algorithms
- API endpoint handlers
- React components

**Target Coverage**: 90%+

### Integration Tests

- End-to-end flows
- API contracts
- Database operations
- File system operations

**Target Coverage**: 80%+

### UI Tests

- Component behavior
- User interactions
- Visual regression
- Accessibility

**Target Coverage**: 70%+

### Performance Tests

- Load testing
- Stress testing
- Profiling
- Memory leak detection

**Target Benchmarks**: See Task 5.1

## Risk Mitigation

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Performance issues with many projects | Medium | High | Early performance testing, implement caching, lazy loading |
| Complex UI confuses users | Medium | Medium | User testing, clear tooltips, progressive disclosure |
| Migration breaks existing data | Low | Critical | Backup strategy, dry-run mode, rollback plan |
| API changes break clients | Low | High | Versioned API, deprecation warnings, backward compatibility |
| Race conditions in modification checks | Medium | Medium | File locking, atomic updates, debouncing |

## Success Criteria

### Functional

- [ ] All API endpoints functional and tested
- [ ] UI components render correctly
- [ ] Version graphs accurate
- [ ] Modification detection 99%+ accurate
- [ ] No data loss during migration

### Performance

- [ ] Version graph <500ms (100 projects)
- [ ] Modification check <100ms/artifact
- [ ] UI rendering <200ms
- [ ] Memory usage <100MB

### Quality

- [ ] Unit test coverage >90%
- [ ] Integration test coverage >80%
- [ ] No critical bugs
- [ ] Accessibility WCAG 2.1 AA compliant

### User Experience

- [ ] Beta user satisfaction >8/10
- [ ] Documentation complete and clear
- [ ] Error messages helpful
- [ ] UI intuitive (no training required)

## Rollout Plan

### Phase 1: Internal Testing (Week 5)

- Deploy to staging environment
- Internal team testing
- Fix critical bugs

### Phase 2: Beta Release (Week 6)

- Deploy to production with feature flag
- Invite 10 beta users
- Monitor usage and collect feedback

### Phase 3: General Availability (Week 7)

- Remove feature flag
- Announce in release notes
- Publish documentation
- Monitor metrics

## Monitoring and Metrics

### Technical Metrics

- API response times (p50, p95, p99)
- Error rates
- Cache hit rates
- Database query times
- Frontend bundle size

### Business Metrics

- Feature adoption rate
- Daily active users
- Version graph views
- Modification checks performed
- User satisfaction scores

### Alerts

- API error rate >5%
- Response time p95 >1s
- Cache hit rate <70%
- Memory usage >200MB
- Crash rate >0.1%

## Post-Launch Activities

### Week 1

- Monitor metrics closely
- Respond to user feedback
- Fix high-priority bugs
- Update documentation based on questions

### Week 2-4

- Analyze usage patterns
- Identify improvement opportunities
- Plan enhancements based on feedback
- Optimize performance bottlenecks

### Month 2

- Retrospective meeting
- Document lessons learned
- Plan Phase 3 enhancements
- Update roadmap

## Appendix

### Related Documents

- ADR-004: Artifact Version Tracking
- Phase 2 Intelligence PRD
- API Reference Documentation
- Architecture Diagrams

### Key Files to Create

**Backend**:
- `skillmeat/core/version_tracker.py`
- `skillmeat/storage/migration.py`
- `skillmeat/api/schemas/versions.py`
- `tests/performance/test_version_tracking.py`
- `tests/integration/test_version_tracking_flow.py`

**Frontend**:
- `web/src/lib/api/versions.ts`
- `web/src/hooks/useVersionTracking.ts`
- `web/src/stores/versionVisualizationStore.ts`
- `web/src/components/versions/VersionTreeView.tsx`
- `web/src/components/versions/ModificationBadge.tsx`

**Documentation**:
- `docs/guides/version-tracking.md`
- `docs/api/version-endpoints.md`

### Specialist Assignments

**Backend Implementation**:
- Delegate to: `backend-typescript-architect` (Tasks 1.x, 2.x, 3.x)
- Delegate to: `data-layer-expert` (Tasks 1.3, 1.4 for storage)

**Frontend Implementation**:
- Delegate to: `frontend-architect` (Tasks 4.1-4.3 for architecture)
- Delegate to: `ui-engineer` (Tasks 4.4-4.7 for components)

**Testing**:
- Delegate to: `debugger` (Tasks 5.1, 5.2 for test implementation)

**Documentation**:
- Delegate to: `documentation-writer` (Task 5.3 using Haiku 4.5)
