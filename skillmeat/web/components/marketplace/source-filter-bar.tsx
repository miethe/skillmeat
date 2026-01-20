'use client';

/**
 * SourceFilterBar Component
 *
 * Filter bar for marketplace sources list with:
 * - Artifact type filter (skill, command, agent, mcp, hook)
 * - Tags multi-select filter with searchable popover
 * - Trust level filter
 * - Clear individual and all filters
 */

import * as React from 'react';
import { X, Sparkles, Bot, Terminal, Server, Webhook, Filter, Check, Search } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import { ScrollArea } from '@/components/ui/scroll-area';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { cn } from '@/lib/utils';
import type { ArtifactType, TrustLevel } from '@/types/marketplace';

// ============================================================================
// Types
// ============================================================================

export interface FilterState {
  artifact_type?: string;
  tags?: string[];
  trust_level?: string;
}

export interface TagWithCount {
  name: string;
  count: number;
}

export interface SourceFilterBarProps {
  currentFilters: FilterState;
  onFilterChange: (filters: FilterState) => void;
  availableTags?: string[];
  /** Optional tag counts - map of tag name to source count */
  tagCounts?: Record<string, number>;
  trustLevels?: string[];
  className?: string;
}

interface SourceTagFilterPopoverProps {
  selectedTags: string[];
  availableTags: string[];
  tagCounts?: Record<string, number>;
  onChange: (tags: string[]) => void;
  className?: string;
}

// ============================================================================
// Color Utilities (from tag-badge.tsx pattern)
// ============================================================================

/**
 * Predefined color palette for tags.
 * Selected for WCAG AA contrast compliance.
 */
const TAG_COLORS = [
  '#6366f1', // Indigo
  '#8b5cf6', // Violet
  '#d946ef', // Fuchsia
  '#ec4899', // Pink
  '#f43f5e', // Rose
  '#ef4444', // Red
  '#f97316', // Orange
  '#eab308', // Yellow
  '#84cc16', // Lime
  '#22c55e', // Green
  '#14b8a6', // Teal
  '#06b6d4', // Cyan
  '#0ea5e9', // Sky
  '#3b82f6', // Blue
] as const;

/**
 * Generate a deterministic hash from a string.
 */
function hashString(str: string): number {
  let hash = 0;
  for (let i = 0; i < str.length; i++) {
    const char = str.charCodeAt(i);
    hash = (hash << 5) - hash + char;
    hash = hash & hash;
  }
  return Math.abs(hash);
}

/**
 * Get a consistent color for a tag based on its name.
 */
function getTagColor(tag: string): string {
  const hash = hashString(tag.toLowerCase());
  return TAG_COLORS[hash % TAG_COLORS.length] ?? TAG_COLORS[0];
}

// ============================================================================
// Constants
// ============================================================================

const ARTIFACT_TYPES: Array<{
  value: ArtifactType;
  label: string;
  Icon: React.ComponentType<{ className?: string }>;
}> = [
  { value: 'skill', label: 'Skills', Icon: Sparkles },
  { value: 'agent', label: 'Agents', Icon: Bot },
  { value: 'command', label: 'Commands', Icon: Terminal },
  { value: 'mcp', label: 'MCP', Icon: Server },
  { value: 'hook', label: 'Hooks', Icon: Webhook },
];

const DEFAULT_TRUST_LEVELS: Array<{ value: TrustLevel; label: string }> = [
  { value: 'untrusted', label: 'Untrusted' },
  { value: 'basic', label: 'Basic' },
  { value: 'verified', label: 'Verified' },
  { value: 'official', label: 'Official' },
];

// ============================================================================
// SourceTagFilterPopover Component
// ============================================================================

/**
 * Tag filter popover component with search and multi-select for source tags.
 *
 * Shows a searchable dropdown with all available source tags and their counts.
 * Uses consistent color hashing for tag badge colors.
 *
 * @example
 * ```tsx
 * <SourceTagFilterPopover
 *   selectedTags={['python', 'testing']}
 *   availableTags={['python', 'testing', 'automation']}
 *   tagCounts={{ python: 5, testing: 3, automation: 2 }}
 *   onChange={(tags) => setSelectedTags(tags)}
 * />
 * ```
 */
export function SourceTagFilterPopover({
  selectedTags,
  availableTags,
  tagCounts,
  onChange,
  className,
}: SourceTagFilterPopoverProps) {
  const [open, setOpen] = React.useState(false);
  const [search, setSearch] = React.useState('');

  // Filter tags by search query
  const filteredTags = React.useMemo(() => {
    if (!search.trim()) return availableTags;
    const query = search.toLowerCase();
    return availableTags.filter((tag) => tag.toLowerCase().includes(query));
  }, [availableTags, search]);

  const toggleTag = (tag: string) => {
    if (selectedTags.includes(tag)) {
      onChange(selectedTags.filter((t) => t !== tag));
    } else {
      onChange([...selectedTags, tag]);
    }
  };

  const clearAll = () => {
    onChange([]);
    setSearch('');
  };

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button
          variant="outline"
          size="sm"
          className={cn('h-9 gap-2', className)}
          aria-label="Filter by tags"
        >
          <Filter className="h-4 w-4" aria-hidden="true" />
          Tags
          {selectedTags.length > 0 && (
            <Badge variant="secondary" className="ml-1 rounded-full px-2">
              {selectedTags.length}
            </Badge>
          )}
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-72 p-0" align="start">
        <div className="border-b p-3">
          <div className="mb-2 flex items-center justify-between">
            <span className="text-sm font-medium">Filter by tags</span>
            {selectedTags.length > 0 && (
              <Button
                variant="ghost"
                size="sm"
                onClick={clearAll}
                className="h-6 px-2 text-xs"
                aria-label="Clear all selected tags"
              >
                Clear all
              </Button>
            )}
          </div>
          <div className="relative">
            <Search
              className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground"
              aria-hidden="true"
            />
            <Input
              placeholder="Search tags..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="h-9 pl-8"
              aria-label="Search tags"
            />
          </div>
        </div>
        <ScrollArea className="h-60">
          <div className="p-2">
            {filteredTags.length === 0 ? (
              <div className="py-4 text-center text-sm text-muted-foreground">
                {search ? 'No tags found' : 'No tags available'}
              </div>
            ) : (
              filteredTags.map((tag) => {
                const isSelected = selectedTags.includes(tag);
                const color = getTagColor(tag);
                const count = tagCounts?.[tag];

                return (
                  <div
                    key={tag}
                    className={cn(
                      'flex cursor-pointer items-center justify-between rounded-md px-2 py-1.5 hover:bg-accent',
                      isSelected && 'bg-accent'
                    )}
                    onClick={() => toggleTag(tag)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' || e.key === ' ') {
                        e.preventDefault();
                        toggleTag(tag);
                      }
                    }}
                    role="option"
                    aria-selected={isSelected}
                    tabIndex={0}
                  >
                    <div className="flex items-center gap-2">
                      <div
                        className={cn(
                          'flex h-4 w-4 items-center justify-center rounded border',
                          isSelected ? 'border-primary bg-primary' : 'border-input'
                        )}
                      >
                        {isSelected && (
                          <Check className="h-3 w-3 text-primary-foreground" aria-hidden="true" />
                        )}
                      </div>
                      <Badge colorStyle={color} className="text-xs">
                        {tag}
                      </Badge>
                    </div>
                    {count !== undefined && (
                      <span className="text-xs text-muted-foreground">{count}</span>
                    )}
                  </div>
                );
              })
            )}
          </div>
        </ScrollArea>
      </PopoverContent>
    </Popover>
  );
}

// ============================================================================
// SourceFilterBar Component
// ============================================================================

export function SourceFilterBar({
  currentFilters,
  onFilterChange,
  availableTags = [],
  tagCounts,
  trustLevels,
  className,
}: SourceFilterBarProps) {
  // Use provided trust levels or defaults
  const trustLevelOptions = trustLevels
    ? trustLevels.map((level) => ({
        value: level as TrustLevel,
        label: level.charAt(0).toUpperCase() + level.slice(1),
      }))
    : DEFAULT_TRUST_LEVELS;

  // Handle filter changes
  const handleArtifactTypeChange = (value: string) => {
    onFilterChange({
      ...currentFilters,
      artifact_type: value === 'all' ? undefined : value,
    });
  };

  const handleTrustLevelChange = (value: string) => {
    onFilterChange({
      ...currentFilters,
      trust_level: value === 'all' ? undefined : value,
    });
  };

  const handleRemoveTag = (tag: string) => {
    const currentTags = currentFilters.tags || [];
    const newTags = currentTags.filter((t) => t !== tag);

    onFilterChange({
      ...currentFilters,
      tags: newTags.length > 0 ? newTags : undefined,
    });
  };

  const handleClearFilter = (key: keyof FilterState) => {
    const newFilters = { ...currentFilters };
    delete newFilters[key];
    onFilterChange(newFilters);
  };

  const handleClearAll = () => {
    onFilterChange({});
  };

  // Count active filters
  const activeFilterCount =
    (currentFilters.artifact_type ? 1 : 0) +
    (currentFilters.trust_level ? 1 : 0) +
    (currentFilters.tags?.length || 0);

  return (
    <div className={cn('space-y-3', className)}>
      {/* Filter Controls Row */}
      <div className="flex flex-wrap items-center gap-3">
        {/* Artifact Type Filter */}
        <div className="flex items-center gap-2">
          <label
            htmlFor="artifact-type-filter"
            className="text-sm font-medium text-muted-foreground"
          >
            Type
          </label>
          <Select
            value={currentFilters.artifact_type || 'all'}
            onValueChange={handleArtifactTypeChange}
          >
            <SelectTrigger
              id="artifact-type-filter"
              className="h-9 w-[140px]"
              aria-label="Filter by artifact type"
            >
              <SelectValue placeholder="All Types" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Types</SelectItem>
              {ARTIFACT_TYPES.map((type) => {
                const Icon = type.Icon;
                return (
                  <SelectItem key={type.value} value={type.value}>
                    <span className="flex items-center gap-2">
                      <Icon className="h-4 w-4" />
                      {type.label}
                    </span>
                  </SelectItem>
                );
              })}
            </SelectContent>
          </Select>
        </div>

        {/* Trust Level Filter */}
        <div className="flex items-center gap-2">
          <label htmlFor="trust-level-filter" className="text-sm font-medium text-muted-foreground">
            Trust
          </label>
          <Select
            value={currentFilters.trust_level || 'all'}
            onValueChange={handleTrustLevelChange}
          >
            <SelectTrigger
              id="trust-level-filter"
              className="h-9 w-[130px]"
              aria-label="Filter by trust level"
            >
              <SelectValue placeholder="All Levels" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Levels</SelectItem>
              {trustLevelOptions.map((level) => (
                <SelectItem key={level.value} value={level.value}>
                  {level.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {/* Tags Filter - Popover with search and multi-select */}
        {availableTags.length > 0 && (
          <SourceTagFilterPopover
            selectedTags={currentFilters.tags || []}
            availableTags={availableTags}
            tagCounts={tagCounts}
            onChange={(tags) =>
              onFilterChange({
                ...currentFilters,
                tags: tags.length > 0 ? tags : undefined,
              })
            }
          />
        )}

        {/* Clear All Button */}
        {activeFilterCount > 0 && (
          <Button
            variant="ghost"
            size="sm"
            onClick={handleClearAll}
            className="h-9 gap-2"
            aria-label="Clear all filters"
          >
            <X className="h-4 w-4" />
            Clear all
          </Button>
        )}
      </div>

      {/* Active Filters Display */}
      {activeFilterCount > 0 && (
        <div className="flex flex-wrap items-center gap-2 border-t pt-2">
          <span className="text-sm text-muted-foreground">Active filters:</span>

          {/* Artifact Type Badge */}
          {currentFilters.artifact_type && (
            <Badge variant="secondary" className="gap-1">
              Type: {currentFilters.artifact_type}
              <button
                onClick={() => handleClearFilter('artifact_type')}
                className="rounded-full hover:text-destructive focus:outline-none focus:ring-2 focus:ring-ring"
                aria-label={`Remove artifact type filter: ${currentFilters.artifact_type}`}
              >
                <X className="h-3 w-3" />
              </button>
            </Badge>
          )}

          {/* Trust Level Badge */}
          {currentFilters.trust_level && (
            <Badge variant="secondary" className="gap-1">
              Trust: {currentFilters.trust_level}
              <button
                onClick={() => handleClearFilter('trust_level')}
                className="rounded-full hover:text-destructive focus:outline-none focus:ring-2 focus:ring-ring"
                aria-label={`Remove trust level filter: ${currentFilters.trust_level}`}
              >
                <X className="h-3 w-3" />
              </button>
            </Badge>
          )}

          {/* Tag Badges - with consistent color styling */}
          {currentFilters.tags?.map((tag) => (
            <Badge key={tag} colorStyle={getTagColor(tag)} className="gap-1">
              {tag}
              <button
                onClick={() => handleRemoveTag(tag)}
                className="rounded-full opacity-80 hover:opacity-100 focus:outline-none focus:ring-2 focus:ring-ring"
                aria-label={`Remove tag filter: ${tag}`}
              >
                <X className="h-3 w-3" />
              </button>
            </Badge>
          ))}

          <span className="text-sm text-muted-foreground">
            ({activeFilterCount} {activeFilterCount === 1 ? 'filter' : 'filters'})
          </span>
        </div>
      )}
    </div>
  );
}
