---
title: Manage Page - Tabbed Artifact Type Views Pattern
references:
  - skillmeat/web/app/manage/page.tsx
  - skillmeat/web/app/manage/components/entity-tabs.tsx
  - skillmeat/web/types/entity.ts
  - skillmeat/web/components/ui/tabs.tsx
last_verified: 2025-12-31
---

# Manage Page - Tabbed Artifact Type Views Pattern

Complete reference for the tabbed artifact type views implementation used in the manage page. This pattern can be replicated for marketplace catalog or similar views with multiple artifact type filtering.

## Overview

The manage page uses a sophisticated tabbed interface to display different artifact types (skills, commands, agents, MCP servers, hooks) with:
- Type-specific icons and colors from a centralized configuration
- URL-based state management for tab selection
- Dynamic artifact counts per tab
- Shared filters and search across all types
- Responsive display (abbreviated on mobile, full labels on desktop)

## Architecture Pattern

```
┌─────────────────────────────────────────────────────────┐
│ ManagePageContent (page.tsx)                            │
│ - Manages entity state (via EntityLifecycleProvider)    │
│ - Handles view mode (grid/list), search, filters       │
│ - Renders EntityTabs wrapper                            │
└────────────┬────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────┐
│ EntityTabs (entity-tabs.tsx)                            │
│ - Renders tabbed interface with all entity types        │
│ - Manages tab selection via URL search params           │
│ - Passes render function to render tab content          │
└────────────┬────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────┐
│ Tab Content (rendered by ManagePageContent)             │
│ - EntityFilters (search, status, tags)                  │
│ - Entity count display                                  │
│ - EntityList (grid or list view)                        │
└─────────────────────────────────────────────────────────┘
```

## Key Components

### 1. EntityTabs Component

**File**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/web/app/manage/components/entity-tabs.tsx`

Renders tabs for each artifact type with URL-based state management.

**Key Features**:
- Uses Radix UI tabs via shadcn/ui `Tabs` component
- Tab selection stored in URL query parameter `?type=skill`
- Dynamic icon rendering from Lucide icons
- Responsive display (icons only on mobile)
- Render prop pattern for flexible content

**Usage Pattern**:
```tsx
<EntityTabs>
  {(entityType) => (
    <div className="flex h-full flex-col">
      {/* Content for current tab type */}
      <EntityFilters {...props} />
      <div>Entities: {filteredEntities.length}</div>
      <EntityList {...props} />
    </div>
  )}
</EntityTabs>
```

**Implementation Details**:

```typescript
// Tab setup
<Tabs value={activeTab} onValueChange={handleTabChange} className="w-full">
  <TabsList className="grid w-full grid-cols-5">
    {/* Renders 5 tabs (skills, commands, agents, MCPs, hooks) */}
    {entityTypes.map((type) => {
      const config = ENTITY_TYPES[type];
      const IconComponent = (LucideIcons as any)[config.icon] as LucideIcon;
      return (
        <TabsTrigger key={type} value={type} className="flex items-center gap-2">
          {IconComponent && <IconComponent className="h-4 w-4" />}
          <span className="hidden sm:inline">{config.pluralLabel}</span>
          <span className="sm:hidden">{config.label}</span>
        </TabsTrigger>
      );
    })}
  </TabsList>

  {/* Content for each tab */}
  {entityTypes.map((type) => (
    <TabsContent key={type} value={type} className="flex-1">
      {children(type)}
    </TabsContent>
  ))}
</Tabs>
```

**URL State Management**:
```typescript
const handleTabChange = (value: string) => {
  const params = new URLSearchParams(searchParams.toString());
  params.set('type', value);
  router.push(`${pathname}?${params.toString()}`);
};
```

### 2. Entity Type Configuration

**File**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/web/types/entity.ts`

Centralized configuration for all artifact types.

**Type Registry** (`ENTITY_TYPES` constant):
```typescript
export const ENTITY_TYPES: Record<EntityType, EntityTypeConfig> = {
  skill: {
    type: 'skill',
    label: 'Skill',                    // singular (for mobile)
    pluralLabel: 'Skills',             // plural (for desktop)
    icon: 'Sparkles',                  // Lucide icon name
    color: 'text-purple-500',          // Tailwind color class
    requiredFile: 'SKILL.md',
    formSchema: { /* form fields */ }
  },
  command: {
    type: 'command',
    label: 'Command',
    pluralLabel: 'Commands',
    icon: 'Terminal',
    color: 'text-blue-500',
    // ...
  },
  agent: {
    type: 'agent',
    label: 'Agent',
    pluralLabel: 'Agents',
    icon: 'Bot',
    color: 'text-green-500',
    // ...
  },
  mcp: {
    type: 'mcp',
    label: 'MCP Server',
    pluralLabel: 'MCP Servers',
    icon: 'Server',
    color: 'text-orange-500',
    // ...
  },
  hook: {
    type: 'hook',
    label: 'Hook',
    pluralLabel: 'Hooks',
    icon: 'Webhook',
    color: 'text-pink-500',
    // ...
  },
};
```

**Helper Functions**:
```typescript
// Get all entity types as array
getAllEntityTypes(): EntityType[]
// Returns: ['skill', 'command', 'agent', 'mcp', 'hook']

// Get configuration for specific type
getEntityTypeConfig(type: EntityType): EntityTypeConfig
```

### 3. Artifact Count Display

**File**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/web/app/manage/page.tsx` (lines 184-194)

Simple count display under the tabs showing filtered entity count:

```tsx
<div className="border-b px-4 py-2 text-sm text-muted-foreground">
  {isLoading ? (
    <div className="flex items-center gap-2">
      <Loader2 className="h-4 w-4 animate-spin" />
      Loading...
    </div>
  ) : (
    `${filteredEntities.length} ${filteredEntities.length === 1 ? 'entity' : 'entities'} found`
  )}
</div>
```

**Key Details**:
- Displays count of entities in current tab after applying all filters
- Shows loading state while fetching
- Uses `muted-foreground` color for secondary importance
- Responsive to filter changes in real-time

### 4. Filter System

**File**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/web/app/manage/components/entity-filters.tsx`

Shared filters that apply to all entity types:

**Filter Types**:
1. **Search**: Full-text search across entity names
2. **Status**: Filter by sync status (synced, modified, outdated, conflict)
3. **Tags**: Multi-select tag filtering (client-side)

**Filter Implementation**:
```tsx
<EntityFilters
  searchQuery={searchQuery}
  onSearchChange={setSearchQuery}
  statusFilter={statusFilter}
  onStatusFilterChange={setStatusFilter}
  tagFilter={tagFilter}
  onTagFilterChange={setTagFilter}
/>
```

**Client-Side Filtering**:
```typescript
const filteredEntities =
  tagFilter.length > 0
    ? entities.filter((entity) => tagFilter.some((tag) => entity.tags?.includes(tag)))
    : entities;
```

## Implementation Steps for Marketplace Catalog

### 1. Create Catalog Tabs Component

```typescript
// skillmeat/web/app/marketplace/components/catalog-tabs.tsx
'use client';

import { useRouter, useSearchParams, usePathname } from 'next/navigation';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import { ENTITY_TYPES, getAllEntityTypes, EntityType } from '@/types/entity';
import * as LucideIcons from 'lucide-react';
import { LucideIcon } from 'lucide-react';

interface CatalogTabsProps {
  children: (entityType: EntityType) => React.ReactNode;
}

export function CatalogTabs({ children }: CatalogTabsProps) {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const activeTab = (searchParams.get('category') as EntityType) || 'skill';

  const handleTabChange = (value: string) => {
    const params = new URLSearchParams(searchParams.toString());
    params.set('category', value);
    router.push(`${pathname}?${params.toString()}`);
  };

  const entityTypes = getAllEntityTypes();

  return (
    <Tabs value={activeTab} onValueChange={handleTabChange} className="w-full">
      <TabsList className="grid w-full grid-cols-5">
        {entityTypes.map((type) => {
          const config = ENTITY_TYPES[type];
          const IconComponent = (LucideIcons as any)[config.icon] as LucideIcon;

          return (
            <TabsTrigger key={type} value={type} className="flex items-center gap-2">
              {IconComponent && <IconComponent className="h-4 w-4" />}
              <span className="hidden sm:inline">{config.pluralLabel}</span>
              <span className="sm:hidden">{config.label}</span>
            </TabsTrigger>
          );
        })}
      </TabsList>

      {entityTypes.map((type) => (
        <TabsContent key={type} value={type} className="flex-1">
          {children(type)}
        </TabsContent>
      ))}
    </Tabs>
  );
}
```

### 2. Usage in Marketplace Page

```typescript
// In your marketplace catalog page
<CatalogTabs>
  {(entityType) => (
    <div className="flex h-full flex-col">
      {/* Catalog filters */}
      <CatalogFilters entityType={entityType} {...props} />

      {/* Count display */}
      <div className="border-b px-4 py-2 text-sm text-muted-foreground">
        {isLoading ? (
          <div className="flex items-center gap-2">
            <Loader2 className="h-4 w-4 animate-spin" />
            Loading...
          </div>
        ) : (
          `${filteredListings.length} ${filteredListings.length === 1 ? 'listing' : 'listings'}`
        )}
      </div>

      {/* Catalog items */}
      <div className="flex-1 overflow-auto">
        <CatalogGrid listings={filteredListings} />
      </div>
    </div>
  )}
</CatalogTabs>
```

## Tab Component Library

**shadcn/ui Tabs** (built on Radix UI):

**File**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/web/components/ui/tabs.tsx`

Core components used:
- `Tabs` - Root container
- `TabsList` - Tab button container
- `TabsTrigger` - Individual tab button
- `TabsContent` - Tab content panel

**Key Styling**:
- Active tab: `data-[state=active]:bg-background data-[state=active]:text-foreground`
- Inactive tab: `text-muted-foreground`
- Grid layout: `grid w-full grid-cols-5` (5 tabs across)
- Gap between tabs: Handled by Radix UI

## Responsive Behavior

### Desktop (sm and above)
- Shows full plural labels: "Skills", "Commands", "Agents", "MCP Servers", "Hooks"
- Wider tab buttons with text
- More screen space available

### Mobile (below sm)
- Shows abbreviated singular labels: "Skill", "Command", "Agent", "MCP", "Hook"
- Icons only with space-constrained text
- Tabs still fully functional and scrollable

**Implementation**:
```tsx
<span className="hidden sm:inline">{config.pluralLabel}</span>
<span className="sm:hidden">{config.label}</span>
```

## URL State Management

Tabs use URL query parameters for state persistence:

**Pattern**: `?type=skill` or `?category=skill` (your choice of parameter name)

**Benefits**:
- Users can bookmark/share filtered views
- Tab selection persists on page reload
- Works with browser back/forward buttons
- Maintains state when combining with other filters

**Implementation**:
```typescript
const activeTab = (searchParams.get('type') as EntityType) || 'skill';

const handleTabChange = (value: string) => {
  const params = new URLSearchParams(searchParams.toString());
  params.set('type', value);
  router.push(`${pathname}?${params.toString()}`);
};
```

## Reusable Elements

### Entity Type Configuration System

The `ENTITY_TYPES` registry in `types/entity.ts` is the single source of truth for:
- Type names and labels
- Icons (must be valid Lucide icon names)
- Colors (Tailwind classes)
- Required files
- Form schemas

**Adding a new artifact type**:
1. Add type to `EntityType` union
2. Add config to `ENTITY_TYPES` object
3. All UI components automatically update

### Lucide Icon Rendering

```typescript
import * as LucideIcons from 'lucide-react';

// Dynamically get icon component by name
const IconComponent = (LucideIcons as any)[config.icon] as LucideIcon;

// Render with className
<IconComponent className="h-4 w-4" />
```

Valid Lucide icon names from config:
- `Sparkles` (skill)
- `Terminal` (command)
- `Bot` (agent)
- `Server` (mcp)
- `Webhook` (hook)

## Common Patterns

### Filter Combination Pattern

Filters are combined both server-side and client-side:

```typescript
// Server-side: EntityLifecycleProvider handles entity type filter
setTypeFilter(activeEntityType);

// Client-side: Additional filtering in component
const filteredEntities =
  tagFilter.length > 0
    ? entities.filter((entity) =>
        tagFilter.some((tag) => entity.tags?.includes(tag))
      )
    : entities;
```

### Entity Count Display Pattern

Always show count after filters applied:

```typescript
`${filteredEntities.length} ${filteredEntities.length === 1 ? 'entity' : 'entities'} found`
```

### Loading State Pattern

Show spinner while loading:

```typescript
{isLoading ? (
  <div className="flex items-center gap-2">
    <Loader2 className="h-4 w-4 animate-spin" />
    Loading...
  </div>
) : (
  // content
)}
```

## Files to Reference

| File | Purpose |
|------|---------|
| `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/web/app/manage/page.tsx` | Main page with tab wrapper |
| `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/web/app/manage/components/entity-tabs.tsx` | Tabbed interface implementation |
| `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/web/types/entity.ts` | Entity type configuration |
| `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/web/components/ui/tabs.tsx` | shadcn/ui Tabs primitives |
| `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/web/app/manage/components/entity-filters.tsx` | Filter system reference |

## Migration Checklist for New Views

- [ ] Create tabs component extending EntityTabs pattern
- [ ] Choose parameter name for URL state (`?type=` or `?category=`)
- [ ] Create filters component (can reuse EntityFilters or extend)
- [ ] Add count display below tabs
- [ ] Implement content area (grid, list, or custom)
- [ ] Add loading states
- [ ] Test responsive behavior (mobile/desktop)
- [ ] Verify URL state persistence
- [ ] Test tab switching with filters applied

## Performance Notes

- Tab switching uses client-side routing (no server request)
- Entity type configuration is static and never changes
- Icons are lazily loaded from lucide-react
- Filter results computed locally when dataset is small (<1000 items)
- For larger datasets, consider server-side filtering

