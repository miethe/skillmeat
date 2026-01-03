---
title: Marketplace Detection & Confidence Scoring Patterns
description: Patterns for skill detection, confidence scoring, SKILL.md validation, and source detail page architecture
references:
  - skillmeat/core/marketplace/heuristic_detector.py
  - skillmeat/api/schemas/marketplace.py
  - skillmeat/web/app/marketplace/sources/[id]/page.tsx
  - skillmeat/web/app/marketplace/sources/[id]/components/catalog-tabs.tsx
  - skillmeat/api/routers/marketplace_sources.py
last_verified: 2025-01-02
---

# Marketplace Patterns: Detection, Confidence Scoring & Source Details

## 1. Skill Detection & Confidence Scoring

### Architecture: Multi-Signal Heuristic Scoring

**Location**: `skillmeat/core/marketplace/heuristic_detector.py`

The detector uses **7 independent signals** combined into a single confidence score (0-100):

```
Signal Contributions (MAX_RAW_SCORE = 120):
├── dir_name:         10 points  (e.g., "skills/", "commands/")
├── manifest:         20 points  (e.g., SKILL.md, COMMAND.md)
├── extensions:        5 points  (.py, .ts, .json, .yaml, etc.)
├── parent_hint:      15 points  (parent dir matches pattern)
├── frontmatter:      15 points  (markdown frontmatter metadata)
├── container_hint:   25 points  (detected type matches container)
└── frontmatter_type: 30 points  (frontmatter "type:" field - strongest)

Penalties:
└── depth_penalty:   -N points  (reduced by 50% inside typed containers)

Normalization: raw_score / 120 * 100 → 0-100 scale
```

### Manifest File Detection

**SKILL.md is the primary detection signal** (20 points base):

```python
# From DetectionConfig class
manifest_files: Dict[ArtifactType, Set[str]] = {
    ArtifactType.SKILL: {"SKILL.md", "skill.md"},
    ArtifactType.COMMAND: {"COMMAND.md", "command.md"},
    ArtifactType.AGENT: {"AGENT.md", "agent.md"},
    ArtifactType.MCP_SERVER: {"MCP.md", "mcp.md", "server.json"},
    ArtifactType.HOOK: {"HOOK.md", "hook.md", "hooks.json"},
}
```

**Key Pattern**: Manifest presence is the **strongest directory-level signal** and:
- Overrides directory name detection if conflicting types
- Case-insensitive match (SKILL.md, skill.md both valid)
- Required for directory-based artifacts (e.g., skills)

### Detection Flow: Directory-Based vs Single-File

#### Directory-Based (Skills Primarily)

Skills are typically **directory-based** with structure:
```
skills/canvas-design/
├── SKILL.md              # Detection: manifest_score +20
├── index.ts              # Detection: extension_score +5
├── package.json          # Detection: extension_score +5
└── README.md             # Support file
```

**Confidence Calculation**:
```
Signal Breakdown:
- dir_name ("canvas-design" in "skills/"):        +0  (name doesn't match patterns)
- manifest (SKILL.md present):                     +20 (manifest_score)
- extensions (3 relevant files):                   +5  (capped at extension_weight)
- parent_hint ("skills" parent dir):              +15  (parent_hint_score)
- container_hint (detected=SKILL, container=SKILL): +25 (container_hint_score)
- depth_penalty (depth 2, inside container):      -1  (reduced 50%)
                                          ────────────
Total Raw: 20+5+15+25-1 = 64
Normalized: 64/120 * 100 = 53% → Would be boosted by frontmatter
```

#### Single-File Artifacts (Commands, Agents, Hooks)

Commands/Agents often are **single .md files** inside containers:
```
commands/git/
├── cm.md                 # Single-file: "checkout merge"
├── cp.md                 # Single-file: "cherry-pick"
└── pr.md                 # Single-file: "pull request"
```

**Single-File Detection Logic** (from `_detect_single_file_artifacts`):
```python
# Base confidence by depth within container
if relative_depth == 0:
    confidence = 75  # Directly in container (e.g., commands/git.md)
elif relative_depth == 1:
    confidence = 70  # One level deep (e.g., commands/git/cm.md)
else:
    # Each additional level: -5 points
    confidence = max(50, 70 - (relative_depth - 1) * 5)

# Breakdown:
# container_hint_score: 25 (inside commands/)
# extensions_score:      5 (.md extension)
# raw_total:            30
# normalized:           75-80% confidence
```

### Confidence Score Breakdown Structure

**Field**: `score_breakdown` (Dict[str, int])

```python
{
    "dir_name_score": int,           # 0-10
    "manifest_score": int,           # 0-20 (STRONGEST SIGNAL)
    "extensions_score": int,         # 0-5
    "parent_hint_score": int,        # 0-15
    "frontmatter_score": int,        # 0-15
    "container_hint_score": int,     # 0-25
    "frontmatter_type_score": int,   # 0-30 (if type found in metadata)
    "depth_penalty": int,            # negative (reduced if in container)
    "raw_total": int,                # sum of all signals (typically 0-120)
    "normalized_score": int,         # final 0-100 score
    "single_file_detection": bool,   # True if single-file artifact
}
```

### Frontmatter Type Detection

**Strongest Signal** (30 points) when enabled:

```yaml
# Example SKILL.md frontmatter
---
type: skill
name: Canvas Designer
version: 1.0.0
description: Design with canvas
---
# Content...
```

**Type Parsing**:
```python
def _parse_manifest_frontmatter(self, content: str) -> Optional[str]:
    """Parse YAML frontmatter and extract artifact type.

    Returns:
        Normalized type value (lowercase) or None

    Examples:
        "---\ntype: skill\n---" → 'skill'
        "---\ntype: COMMAND\n---" → 'command'
        "# No frontmatter" → None
    """
```

**Type Mapping**:
```python
type_mapping = {
    "skill": ArtifactType.SKILL,
    "command": ArtifactType.COMMAND,
    "agent": ArtifactType.AGENT,
    "mcp_server": ArtifactType.MCP_SERVER,
    "mcp-server": ArtifactType.MCP_SERVER,
    "mcpserver": ArtifactType.MCP_SERVER,
    "hook": ArtifactType.HOOK,
}
```

### Key Detection Rules

#### Rule 1: Container Types Don't Get Detected as Artifacts

```python
# These are CONTAINERS, not artifacts (will be skipped)
CONTAINER_TYPE_MAPPING = {
    "commands": ArtifactType.COMMAND,    # Container
    "agents": ArtifactType.AGENT,        # Container
    "skills": ArtifactType.SKILL,        # Container
    "hooks": ArtifactType.HOOK,          # Container
    "mcp": ArtifactType.MCP_SERVER,      # Container
    "mcp-servers": ArtifactType.MCP_SERVER,
    "servers": ArtifactType.MCP_SERVER,
}

# Directory "skills/" itself is not detected as artifact
# But "skills/my-skill/" with SKILL.md IS detected as artifact
```

**Implementation**:
```python
def _is_container_directory(self, dir_path: str, dir_to_files: Dict[str, Set[str]]) -> bool:
    """Returns True if directory matches container naming pattern."""
    return self._get_container_type(dir_path, dir_to_files) is not None
```

#### Rule 2: Plugin Directories (2+ entity types)

```python
# Plugin structure with multiple artifact types
my-plugin/
├── commands/      # Entity type subdirectory
├── agents/        # Entity type subdirectory
└── skills/        # Entity type subdirectory
    └── my-skill/

# "my-plugin" is detected as plugin because it contains 2+ type directories
# Individual artifacts still detected: commands/{cmd}, agents/{agent}, skills/my-skill/
```

#### Rule 3: Grouping Directories for Single-File Artifacts

```python
# GROUPING DIRECTORY (should NOT be detected as artifact)
commands/git/                          # Grouping: only .md files, inside container
├── cm.md                             # Detected as single-file artifact
├── cp.md                             # Detected as single-file artifact
└── pr.md                             # Detected as single-file artifact

# Implementation: _is_single_file_grouping_directory()
# - Checks if inside typed container
# - Has no manifest files
# - Contains ONLY .md files (except excluded ones)
# If all true → treated as grouping, not detected itself
```

#### Rule 4: Directory Nesting Penalties

```python
# Flat artifact types (COMMANDS, AGENTS, HOOKS) get penalized for nesting
if artifact_type in (COMMAND, AGENT, HOOK):
    allowed_nested = {"tests", "test", "__tests__", "lib", "dist", "build"}
    # Any OTHER nested directories reduce confidence by 15 points
```

### Minimum Confidence Threshold

**Default**: 30% (configurable)

```python
class DetectionConfig:
    min_confidence: int = 30  # Below this, entries not returned
```

**Practical Impact**:
- Entries below 30 are filtered in API response
- Still stored in database with status markers
- Can be shown with `includeBelowThreshold=true` in filters

---

## 2. Marketplace Source Detail Page

### Page Location & Architecture

**Frontend Route**: `/marketplace/sources/[id]`

**Files**:
- Page: `skillmeat/web/app/marketplace/sources/[id]/page.tsx`
- Tabs Component: `skillmeat/web/app/marketplace/sources/[id]/components/catalog-tabs.tsx`
- Excluded List: `skillmeat/web/app/marketplace/sources/[id]/components/excluded-list.tsx`

### Page Data Model

**Props from URL**:
```typescript
interface SourceDetailPageProps {
  params: {
    id: string  // Source ID from URL
  }
}
```

**State Management**:
```typescript
// Filters (synced to URL params)
const [filters, setFilters] = useState<CatalogFilters>({
  artifact_type?: ArtifactType,
  status?: CatalogStatus,
});

const [confidenceFilters, setConfidenceFilters] = useState({
  minConfidence: 50,      // Default: 50%
  maxConfidence: 100,     // Default: 100%
  includeBelowThreshold: false,
});

// Selection & Modals
const [selectedEntries, setSelectedEntries] = useState<Set<string>>();
const [selectedEntry, setSelectedEntry] = useState<CatalogEntry | null>();
const [modalOpen, setModalOpen] = useState(false);
const [editModalOpen, setEditModalOpen] = useState(false);
const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
```

### Data Fetching with Pagination

**API Hooks**:
```typescript
// Source info
const { data: source, isLoading, error } = useSource(sourceId);

// Catalog entries (infinite query for pagination)
const {
  data: catalogData,
  isLoading: catalogLoading,
  isFetching: catalogFetching,
  fetchNextPage,
  hasNextPage,
  isFetchingNextPage,
} = useSourceCatalog(sourceId, mergedFilters);

// Mutations
const rescanMutation = useRescanSource(sourceId);
const importMutation = useImportArtifacts(sourceId);
const excludeMutation = useExcludeCatalogEntry(sourceId);
```

**Filter Merging** (for API):
```typescript
// Client filters split into two groups
const mergedFilters: CatalogFilters = {
  ...filters,                                    // Type + status
  min_confidence: confidenceFilters.minConfidence,
  max_confidence: confidenceFilters.maxConfidence,
  include_below_threshold: confidenceFilters.includeBelowThreshold,
};
```

### Catalog Tabs Component

**Location**: `catalog-tabs.tsx`

**Features**:
- "All Types" tab showing total count
- Individual tabs for each artifact type with counts
- Zero-count types visually muted but clickable
- Scrollable on mobile with `overflow-x-auto`

**Props**:
```typescript
interface CatalogTabsProps {
  countsByType: Record<string, number>;      // From API response
  selectedType: string | null;               // null = "All Types"
  onTypeChange: (type: string | null) => void;
}
```

**Artifact Types Display**:
```typescript
const ARTIFACT_TYPE_TABS = [
  { value: 'skill', label: 'Skills', Icon: Sparkles },
  { value: 'agent', label: 'Agents', Icon: Bot },
  { value: 'command', label: 'Commands', Icon: Terminal },
  { value: 'mcp_server', label: 'MCP', Icon: Server },
  { value: 'hook', label: 'Hooks', Icon: Webhook },
];
```

**Count Display**: `({count})` in parentheses next to label

### Catalog Card Component

**Features per Card**:

```typescript
interface CatalogCardProps {
  entry: CatalogEntry;
  selected: boolean;
  onSelect: (selected: boolean) => void;
  onImport: () => void;
  isImporting: boolean;
  onClick?: () => void;
  sourceId: string;
}
```

**Card Layout**:
```
┌─────────────────────────────────────────┐
│ ☑ [checkbox]      [Type Badge] [Status] │
│ artifact-name                            │
│ path/to/artifact                        │
│ [Score Badge]        [View on GitHub →] │
│                                         │
│ [Import Button]                         │
│ [Not an artifact link]                  │
│                                         │
│ (Optional: Imported on date)            │
└─────────────────────────────────────────┘
```

**Status Badges**:
```typescript
const statusConfig = {
  new:      { label: 'New',      className: 'border-green-500 ...' },
  updated:  { label: 'Updated',  className: 'border-blue-500 ...' },
  imported: { label: 'Imported',  className: 'border-gray-500 ...' },
  removed:  { label: 'Removed',   className: 'border-red-500 ...' },
  excluded: { label: 'Excluded',  className: 'border-gray-400 ...' },
}
```

**Type Badges** (e.g., "Skill", "Command"):
```typescript
const typeConfig: Record<ArtifactType, { label: string; color: string }> = {
  skill: { label: 'Skill', color: 'bg-blue-100 ...' },
  command: { label: 'Command', color: 'bg-purple-100 ...' },
  agent: { label: 'Agent', color: 'bg-green-100 ...' },
  mcp_server: { label: 'MCP', color: 'bg-orange-100 ...' },
  hook: { label: 'Hook', color: 'bg-pink-100 ...' },
}
```

**Interaction**:
- Click card → Opens modal with entry details
- Click checkbox → Selects for bulk import
- Click "Import" button → Single import
- Click "Not an artifact" → Opens exclude dialog
- Click "View on GitHub" → External link

### Filters Bar Layout

**Components (top to bottom)**:

```
[Search input]  [Type tabs]  [Confidence filter]  [Clear filters]

[Select All]  [Import N selected]  [X excluded indicator]
```

**Search** (client-side):
```typescript
// Filters by entry.name or entry.path
const filteredEntries = useMemo(() => {
  const query = searchQuery.toLowerCase();
  return allEntries.filter(entry =>
    entry.name.toLowerCase().includes(query) ||
    entry.path.toLowerCase().includes(query)
  );
}, [allEntries, searchQuery]);
```

**Confidence Filter**:
```typescript
<ConfidenceFilter
  minConfidence={confidenceFilters.minConfidence}
  maxConfidence={confidenceFilters.maxConfidence}
  includeBelowThreshold={confidenceFilters.includeBelowThreshold}
  onMinChange={...}
  onMaxChange={...}
  onIncludeBelowThresholdChange={...}
/>
```

### Bulk Filtering & URL Persistence

**URL Parameter Mapping**:
```typescript
// When filters change, update URL
const updateURLParams = (newConfidenceFilters, newFilters) => {
  const params = new URLSearchParams();

  // Confidence (only if different from defaults)
  if (minConfidence !== 50) params.set('minConfidence', minConfidence);
  if (maxConfidence !== 100) params.set('maxConfidence', maxConfidence);
  if (includeBelowThreshold) params.set('includeBelowThreshold', 'true');

  // Type and status
  if (artifact_type) params.set('type', artifact_type);
  if (status) params.set('status', status);

  router.replace(`${pathname}${query ? `?${query}` : ''}`);
};

// Sync on mount from URL
const [filters] = useState(() => ({
  artifact_type: (searchParams.get('type') as ArtifactType) || undefined,
  status: (searchParams.get('status') as CatalogStatus) || undefined,
}));
```

### Bulk Actions

**Selection Logic**:
```typescript
const handleSelectAll = () => {
  // Only selectable: status === 'new' || 'updated'
  const importableEntries = filteredEntries.filter(
    e => e.status === 'new' || e.status === 'updated'
  );

  if (selectedEntries.size === importableEntries.length) {
    setSelectedEntries(new Set());  // Deselect
  } else {
    setSelectedEntries(new Set(importableEntries.map(e => e.id)));
  }
};
```

**Import**:
```typescript
const handleImportSelected = async () => {
  if (selectedEntries.size === 0) return;

  await importMutation.mutateAsync({
    entry_ids: Array.from(selectedEntries),
    conflict_strategy: 'skip',
  });

  setSelectedEntries(new Set());
};
```

### Excluded Artifacts Handling

**In Catalog Response**:
```typescript
// API returns entries with status='excluded' mixed in
// Separate them client-side for dedicated section
const excludedEntries = useMemo(() => {
  return allEntries.filter(entry => entry.status === 'excluded');
}, [allEntries]);
```

**Exclude Dialog**:
```typescript
<ExcludeArtifactDialog
  entry={entry}
  open={excludeDialogOpen}
  onConfirm={() => {
    excludeMutation.mutate({ entryId: entry.id });
    setExcludeDialogOpen(false);
  }}
/>
```

**REST Endpoint** (for exclusion):
```
PATCH /marketplace/sources/{id}/artifacts/{entry_id}/exclude
Body: { excluded: true, reason: "string" }

DELETE /marketplace/sources/{id}/artifacts/{entry_id}/exclude
(Restore excluded entry)
```

### Deduplication

**Important**: Flatten paginated results with deduplication:

```typescript
const allEntries = useMemo(() => {
  if (!catalogData?.pages) return [];
  const seen = new Set<string>();
  return catalogData.pages
    .flatMap(page => page.items)
    .filter(entry => {
      if (seen.has(entry.id)) return false;
      seen.add(entry.id);
      return true;
    });
}, [catalogData]);
```

**Why**: When pagination happens, some entries might appear on multiple pages during filtering changes.

### Stats Display

**Status Counts** (from first page response):
```typescript
const countsByStatus = catalogData?.pages[0]?.counts_by_status || {};

// Render as clickable badges
{Object.entries(countsByStatus).map(([status, count]) => (
  <Badge
    key={status}
    className={filters.status === status && 'ring-2 ring-primary'}
    onClick={() => setFilters(prev => ({
      ...prev,
      status: prev.status === status ? undefined : status
    }))}
  >
    {status}: {count}
  </Badge>
))}
```

---

## 3. API Response Models

### CatalogEntryResponse Schema

**From**: `skillmeat/api/schemas/marketplace.py`

```python
class CatalogEntryResponse(BaseModel):
    """Response model for detected artifact."""

    id: str                                  # Unique catalog entry ID
    source_id: str                           # Source this came from
    artifact_type: Literal[...]              # skill, command, agent, mcp_server, hook
    name: str                                # Extracted name
    path: str                                # Repository path
    upstream_url: str                        # GitHub URL
    detected_version: Optional[str]          # Version if found
    detected_sha: Optional[str]              # Git commit SHA
    detected_at: datetime                    # When detected
    confidence_score: int                    # 0-100
    raw_score: Optional[int]                 # 0-120 (before normalization)
    score_breakdown: Optional[Dict[str, int]]  # Signal details
    status: Literal[...]                     # new, updated, removed, imported, excluded
    import_date: Optional[datetime]          # If imported
    import_id: Optional[str]                 # Import operation ID
    excluded_at: Optional[datetime]          # If excluded
    excluded_reason: Optional[str]           # Why excluded (max 500 chars)
```

### CatalogListResponse Schema

```python
class CatalogListResponse(BaseModel):
    """Paginated list with statistics."""

    items: List[CatalogEntryResponse]
    page_info: PageInfo                      # Cursor-based pagination
    counts_by_status: Dict[str, int]         # e.g., {"new": 45, "imported": 33}
    counts_by_type: Dict[str, int]           # e.g., {"skill": 60, "command": 20}
```

**Pagination Fields**:
```python
class PageInfo(BaseModel):
    has_next_page: bool
    has_previous_page: bool
    start_cursor: Optional[str]   # Base64 encoded
    end_cursor: Optional[str]     # Base64 encoded
    total_count: Optional[int]
```

### SourceResponse Schema

```python
class SourceResponse(BaseModel):
    """GitHub source with scan status."""

    id: str                                  # Source ID
    repo_url: str                            # Full GitHub URL
    owner: str                               # Owner username
    repo_name: str                           # Repo name
    ref: str                                 # Branch/tag/SHA being tracked
    root_hint: Optional[str]                 # Subdirectory focus
    trust_level: str                         # untrusted, basic, verified, official
    visibility: str                          # public/private
    scan_status: Literal[...]                # pending, scanning, success, error
    artifact_count: int                      # Total detected
    last_sync_at: Optional[datetime]         # Last successful scan
    last_error: Optional[str]                # Error message if failed
    created_at: datetime
    updated_at: datetime
    description: Optional[str]               # User notes (max 500)
    notes: Optional[str]                     # Internal notes (max 2000)
    enable_frontmatter_detection: bool       # Frontmatter parsing enabled
```

---

## 4. Signal Scoring Examples

### Example 1: High-Confidence Skill

```
Path: skills/canvas-design/
Files: SKILL.md, index.ts, package.json, README.md

Scoring Breakdown:
✓ dir_name_score:        0  (name doesn't match patterns)
✓ manifest_score:       20  (SKILL.md present) ← STRONGEST
✓ extensions_score:      5  (3 relevant files, capped at 5)
✓ parent_hint_score:    15  (parent="skills" matches pattern)
✓ container_hint_score: 25  (inside skills/, type=SKILL matches)
✓ depth_penalty:        -1  (depth=2, reduced 50% in container)
────────────────────────────
  raw_total:            64
  normalized:           64/120 * 100 = 53%

BUT if SKILL.md has frontmatter type field:
✓ frontmatter_type:     30  (type: skill in YAML frontmatter)
────────────────────────────
  raw_total:            94
  normalized:           94/120 * 100 = 78%
```

### Example 2: Medium-Confidence Single-File Command

```
Path: commands/git/cm.md
File: cm.md

Scoring Breakdown (Single-File):
✓ container_hint_score: 25  (inside commands/, type=COMMAND)
✓ extensions_score:      5  (.md file)
✓ depth_penalty:        -5  (relative_depth=1, one level: -5)
────────────────────────────
  raw_total:            25
  normalized:           25/120 * 100 = 21%

BUT single-file detection overrides with:
  confidence:           70% (relative_depth=1 case)
```

### Example 3: Low-Confidence (Below Threshold)

```
Path: docs/examples/test-example.md
Files: test-example.md, README.md

Scoring Breakdown:
✓ dir_name_score:       0  (name doesn't match)
✓ manifest_score:       0  (no manifest file)
✓ extensions_score:     2  (one .md file)
✓ parent_hint_score:    0  (parent "docs" or "examples" don't match)
✓ container_hint_score: 0  (not in typed container)
✓ depth_penalty:       -6  (depth=3, not in container)
────────────────────────────
  raw_total:           -4 → clamped to 0
  normalized:          0%

Status: FILTERED OUT (below min_confidence=30)
```

---

## 5. Key Design Decisions

### Decision 1: Manifest-Centric Detection

**Rationale**: SKILL.md presence is authoritative

```python
# Manifest is strongest signal and overrides directory names
if manifest_type and artifact_type != manifest_type:
    artifact_type = manifest_type  # Use manifest type
    match_reasons.append(f"Manifest overrides type to {manifest_type.value}")
```

### Decision 2: Container Propagation

**Rationale**: Artifacts inherit type from parent container

```python
# skills/my-skill/ → type=SKILL from container
# Not: inferred from directory name or files alone
```

### Decision 3: Frontmatter as Strongest Signal

**Rationale**: Explicit metadata trumps heuristics

```python
# frontmatter_type_weight = 30 (highest individual signal)
# If type field found in YAML, add 30 points
```

### Decision 4: Reduced Depth Penalty in Containers

**Rationale**: Prevent penalizing well-organized repos

```python
# commands/dev/subgroup/my-cmd/ should not be heavily penalized
# Depth penalty reduced by 50% when inside typed container
base_penalty // 2  # if container_hint is not None
```

### Decision 5: URL Parameter Persistence

**Rationale**: Shareable filtered views

```typescript
// Filters automatically sync to URL
// User can share: /marketplace/sources/123?type=skill&minConfidence=70
// And filters are restored on load
```

---

## 6. When to Update This Document

- **Confidence thresholds change**: Update "Minimum Confidence Threshold" section
- **New manifest file types added**: Update "Manifest File Detection" section
- **Frontend filters change**: Update "Filters Bar Layout" section
- **Signal weights adjusted**: Update "Multi-Signal Heuristic Scoring" section
- **New detection rules**: Add to "Key Detection Rules" section
- **Response schema changes**: Update API models sections

