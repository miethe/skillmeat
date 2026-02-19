---
status: inferred_complete
schema_version: 2
doc_type: phase_plan
feature_slug: agent-context-entities
prd_ref: null
plan_ref: null
---
# Phase 5: Progressive Disclosure & Sync

**Parent Plan**: [agent-context-entities-v1.md](../agent-context-entities-v1.md)
**Duration**: 1.5 weeks
**Story Points**: 12
**Dependencies**: Phase 1, 2, 3, 4

---

## Overview

Implement context entity synchronization between projects and collections, change detection via content hashing, progressive disclosure configuration, and context discovery API.

### Key Deliverables

1. Content hashing for change detection
2. Context sync service (pull/push changes)
3. Context discovery API endpoint (auto-load mapping)
4. Sync operations API endpoints
5. **Extend** existing diff-viewer with sync resolution actions
6. **Extend** existing discovery components for context entities
7. CLI sync commands

### Component Reuse Principle

**IMPORTANT**: This phase prioritizes extending existing components over creating new ones:

| Existing Component | Location | Extend For |
|-------------------|----------|------------|
| `diff-viewer.tsx` (397 lines) | `components/entity/` | Add resolution actions (Keep Local/Remote/Merge) |
| `DiscoveryTab.tsx` (19KB) | `components/discovery/` | Add token counts, auto-load toggles |
| `unified-entity-modal.tsx` (66KB) | `components/entity/` | Integrate context sync into Sync Status tab |
| `merge-workflow.tsx` (36KB) | `components/entity/` | Reuse for context conflict resolution |
| `context-entity-*.tsx` | `components/context/` | Extend existing context components |

**Rationale**: These components already implement 80%+ of required functionality. Extending saves significant development time and maintains UI consistency.

---

## Task Breakdown

### TASK-5.1: Implement Content Hashing for Change Detection

**Story Points**: 2
**Assigned To**: `python-backend-engineer`
**Dependencies**: Phase 1

**Files to Create**:
- `skillmeat/core/services/content_hash.py`

**Features**:
- SHA256 hash of entity content
- Hash computed on create/update
- Compare deployed file hash with collection hash
- Detect if file has been manually edited

**Implementation**:
```python
import hashlib

def compute_content_hash(content: str) -> str:
    """Compute SHA256 hash of content."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()

def detect_changes(collection_entity: Artifact, deployed_file_path: str) -> bool:
    """Detect if deployed file differs from collection entity."""
    if not os.path.exists(deployed_file_path):
        return False  # File doesn't exist, not a change

    with open(deployed_file_path, "r") as f:
        deployed_content = f.read()

    deployed_hash = compute_content_hash(deployed_content)
    return deployed_hash != collection_entity.content_hash
```

**Acceptance Criteria**:
- [ ] Hash is deterministic (same content = same hash)
- [ ] Hash updates on content change
- [ ] Change detection works for deployed files

---

### TASK-5.2: Create Context Sync Service

**Story Points**: 3
**Assigned To**: `python-backend-engineer`
**Dependencies**: TASK-5.1

**Files to Create**:
- `skillmeat/core/services/context_sync.py`

**Features**:
1. **Pull Changes**: Detect modified entities in project, pull to collection
2. **Push Changes**: Push collection changes to project
3. **Conflict Detection**: Identify when both collection and project modified
4. **User Choice**: Keep local, keep remote, or merge

**Implementation**:
```python
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class SyncConflict:
    entity_id: str
    entity_name: str
    collection_hash: str
    deployed_hash: str
    collection_content: str
    deployed_content: str

class ContextSyncService:
    def detect_modified_entities(self, project_path: str) -> List[Artifact]:
        """Scan project for modified context entities."""
        pass

    def pull_changes(
        self,
        project_path: str,
        entity_ids: Optional[List[str]] = None
    ) -> List[Artifact]:
        """Pull changes from project to collection."""
        pass

    def push_changes(
        self,
        project_path: str,
        entity_ids: Optional[List[str]] = None,
        overwrite: bool = False
    ) -> List[Artifact]:
        """Push collection changes to project."""
        pass

    def detect_conflicts(self, project_path: str) -> List[SyncConflict]:
        """Detect entities modified in both places."""
        pass

    def resolve_conflict(
        self,
        conflict: SyncConflict,
        resolution: Literal["keep_local", "keep_remote", "merge"]
    ):
        """Resolve sync conflict based on user choice."""
        pass
```

**Acceptance Criteria**:
- [ ] Detects modified files in project
- [ ] Pull updates collection entity
- [ ] Push updates deployed file
- [ ] Conflicts detected and returned
- [ ] Resolution applies user choice

---

### TASK-5.3: Create Context Discovery Endpoint

**Story Points**: 2
**Assigned To**: `python-backend-engineer`
**Dependencies**: Phase 1

**Files to Modify**:
- `skillmeat/api/routers/projects.py` (or create new router)

**Endpoint**:
```
GET /projects/{id}/context-map
```

**Response**:
```json
{
  "auto_loaded": [
    {
      "type": "spec_file",
      "name": "doc-policy-spec.md",
      "path": ".claude/specs/doc-policy-spec.md",
      "tokens": 250
    },
    {
      "type": "rule_file",
      "name": "api/routers.md",
      "path": ".claude/rules/api/routers.md",
      "tokens": 300
    }
  ],
  "on_demand": [
    {
      "type": "context_file",
      "name": "backend-api-patterns.md",
      "path": ".claude/context/backend-api-patterns.md",
      "tokens": 500
    }
  ],
  "total_auto_load_tokens": 550
}
```

**Logic**:
- Scan project `.claude/` directory
- Identify auto-load entities (from `auto_load` flag or path-based rules)
- Estimate token count (approx: content.split().length * 1.3)
- Return structured map

**Acceptance Criteria**:
- [ ] Returns auto-loaded and on-demand entities
- [ ] Token estimates are reasonable
- [ ] Works for projects without `.claude/` directory

---

### TASK-5.4: Create Sync Operations Endpoints

**Story Points**: 2
**Assigned To**: `python-backend-engineer`
**Dependencies**: TASK-5.2

**Files to Create**:
- `skillmeat/api/routers/context_sync.py`

**Endpoints**:
| Method | Path | Purpose |
|--------|------|---------|
| POST | `/context-sync/pull` | Pull changes from project to collection |
| POST | `/context-sync/push` | Push collection changes to project |
| GET | `/context-sync/status` | Get sync status for project |

**Request Bodies**:
```python
class SyncPullRequest(BaseModel):
    project_path: str
    entity_ids: Optional[List[str]] = None  # If None, sync all

class SyncPushRequest(BaseModel):
    project_path: str
    entity_ids: Optional[List[str]] = None
    overwrite: bool = False

class SyncStatusResponse(BaseModel):
    modified_in_project: List[str]  # Entity IDs
    modified_in_collection: List[str]
    conflicts: List[SyncConflict]
```

**Acceptance Criteria**:
- [ ] Pull endpoint updates collection
- [ ] Push endpoint updates project files
- [ ] Status endpoint returns conflicts
- [ ] Endpoints validate project path

---

### TASK-5.5: Extend Diff Viewer with Sync Resolution Actions

**Story Points**: 2 _(reduced from 3 - extending existing component)_
**Assigned To**: `ui-engineer-enhanced`
**Dependencies**: Phase 3

**Files to Modify**:
- `skillmeat/web/components/entity/diff-viewer.tsx` _(existing, 397 lines)_

**Existing Features** (already implemented):
- ✅ Side-by-side diff view
- ✅ Color-coded additions (green) and deletions (red)
- ✅ File sidebar with change statistics
- ✅ Scroll support for large files
- ✅ Unified diff parsing

**New Features to Add**:
- Resolution action bar: "Keep Local", "Keep Remote", "Merge" (future)
- Optional `onResolve` callback prop for conflict resolution
- Preview mode to show result before applying
- Integration with context sync workflow

**Implementation Approach**:
```typescript
// Extend existing DiffViewer props
interface DiffViewerProps {
  // ... existing props
  showResolutionActions?: boolean;
  onResolve?: (resolution: 'keep_local' | 'keep_remote' | 'merge') => void;
  previewMode?: boolean;
}
```

**Acceptance Criteria**:
- [ ] Resolution buttons appear when `showResolutionActions={true}`
- [ ] `onResolve` callback fires with correct resolution type
- [ ] Preview mode shows final result
- [ ] Existing diff-viewer functionality unchanged when new props not used

---

### TASK-5.6: Extend Discovery Components for Context Entities

**Story Points**: 2
**Assigned To**: `ui-engineer-enhanced`
**Dependencies**: TASK-5.3, Phase 3

**Files to Modify**:
- `skillmeat/web/components/discovery/DiscoveryTab.tsx` _(existing, 19KB)_
- `skillmeat/web/components/context/context-entity-card.tsx` _(existing)_
- `skillmeat/web/components/context/context-entity-detail.tsx` _(existing)_

**Files to Create** (minimal):
- `skillmeat/web/components/context/context-load-order.tsx` _(small, ~100 lines)_

**Existing Components to Leverage**:
- `DiscoveryTab.tsx` - Main discovery interface with filtering, search, import
- `context-entity-card.tsx` - Card display for context entities
- `context-entity-detail.tsx` - Detail view for context entities
- `context-entity-filters.tsx` - Filtering for context type

**New Features to Add**:
- Token count badges on context entity cards
- Auto-load toggle switch on cards and detail view
- Token usage summary in discovery header
- Load order visualization component (new, small)
- Warning banner when total auto-load tokens > 2000

**Implementation Approach**:
```typescript
// Extend existing ContextEntityCard props
interface ContextEntityCardProps {
  // ... existing props
  showTokenCount?: boolean;
  tokenCount?: number;
  onAutoLoadToggle?: (enabled: boolean) => void;
}

// New small component for load order
const ContextLoadOrder: React.FC<{ entities: ContextEntity[] }>;
```

**Acceptance Criteria**:
- [ ] Token counts displayed on cards when `showTokenCount={true}`
- [ ] Auto-load toggle works and calls API
- [ ] Load order visualization shows specs → rules → context
- [ ] Warning appears when total tokens > 2000
- [ ] Integrates with existing DiscoveryTab filtering

---

### TASK-5.7: Integrate Context Sync into Unified Entity Modal

**Story Points**: 2
**Assigned To**: `ui-engineer-enhanced`
**Dependencies**: TASK-5.5, 5.6

**Existing Components to Leverage**:
- `unified-entity-modal.tsx` (66KB) - Already has "Sync Status" tab with diff viewing
- `merge-workflow.tsx` (36KB) - Already handles merge conflict resolution
- `conflict-resolver.tsx` - Collection conflict resolution component

**Files to Modify**:
- `skillmeat/web/components/entity/unified-entity-modal.tsx`
- `skillmeat/web/app/projects/[id]/page.tsx` (if exists)

**Approach**:
Rather than creating new sync UI, extend the existing unified-entity-modal's "Sync Status" tab to:
1. Support context entity type in sync status checks
2. Show context entities alongside other artifact types in sync view
3. Use extended diff-viewer (TASK-5.5) for context conflict resolution
4. Add "Sync Context" action to project toolbar/card

**Features**:
- Context entities appear in unified modal's Sync Status tab
- Sync button on project page/card triggers existing modal
- Badge showing pending context changes
- Batch sync leverages existing merge-workflow.tsx patterns

**Implementation Approach**:
```typescript
// Extend SyncStatusTab to handle context entities
// No new component needed - enhance existing
const SyncStatusTab: React.FC<{
  // ... existing props
  includeContextEntities?: boolean;
}>;
```

**Acceptance Criteria**:
- [ ] Context entities appear in unified modal's Sync Status tab
- [ ] Sync button visible on project page/card
- [ ] Badge shows count of pending context changes
- [ ] Can review diffs in existing diff-viewer
- [ ] Batch sync works for context entities
- [ ] Existing sync functionality for skills/agents unchanged

---

### TASK-5.8: Implement CLI Sync Commands

**Story Points**: 1
**Assigned To**: `python-backend-engineer`
**Dependencies**: TASK-5.2, 5.4

**Commands**:
```bash
# Pull changes from project to collection
skillmeat project sync-context <project-path> --pull

# Push collection changes to project
skillmeat project sync-context <project-path> --push

# Show sync status
skillmeat project sync-context <project-path> --status

# Sync specific entities
skillmeat project sync-context <project-path> --pull --entities doc-policy-spec,routers-rule
```

**Features**:
- Colored diff output in terminal
- Confirmation prompt before applying changes
- Show summary of changes (X entities updated)

**Acceptance Criteria**:
- [ ] Pull command updates collection
- [ ] Push command updates project files
- [ ] Status shows pending changes
- [ ] Diff displayed in terminal with colors

---

## Parallelization Plan

**Batch 1** (Parallel - Core Logic):
```python
Task("python-backend-engineer", "TASK-5.1: Content hashing for change detection...")
Task("python-backend-engineer", "TASK-5.3: Context discovery endpoint...")
```

**Batch 2** (Sequential - Sync Service):
```python
Task("python-backend-engineer", "TASK-5.2: Context sync service (pull/push/conflicts)...")
```

**Batch 3** (Parallel - API + CLI):
```python
Task("python-backend-engineer", "TASK-5.4: Sync operations API endpoints...")
Task("python-backend-engineer", "TASK-5.8: CLI sync commands...")
```

**Batch 4** (Parallel - UI Extensions):
```python
Task("ui-engineer-enhanced", "TASK-5.5: Extend diff-viewer.tsx with sync resolution actions (Keep Local/Remote). Add showResolutionActions and onResolve props. File: components/entity/diff-viewer.tsx")
Task("ui-engineer-enhanced", "TASK-5.6: Extend discovery components for context entities - add token counts to cards, auto-load toggles, token warning banner. Files: components/discovery/DiscoveryTab.tsx, components/context/context-entity-card.tsx. Create small context-load-order.tsx for load order visualization.")
```

**Batch 5** (Sequential - UI Integration):
```python
Task("ui-engineer-enhanced", "TASK-5.7: Extend unified-entity-modal's Sync Status tab to include context entities. Leverage existing merge-workflow.tsx patterns. Add Sync Context button to project toolbar. File: components/entity/unified-entity-modal.tsx")
```

**Note**: Batch 4 and 5 are UI extension work, not net-new component creation. This reduces risk and development time.

---

## Quality Gates

- [ ] Change detection identifies modified files
- [ ] Pull updates collection correctly
- [ ] Push updates project files correctly
- [ ] Conflicts detected and shown
- [ ] Diff view highlights changes accurately
- [ ] Context map returns correct auto-load status
- [ ] Token estimates are reasonable
- [ ] CLI sync commands work

---

## Success Metrics

| Metric | Target | Actual |
|--------|--------|--------|
| Sync accuracy (detect changes) | 100% | ___ |
| Conflict detection accuracy | 100% | ___ |
| Token estimate accuracy | ±20% | ___ |
| CLI sync command coverage | 100% | ___ |

---

## Next Phase

Once Phase 5 is complete, proceed to:
**[Phase 6: Polish & Documentation](phase-6-polish-documentation.md)**
