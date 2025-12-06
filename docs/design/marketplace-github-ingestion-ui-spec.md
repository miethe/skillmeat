---
title: GitHub Marketplace Ingestion - UI Design Specification
version: 1.0.0
created: 2025-12-06
status: draft
author: ui-designer
---

# GitHub Marketplace Ingestion - UI Design Specification

## Overview

This specification defines the UI layer for the GitHub marketplace ingestion feature in SkillMeat's Next.js web interface. The design emphasizes rapid implementation using shadcn/ui components, Radix UI primitives, and TanStack Query for data management.

**Design Philosophy**:
- Mobile-first responsive design
- Component reuse from @meaty/ui package
- Optimistic UI updates for instant feedback
- Accessible by default (WCAG 2.1 AA)
- Minimal custom components (leverage shadcn/ui)

---

## Architecture Overview

### Technology Stack
- **Framework**: Next.js 15 (App Router)
- **UI Components**: Radix UI + shadcn/ui
- **Styling**: TailwindCSS
- **Data Fetching**: TanStack Query (React Query v5)
- **State Management**: React hooks + URL state
- **Form Handling**: react-hook-form + Zod validation
- **Animations**: Framer Motion (optional, for stepper transitions)

### File Structure

```
skillmeat/web/
├── app/
│   └── (main)/
│       └── marketplace/
│           ├── page.tsx                    # Marketplace list page
│           ├── [id]/
│           │   └── page.tsx               # Source detail page
│           ├── loading.tsx                 # Loading state
│           └── error.tsx                   # Error boundary
│
├── components/
│   └── marketplace/
│       ├── source-card.tsx                 # GitHub source card
│       ├── source-status-badge.tsx         # Status indicator
│       ├── add-source-modal/
│       │   ├── index.tsx                  # Modal wrapper
│       │   ├── step-1-repository.tsx      # Repository input
│       │   ├── step-2-scan-preview.tsx    # Scan results
│       │   ├── step-3-manual-catalog.tsx  # Manual overrides
│       │   ├── step-4-review.tsx          # Final review
│       │   └── stepper-context.tsx        # Shared state
│       ├── artifact-catalog/
│       │   ├── catalog-grid.tsx           # Artifact grid
│       │   ├── catalog-card.tsx           # Artifact card
│       │   ├── catalog-filters.tsx        # Filter bar
│       │   └── status-chip.tsx            # Catalog status chip
│       └── shared/
│           ├── github-link.tsx            # GitHub icon + link
│           ├── trust-badge.tsx            # Trust level badge
│           └── rescan-button.tsx          # Rescan action
│
├── hooks/
│   └── marketplace/
│       ├── use-marketplace-sources.ts     # Sources CRUD
│       ├── use-source-artifacts.ts        # Artifacts listing
│       ├── use-source-scan.ts             # Scan/rescan
│       └── use-import-artifacts.ts        # Import action
│
└── types/
    └── marketplace.ts                      # TypeScript interfaces
```

---

## Component Specifications

### 1. Marketplace List Page (`/marketplace`)

**Route**: `/marketplace`

#### Layout Structure

```
┌─────────────────────────────────────────────────────┐
│ Header                                              │
│ ┌─────────────────────────────────────────────┐   │
│ │ Marketplace                          [Add +] │   │
│ │ Discover and manage GitHub artifact sources │   │
│ └─────────────────────────────────────────────┘   │
│                                                     │
│ ┌─────────────────────────────────────────────┐   │
│ │ Source Card 1                               │   │
│ │ [GitHub Icon] anthropics/quickstarts        │   │
│ │ Skills: 12 | Commands: 5 | Agents: 3        │   │
│ │ Last sync: 2 hours ago      [Updated] ⚡    │   │
│ │ [Rescan] [Open →]                           │   │
│ └─────────────────────────────────────────────┘   │
│ ┌─────────────────────────────────────────────┐   │
│ │ Source Card 2                               │   │
│ └─────────────────────────────────────────────┘   │
│ ┌─────────────────────────────────────────────┐   │
│ │ Source Card 3                               │   │
│ └─────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────┘
```

#### Component Props

**SourceCard Component**:
```typescript
interface SourceCardProps {
  source: GitHubSource;
  onRescan: (sourceId: string) => void;
  onViewDetails: (sourceId: string) => void;
}

interface GitHubSource {
  id: string;
  owner: string;
  repo: string;
  branch: string;
  rootHint?: string;
  lastSyncAt: string;
  status: 'active' | 'error' | 'scanning';
  errorMessage?: string;
  trustLevel: 'basic' | 'verified' | 'official';
  artifactCounts: {
    skills: number;
    commands: number;
    agents: number;
    mcpServers: number;
    hooks: number;
  };
  // Status indicators
  hasNewArtifacts: boolean;
  hasUpdatedArtifacts: boolean;
}
```

#### Visual Design

**Card Layout** (Mobile-first):
- Minimum height: 160px
- Border: 1px solid `border`
- Border radius: `rounded-lg` (8px)
- Padding: `p-4` (16px)
- Hover: Subtle shadow lift (`hover:shadow-md`)
- Transition: `transition-shadow duration-200`

**Status Badges**:
- **New**: Green outline badge with pulse animation
  - Border: `border-green-500`
  - Background: `bg-green-50 dark:bg-green-950`
  - Text: `text-green-700 dark:text-green-300`

- **Updated**: Blue outline badge
  - Border: `border-blue-500`
  - Background: `bg-blue-50 dark:bg-blue-950`
  - Text: `text-blue-700 dark:text-blue-300`

- **Error**: Red solid badge
  - Background: `bg-red-500`
  - Text: `text-white`

**Trust Level Badges**:
- **Basic**: Gray outline
  - `border-gray-300 text-gray-600`

- **Verified**: Blue with checkmark icon
  - `bg-blue-500 text-white` + Shield check icon

- **Official**: Purple with star icon
  - `bg-purple-500 text-white` + Star icon

**Artifact Counts**:
- Display as inline chips
- Format: `Skills: 12` with icon
- Use subtle background: `bg-muted`
- Text size: `text-sm`

#### States to Design

**1. Loading State** (Skeleton):
```tsx
// Use shadcn/ui Skeleton component
<div className="space-y-4">
  <Skeleton className="h-40 w-full" />
  <Skeleton className="h-40 w-full" />
  <Skeleton className="h-40 w-full" />
</div>
```

**2. Empty State**:
```
┌─────────────────────────────────────────────┐
│                                             │
│        [GitHub Icon - Large]                │
│                                             │
│     No GitHub Sources Added                 │
│                                             │
│  Add your first GitHub repository to        │
│  discover and manage Claude artifacts       │
│                                             │
│        [Add Source Button]                  │
│                                             │
└─────────────────────────────────────────────┘
```

**3. Error State**:
```tsx
// Use Alert component from shadcn/ui
<Alert variant="destructive">
  <AlertCircle className="h-4 w-4" />
  <AlertTitle>Failed to load sources</AlertTitle>
  <AlertDescription>
    {errorMessage}
    <Button variant="link" onClick={retry}>Try again</Button>
  </AlertDescription>
</Alert>
```

#### Responsive Breakpoints

- **Mobile** (<768px): Single column, stacked cards
- **Tablet** (768-1024px): 2 columns grid
- **Desktop** (>1024px): 3 columns grid

```css
/* Grid classes */
.marketplace-grid {
  @apply grid gap-4;
  @apply grid-cols-1 md:grid-cols-2 lg:grid-cols-3;
}
```

---

### 2. Add Source Modal (Multi-Step)

**Trigger**: "Add Source" button on marketplace page

#### Component Architecture

**Modal Wrapper**:
```typescript
interface AddSourceModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess: (source: GitHubSource) => void;
}

interface StepperState {
  currentStep: number;
  totalSteps: 4;
  formData: {
    repositoryUrl: string;
    branch: string;
    rootHint?: string;
    personalAccessToken?: string;
    scanResults?: ScanPreview;
    manualPaths?: ManualCatalogEntry[];
  };
}
```

#### Step 1: Repository Information

**Layout**:
```
┌────────────────────────────────────────────┐
│ Add GitHub Source                     [×]  │
│ ──────────────────────────────────────────│
│ Step 1 of 4: Repository Information       │
│                                            │
│ GitHub Repository URL *                    │
│ ┌────────────────────────────────────┐    │
│ │ https://github.com/owner/repo      │    │
│ └────────────────────────────────────┘    │
│ ✓ Valid repository URL                     │
│                                            │
│ Branch/Tag/SHA                             │
│ ┌────────────────────────────────────┐    │
│ │ main                        [▼]    │    │
│ └────────────────────────────────────┘    │
│                                            │
│ Root Directory Hint (optional)             │
│ ┌────────────────────────────────────┐    │
│ │ /artifacts                         │    │
│ └────────────────────────────────────┘    │
│ Scan only this subdirectory                │
│                                            │
│ Personal Access Token (optional)           │
│ ┌────────────────────────────────────┐    │
│ │ ●●●●●●●●●●●●●●●●               [👁]│    │
│ └────────────────────────────────────┘    │
│ Required for private repositories          │
│                                            │
│ ──────────────────────────────────────────│
│                    [Cancel]  [Next →]     │
└────────────────────────────────────────────┘
```

**Validation Rules**:
```typescript
const step1Schema = z.object({
  repositoryUrl: z.string()
    .url('Must be a valid URL')
    .regex(/^https:\/\/github\.com\/[^\/]+\/[^\/]+\/?$/,
           'Must be a GitHub repository URL'),
  branch: z.string()
    .min(1, 'Branch is required')
    .default('main'),
  rootHint: z.string().optional(),
  personalAccessToken: z.string().optional(),
});
```

**Real-time Validation**:
- URL validation on blur
- Show checkmark icon when valid
- Show error message below input when invalid
- Disable "Next" button until valid

**UI Components**:
- `Dialog` from shadcn/ui
- `Input` with validation states
- `Select` for branch dropdown
- `Label` with required indicator
- Custom password input with show/hide toggle

#### Step 2: Scan Results Preview

**Layout**:
```
┌────────────────────────────────────────────┐
│ Add GitHub Source                     [×]  │
│ ──────────────────────────────────────────│
│ Step 2 of 4: Scan Preview                 │
│                                            │
│ Scanning anthropics/quickstarts...         │
│ ┌────────────────────────────────────┐    │
│ │ [▓▓▓▓▓▓▓▓░░░░░░░] 65%             │    │
│ └────────────────────────────────────┘    │
│                                            │
│ Detected Artifacts (15 total)              │
│                                            │
│ Skills (12) - High confidence              │
│ ├─ canvas-design         [95%] ✓          │
│ ├─ document-analyzer     [88%] ✓          │
│ ├─ code-reviewer         [82%] ✓          │
│ ├─ ...and 9 more                           │
│                                            │
│ Commands (3) - Medium confidence           │
│ ├─ git-helper           [65%] ✓           │
│ ├─ file-ops             [58%] ⚠           │
│ ├─ ...and 1 more                           │
│                                            │
│ [Show All Artifacts]                       │
│                                            │
│ ⓘ Low confidence items may need manual     │
│   verification in Step 3                   │
│                                            │
│ ──────────────────────────────────────────│
│         [← Back]  [Skip]  [Continue →]    │
└────────────────────────────────────────────┘
```

**Scan States**:

1. **Scanning** (Initial):
   - Progress bar with percentage
   - "Scanning..." text with animated dots
   - Disable all buttons except Cancel

2. **Completed**:
   - Show categorized results
   - Group by artifact type
   - Display confidence scores
   - Enable Continue button

3. **Error**:
   - Show error alert
   - Offer "Retry Scan" button
   - Allow "Skip" to manual entry

**Confidence Indicators**:
- **High** (>80%): Green checkmark `✓`
- **Medium** (50-80%): Yellow warning `⚠`
- **Low** (<50%): Gray question mark `?`

**Collapsible Lists**:
- Show first 3 items per category
- "...and N more" link to expand
- Use Accordion from shadcn/ui

#### Step 3: Manual Catalog Override (Optional)

**Layout**:
```
┌────────────────────────────────────────────┐
│ Add GitHub Source                     [×]  │
│ ──────────────────────────────────────────│
│ Step 3 of 4: Manual Catalog (Optional)    │
│                                            │
│ Override or supplement detected paths      │
│                                            │
│ ┌──────────────────────────────────────┐  │
│ │ Artifact Type: [Skills ▼]           │  │
│ │                                      │  │
│ │ Detected Paths (12):                 │  │
│ │ ┌────────────────────────────┐       │  │
│ │ │ ✓ /skills/canvas.md        │ [×]  │  │
│ │ │ ✓ /skills/analyzer.md      │ [×]  │  │
│ │ │ ⚠ /docs/skill-example.md   │ [×]  │  │
│ │ └────────────────────────────┘       │  │
│ │                                      │  │
│ │ [+ Add Custom Path]                  │  │
│ └──────────────────────────────────────┘  │
│                                            │
│ ⓘ Most users can skip this step and use   │
│   automatic detection                      │
│                                            │
│ ──────────────────────────────────────────│
│         [← Back]  [Skip]  [Continue →]    │
└────────────────────────────────────────────┘
```

**Features**:
- Filter by artifact type (tabs or dropdown)
- Checkbox to include/exclude detected paths
- Add custom paths manually
- Delete/edit custom entries
- Visual indication of confidence level

**UI Components**:
- `Tabs` or `Select` for artifact type filter
- `Checkbox` for path selection
- `Input` + `Button` for adding custom paths
- `ScrollArea` for long path lists

#### Step 4: Review & Create

**Layout**:
```
┌────────────────────────────────────────────┐
│ Add GitHub Source                     [×]  │
│ ──────────────────────────────────────────│
│ Step 4 of 4: Review & Create               │
│                                            │
│ Repository Details                         │
│ ┌────────────────────────────────────┐    │
│ │ Repository: anthropics/quickstarts │    │
│ │ Branch: main                       │    │
│ │ Root Directory: /                  │    │
│ │ Authentication: ✓ Token provided   │    │
│ └────────────────────────────────────┘    │
│                                            │
│ Artifacts to Catalog                       │
│ ┌────────────────────────────────────┐    │
│ │ Skills: 12 artifacts               │    │
│ │ Commands: 3 artifacts              │    │
│ │ Agents: 0 artifacts                │    │
│ │                                    │    │
│ │ Total: 15 artifacts                │    │
│ └────────────────────────────────────┘    │
│                                            │
│ ✓ Ready to create source                   │
│                                            │
│ ──────────────────────────────────────────│
│         [← Back]       [Create Source]    │
└────────────────────────────────────────────┘
```

**States**:

1. **Ready**: Enable "Create Source" button
2. **Creating**: Show spinner, disable button
3. **Success**: Close modal, show toast notification
4. **Error**: Show inline error, keep modal open

**Success Flow**:
```typescript
// Optimistic update pattern
const { mutate, isPending } = useCreateSource({
  onMutate: async (newSource) => {
    // Cancel outgoing refetches
    await queryClient.cancelQueries({ queryKey: ['sources'] });

    // Snapshot previous value
    const previousSources = queryClient.getQueryData(['sources']);

    // Optimistically update cache
    queryClient.setQueryData(['sources'], (old) => [
      ...old,
      { ...newSource, id: 'temp-id', status: 'scanning' }
    ]);

    return { previousSources };
  },
  onError: (err, newSource, context) => {
    // Rollback on error
    queryClient.setQueryData(['sources'], context.previousSources);
  },
  onSuccess: () => {
    // Invalidate and refetch
    queryClient.invalidateQueries({ queryKey: ['sources'] });
  },
});
```

#### Stepper Navigation

**Progress Indicator**:
```
Step 1        Step 2        Step 3        Step 4
  ●────────────○────────────○────────────○
Repository   Scan Preview  Catalog      Review
```

**Visual Design**:
- Active step: Filled circle with primary color
- Completed step: Filled circle with checkmark
- Future step: Outlined circle
- Connecting line: Dashed for future, solid for past

**Navigation Rules**:
- Can go back to any previous step
- Cannot skip ahead (except Step 3)
- Step 3 is optional (can skip)
- Validate before proceeding to next step

---

### 3. Source Detail Page (`/marketplace/[id]`)

**Route**: `/marketplace/[id]`

#### Layout Structure

```
┌─────────────────────────────────────────────────────┐
│ ← Back to Marketplace                               │
│                                                     │
│ ┌─────────────────────────────────────────────┐   │
│ │ [GitHub Icon] anthropics/quickstarts        │   │
│ │ main branch | Last sync: 2 hours ago       │   │
│ │ [GitHub Link ↗] [Rescan] [Delete]          │   │
│ │ ─────────────────────────────────────────── │   │
│ │ Status: Active | Trust Level: Verified ✓   │   │
│ └─────────────────────────────────────────────┘   │
│                                                     │
│ ┌─────────────────────────────────────────────┐   │
│ │ Filters & Search                            │   │
│ │ [Search...] [Type ▼] [Status ▼] [Clear]   │   │
│ └─────────────────────────────────────────────┘   │
│                                                     │
│ ┌───────────┬───────────┬───────────┐             │
│ │ Canvas    │ Analyzer  │ Reviewer  │             │
│ │ Skill     │ Skill     │ Skill     │             │
│ │ [New] 95% │ [Updated] │ 82%       │             │
│ │ [Import]  │ [Import]  │ [Import]  │             │
│ └───────────┴───────────┴───────────┘             │
│                                                     │
│ ... more artifact cards ...                        │
│                                                     │
│ Showing 15 of 15 artifacts                         │
└─────────────────────────────────────────────────────┘
```

#### Header Section

**Component Props**:
```typescript
interface SourceHeaderProps {
  source: GitHubSource;
  onRescan: () => void;
  onDelete: () => void;
}
```

**Visual Elements**:
- Repository name as H1 heading
- GitHub icon + external link
- Branch and sync timestamp
- Action buttons (Rescan, Delete)
- Status indicators
- Error message if last sync failed

**Error State**:
```tsx
<Alert variant="destructive">
  <AlertCircle className="h-4 w-4" />
  <AlertTitle>Last sync failed</AlertTitle>
  <AlertDescription>
    {errorMessage}
    <Button variant="link" onClick={handleRescan}>
      Rescan now
    </Button>
  </AlertDescription>
</Alert>
```

#### Filter Bar

**Component Props**:
```typescript
interface CatalogFiltersProps {
  onFilterChange: (filters: CatalogFilters) => void;
  counts: {
    total: number;
    filtered: number;
  };
}

interface CatalogFilters {
  search: string;
  artifactTypes: ArtifactType[];
  statuses: CatalogStatus[];
  confidenceLevels: ('high' | 'medium' | 'low')[];
}

type CatalogStatus = 'new' | 'updated' | 'imported' | 'removed';
```

**Layout**:
```
┌─────────────────────────────────────────────────┐
│ [🔍 Search artifacts...]                        │
│                                                 │
│ Type: [All ▼] Status: [All ▼] Confidence: [▼] │
│                                         [Clear] │
└─────────────────────────────────────────────────┘
```

**Filter Components**:
- Search input with debounce (300ms)
- Type multi-select (pills or dropdown)
- Status multi-select
- Confidence slider or dropdown
- Clear all filters button

**Active Filters Display**:
```
┌─────────────────────────────────────────────────┐
│ Active Filters:                                 │
│ [Skills ×] [New ×] [High Confidence ×]         │
└─────────────────────────────────────────────────┘
```

#### Artifact Catalog Grid

**Component Props**:
```typescript
interface CatalogGridProps {
  artifacts: CatalogEntry[];
  isLoading: boolean;
  onImport: (artifactId: string) => void;
}

interface CatalogEntry {
  id: string;
  name: string;
  type: ArtifactType;
  path: string;
  status: CatalogStatus;
  confidence: number;
  upstreamUrl: string;
  lastDetected: string;
  importedAt?: string;
  hasUpstreamChanges: boolean;
}
```

**Grid Layout**:
- Responsive grid (same as marketplace page)
- Cards show artifact details
- Import action button
- Status chips

**Empty States**:

1. **No artifacts found**:
```
┌─────────────────────────────────────────────┐
│        [Magnifying Glass Icon]              │
│                                             │
│     No artifacts match your filters         │
│                                             │
│  Try adjusting your search or filters       │
│                                             │
│        [Clear Filters]                      │
└─────────────────────────────────────────────┘
```

2. **Source has no artifacts**:
```
┌─────────────────────────────────────────────┐
│        [Empty Box Icon]                     │
│                                             │
│     No artifacts detected                   │
│                                             │
│  This repository doesn't contain any        │
│  recognized Claude artifacts                │
│                                             │
│        [Rescan]                             │
└─────────────────────────────────────────────┘
```

---

### 4. Artifact Catalog Card

**Component Design**:

```
┌─────────────────────────────────────┐
│ Canvas Design                       │
│ ─────────────────────────────────── │
│ Type: Skill                   [New] │
│ Confidence: 95%              ⚡ High │
│                                     │
│ /skills/canvas-design.md            │
│ [GitHub ↗]                          │
│                                     │
│ ───────────────────────────────────  │
│                        [Import →]   │
└─────────────────────────────────────┘
```

**Component Props**:
```typescript
interface CatalogCardProps {
  artifact: CatalogEntry;
  onImport: () => void;
  isImporting?: boolean;
}
```

**Visual Design**:
- Card container with border
- Artifact name as card title
- Type badge (using existing artifact type chips)
- Status chip (new, updated, imported, removed)
- Confidence indicator with visual coding
- File path in monospace font
- GitHub link to source file
- Import button (primary action)

**Status Chips**:

```typescript
interface StatusChipProps {
  status: CatalogStatus;
  variant?: 'default' | 'compact';
}
```

**Chip Styles**:

| Status | Color | Border | Background | Icon |
|--------|-------|--------|------------|------|
| New | green-500 | outline | green-50 | Sparkles |
| Updated | blue-500 | outline | blue-50 | ArrowUpCircle |
| Imported | green-600 | solid | green-600 | CheckCircle |
| Removed | gray-400 | solid | gray-100 | XCircle |

**Confidence Indicators**:

| Level | Range | Color | Icon |
|-------|-------|-------|------|
| High | >80% | green-600 | CheckCircle2 |
| Medium | 50-80% | yellow-600 | AlertCircle |
| Low | <50% | gray-500 | HelpCircle |

**Import Button States**:

1. **Default**: `Import →`
   - Primary button variant
   - Enabled and ready

2. **Importing**: `Importing...`
   - Disabled with spinner
   - Loading state

3. **Imported**: `Re-import`
   - Secondary variant
   - Different text for already imported

4. **Error**: `Import Failed`
   - Destructive variant
   - Click to retry

---

### 5. Shared Components

#### GitHub Link Component

**Usage**:
```tsx
<GitHubLink
  owner="anthropics"
  repo="quickstarts"
  path="/skills/canvas.md"
  branch="main"
/>
```

**Design**:
- GitHub icon (from lucide-react)
- Truncated path if too long
- External link icon
- Opens in new tab
- Hover state shows full path in tooltip

#### Trust Badge Component

**Component Props**:
```typescript
interface TrustBadgeProps {
  level: 'basic' | 'verified' | 'official';
  size?: 'sm' | 'md' | 'lg';
}
```

**Visual Design**:

| Level | Icon | Color | Description |
|-------|------|-------|-------------|
| Basic | Shield | gray-500 | Default trust level |
| Verified | ShieldCheck | blue-500 | Verified publisher |
| Official | Star | purple-500 | Official Anthropic source |

#### Rescan Button Component

**Component Props**:
```typescript
interface RescanButtonProps {
  sourceId: string;
  onRescan: () => void;
  isScanning?: boolean;
}
```

**States**:
1. **Idle**: `Rescan` button
2. **Scanning**: `Scanning...` with spinner
3. **Success**: Brief checkmark, then back to Idle
4. **Error**: Red error state with tooltip

---

## Data Fetching & State Management

### React Query Hooks

#### 1. useMarketplaceSources

**File**: `hooks/marketplace/use-marketplace-sources.ts`

```typescript
export function useMarketplaceSources() {
  return useQuery({
    queryKey: ['marketplace', 'sources'],
    queryFn: async () => {
      const response = await fetch('/api/v1/marketplace/sources');
      if (!response.ok) throw new Error('Failed to fetch sources');
      return response.json();
    },
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}

export function useMarketplaceSource(sourceId: string) {
  return useQuery({
    queryKey: ['marketplace', 'sources', sourceId],
    queryFn: async () => {
      const response = await fetch(`/api/v1/marketplace/sources/${sourceId}`);
      if (!response.ok) throw new Error('Failed to fetch source');
      return response.json();
    },
    enabled: !!sourceId,
  });
}

export function useCreateSource() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: CreateSourceRequest) => {
      const response = await fetch('/api/v1/marketplace/sources', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      });
      if (!response.ok) throw new Error('Failed to create source');
      return response.json();
    },
    onMutate: async (newSource) => {
      // Optimistic update (see Step 4 implementation above)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['marketplace', 'sources'] });
    },
  });
}

export function useDeleteSource() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (sourceId: string) => {
      const response = await fetch(`/api/v1/marketplace/sources/${sourceId}`, {
        method: 'DELETE',
      });
      if (!response.ok) throw new Error('Failed to delete source');
      return response.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['marketplace', 'sources'] });
    },
  });
}
```

#### 2. useSourceScan

**File**: `hooks/marketplace/use-source-scan.ts`

```typescript
export function useSourceScan(sourceId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async () => {
      const response = await fetch(
        `/api/v1/marketplace/sources/${sourceId}/rescan`,
        { method: 'POST' }
      );
      if (!response.ok) throw new Error('Failed to trigger rescan');
      return response.json();
    },
    onMutate: async () => {
      // Update source status to 'scanning'
      queryClient.setQueryData(
        ['marketplace', 'sources', sourceId],
        (old: any) => ({ ...old, status: 'scanning' })
      );
    },
    onSuccess: () => {
      // Poll for scan completion
      queryClient.invalidateQueries({
        queryKey: ['marketplace', 'sources', sourceId]
      });
    },
  });
}

// Hook for initial scan in Add Source modal
export function useInitialScan() {
  return useMutation({
    mutationFn: async (params: ScanParams) => {
      const response = await fetch('/api/v1/marketplace/scan-preview', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(params),
      });
      if (!response.ok) throw new Error('Failed to scan repository');
      return response.json();
    },
  });
}
```

#### 3. useSourceArtifacts

**File**: `hooks/marketplace/use-source-artifacts.ts`

```typescript
export function useSourceArtifacts(
  sourceId: string,
  filters?: CatalogFilters
) {
  const queryParams = new URLSearchParams();

  if (filters?.search) {
    queryParams.set('search', filters.search);
  }
  if (filters?.artifactTypes?.length) {
    filters.artifactTypes.forEach(type =>
      queryParams.append('type', type)
    );
  }
  if (filters?.statuses?.length) {
    filters.statuses.forEach(status =>
      queryParams.append('status', status)
    );
  }

  return useQuery({
    queryKey: ['marketplace', 'sources', sourceId, 'artifacts', filters],
    queryFn: async () => {
      const url = `/api/v1/marketplace/sources/${sourceId}/artifacts?${queryParams}`;
      const response = await fetch(url);
      if (!response.ok) throw new Error('Failed to fetch artifacts');
      return response.json();
    },
    enabled: !!sourceId,
    staleTime: 2 * 60 * 1000, // 2 minutes
  });
}
```

#### 4. useImportArtifacts

**File**: `hooks/marketplace/use-import-artifacts.ts`

```typescript
export function useImportArtifact(sourceId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (artifactId: string) => {
      const response = await fetch(
        `/api/v1/marketplace/sources/${sourceId}/import`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ artifact_ids: [artifactId] }),
        }
      );
      if (!response.ok) throw new Error('Failed to import artifact');
      return response.json();
    },
    onMutate: async (artifactId) => {
      // Optimistically update artifact status
      const queryKey = ['marketplace', 'sources', sourceId, 'artifacts'];
      const previous = queryClient.getQueryData(queryKey);

      queryClient.setQueryData(queryKey, (old: any) => ({
        ...old,
        artifacts: old.artifacts.map((a: any) =>
          a.id === artifactId ? { ...a, status: 'imported' } : a
        ),
      }));

      return { previous };
    },
    onError: (err, artifactId, context) => {
      // Rollback on error
      if (context?.previous) {
        queryClient.setQueryData(
          ['marketplace', 'sources', sourceId, 'artifacts'],
          context.previous
        );
      }
    },
    onSuccess: () => {
      // Invalidate both catalog and collection queries
      queryClient.invalidateQueries({
        queryKey: ['marketplace', 'sources', sourceId, 'artifacts']
      });
      queryClient.invalidateQueries({
        queryKey: ['collection', 'artifacts']
      });
    },
  });
}

export function useBulkImportArtifacts(sourceId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (artifactIds: string[]) => {
      const response = await fetch(
        `/api/v1/marketplace/sources/${sourceId}/import`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ artifact_ids: artifactIds }),
        }
      );
      if (!response.ok) throw new Error('Failed to import artifacts');
      return response.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ['marketplace', 'sources', sourceId]
      });
    },
  });
}
```

### URL State Management

**Use search params for filters** (shareable URLs):

```typescript
// In catalog filters component
import { useSearchParams, useRouter } from 'next/navigation';

function CatalogFilters() {
  const router = useRouter();
  const searchParams = useSearchParams();

  const updateFilters = (newFilters: Partial<CatalogFilters>) => {
    const params = new URLSearchParams(searchParams);

    // Update search param
    if (newFilters.search !== undefined) {
      if (newFilters.search) {
        params.set('search', newFilters.search);
      } else {
        params.delete('search');
      }
    }

    // Update type filters
    if (newFilters.artifactTypes) {
      params.delete('type');
      newFilters.artifactTypes.forEach(type => {
        params.append('type', type);
      });
    }

    router.push(`?${params.toString()}`);
  };

  return (
    // Filter UI components
  );
}
```

---

## Accessibility Requirements

### Keyboard Navigation

**All interactive elements must be keyboard accessible**:

1. **Tab Order**:
   - Cards should be tabbable
   - Action buttons in logical order
   - Modal stepper navigation

2. **Focus Indicators**:
   - Visible focus ring on all interactive elements
   - Use Tailwind's `focus:ring-2 focus:ring-primary`

3. **Keyboard Shortcuts**:
   - `Escape` to close modals
   - `Enter` to submit forms
   - Arrow keys for navigation (where applicable)

### ARIA Labels

**Required ARIA attributes**:

```tsx
// Source card
<article
  aria-label={`GitHub source: ${owner}/${repo}`}
  role="article"
>
  {/* Card content */}
</article>

// Status badge
<span
  aria-label={`Status: ${status}`}
  role="status"
>
  {/* Badge content */}
</span>

// Import button
<button
  aria-label={`Import ${artifactName}`}
  aria-busy={isImporting}
  aria-disabled={isImporting}
>
  {isImporting ? 'Importing...' : 'Import'}
</button>

// Filter bar
<div role="search" aria-label="Filter artifacts">
  <input
    type="search"
    aria-label="Search artifacts by name"
    placeholder="Search artifacts..."
  />
</div>
```

### Screen Reader Support

**Announce dynamic updates**:

```tsx
// Use aria-live for status updates
<div
  role="status"
  aria-live="polite"
  aria-atomic="true"
  className="sr-only"
>
  {statusMessage}
</div>

// Loading states
<div aria-busy="true" aria-label="Loading sources">
  <Skeleton />
</div>
```

### Color Contrast

**WCAG 2.1 AA Requirements**:
- Text contrast: 4.5:1 minimum
- Large text (18pt+): 3:1 minimum
- Interactive elements: 3:1 minimum

**Use Tailwind's contrast-safe colors**:
- Avoid pure grays (use slate/zinc)
- Test with dark mode
- Use semantic color variables

---

## Responsive Design

### Breakpoint Strategy

**Mobile-first approach**:

```css
/* Base (mobile): <768px */
.marketplace-grid {
  @apply grid-cols-1 gap-4;
}

/* Tablet: 768px - 1024px */
@media (min-width: 768px) {
  .marketplace-grid {
    @apply grid-cols-2 gap-6;
  }
}

/* Desktop: >1024px */
@media (min-width: 1024px) {
  .marketplace-grid {
    @apply grid-cols-3 gap-6;
  }
}

/* Large desktop: >1536px */
@media (min-width: 1536px) {
  .marketplace-grid {
    @apply grid-cols-4;
  }
}
```

### Component Adaptations

**Source Card**:
- Mobile: Full width, stacked layout
- Tablet: 2-column grid
- Desktop: 3-column grid

**Add Source Modal**:
- Mobile: Full screen modal
- Tablet/Desktop: Centered modal with max-width

**Filter Bar**:
- Mobile: Collapsible drawer
- Tablet/Desktop: Inline filter bar

**Catalog Grid**:
- Mobile: Single column
- Tablet: 2 columns
- Desktop: 3-4 columns

### Touch Targets

**Minimum tap target size**: 44x44px (iOS), 48x48px (Android)

```tsx
// Button sizing
<Button
  size="lg"          // Ensures minimum touch target
  className="min-h-[44px] min-w-[44px]"
>
  Import
</Button>

// Card interactive area
<Card
  className="cursor-pointer p-4 min-h-[88px]"
  onClick={handleClick}
>
  {/* Card content */}
</Card>
```

---

## Loading & Error States

### Loading Patterns

**1. Skeleton Loaders**:
```tsx
// Card skeleton
<div className="space-y-4">
  <Skeleton className="h-10 w-3/4" />  {/* Title */}
  <Skeleton className="h-4 w-full" />   {/* Description line 1 */}
  <Skeleton className="h-4 w-5/6" />    {/* Description line 2 */}
  <div className="flex gap-2">
    <Skeleton className="h-6 w-16" />   {/* Badge */}
    <Skeleton className="h-6 w-16" />   {/* Badge */}
  </div>
  <Skeleton className="h-10 w-full" />  {/* Button */}
</div>
```

**2. Spinner for Actions**:
```tsx
import { Loader2 } from 'lucide-react';

<Button disabled={isLoading}>
  {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
  {isLoading ? 'Importing...' : 'Import'}
</Button>
```

**3. Progress Bars**:
```tsx
// Scan progress
<Progress value={scanProgress} className="w-full" />
<p className="text-sm text-muted-foreground">
  Scanning... {scanProgress}%
</p>
```

### Error Handling

**1. Inline Errors** (Form validation):
```tsx
<div>
  <Input
    {...register('repositoryUrl')}
    aria-invalid={!!errors.repositoryUrl}
  />
  {errors.repositoryUrl && (
    <p className="text-sm text-destructive mt-1">
      {errors.repositoryUrl.message}
    </p>
  )}
</div>
```

**2. Alert Banners** (API errors):
```tsx
{error && (
  <Alert variant="destructive">
    <AlertCircle className="h-4 w-4" />
    <AlertTitle>Error</AlertTitle>
    <AlertDescription>
      {error.message}
      <Button
        variant="link"
        onClick={retry}
        className="ml-2"
      >
        Try again
      </Button>
    </AlertDescription>
  </Alert>
)}
```

**3. Toast Notifications** (Success/Error feedback):
```tsx
import { useToast } from '@/components/ui/use-toast';

const { toast } = useToast();

// Success
toast({
  title: 'Source created',
  description: 'Successfully added GitHub source',
});

// Error
toast({
  title: 'Import failed',
  description: error.message,
  variant: 'destructive',
});
```

**4. Error Boundaries** (Component-level errors):
```tsx
// app/marketplace/error.tsx
'use client';

export default function Error({
  error,
  reset,
}: {
  error: Error;
  reset: () => void;
}) {
  return (
    <div className="flex flex-col items-center justify-center min-h-[400px]">
      <h2 className="text-2xl font-bold mb-4">Something went wrong</h2>
      <p className="text-muted-foreground mb-4">{error.message}</p>
      <Button onClick={reset}>Try again</Button>
    </div>
  );
}
```

---

## Animation & Transitions

### Micro-interactions

**Card Hover**:
```tsx
<Card className="transition-all duration-200 hover:shadow-lg hover:-translate-y-1">
  {/* Card content */}
</Card>
```

**Button States**:
```tsx
<Button className="transition-colors duration-150 hover:bg-primary/90 active:scale-95">
  Import
</Button>
```

**Status Badge Pulse** (New items):
```tsx
<Badge className="animate-pulse">
  New
</Badge>
```

### Stepper Transitions

**Step Change Animation**:
```tsx
import { motion, AnimatePresence } from 'framer-motion';

<AnimatePresence mode="wait">
  <motion.div
    key={currentStep}
    initial={{ opacity: 0, x: 20 }}
    animate={{ opacity: 1, x: 0 }}
    exit={{ opacity: 0, x: -20 }}
    transition={{ duration: 0.2 }}
  >
    {renderStep(currentStep)}
  </motion.div>
</AnimatePresence>
```

**Progress Bar Animation**:
```tsx
<motion.div
  className="h-1 bg-primary"
  initial={{ width: 0 }}
  animate={{ width: `${(currentStep / totalSteps) * 100}%` }}
  transition={{ duration: 0.3, ease: 'easeInOut' }}
/>
```

### List Animations

**Stagger Effect** (Card grid):
```tsx
<motion.div
  className="marketplace-grid"
  initial="hidden"
  animate="visible"
  variants={{
    visible: {
      transition: {
        staggerChildren: 0.05
      }
    }
  }}
>
  {sources.map((source) => (
    <motion.div
      key={source.id}
      variants={{
        hidden: { opacity: 0, y: 20 },
        visible: { opacity: 1, y: 0 }
      }}
    >
      <SourceCard source={source} />
    </motion.div>
  ))}
</motion.div>
```

---

## TypeScript Type Definitions

**File**: `types/marketplace.ts`

```typescript
// GitHub Source Types
export interface GitHubSource {
  id: string;
  owner: string;
  repo: string;
  branch: string;
  rootHint?: string;
  lastSyncAt: string;
  status: SourceStatus;
  errorMessage?: string;
  trustLevel: TrustLevel;
  artifactCounts: ArtifactCounts;
  hasNewArtifacts: boolean;
  hasUpdatedArtifacts: boolean;
  createdAt: string;
  updatedAt: string;
}

export type SourceStatus = 'active' | 'error' | 'scanning';
export type TrustLevel = 'basic' | 'verified' | 'official';

export interface ArtifactCounts {
  skills: number;
  commands: number;
  agents: number;
  mcpServers: number;
  hooks: number;
}

// Catalog Entry Types
export interface CatalogEntry {
  id: string;
  name: string;
  type: ArtifactType;
  path: string;
  status: CatalogStatus;
  confidence: number;
  upstreamUrl: string;
  lastDetected: string;
  importedAt?: string;
  hasUpstreamChanges: boolean;
  metadata?: Record<string, any>;
}

export type ArtifactType = 'skill' | 'command' | 'agent' | 'mcp' | 'hook';
export type CatalogStatus = 'new' | 'updated' | 'imported' | 'removed';

// API Request/Response Types
export interface CreateSourceRequest {
  repositoryUrl: string;
  branch: string;
  rootHint?: string;
  personalAccessToken?: string;
  manualCatalog?: ManualCatalogEntry[];
}

export interface ManualCatalogEntry {
  type: ArtifactType;
  path: string;
}

export interface ScanPreview {
  detectedArtifacts: DetectedArtifact[];
  totalCount: number;
  confidenceSummary: {
    high: number;
    medium: number;
    low: number;
  };
}

export interface DetectedArtifact {
  name: string;
  type: ArtifactType;
  path: string;
  confidence: number;
}

export interface ImportRequest {
  artifact_ids: string[];
}

export interface ImportResponse {
  success: boolean;
  imported: string[];
  failed: string[];
  errors?: Record<string, string>;
}

// Filter Types
export interface CatalogFilters {
  search: string;
  artifactTypes: ArtifactType[];
  statuses: CatalogStatus[];
  confidenceLevels: ConfidenceLevel[];
}

export type ConfidenceLevel = 'high' | 'medium' | 'low';

// Pagination Types
export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  pageSize: number;
  totalPages: number;
}
```

---

## Testing Strategy

### Unit Tests (Jest + React Testing Library)

**Component Tests**:

```typescript
// components/marketplace/__tests__/source-card.test.tsx
import { render, screen, fireEvent } from '@testing-library/react';
import { SourceCard } from '../source-card';

describe('SourceCard', () => {
  const mockSource: GitHubSource = {
    id: '1',
    owner: 'anthropics',
    repo: 'quickstarts',
    branch: 'main',
    status: 'active',
    trustLevel: 'verified',
    artifactCounts: {
      skills: 12,
      commands: 3,
      agents: 0,
      mcpServers: 0,
      hooks: 0,
    },
    hasNewArtifacts: true,
    hasUpdatedArtifacts: false,
    lastSyncAt: '2025-12-06T10:00:00Z',
    createdAt: '2025-12-01T00:00:00Z',
    updatedAt: '2025-12-06T10:00:00Z',
  };

  it('renders source information', () => {
    render(<SourceCard source={mockSource} />);
    expect(screen.getByText('anthropics/quickstarts')).toBeInTheDocument();
    expect(screen.getByText('Skills: 12')).toBeInTheDocument();
  });

  it('shows new artifacts badge', () => {
    render(<SourceCard source={mockSource} />);
    expect(screen.getByText('New')).toBeInTheDocument();
  });

  it('calls onRescan when rescan button clicked', () => {
    const onRescan = jest.fn();
    render(<SourceCard source={mockSource} onRescan={onRescan} />);
    fireEvent.click(screen.getByText('Rescan'));
    expect(onRescan).toHaveBeenCalledWith('1');
  });
});
```

**Hook Tests**:

```typescript
// hooks/marketplace/__tests__/use-marketplace-sources.test.ts
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useMarketplaceSources } from '../use-marketplace-sources';

describe('useMarketplaceSources', () => {
  const queryClient = new QueryClient();
  const wrapper = ({ children }: any) => (
    <QueryClientProvider client={queryClient}>
      {children}
    </QueryClientProvider>
  );

  it('fetches sources successfully', async () => {
    global.fetch = jest.fn(() =>
      Promise.resolve({
        ok: true,
        json: () => Promise.resolve({ sources: [] }),
      })
    ) as jest.Mock;

    const { result } = renderHook(() => useMarketplaceSources(), { wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toEqual({ sources: [] });
  });
});
```

### E2E Tests (Playwright)

**User Flow Tests**:

```typescript
// tests/marketplace/add-source.spec.ts
import { test, expect } from '@playwright/test';

test.describe('Add GitHub Source', () => {
  test('completes full source creation flow', async ({ page }) => {
    await page.goto('/marketplace');

    // Click Add Source button
    await page.click('button:has-text("Add Source")');

    // Step 1: Enter repository
    await page.fill('input[name="repositoryUrl"]',
      'https://github.com/anthropics/quickstarts');
    await page.click('button:has-text("Next")');

    // Step 2: Wait for scan
    await expect(page.getByText('Scanning...')).toBeVisible();
    await expect(page.getByText('Detected Artifacts')).toBeVisible({
      timeout: 10000
    });
    await page.click('button:has-text("Continue")');

    // Step 3: Skip manual catalog
    await page.click('button:has-text("Skip")');

    // Step 4: Review and create
    await expect(page.getByText('anthropics/quickstarts')).toBeVisible();
    await page.click('button:has-text("Create Source")');

    // Verify success
    await expect(page.getByText('Source created')).toBeVisible();
    await expect(page).toHaveURL('/marketplace');
  });
});
```

---

## Performance Optimization

### Code Splitting

**Dynamic imports for heavy components**:

```tsx
import dynamic from 'next/dynamic';

// Lazy load modal (not needed on initial page load)
const AddSourceModal = dynamic(
  () => import('@/components/marketplace/add-source-modal'),
  {
    loading: () => <div>Loading...</div>,
    ssr: false, // Modal doesn't need SSR
  }
);
```

### Image Optimization

**Use Next.js Image component**:

```tsx
import Image from 'next/image';

<Image
  src="/github-icon.svg"
  alt="GitHub"
  width={24}
  height={24}
  priority={false}
/>
```

### Debounce Search

**Optimize search input**:

```typescript
import { useDebouncedCallback } from 'use-debounce';

const debouncedSearch = useDebouncedCallback(
  (value: string) => {
    updateFilters({ search: value });
  },
  300 // 300ms delay
);

<Input
  type="search"
  onChange={(e) => debouncedSearch(e.target.value)}
  placeholder="Search artifacts..."
/>
```

### Virtual Scrolling

**For large artifact lists**:

```tsx
import { useVirtualizer } from '@tanstack/react-virtual';

function CatalogGrid({ artifacts }: { artifacts: CatalogEntry[] }) {
  const parentRef = useRef<HTMLDivElement>(null);

  const virtualizer = useVirtualizer({
    count: artifacts.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => 200, // Estimated card height
    overscan: 5,
  });

  return (
    <div ref={parentRef} className="h-[600px] overflow-auto">
      <div
        style={{
          height: `${virtualizer.getTotalSize()}px`,
          position: 'relative',
        }}
      >
        {virtualizer.getVirtualItems().map((virtualRow) => (
          <div
            key={virtualRow.key}
            style={{
              position: 'absolute',
              top: 0,
              left: 0,
              width: '100%',
              transform: `translateY(${virtualRow.start}px)`,
            }}
          >
            <CatalogCard artifact={artifacts[virtualRow.index]} />
          </div>
        ))}
      </div>
    </div>
  );
}
```

---

## Implementation Checklist

### Phase 1: Core Pages
- [ ] Create marketplace list page (`/marketplace`)
- [ ] Implement source card component
- [ ] Add loading and error states
- [ ] Create empty state UI
- [ ] Set up React Query hooks for sources

### Phase 2: Add Source Modal
- [ ] Build modal wrapper with stepper
- [ ] Implement Step 1: Repository input
- [ ] Implement Step 2: Scan preview
- [ ] Implement Step 3: Manual catalog (optional)
- [ ] Implement Step 4: Review & create
- [ ] Add form validation with Zod
- [ ] Integrate with create source API

### Phase 3: Detail Page
- [ ] Create source detail page (`/marketplace/[id]`)
- [ ] Build filter bar component
- [ ] Implement catalog grid
- [ ] Create catalog card component
- [ ] Add status chips
- [ ] Implement search and filtering
- [ ] Set up artifact queries

### Phase 4: Actions & Interactions
- [ ] Implement rescan functionality
- [ ] Add import artifact action
- [ ] Create bulk import feature
- [ ] Add delete source action
- [ ] Implement optimistic updates
- [ ] Add toast notifications

### Phase 5: Polish & Accessibility
- [ ] Add keyboard navigation
- [ ] Implement ARIA labels
- [ ] Test screen reader support
- [ ] Verify color contrast
- [ ] Add loading animations
- [ ] Implement responsive design
- [ ] Test on mobile devices

### Phase 6: Testing
- [ ] Write unit tests for components
- [ ] Write hook tests
- [ ] Create E2E test suite
- [ ] Test error scenarios
- [ ] Performance testing
- [ ] Accessibility audit

---

## Design System Integration

### shadcn/ui Components Used

| Component | Purpose | Documentation |
|-----------|---------|---------------|
| Dialog | Add source modal | [docs](https://ui.shadcn.com/docs/components/dialog) |
| Button | All actions | [docs](https://ui.shadcn.com/docs/components/button) |
| Card | Source/artifact cards | [docs](https://ui.shadcn.com/docs/components/card) |
| Input | Form inputs | [docs](https://ui.shadcn.com/docs/components/input) |
| Select | Dropdowns | [docs](https://ui.shadcn.com/docs/components/select) |
| Badge | Status indicators | [docs](https://ui.shadcn.com/docs/components/badge) |
| Alert | Error messages | [docs](https://ui.shadcn.com/docs/components/alert) |
| Skeleton | Loading states | [docs](https://ui.shadcn.com/docs/components/skeleton) |
| Progress | Scan progress | [docs](https://ui.shadcn.com/docs/components/progress) |
| Tabs | Filter categories | [docs](https://ui.shadcn.com/docs/components/tabs) |
| ScrollArea | Long lists | [docs](https://ui.shadcn.com/docs/components/scroll-area) |
| Accordion | Collapsible lists | [docs](https://ui.shadcn.com/docs/components/accordion) |

### Custom Components to Build

1. **SourceCard** - Reusable GitHub source card
2. **StatusChip** - Catalog status indicator
3. **TrustBadge** - Trust level indicator
4. **GitHubLink** - External GitHub link
5. **RescanButton** - Action button with states
6. **StepperNav** - Multi-step navigation
7. **CatalogCard** - Artifact catalog card

---

## Resources & References

### Design Inspiration
- [GitHub UI patterns](https://primer.style/)
- [shadcn/ui examples](https://ui.shadcn.com/examples)
- [Vercel dashboard](https://vercel.com/dashboard)

### Technical Resources
- [Next.js 15 App Router](https://nextjs.org/docs/app)
- [TanStack Query (React Query)](https://tanstack.com/query/latest)
- [Radix UI primitives](https://www.radix-ui.com/)
- [Tailwind CSS](https://tailwindcss.com/)

### Accessibility
- [WCAG 2.1 Guidelines](https://www.w3.org/WAI/WCAG21/quickref/)
- [Radix UI accessibility](https://www.radix-ui.com/primitives/docs/overview/accessibility)
- [React ARIA patterns](https://react-spectrum.adobe.com/react-aria/)

---

## Appendix: API Integration Reference

### API Endpoints Summary

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/api/v1/marketplace/sources` | Create source |
| GET | `/api/v1/marketplace/sources` | List sources |
| GET | `/api/v1/marketplace/sources/{id}` | Get source |
| POST | `/api/v1/marketplace/sources/{id}/rescan` | Trigger rescan |
| DELETE | `/api/v1/marketplace/sources/{id}` | Delete source |
| GET | `/api/v1/marketplace/sources/{id}/artifacts` | List artifacts |
| POST | `/api/v1/marketplace/sources/{id}/import` | Import artifacts |

### Error Response Format

```json
{
  "detail": "Error message",
  "status": 400,
  "type": "validation_error",
  "errors": [
    {
      "field": "repositoryUrl",
      "message": "Invalid GitHub URL"
    }
  ]
}
```

### Pagination Response Format

```json
{
  "items": [...],
  "total": 100,
  "page": 1,
  "pageSize": 20,
  "totalPages": 5
}
```

---

## Sign-off

This specification provides a complete blueprint for implementing the GitHub marketplace ingestion UI. Developers should:

1. Start with Phase 1 (core pages)
2. Use shadcn/ui components wherever possible
3. Follow the type definitions exactly
4. Implement optimistic updates for better UX
5. Test accessibility at each phase
6. Ensure mobile responsiveness

**Estimated Implementation Time**: 3-4 sprints (2 weeks each)

**Dependencies**:
- Backend API endpoints (Phase 4) must be complete
- shadcn/ui components installed
- TanStack Query configured
- TypeScript types generated from API schema

---

**Document Version**: 1.0.0
**Created**: 2025-12-06
**Author**: ui-designer
**Status**: Ready for Implementation
