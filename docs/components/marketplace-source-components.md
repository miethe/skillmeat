# Marketplace Source Components

React components for displaying and managing marketplace GitHub sources.

**Location**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/web/components/marketplace/`

---

## Overview

The marketplace source components provide a complete UI for browsing, filtering, and managing GitHub repository sources. These components follow the SkillMeat design system with Radix UI primitives and shadcn/ui styling.

**Component Architecture**:

- `SourceFilterBar` - Multi-faceted filtering UI
- `SourceCard` - Repository source display with actions
- `TagBadge` - Color-coded tag display with overflow handling
- `CountBadge` - Artifact count badge with tooltip breakdown
- `RepoDetailsModal` - Repository description and README viewer

---

## SourceFilterBar

Filter control bar for marketplace sources list with artifact type, tags, and trust level filters.

### Props

```typescript
interface FilterState {
  artifact_type?: string;
  tags?: string[];
  trust_level?: string;
}

interface SourceFilterBarProps {
  currentFilters: FilterState;
  onFilterChange: (filters: FilterState) => void;
  availableTags?: string[];
  trustLevels?: string[];
  className?: string;
}
```

**Props Table**:

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| `currentFilters` | `FilterState` | *Required* | Current filter state |
| `onFilterChange` | `(filters: FilterState) => void` | *Required* | Callback when filters change |
| `availableTags` | `string[]` | `[]` | Available tags to show as filter options |
| `trustLevels` | `string[]` | `['untrusted', 'basic', 'verified', 'official']` | Trust levels to show in dropdown |
| `className` | `string` | `undefined` | Additional CSS classes |

### Usage

```tsx
import { SourceFilterBar } from '@/components/marketplace/source-filter-bar';
import { useState } from 'react';

export function SourcesPage() {
  const [filters, setFilters] = useState<FilterState>({});

  return (
    <SourceFilterBar
      currentFilters={filters}
      onFilterChange={setFilters}
      availableTags={['official', 'verified', 'ui', 'backend']}
      trustLevels={['basic', 'verified', 'official']}
    />
  );
}
```

### Features

- **Artifact Type Filter**: Select dropdown with icons for each artifact type (skill, agent, command, mcp, hook)
- **Trust Level Filter**: Select dropdown for trust levels (untrusted, basic, verified, official)
- **Tag Filters**: Clickable badges for quick tag selection (up to 8 shown inline)
- **Active Filters Display**: Shows current filters as removable badges
- **Clear All**: Button to reset all filters at once
- **Individual Clear**: Each active filter can be removed individually

### Filter Behavior

All filters are passed to `onFilterChange` as a single `FilterState` object:

```typescript
// Selecting artifact type
onFilterChange({
  ...currentFilters,
  artifact_type: 'skill'
});

// Toggling a tag
const newTags = currentFilters.tags?.includes(tag)
  ? currentFilters.tags.filter(t => t !== tag)
  : [...(currentFilters.tags || []), tag];

onFilterChange({
  ...currentFilters,
  tags: newTags.length > 0 ? newTags : undefined
});

// Clearing all filters
onFilterChange({});
```

### Accessibility

- **Keyboard Navigation**: All controls are keyboard accessible
- **ARIA Labels**: Descriptive labels for screen readers
- **Focus Management**: Proper focus indicators on all interactive elements
- **Role Attributes**: Correct button/select roles for assistive technology

---

## SourceCard

Display card for a GitHub repository source with status badges, artifact counts, and action buttons.

### Props

```typescript
interface SourceCardProps {
  source: GitHubSource;
  onRescan?: (sourceId: string) => void;
  isRescanning?: boolean;
  onClick?: () => void;
  onEdit?: (source: GitHubSource) => void;
  onDelete?: (source: GitHubSource) => void;
  onTagClick?: (tag: string) => void;
}
```

**Props Table**:

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| `source` | `GitHubSource` | *Required* | Source data to display |
| `onRescan` | `(sourceId: string) => void` | `undefined` | Callback when rescan button clicked |
| `isRescanning` | `boolean` | `false` | Whether rescan is in progress |
| `onClick` | `() => void` | Navigate to detail page | Custom click handler |
| `onEdit` | `(source: GitHubSource) => void` | `undefined` | Callback when edit button clicked |
| `onDelete` | `(source: GitHubSource) => void` | `undefined` | Callback when delete button clicked |
| `onTagClick` | `(tag: string) => void` | `undefined` | Callback when tag is clicked |

### Usage

```tsx
import { SourceCard } from '@/components/marketplace/source-card';
import { useRouter } from 'next/navigation';

export function SourcesList() {
  const router = useRouter();

  const handleRescan = async (sourceId: string) => {
    await fetch(`/api/v1/marketplace/sources/${sourceId}/rescan`, {
      method: 'POST'
    });
  };

  const handleEdit = (source: GitHubSource) => {
    router.push(`/marketplace/sources/${source.id}/edit`);
  };

  const handleTagClick = (tag: string) => {
    // Add tag to filters
    setFilters(prev => ({
      ...prev,
      tags: [...(prev.tags || []), tag]
    }));
  };

  return (
    <SourceCard
      source={source}
      onRescan={handleRescan}
      isRescanning={isRescanning}
      onEdit={handleEdit}
      onTagClick={handleTagClick}
    />
  );
}
```

### Visual Design

The card follows the unified card style with:

- **Left border**: 4px blue accent border (`border-l-blue-500`)
- **Background tint**: Subtle blue tint (`bg-blue-500/[0.02]`)
- **Hover effect**: Shadow elevation on hover
- **Status badges**: Color-coded trust level and scan status badges
- **Artifact counts**: Tooltip with breakdown by artifact type

### Card Sections

1. **Header**: Repository name (`owner/repo`) with GitHub icon
2. **Metadata**: Branch/tag (`ref`) and subdirectory (`root_hint`) if set
3. **Description**: User description with fallback to `repo_description`
4. **Tags & Counts**: Tag badges (clickable if `onTagClick` provided) and artifact count badge
5. **Footer**: Last sync time and action buttons (edit, delete, rescan, view source on GitHub)

### New Props (vs. Legacy)

- `onTagClick`: Enable tag filtering by clicking tags on the card
- `source.tags`: Array of tags to display
- `source.counts_by_type`: Breakdown of artifacts by type (shown in tooltip)
- `source.repo_description`: GitHub repo description (fallback for display)

### Event Handlers

```typescript
// Custom click handler (default navigates to detail page)
onClick={() => router.push(`/marketplace/sources/${source.id}`)}

// Rescan with loading state
const [isRescanning, setIsRescanning] = useState(false);

const handleRescan = async (sourceId: string) => {
  setIsRescanning(true);
  try {
    await fetch(`/api/v1/marketplace/sources/${sourceId}/rescan`, {
      method: 'POST'
    });
  } finally {
    setIsRescanning(false);
  }
};

// Tag click for filtering
onTagClick={(tag) => {
  setFilters(prev => ({
    ...prev,
    tags: [...(prev.tags || []), tag]
  }));
}}
```

### Accessibility

- **Keyboard Navigation**: Card and all buttons are keyboard accessible
- **ARIA Labels**: Descriptive labels for all actions
- **Focus Management**: Visible focus indicators
- **Screen Reader**: Proper roles and labels for status badges

---

## TagBadge

Color-coded tag display component with overflow handling.

### Props

```typescript
interface TagBadgeProps {
  tags: string[];
  maxDisplay?: number;
  onTagClick?: (tag: string) => void;
  className?: string;
}
```

**Props Table**:

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| `tags` | `string[]` | *Required* | Array of tag strings |
| `maxDisplay` | `number` | `3` | Max tags to show before "+n more" |
| `onTagClick` | `(tag: string) => void` | `undefined` | Callback when tag clicked |
| `className` | `string` | `undefined` | Additional CSS classes |

### Usage

```tsx
import { TagBadge } from '@/components/marketplace/tag-badge';

// Display-only mode
<TagBadge tags={['ui', 'ux', 'design']} maxDisplay={3} />

// Interactive mode (clickable tags for filtering)
<TagBadge
  tags={['official', 'verified', 'production', 'ui', 'backend']}
  maxDisplay={4}
  onTagClick={(tag) => console.log(`Clicked: ${tag}`)}
/>
```

### Color Coding

Tags are assigned consistent colors using a deterministic hash:

```typescript
// Same tag always gets same color
getTagColor('ui-ux');  // Always returns '#6366f1' (indigo)
getTagColor('backend'); // Always returns '#22c55e' (green)
```

**Color Palette** (14 WCAG AA-compliant colors):

- Indigo, Violet, Fuchsia, Pink, Rose, Red, Orange, Yellow, Lime, Green, Teal, Cyan, Sky, Blue

### Overflow Handling

When `tags.length > maxDisplay`, the component shows:

1. First `maxDisplay` tags as colored badges
2. "+n more" badge with tooltip showing remaining tags

```tsx
// 8 tags with maxDisplay=3
// Displays: [ui] [ux] [design] [+5 more]
//           ^--- visible
//                               ^--- tooltip shows: backend, api, python, django, postgresql
```

### Interactive vs Display-Only

**Display-Only** (no `onTagClick`):
- Tags are not clickable
- No hover effects
- ARIA label: "Tag: {tag}"

**Interactive** (with `onTagClick`):
- Tags are clickable buttons
- Hover opacity effect
- ARIA label: "Filter by tag: {tag}"
- Keyboard accessible (Enter/Space to activate)

### Accessibility

- **Keyboard Navigation**: Interactive tags are keyboard accessible
- **ARIA Labels**: Appropriate labels for mode (display vs interactive)
- **Focus Indicators**: Visible focus rings on interactive tags
- **Tooltip**: Hidden tags revealed in tooltip on overflow badge

---

## CountBadge

Artifact count badge with tooltip breakdown by type.

### Props

```typescript
interface CountBadgeProps {
  countsByType: Record<string, number>;
  className?: string;
}
```

**Props Table**:

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| `countsByType` | `Record<string, number>` | *Required* | Counts by artifact type |
| `className` | `string` | `undefined` | Additional CSS classes |

### Usage

```tsx
import { CountBadge } from '@/components/marketplace/count-badge';

<CountBadge
  countsByType={{
    skill: 8,
    command: 3,
    agent: 1
  }}
/>

// Displays: [12] (with tooltip: "Skills: 8, Commands: 3, Agents: 1")
```

### Tooltip Breakdown

The badge shows the **total count** as the badge text, with a tooltip showing the breakdown:

```
Hover over [12] badge:
┌────────────────────────────┐
│ Skills: 8                  │
│ Commands: 3                │
│ Agents: 1                  │
└────────────────────────────┘
```

**Tooltip Format**:
- Sorted by count (descending)
- Type names pluralized and title-cased
- Handles snake_case types (e.g., `mcp_server` → "Mcp Servers")

### Empty State

When total count is 0:

```tsx
<CountBadge countsByType={{}} />
// Displays: [0] with muted styling
// Tooltip: "No artifacts"
```

### Accessibility

- **ARIA Label**: Full breakdown (e.g., "12 artifacts: Skills: 8, Commands: 3, Agents: 1")
- **Tabular Numbers**: Uses `tabular-nums` class for consistent width
- **Tooltip**: Accessible to keyboard and screen reader users

---

## RepoDetailsModal

Modal dialog for displaying repository description and README content.

### Props

```typescript
interface GitHubSourceWithReadme extends GitHubSource {
  repo_description?: string;
  readme_content?: string;
}

interface RepoDetailsModalProps {
  isOpen: boolean;
  onClose: () => void;
  source: GitHubSourceWithReadme;
}
```

**Props Table**:

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| `isOpen` | `boolean` | *Required* | Whether modal is open |
| `onClose` | `() => void` | *Required* | Callback to close modal |
| `source` | `GitHubSourceWithReadme` | *Required* | Source with optional README content |

### Usage

```tsx
import { RepoDetailsModal } from '@/components/marketplace/repo-details-modal';
import { useState } from 'react';

export function SourceDetail() {
  const [showDetails, setShowDetails] = useState(false);

  return (
    <>
      <Button onClick={() => setShowDetails(true)}>
        View Details
      </Button>

      <RepoDetailsModal
        isOpen={showDetails}
        onClose={() => setShowDetails(false)}
        source={source}
      />
    </>
  );
}
```

### Content Rendering

The modal displays content in this priority order:

1. **User Description** (from `source.description`)
2. **GitHub Repo Description** (from `source.repo_description`)
3. **README Content** (from `source.readme_content`, rendered as markdown)

**Markdown Rendering**:
- Uses `react-markdown` with `remark-gfm` plugin
- Supports GitHub Flavored Markdown (tables, strikethrough, task lists, etc.)
- Prose styling with `prose` classes (dark mode support)
- Word wrapping for long lines

### Empty State

When no content is available (`!description && !readme_content`):

```tsx
// Displays centered message:
// 📄 No repository details available
//    This repository does not have a description or README content.
```

### Modal Structure

```
┌─────────────────────────────────────────────┐
│ 📄 owner/repo                         [×]   │ ← Header with close button
│ Optional description text here...           │ ← DialogDescription
├─────────────────────────────────────────────┤
│ README                                      │ ← Section label
│ ┌─────────────────────────────────────────┐│
│ │ # My Project                            ││ ← Scrollable markdown
│ │                                         ││   content area
│ │ This is the README content...          ││
│ │ ...                                     ││
│ └─────────────────────────────────────────┘│
└─────────────────────────────────────────────┘
```

### Accessibility

- **Keyboard Navigation**: Escape to close, focus trap within modal
- **ARIA**: Proper dialog role and labeling
- **Focus Management**: Restores focus on close (handled by Radix Dialog)
- **Screen Reader**: DialogDescription provides context

### Styling

- **Max Height**: 85vh to prevent overflow on small screens
- **Max Width**: 2xl (Tailwind) for comfortable reading
- **Scrollable**: README content scrolls independently
- **Dark Mode**: Full dark mode support via Tailwind `dark:` variant

---

## Common Patterns

### Filter State Management

```tsx
import { useState } from 'react';
import { SourceFilterBar, FilterState } from '@/components/marketplace';

function SourcesPage() {
  const [filters, setFilters] = useState<FilterState>({});

  // Apply filters to API query
  const { data } = useMarketplaceSources({
    artifact_type: filters.artifact_type,
    tags: filters.tags,
    trust_level: filters.trust_level,
    search: filters.search,
  });

  return (
    <div>
      <SourceFilterBar
        currentFilters={filters}
        onFilterChange={setFilters}
        availableTags={data?.availableTags || []}
      />

      {/* Source list */}
    </div>
  );
}
```

### Tag Click Filtering

Enable tag-based filtering by clicking tags on cards:

```tsx
function SourcesList() {
  const [filters, setFilters] = useState<FilterState>({});

  const handleTagClick = (tag: string) => {
    setFilters(prev => ({
      ...prev,
      tags: prev.tags?.includes(tag)
        ? prev.tags.filter(t => t !== tag)  // Toggle off if already selected
        : [...(prev.tags || []), tag],       // Add to selection
    }));
  };

  return (
    <div className="grid gap-4">
      {sources.map(source => (
        <SourceCard
          key={source.id}
          source={source}
          onTagClick={handleTagClick}
        />
      ))}
    </div>
  );
}
```

### Rescan with Loading State

```tsx
import { useState } from 'react';
import { useRescanSource } from '@/hooks';

function SourcesList() {
  const [rescanningId, setRescanningId] = useState<string | null>(null);
  const { mutate: rescan } = useRescanSource();

  const handleRescan = (sourceId: string) => {
    setRescanningId(sourceId);
    rescan(sourceId, {
      onSettled: () => setRescanningId(null),
    });
  };

  return (
    <div>
      {sources.map(source => (
        <SourceCard
          key={source.id}
          source={source}
          onRescan={handleRescan}
          isRescanning={rescanningId === source.id}
        />
      ))}
    </div>
  );
}
```

---

## Design System Integration

All components follow SkillMeat design patterns:

### Color Palette

- **Primary**: Blue (`blue-500`, `blue-600`)
- **Accent**: Left border on cards (`border-l-blue-500`)
- **Background Tint**: Subtle blue tint (`bg-blue-500/[0.02]`)
- **Status Colors**:
  - Success: Green (`green-500`)
  - Error: Red (`red-500`)
  - Warning: Yellow (`yellow-500`)
  - Info: Blue (`blue-500`)
  - Trust levels: Gray, Blue, Purple

### Spacing Tokens

- **Card Padding**: `p-4` (16px)
- **Internal Gaps**: `gap-3` (12px) for vertical, `gap-2` (8px) for horizontal
- **Section Spacing**: `space-y-3` (12px between sections)

### Typography

- **Headings**: `font-semibold` with appropriate sizes
- **Body**: Default size with `text-muted-foreground` for secondary text
- **Labels**: `text-sm` with `font-medium`

### Accessibility

All components implement:
- **Keyboard Navigation**: Full keyboard accessibility
- **ARIA Labels**: Descriptive labels for screen readers
- **Focus Indicators**: Visible focus rings
- **Color Contrast**: WCAG AA compliance
- **Semantic HTML**: Proper heading hierarchy, button roles, etc.

---

## Testing

### Unit Tests (Jest + RTL)

```tsx
import { render, screen, fireEvent } from '@testing-library/react';
import { SourceCard } from '@/components/marketplace/source-card';

describe('SourceCard', () => {
  it('calls onRescan when rescan button clicked', () => {
    const onRescan = jest.fn();
    render(<SourceCard source={mockSource} onRescan={onRescan} />);

    const rescanButton = screen.getByLabelText('Rescan repository');
    fireEvent.click(rescanButton);

    expect(onRescan).toHaveBeenCalledWith(mockSource.id);
  });

  it('shows tags as clickable when onTagClick provided', () => {
    const onTagClick = jest.fn();
    render(
      <SourceCard
        source={{ ...mockSource, tags: ['ui', 'ux'] }}
        onTagClick={onTagClick}
      />
    );

    const uiTag = screen.getByText('ui');
    fireEvent.click(uiTag);

    expect(onTagClick).toHaveBeenCalledWith('ui');
  });
});
```

### E2E Tests (Playwright)

```typescript
test('filter sources by tag', async ({ page }) => {
  await page.goto('/marketplace/sources');

  // Click tag on a source card
  await page.click('text=official');

  // Verify filter badge appears
  await expect(page.locator('text=official')).toBeVisible();

  // Verify only sources with 'official' tag are shown
  const cards = page.locator('[data-testid="source-card"]');
  await expect(cards).toHaveCount(3);
});
```

---

## Best Practices

1. **State Management**: Keep filter state in URL search params for shareable links
2. **Loading States**: Show skeleton loaders while fetching sources
3. **Error Handling**: Display error messages with retry buttons
4. **Optimistic Updates**: Update UI immediately on actions, rollback on error
5. **Accessibility**: Test with keyboard navigation and screen readers
6. **Performance**: Virtualize long lists with `react-window` or `react-virtuoso`

---

## See Also

- [Marketplace Sources API Documentation](/Users/miethe/dev/homelab/development/skillmeat/docs/api/endpoints/marketplace-sources.md)
- [SkillMeat Design System](/Users/miethe/dev/homelab/development/skillmeat/docs/design-system.md)
- [Component Testing Guide](/Users/miethe/dev/homelab/development/skillmeat/docs/testing/components.md)
