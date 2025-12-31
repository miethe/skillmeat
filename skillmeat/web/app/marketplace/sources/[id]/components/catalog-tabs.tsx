'use client';

/**
 * CatalogTabs Component
 *
 * Filters marketplace catalog entries by artifact type with count indicators.
 * Adapted from the EntityTabs pattern for use in the marketplace source detail page.
 */

import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { cn } from '@/lib/utils';
import * as LucideIcons from 'lucide-react';
import type { LucideIcon } from 'lucide-react';

/**
 * Artifact type configuration for display
 */
interface ArtifactTypeConfig {
  /** API value for filtering */
  value: string;
  /** Display label (plural) */
  label: string;
  /** Lucide icon name */
  icon: string;
}

/**
 * Ordered list of artifact types for tab display
 * Maps API values to display configuration
 */
const ARTIFACT_TYPE_TABS: ArtifactTypeConfig[] = [
  { value: 'skill', label: 'Skills', icon: 'Sparkles' },
  { value: 'agent', label: 'Agents', icon: 'Bot' },
  { value: 'command', label: 'Commands', icon: 'Terminal' },
  { value: 'mcp_server', label: 'MCP', icon: 'Server' },
  { value: 'hook', label: 'Hooks', icon: 'Webhook' },
];

export interface CatalogTabsProps {
  /** Counts by artifact type, e.g., { skill: 12, agent: 8, ... } */
  countsByType: Record<string, number>;
  /** Currently selected type filter, null means "All Types" */
  selectedType: string | null;
  /** Callback when type filter changes */
  onTypeChange: (type: string | null) => void;
}

/**
 * CatalogTabs displays filterable tabs for artifact types with counts.
 *
 * Features:
 * - "All Types" tab showing total count
 * - Individual tabs for each artifact type with counts in parentheses
 * - Zero-count types are visually muted but still clickable
 * - Horizontal scroll on mobile with overflow-x-auto
 * - Uses Radix Tabs primitive via shadcn
 */
export function CatalogTabs({
  countsByType,
  selectedType,
  onTypeChange,
}: CatalogTabsProps) {
  // Calculate total count across all types
  const totalCount = Object.values(countsByType).reduce((sum, count) => sum + count, 0);

  // Get count for a specific type (defaults to 0)
  const getCount = (type: string): number => countsByType[type] ?? 0;

  // Convert null to 'all' for Tabs component value
  const tabValue = selectedType ?? 'all';

  const handleValueChange = (value: string) => {
    onTypeChange(value === 'all' ? null : value);
  };

  return (
    <Tabs value={tabValue} onValueChange={handleValueChange} className="w-full">
      <TabsList className="inline-flex h-10 w-full items-center justify-start gap-1 overflow-x-auto rounded-lg bg-muted p-1 scrollbar-hide">
        {/* All Types tab */}
        <TabsTrigger
          value="all"
          className={cn(
            'inline-flex items-center gap-2 whitespace-nowrap rounded-md px-3 py-1.5 text-sm font-medium transition-all',
            'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2',
            'disabled:pointer-events-none disabled:opacity-50',
            'data-[state=active]:bg-background data-[state=active]:text-foreground data-[state=active]:shadow',
            'data-[state=active]:border-b-2 data-[state=active]:border-primary',
            'text-muted-foreground'
          )}
        >
          <span>All Types</span>
          <span className="text-xs opacity-70">({totalCount})</span>
        </TabsTrigger>

        {/* Individual type tabs */}
        {ARTIFACT_TYPE_TABS.map((typeConfig) => {
          const count = getCount(typeConfig.value);
          const isZeroCount = count === 0;
          const IconComponent = (LucideIcons as any)[typeConfig.icon] as LucideIcon;

          return (
            <TabsTrigger
              key={typeConfig.value}
              value={typeConfig.value}
              className={cn(
                'inline-flex items-center gap-2 whitespace-nowrap rounded-md px-3 py-1.5 text-sm font-medium transition-all',
                'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2',
                'disabled:pointer-events-none disabled:opacity-50',
                'data-[state=active]:bg-background data-[state=active]:text-foreground data-[state=active]:shadow',
                'data-[state=active]:border-b-2 data-[state=active]:border-primary',
                'text-muted-foreground',
                isZeroCount && 'opacity-50'
              )}
            >
              {IconComponent && <IconComponent className="h-4 w-4" />}
              <span className="hidden sm:inline">{typeConfig.label}</span>
              <span
                className={cn(
                  'text-xs',
                  isZeroCount ? 'opacity-50' : 'opacity-70'
                )}
              >
                ({count})
              </span>
            </TabsTrigger>
          );
        })}
      </TabsList>
    </Tabs>
  );
}
