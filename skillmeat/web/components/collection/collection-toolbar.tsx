'use client';

import { useState, useEffect, useCallback } from 'react';
import { Grid3x3, List, Layers, Search, RefreshCw, Filter, X, ArrowUpDown, Check } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuSub,
  DropdownMenuSubContent,
  DropdownMenuSubTrigger,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Badge } from '@/components/ui/badge';
import { TagFilterPopover } from '@/components/ui/tag-filter-popover';
import { cn } from '@/lib/utils';
import type { ArtifactFilters } from '@/types/artifact';
import type { Group } from '@/types/groups';

interface AvailableTag {
  name: string;
  artifact_count: number;
}

interface AvailableTool {
  name: string;
  artifact_count: number;
}

interface CollectionToolbarProps {
  viewMode: 'grid' | 'list' | 'grouped';
  onViewModeChange: (mode: 'grid' | 'list' | 'grouped') => void;
  filters: ArtifactFilters;
  onFiltersChange: (filters: ArtifactFilters) => void;
  searchQuery: string;
  onSearchChange: (query: string) => void;
  sortField: string;
  sortOrder: 'asc' | 'desc';
  onSortChange: (field: string, order: 'asc' | 'desc') => void;
  onRefresh: () => void;
  isRefreshing?: boolean;
  lastUpdated?: Date | null;
  selectedTags?: string[];
  onTagsChange?: (tags: string[]) => void;
  /** Optional: If provided, use these tags instead of fetching from API */
  availableTags?: AvailableTag[];
  selectedTools?: string[];
  onToolsChange?: (tools: string[]) => void;
  /** Optional: If provided, use these tools instead of static list */
  availableTools?: AvailableTool[];
  /** Currently selected group IDs for filtering (multi-select) */
  selectedGroups?: string[];
  /** Handler for group filter changes */
  onGroupsChange?: (groupIds: string[]) => void;
  /** Available groups for the group filter dropdown */
  availableGroups?: Group[];
  /** Multi-select status filter values */
  selectedStatuses?: string[];
  /** Handler for status filter changes */
  onStatusesChange?: (statuses: string[]) => void;
  /** Multi-select scope filter values */
  selectedScopes?: string[];
  /** Handler for scope filter changes */
  onScopesChange?: (scopes: string[]) => void;
  /** Multi-select platform filter values */
  selectedPlatforms?: string[];
  /** Handler for platform filter changes */
  onPlatformsChange?: (platforms: string[]) => void;
  /** Show type filter in dropdown (disable when type tabs are rendered separately) */
  showTypeFilter?: boolean;
  /** Whether grouped view should be selectable */
  allowGroupedView?: boolean;
}

/**
 * Debounce hook for search input
 */
function useDebounce<T>(value: T, delay: number): T {
  const [debouncedValue, setDebouncedValue] = useState<T>(value);

  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedValue(value);
    }, delay);

    return () => {
      clearTimeout(handler);
    };
  }, [value, delay]);

  return debouncedValue;
}

/**
 * Format relative time for last updated timestamp
 */
function formatRelativeTime(date: Date): string {
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  if (diffMins < 1) return 'just now';
  if (diffMins < 60) return `${diffMins}m ago`;
  const diffHours = Math.floor(diffMins / 60);
  if (diffHours < 24) return `${diffHours}h ago`;
  return date.toLocaleDateString();
}

export function CollectionToolbar({
  viewMode,
  onViewModeChange,
  filters,
  onFiltersChange,
  searchQuery,
  onSearchChange,
  sortField,
  sortOrder,
  onSortChange,
  onRefresh,
  isRefreshing = false,
  lastUpdated = null,
  selectedTags = [],
  onTagsChange,
  availableTags,
  selectedTools = [],
  onToolsChange,
  availableTools,
  selectedGroups = [],
  onGroupsChange,
  availableGroups = [],
  selectedStatuses = [],
  onStatusesChange,
  selectedScopes = [],
  onScopesChange,
  selectedPlatforms = [],
  onPlatformsChange,
  showTypeFilter = true,
  allowGroupedView = true,
}: CollectionToolbarProps) {
  // Local search state for immediate UI feedback
  const [localSearch, setLocalSearch] = useState(searchQuery);

  // Debounce search updates
  const debouncedSearch = useDebounce(localSearch, 300);

  // Update parent when debounced value changes
  useEffect(() => {
    onSearchChange(debouncedSearch);
  }, [debouncedSearch, onSearchChange]);

  // Sync local search when external searchQuery changes
  useEffect(() => {
    setLocalSearch(searchQuery);
  }, [searchQuery]);

  const handleFilterChange = useCallback(
    (key: keyof ArtifactFilters, value: string) => {
      onFiltersChange({
        ...filters,
        [key]: value === 'all' ? undefined : value,
      });
    },
    [filters, onFiltersChange]
  );

  const handleClearFilters = useCallback(() => {
    onFiltersChange({});
    setLocalSearch('');
    onTagsChange?.([]);
    onToolsChange?.([]);
    onGroupsChange?.([]);
    onStatusesChange?.([]);
    onScopesChange?.([]);
    onPlatformsChange?.([]);
  }, [onFiltersChange, onTagsChange, onToolsChange, onGroupsChange, onStatusesChange, onScopesChange, onPlatformsChange]);

  // Calculate active filter count (includes all filters in the dropdown)
  const activeFilterCount =
    selectedStatuses.length +
    selectedScopes.length +
    selectedPlatforms.length +
    (selectedTags.length > 0 ? 1 : 0) +
    (selectedTools.length > 0 ? 1 : 0) +
    selectedGroups.length;

  const hasActiveFilters =
    activeFilterCount > 0 || localSearch.length > 0;

  return (
    <div className="border-b bg-muted/30 px-6 py-3">
      <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        {/* Left: Search and Filters */}
        <div className="flex flex-1 items-center gap-2">
          {/* Search Input */}
          <div className="relative w-full max-w-sm">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              type="search"
              placeholder="Search artifacts..."
              value={localSearch}
              onChange={(e) => setLocalSearch(e.target.value)}
              className="pl-9 pr-4"
              aria-label="Search artifacts"
            />
          </div>

          {/* Tag Filter Popover */}
          {onTagsChange && (
            <TagFilterPopover
              selectedTags={selectedTags}
              onChange={onTagsChange}
              availableTags={availableTags}
            />
          )}

          {/* Filter Dropdown (Status, Scope, Platform, Group, Tools) */}
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="outline" size="sm" className="gap-2">
                <Filter className="h-4 w-4" />
                Filters
                {activeFilterCount > 0 && (
                  <Badge variant="secondary" className="ml-1 h-5 min-w-[1.25rem] px-1">
                    {activeFilterCount}
                  </Badge>
                )}
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="start" className="w-56">
              <DropdownMenuLabel>Filter By</DropdownMenuLabel>
              <DropdownMenuSeparator />

              {/* Type Filter */}
              {showTypeFilter && (
                <div className="p-2">
                  <label htmlFor="type-filter" className="mb-1.5 block text-xs font-medium">
                    Type
                  </label>
                  <Select
                    value={filters.type || 'all'}
                    onValueChange={(value) => handleFilterChange('type', value)}
                  >
                    <SelectTrigger id="type-filter" className="h-8">
                      <SelectValue placeholder="All Types" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">All Types</SelectItem>
                      <SelectItem value="skill">Skills</SelectItem>
                      <SelectItem value="command">Commands</SelectItem>
                      <SelectItem value="agent">Agents</SelectItem>
                      <SelectItem value="mcp">MCP Servers</SelectItem>
                      <SelectItem value="hook">Hooks</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              )}

              {/* Status Filter (multi-select checkboxes) */}
              {onStatusesChange && (
                <>
                  <DropdownMenuSeparator />
                  <DropdownMenuSub>
                    <DropdownMenuSubTrigger>
                      <span className="flex items-center gap-2">
                        Status
                        {selectedStatuses.length > 0 && (
                          <Badge variant="secondary" className="ml-auto h-5 min-w-[1.25rem] px-1 text-[10px]">
                            {selectedStatuses.length}
                          </Badge>
                        )}
                      </span>
                    </DropdownMenuSubTrigger>
                    <DropdownMenuSubContent className="w-48">
                      {selectedStatuses.length > 0 && (
                        <>
                          <DropdownMenuItem
                            onSelect={(e) => e.preventDefault()}
                            onClick={() => onStatusesChange([])}
                          >
                            <span className="text-xs text-muted-foreground">Clear all</span>
                          </DropdownMenuItem>
                          <DropdownMenuSeparator />
                        </>
                      )}
                      {[
                        { value: 'active', label: 'Active' },
                        { value: 'synced', label: 'Synced' },
                        { value: 'modified', label: 'Modified' },
                        { value: 'outdated', label: 'Outdated' },
                        { value: 'conflict', label: 'Conflict' },
                        { value: 'error', label: 'Error' },
                      ].map((item) => {
                        const isSelected = selectedStatuses.includes(item.value);
                        return (
                          <DropdownMenuItem
                            key={item.value}
                            onSelect={(e) => e.preventDefault()}
                            onClick={() => {
                              if (isSelected) {
                                onStatusesChange(selectedStatuses.filter((s) => s !== item.value));
                              } else {
                                onStatusesChange([...selectedStatuses, item.value]);
                              }
                            }}
                          >
                            <span className="flex w-full items-center gap-2">
                              <div
                                className={cn(
                                  'flex h-4 w-4 shrink-0 items-center justify-center rounded border',
                                  isSelected ? 'border-primary bg-primary' : 'border-input'
                                )}
                              >
                                {isSelected && <Check className="h-3 w-3 text-primary-foreground" />}
                              </div>
                              {item.label}
                            </span>
                          </DropdownMenuItem>
                        );
                      })}
                    </DropdownMenuSubContent>
                  </DropdownMenuSub>
                </>
              )}

              {/* Scope Filter (multi-select checkboxes) */}
              {onScopesChange && (
                <>
                  <DropdownMenuSeparator />
                  <DropdownMenuSub>
                    <DropdownMenuSubTrigger>
                      <span className="flex items-center gap-2">
                        Scope
                        {selectedScopes.length > 0 && (
                          <Badge variant="secondary" className="ml-auto h-5 min-w-[1.25rem] px-1 text-[10px]">
                            {selectedScopes.length}
                          </Badge>
                        )}
                      </span>
                    </DropdownMenuSubTrigger>
                    <DropdownMenuSubContent className="w-48">
                      {selectedScopes.length > 0 && (
                        <>
                          <DropdownMenuItem
                            onSelect={(e) => e.preventDefault()}
                            onClick={() => onScopesChange([])}
                          >
                            <span className="text-xs text-muted-foreground">Clear all</span>
                          </DropdownMenuItem>
                          <DropdownMenuSeparator />
                        </>
                      )}
                      {[
                        { value: 'user', label: 'User (Global)' },
                        { value: 'local', label: 'Local (Project)' },
                      ].map((item) => {
                        const isSelected = selectedScopes.includes(item.value);
                        return (
                          <DropdownMenuItem
                            key={item.value}
                            onSelect={(e) => e.preventDefault()}
                            onClick={() => {
                              if (isSelected) {
                                onScopesChange(selectedScopes.filter((s) => s !== item.value));
                              } else {
                                onScopesChange([...selectedScopes, item.value]);
                              }
                            }}
                          >
                            <span className="flex w-full items-center gap-2">
                              <div
                                className={cn(
                                  'flex h-4 w-4 shrink-0 items-center justify-center rounded border',
                                  isSelected ? 'border-primary bg-primary' : 'border-input'
                                )}
                              >
                                {isSelected && <Check className="h-3 w-3 text-primary-foreground" />}
                              </div>
                              {item.label}
                            </span>
                          </DropdownMenuItem>
                        );
                      })}
                    </DropdownMenuSubContent>
                  </DropdownMenuSub>
                </>
              )}

              {/* Platform Filter (multi-select checkboxes) */}
              {onPlatformsChange && (
                <>
                  <DropdownMenuSeparator />
                  <DropdownMenuSub>
                    <DropdownMenuSubTrigger>
                      <span className="flex items-center gap-2">
                        Platform
                        {selectedPlatforms.length > 0 && (
                          <Badge variant="secondary" className="ml-auto h-5 min-w-[1.25rem] px-1 text-[10px]">
                            {selectedPlatforms.length}
                          </Badge>
                        )}
                      </span>
                    </DropdownMenuSubTrigger>
                    <DropdownMenuSubContent className="w-48">
                      {selectedPlatforms.length > 0 && (
                        <>
                          <DropdownMenuItem
                            onSelect={(e) => e.preventDefault()}
                            onClick={() => onPlatformsChange([])}
                          >
                            <span className="text-xs text-muted-foreground">Clear all</span>
                          </DropdownMenuItem>
                          <DropdownMenuSeparator />
                        </>
                      )}
                      {[
                        { value: 'universal', label: 'Universal' },
                        { value: 'claude_code', label: 'Claude Code' },
                        { value: 'codex', label: 'Codex' },
                        { value: 'gemini', label: 'Gemini' },
                        { value: 'cursor', label: 'Cursor' },
                      ].map((item) => {
                        const isSelected = selectedPlatforms.includes(item.value);
                        return (
                          <DropdownMenuItem
                            key={item.value}
                            onSelect={(e) => e.preventDefault()}
                            onClick={() => {
                              if (isSelected) {
                                onPlatformsChange(selectedPlatforms.filter((p) => p !== item.value));
                              } else {
                                onPlatformsChange([...selectedPlatforms, item.value]);
                              }
                            }}
                          >
                            <span className="flex w-full items-center gap-2">
                              <div
                                className={cn(
                                  'flex h-4 w-4 shrink-0 items-center justify-center rounded border',
                                  isSelected ? 'border-primary bg-primary' : 'border-input'
                                )}
                              >
                                {isSelected && <Check className="h-3 w-3 text-primary-foreground" />}
                              </div>
                              {item.label}
                            </span>
                          </DropdownMenuItem>
                        );
                      })}
                    </DropdownMenuSubContent>
                  </DropdownMenuSub>
                </>
              )}

              {/* Group Filter (multi-select checkboxes) */}
              {onGroupsChange && availableGroups.length > 0 && (
                <>
                  <DropdownMenuSeparator />
                  <DropdownMenuSub>
                    <DropdownMenuSubTrigger>
                      <span className="flex items-center gap-2">
                        Group
                        {selectedGroups.length > 0 && (
                          <Badge variant="secondary" className="ml-auto h-5 min-w-[1.25rem] px-1 text-[10px]">
                            {selectedGroups.length}
                          </Badge>
                        )}
                      </span>
                    </DropdownMenuSubTrigger>
                    <DropdownMenuSubContent className="w-48">
                      {selectedGroups.length > 0 && (
                        <>
                          <DropdownMenuItem
                            onSelect={(e) => e.preventDefault()}
                            onClick={() => onGroupsChange([])}
                          >
                            <span className="text-xs text-muted-foreground">Clear all</span>
                          </DropdownMenuItem>
                          <DropdownMenuSeparator />
                        </>
                      )}
                      {availableGroups.map((group) => {
                        const isSelected = selectedGroups.includes(group.id);
                        return (
                          <DropdownMenuItem
                            key={group.id}
                            onSelect={(e) => e.preventDefault()}
                            onClick={() => {
                              if (isSelected) {
                                onGroupsChange(selectedGroups.filter((g) => g !== group.id));
                              } else {
                                onGroupsChange([...selectedGroups, group.id]);
                              }
                            }}
                          >
                            <span className="flex w-full items-center gap-2">
                              <div
                                className={cn(
                                  'flex h-4 w-4 shrink-0 items-center justify-center rounded border',
                                  isSelected ? 'border-primary bg-primary' : 'border-input'
                                )}
                              >
                                {isSelected && <Check className="h-3 w-3 text-primary-foreground" />}
                              </div>
                              <span className="truncate">{group.name}</span>
                              {group.artifact_count > 0 && (
                                <span className="ml-auto text-xs text-muted-foreground">
                                  {group.artifact_count}
                                </span>
                              )}
                            </span>
                          </DropdownMenuItem>
                        );
                      })}
                    </DropdownMenuSubContent>
                  </DropdownMenuSub>
                </>
              )}

              {/* Tools Filter (sub-menu with checkboxes) */}
              {onToolsChange && availableTools && availableTools.length > 0 && (
                <>
                  <DropdownMenuSeparator />
                  <DropdownMenuSub>
                    <DropdownMenuSubTrigger>
                      <span className="flex items-center gap-2">
                        Tools
                        {selectedTools.length > 0 && (
                          <Badge variant="secondary" className="ml-auto h-5 min-w-[1.25rem] px-1 text-[10px]">
                            {selectedTools.length}
                          </Badge>
                        )}
                      </span>
                    </DropdownMenuSubTrigger>
                    <DropdownMenuSubContent className="w-56 max-h-60 overflow-y-auto">
                      {selectedTools.length > 0 && (
                        <>
                          <DropdownMenuItem
                            onSelect={(e) => e.preventDefault()}
                            onClick={() => onToolsChange([])}
                          >
                            <span className="text-xs text-muted-foreground">Clear all</span>
                          </DropdownMenuItem>
                          <DropdownMenuSeparator />
                        </>
                      )}
                      {availableTools.map((tool) => {
                        const isSelected = selectedTools.includes(tool.name);
                        return (
                          <DropdownMenuItem
                            key={tool.name}
                            onSelect={(e) => e.preventDefault()}
                            onClick={() => {
                              if (isSelected) {
                                onToolsChange(selectedTools.filter((t) => t !== tool.name));
                              } else {
                                onToolsChange([...selectedTools, tool.name]);
                              }
                            }}
                          >
                            <span className="flex w-full items-center gap-2">
                              <div
                                className={cn(
                                  'flex h-4 w-4 shrink-0 items-center justify-center rounded border',
                                  isSelected ? 'border-primary bg-primary' : 'border-input'
                                )}
                              >
                                {isSelected && <Check className="h-3 w-3 text-primary-foreground" />}
                              </div>
                              <span className="truncate font-mono text-xs">{tool.name}</span>
                              {tool.artifact_count > 0 && (
                                <span className="ml-auto text-xs text-muted-foreground">
                                  {tool.artifact_count}
                                </span>
                              )}
                            </span>
                          </DropdownMenuItem>
                        );
                      })}
                    </DropdownMenuSubContent>
                  </DropdownMenuSub>
                </>
              )}
            </DropdownMenuContent>
          </DropdownMenu>

          {/* Sort Dropdown */}
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="outline" size="sm" className="gap-2">
                <ArrowUpDown className="h-4 w-4" />
                Sort
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="start">
              <DropdownMenuLabel>Sort By</DropdownMenuLabel>
              <DropdownMenuSeparator />
              <DropdownMenuItem onClick={() => onSortChange('confidence', sortOrder)}>
                Confidence {sortField === 'confidence' && (sortOrder === 'asc' ? '↑' : '↓')}
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => onSortChange('name', sortOrder)}>
                Name {sortField === 'name' && (sortOrder === 'asc' ? '↑' : '↓')}
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => onSortChange('updatedAt', sortOrder)}>
                Last Updated {sortField === 'updatedAt' && (sortOrder === 'asc' ? '↑' : '↓')}
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => onSortChange('usageCount', sortOrder)}>
                Usage Count {sortField === 'usageCount' && (sortOrder === 'asc' ? '↑' : '↓')}
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem
                onClick={() => onSortChange(sortField, sortOrder === 'asc' ? 'desc' : 'asc')}
              >
                {sortOrder === 'asc' ? 'Ascending ↑' : 'Descending ↓'}
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>

          {/* Clear Filters */}
          {hasActiveFilters && (
            <Button variant="ghost" size="sm" onClick={handleClearFilters} className="gap-2">
              <X className="h-4 w-4" />
              Clear
            </Button>
          )}
        </div>

        {/* Right: View Mode and Refresh */}
        <div className="flex items-center gap-2">
          {/* View Mode Toggle */}
          <div
            className="flex items-center gap-1 rounded-md border bg-background p-1"
            role="group"
            aria-label="View mode"
          >
            <Button
              variant={viewMode === 'grid' ? 'secondary' : 'ghost'}
              size="sm"
              onClick={() => onViewModeChange('grid')}
              aria-label="Grid view"
              aria-pressed={viewMode === 'grid'}
              className="h-8 w-8 p-0"
            >
              <Grid3x3 className="h-4 w-4" />
            </Button>
            <Button
              variant={viewMode === 'list' ? 'secondary' : 'ghost'}
              size="sm"
              onClick={() => onViewModeChange('list')}
              aria-label="List view"
              aria-pressed={viewMode === 'list'}
              className="h-8 w-8 p-0"
            >
              <List className="h-4 w-4" />
            </Button>
            <Button
              variant={viewMode === 'grouped' ? 'secondary' : 'ghost'}
              size="sm"
              onClick={() => onViewModeChange('grouped')}
              aria-label="Grouped view"
              aria-pressed={viewMode === 'grouped'}
              className="h-8 w-8 p-0"
              disabled={!allowGroupedView}
            >
              <Layers className="h-4 w-4" />
            </Button>
          </div>

          {/* Refresh Button with timestamp */}
          <div className="flex items-center gap-2">
            {lastUpdated && (
              <span className="text-xs text-muted-foreground">
                Updated {formatRelativeTime(lastUpdated)}
              </span>
            )}
            <Button
              variant="outline"
              size="sm"
              onClick={onRefresh}
              disabled={isRefreshing}
              aria-label="Refresh"
            >
              <RefreshCw className={cn('h-4 w-4', isRefreshing && 'animate-spin')} />
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
