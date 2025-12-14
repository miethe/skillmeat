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
5. Diff viewer component for conflict resolution
6. Context discovery panel for projects
7. CLI sync commands

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

### TASK-5.5: Create Context Diff Viewer Component

**Story Points**: 3
**Assigned To**: `ui-engineer-enhanced`
**Dependencies**: Phase 3

**Files to Create**:
- `skillmeat/web/components/context/context-diff-viewer.tsx`

**Features**:
- Side-by-side diff view
- Highlight additions (green) and deletions (red)
- Resolution actions: Keep Local, Keep Remote, Merge (future)
- Preview result before applying

**Libraries**: Use `react-diff-viewer` or `diff2html`

**Acceptance Criteria**:
- [ ] Diff highlights changes correctly
- [ ] Resolution buttons work
- [ ] Preview shows final result
- [ ] Works for large files (scroll)

---

### TASK-5.6: Create Context Discovery Panel

**Story Points**: 2
**Assigned To**: `ui-engineer-enhanced`
**Dependencies**: TASK-5.3, Phase 3

**Files to Create**:
- `skillmeat/web/components/projects/context-discovery-panel.tsx`

**Features**:
- Display auto-loaded entities (with token counts)
- Display on-demand entities
- Total token usage indicator
- Load order visualization (specs → rules → context)
- Toggle auto-load for entities

**Acceptance Criteria**:
- [ ] Shows auto-loaded vs on-demand
- [ ] Token counts displayed
- [ ] Can toggle auto-load flag
- [ ] Warning if token count > threshold (e.g., 2000)

---

### TASK-5.7: Integrate Sync UI into Project Page

**Story Points**: 2
**Assigned To**: `ui-engineer-enhanced`
**Dependencies**: TASK-5.5, 5.6

**Files to Modify**:
- `skillmeat/web/app/projects/[id]/page.tsx` (assuming project detail page exists)

**Features**:
- "Sync Context" button in project toolbar
- Badge showing pending changes count
- Modal with diff viewer for each modified entity
- Batch apply changes (sync all)

**Acceptance Criteria**:
- [ ] Sync button visible on project page
- [ ] Badge shows count of pending changes
- [ ] Can review diffs before syncing
- [ ] Batch sync works

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

**Batch 4** (Parallel - UI Components):
```python
Task("ui-engineer-enhanced", "TASK-5.5: Context diff viewer component...")
Task("ui-engineer-enhanced", "TASK-5.6: Context discovery panel...")
```

**Batch 5** (Sequential - UI Integration):
```python
Task("ui-engineer-enhanced", "TASK-5.7: Integrate sync UI into project page...")
```

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
