# SkillMeat Feature Catalog - Quick Reference

**Last Updated**: 2026-02-17 | **Version**: 0.3.0-beta

Quick lookup guide for screenshots, feature verification, and UI planning.

---

## Pages at a Glance

### Core Collection Features

| Page | Path | Primary Purpose | Key Features |
|------|------|-----------------|--------------|
| **Dashboard** | `/` | Analytics overview | Stats cards, trends, top artifacts |
| **Collection** | `/collection` | Browse artifacts | Grid/List/Grouped views, search, filter, sort |
| **Manage** | `/manage` | Entity-focused view | By type tabs, unified modal detail |
| **Groups** | `/groups` | Group-based browsing | Two-pane layout (sidebar + artifact grid), DnD group assignment, management hub, color/icon metadata |

### Similar Artifacts Detection

**Feature**: Intelligent duplicate and similarity detection with pre-computed caching and optional semantic scoring
**Status**: Implemented (v0.3.0-beta)

| Component | Description |
|-----------|-------------|
| **Similarity Scoring Engine** | Character bigram + BM25 TF-IDF text matching replaces broken string-length-ratio algorithm |
| **Fingerprint Persistence** | Artifact content/structure metadata persisted to DB: `artifact_content_hash`, `artifact_structure_hash`, `artifact_file_count`, `artifact_total_size` |
| **Pre-Filter with FTS5** | SQLite FTS5 full-text search pre-filters candidates for fast narrowing before pairwise scoring |
| **Similarity Cache** | SimilarityCacheManager maintains `similarity_cache` table with pre-computed pair scores, enabling sub-200ms tab loads vs O(n) live computation |
| **Score Breakdown** | Five-component scoring: Text (30%), Keyword (25%), Metadata (15%), Structure (20%), Semantic (10%) with weighted aggregation |
| **Optional Embeddings** | Sentence-transformer embeddings for semantic scoring via `[semantic]` extras; degrades gracefully if not installed |
| **API Enhancements** | `GET /artifacts/{id}/similar` returns SimilarArtifactDTO with score breakdown and cache age; X-Cache headers indicate freshness |
| **Web UI Display** | Artifact detail modal shows Similar Artifacts tab with score breakdown cards (Text, Keyword, Metadata, Structure, Semantic scores), embedding indicator badge, and sorted results |
| **Cache Invalidation** | Automatic refresh on artifact update/sync; manual refresh via `POST /cache/refresh` endpoint |

### Composite Artifacts (Plugins, Stacks, Suites)

**Feature**: Multi-artifact packages with relational model, smart import, deduplication, version pinning
**Status**: Implemented (v0.4.0-dev)

| Component | Description |
|-----------|-------------|
| **ORM Models** | CompositeArtifact, CompositeMembership (junction table with version pinning) |
| **API Endpoints** | /api/v1/composites (20+ CRUD and sync operations) |
| **Import** | Transactional plugin import with atomic guarantees and hash-based deduplication |
| **UI Components** | CompositeArtifactCard, CompositeMembersList, CompositeDetailModal, CompositeMembershipEditor |
| **Discovery** | DiscoveredGraph detects composite structure from repos with parent-child relationships |
| **Integration** | Composite tab in Manage page, "Part of Composites" section in artifact detail, import preview with conflict detection |
| **Sync** | CompositeVersionDiffViewer for per-member diffs, CompositeSyncDialog for batch sync |

### Project & Deployment

| Page | Path | Primary Purpose | Key Features |
|------|------|-----------------|--------------|
| **Projects** | `/projects` | Manage deployments | Create, list, quick detail view |
| **Project Detail** | `/projects/[id]` | Project info | Deployments, config, history |
| **Project Manage** | `/projects/[id]/manage` | Deployment sync | Pull/push collection, drift detection |
| **Deployments** | `/deployments` | Deployment dashboard | Filter by status/type, flat/grouped views |

### Marketplace & Catalog

| Page | Path | Primary Purpose | Key Features |
|------|------|-----------------|--------------|
| **Marketplace** | `/marketplace` | Browse listings | Filter, search, install dialog |
| **Sources** | `/marketplace/sources` | GitHub sources | Add, rescan, semantic tree |
| **Source Detail** | `/marketplace/sources/[id]` | Single source view | Folder tree, artifacts, README |
| **Listing Detail** | `/marketplace/[listing_id]` | Listing view | Details, bundle contents, install |
| **Publish** | `/marketplace/publish` | Publish bundle | Multi-step wizard |

### Configuration & Management

| Page | Path | Primary Purpose | Key Features |
|------|------|-----------------|--------------|
| **Context Entities** | `/context-entities` | Project config | Create, edit, deploy to projects |
| **Templates** | `/templates` | Quick setup | Browse, deploy template wizard |
| **MCP Servers** | `/mcp` | Protocol servers | Add, list, configure |
| **Settings** | `/settings` | App config | GitHub auth, API settings |
| **Sharing** | `/sharing` | Bundle management | Export, import, share links |

---

## Filter & Sort Quick Reference

### Collection Filters

```
Unified Filter Menu:
  • Type:     All | Skill | Command | Agent | MCP | Hook
  • Scope:    All | User | Local
  • Tags:     Multi-select (from available)
  • Groups:   Multi-select (from available)
  • Mode:     AND | OR toggle for combining filters
Search:   Full-text (name, description, tags)
```

### Collection Sort

```
• Confidence (score, desc)
• Name (A-Z, toggle)
• Updated (newest first, toggle)
• Usage Count (most used first, toggle)
```

### View Modes

```
Collection:  Grid (3-col) | List (table) | Grouped
Deployments: Flat | Grouped by Project
Manage:      Grid | List
```

---

## Modal Catalog

### Artifact Operations (18 modals)

| Modal | Trigger | Purpose |
|-------|---------|---------|
| Artifact Detail | Click card/row | View/edit artifact |
| Move to Collection | Dropdown menu | Change collection |
| Add to Group | Dropdown menu | Assign to group |
| Edit Parameters | Dropdown menu | Modify artifact config |
| Delete Artifact | Dropdown menu | Remove artifact |
| View Diff | Sync tab | Show changes |
| Rollback Version | History tab | Revert to old version |
| Link Artifacts | Entity tab | Create artifact link |
| Merge Conflicts | Merge tab | Resolve conflicts |
| Unsaved Changes | Navigate away | Confirm discard |

### Collection Operations (7 modals)

| Modal | Trigger | Purpose |
|-------|---------|---------|
| Create Collection | + button | New collection |
| Edit Collection | Edit button | Modify collection |
| Manage Groups | Manage button | Create/edit groups |
| Copy Group | Group menu | Clone group config |
| Deploy to Project | Deploy button | Select project |
| Sync Collection | Sync button | Update from source |
| Conflict Resolver | Auto-trigger | Handle sync conflicts |

### Marketplace Operations (10 modals)

| Modal | Trigger | Purpose |
|-------|---------|---------|
| Add Source | + button | Add GitHub repo |
| Edit Source | Source menu | Modify source |
| Delete Source | Source menu | Confirm removal |
| Rescan Updates | Rescan button | Review new artifacts |
| Install Listing | Install button | Select strategy |
| Publish Wizard | Publish button | Multi-step publish |
| Exclude Artifact | Exclude button | Hide from import |
| Bulk Tag | Bulk tag button | Tag multiple items |
| Auto Tags | Auto tags button | Generate tags |
| Catalog Entry | Click artifact | View details |

### Project Operations (5 modals)

| Modal | Trigger | Purpose |
|-------|---------|---------|
| Create Project | + button | New project |
| Edit Project | Edit button | Modify settings |
| Delete Project | Delete button | Confirm removal |
| Project Detail | Click project | Quick view |
| Update Available | Alert button | Review updates |

### Other Operations (6 modals)

| Modal | Trigger | Purpose |
|-------|---------|---------|
| Context Entity Editor | New/Edit | Create/edit entity |
| Deploy to Project | Deploy button | Select target |
| Template Deploy | Deploy button | Multi-step deploy |
| Rating Dialog | Rate button | Submit rating |
| MCP Server Form | + button | Add MCP server |
| Export/Import Bundle | Button | Share bundle |

---

## Key Components by Category

### Artifact Display (10)

- UnifiedCard, UnifiedCardActions, EntityCard, EntityRow
- ArtifactGrid, ArtifactList, DeploymentCard
- ScoreBadge, TrustBadges, OutdatedBadge

### Lists & Trees (8)

- EntityList, EntityListWithPagination
- SemanticTree, FileTree, VersionTimeline
- CatalogList, SourceCard, SourceFilterBar

### Editors & Forms (12)

- EntityForm, MCPServerForm, ContextEntityEditor
- TagEditor, ParameterEditorModal, AutoPopulationForm
- MCPEnvEditor, TemplateDeployWizard
- MarketplacePublishWizard, FileCreationDialog

### Filters & Search (8)

- EntityFilters, ContextEntityFilters, MarketplaceFilters
- SourceFilterBar, SearchModeToggle
- TagFilterPopover, GroupFilterSelect, ConfidenceFilter

### Dialogs & Modals (15+)

- See Modal Catalog above

### Sync & Merge (6)

- SyncDialog, ConflictResolver, DiffViewer
- MergeWorkflow, MergePreviewView, ColoredDiffViewer

### Analytics (5)

- AnalyticsGrid, StatsCards
- UsageTrendsWidget, TagMetricsWidget, TopArtifactsWidget

---

## API Endpoint Quick Reference

### Collections & Artifacts (50+ endpoints)

```
GET/POST     /artifacts              List/Create
GET/PUT/DEL  /artifacts/{id}         Get/Update/Delete
POST         /artifacts/{id}/deploy  Deploy
GET          /artifacts/{id}/diff    Show changes
POST         /artifacts/{id}/sync    Sync upstream

GET          /user-collections       List
POST         /user-collections       Create
GET/PUT/DEL  /user-collections/{id}  Get/Update/Delete
GET          /user-collections/{id}/artifacts
```

### Groups & Management (30+ endpoints)

```
GET/POST     /groups                 List/Create
GET/PUT/DEL  /groups/{id}            Get/Update/Delete
GET          /groups/{id}/artifacts  List group artifacts
POST/DEL     /groups/{id}/artifacts  Add/Remove

GET/POST     /tags                   List/Bulk assign
```

### Composites (Plugins, Stacks, Suites) (20+ endpoints)

```
GET/POST     /composites             List/Create
GET/PUT/DEL  /composites/{id}        Get/Update/Delete
GET          /composites/{id}/members  List child artifacts
POST/DEL     /composites/{id}/members  Add/Remove artifact
GET          /composites/{id}/diff   Show version differences
POST         /composites/{id}/sync   Sync all members

GET          /artifacts/{id}/composites  Get parent composites
```

### Projects & Deployments (30+ endpoints)

```
GET/POST     /projects               List/Create
GET/PUT/DEL  /projects/{id}          Get/Update/Delete
GET/POST     /deployments            List/Deploy
GET/PUT/DEL  /deployments/{id}       Get/Update/Delete
POST         /deployments/{id}/sync  Sync
POST         /deployments/{id}/rollback  Revert
```

### Marketplace (25+ endpoints)

```
GET          /marketplace/listings   List listings
GET          /marketplace/listings/{id}  Get detail
POST         /marketplace/listings/{id}/install  Install

GET/POST     /marketplace/sources    List/Add
GET/PUT/DEL  /marketplace/sources/{id}  Get/Update/Delete
POST         /marketplace/sources/{id}/scan  Rescan
GET          /marketplace/sources/{id}/tree  Directory tree

POST         /marketplace/publish    Publish bundle
GET          /marketplace/brokers    List brokers
```

### Context & Templates (20+ endpoints)

```
GET/POST     /context-entities       List/Create
GET/PUT/DEL  /context-entities/{id}  Get/Update/Delete
POST         /context-entities/{id}/deploy  Deploy

GET          /project-templates      List
GET          /project-templates/{id} Get
POST         /project-templates/{id}/deploy  Deploy
```

### MCP & Settings (15+ endpoints)

```
GET/POST     /mcp                    List/Create
GET/PUT/DEL  /mcp/{name}             Get/Update/Delete
POST         /mcp/{name}/deploy      Deploy
POST         /mcp/{name}/test        Test connection

GET/POST     /settings               Get/Update
```

### Analytics (10+ endpoints)

```
GET          /analytics/usage        Usage stats
GET          /analytics/deployments  Deployment stats
GET          /analytics/artifacts/trending  Trending
GET          /analytics/tags/metrics Tag metrics
GET          /analytics/collections/stats  Collection stats
```

---

## Data Structures at a Glance

### Artifact Type

```typescript
{
  id: string
  name: string
  type: 'skill' | 'command' | 'agent' | 'mcp' | 'hook' | 'composite'
  scope: 'user' | 'local'
  syncStatus: 'synced' | 'modified' | 'outdated' | 'conflict' | 'error'
  description?: string
  tags?: string[]
  version?: string
  sourceUrl?: string
  createdAt: ISO8601
  updatedAt: ISO8601
}
```

### Composite Type

```typescript
{
  id: string
  collectionId: string
  name: string
  type: 'composite'
  description?: string
  sourceUrl?: string
  members: CompositeMembership[]  // Child artifacts with version pinning
  createdAt: ISO8601
  updatedAt: ISO8601
}
```

### CompositeType (internal type enum)

```
PLUGIN  - Multi-artifact plugin package
STACK   - Preconfigured stack of artifacts
SUITE   - Organized suite of related artifacts
```

### Collection Type

```typescript
{
  id: string                 // directory name like "default"
  name: string              // display name like "Default Collection"
  description?: string
  artifacts: Artifact[]
  groups?: Group[]
  createdAt: ISO8601
  updatedAt: ISO8601
}
```

### Deployment Type

```typescript
{
  id: string
  artifactId: string
  artifactName: string
  artifactType: ArtifactType
  projectId: string
  projectName: string
  syncStatus: SyncStatus
  version: string
  deployedAt: ISO8601
  lastSyncAt?: ISO8601
}
```

### Marketplace Listing Type

```typescript
{
  listing_id: string
  name: string
  description: string
  brokerId: string
  brokerName: string
  artifacts: string[]
  rating?: number
  downloads?: number
  publishedAt: ISO8601
  updatedAt: ISO8601
}
```

---

## Common UI States

### Empty States

| Context | Message | Icon |
|---------|---------|------|
| No artifacts | "No artifacts" | Package |
| No collections artifacts | "No artifacts in this collection" | Package |
| No search results | "No results found" / "Try adjusting filters" | Search |
| No deployments | "No deployments" | Inbox |
| No templates | "No templates available" | Package |
| No context entities | "No context entities" | FileText |

### Loading States

- Skeleton cards (grid/list)
- Spinner with text "Loading..."
- Progress indicator for operations
- Tooltip showing refresh time

### Error States

- Red alert cards with icon
- Error message and details
- Retry button
- Link to settings/support

### Success States

- Toast notification (2s fade)
- Updated timestamp
- Success badge on element
- Animation/highlight on affected elements

---

## Common Workflows

### Add Artifact to Collection

1. Collection page → Search/browse
2. Click three-dot menu → "Move to Collection"
3. Select target collection
4. Confirm
5. Refresh/Auto-refresh updates display

### Deploy to Project

1. Artifact → Dropdown → "Deploy"
2. OR Deployments → Click artifact → Deploy button
3. Select project
4. Confirm
5. Auto-navigate to deployment or show toast

### Update from Upstream

1. Collection → Filter by "Modified" or "Outdated"
2. Click artifact → Sync tab
3. View diff
4. Click "Sync" or "Pull"
5. Confirm merge strategy (auto/manual)
6. Resolve conflicts if needed
7. Complete sync

### Publish to Marketplace

1. Marketplace → "Publish Bundle" button
2. Step 1: Select artifacts
3. Step 2: Configure bundle metadata
4. Step 3: Choose broker
5. Step 4: Review
6. Step 5: Publish
7. Success confirmation

### Import from GitHub Source

1. Marketplace Sources → "Add Source"
2. Enter GitHub repo URL
3. Configure settings (tags, exclusions)
4. Click "Scan"
5. Review discovered artifacts
6. Accept/exclude items
7. Configure bulk tags
8. Import to collection

---

## Shortcuts & Hotkeys (if implemented)

```
Ctrl/Cmd + K      Search/Command palette
Ctrl/Cmd + S      Save/Sync
Ctrl/Cmd + Z      Undo
Ctrl/Cmd + Y      Redo
Escape             Close modal/dialog
Tab                Navigate focus
Enter              Confirm action
```

---

## Performance Characteristics

### Pagination

- **Infinite Scroll**: 20 items per request, 200px threshold
- **Cursor Pagination**: Base64 encoded, stateless
- **Total Counts**: Shown from first page response

### Caching

- **Collection View**: LocalStorage for view mode preference
- **Projects**: Cache with stale indicator
- **Query Cache**: TanStack Query with 5-min stale time

### Search

- **Full-text**: Client-side for collections
- **FTS5**: Server-side for marketplace sources
- **Debounce**: 300ms for typed search

### Refresh

- **Manual**: User-triggered refresh button
- **Auto**: After mutations (create, update, delete)
- **Live**: Real-time analytics with polling (if enabled)

---

## Accessibility Features

- ARIA labels on icon buttons
- Semantic HTML structure
- Keyboard navigation
- Tab focus management
- Color contrast compliance
- Loading/status announcements
- Role attributes on interactive elements

---

## Theme & Styling

- **Mode**: Light/Dark via Tailwind
- **Color Scheme**: Primary, secondary, accent, destructive
- **Typography**: Inter (sans) + JetBrains Mono (mono)
- **Component Library**: Radix UI + shadcn/ui
- **Icons**: Lucide React
- **Spacing**: Tailwind scale (4px base unit)
- **Breakpoints**: sm (640px), md (768px), lg (1024px), xl (1280px)

---

End of Quick Reference
