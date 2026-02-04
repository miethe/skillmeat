'use client';

import { useState, useEffect, useCallback } from 'react';
import { Grid3x3, List, Layers, Search, RefreshCw, Filter, X, ArrowUpDown } from 'lucide-react';
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
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Badge } from '@/components/ui/badge';
import { TagFilterPopover } from '@/components/ui/tag-filter-popover';
import { ToolFilterPopover } from '@/components/ui/tool-filter-popover';
import { cn } from '@/lib/utils';
import type { ArtifactFilters } from '@/types/artifact';

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
  selectedTools?: string[];
  onToolsChange?: (tools: string[]) => void;
  /** Optional: If provided, use these tools instead of static list */
  availableTools?: AvailableTool[];
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
  selectedTools = [],
  onToolsChange,
  availableTools,
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

  // Persist view mode to localStorage
  useEffect(() => {
    if (typeof window !== 'undefined') {
      localStorage.setItem('collection-view-mode', viewMode);
    }
  }, [viewMode]);

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
  }, [onFiltersChange, onTagsChange, onToolsChange]);

  // Calculate active filter count
  const activeFilterCount =
    Object.entries(filters).filter(
      ([, value]) => value !== undefined && value !== 'all' && value !== ''
    ).length +
    (selectedTags.length > 0 ? 1 : 0) +
    (selectedTools.length > 0 ? 1 : 0);

  const hasActiveFilters =
    activeFilterCount > 0 || localSearch.length > 0 || selectedTools.length > 0;

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
            />
          )}

          {/* Tool Filter Popover */}
          {onToolsChange && (
            <ToolFilterPopover
              selectedTools={selectedTools}
              onChange={onToolsChange}
              availableTools={availableTools}
            />
          )}

          {/* Filter Dropdown */}
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

              {/* Status Filter */}
              <div className="p-2">
                <label htmlFor="status-filter" className="mb-1.5 block text-xs font-medium">
                  Status
                </label>
                <Select
                  value={filters.status || 'all'}
                  onValueChange={(value) => handleFilterChange('status', value)}
                >
                  <SelectTrigger id="status-filter" className="h-8">
                    <SelectValue placeholder="All Statuses" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All Statuses</SelectItem>
                    <SelectItem value="active">Active</SelectItem>
                    <SelectItem value="outdated">Outdated</SelectItem>
                    <SelectItem value="conflict">Conflict</SelectItem>
                    <SelectItem value="error">Error</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              {/* Scope Filter */}
              <div className="p-2">
                <label htmlFor="scope-filter" className="mb-1.5 block text-xs font-medium">
                  Scope
                </label>
                <Select
                  value={filters.scope || 'all'}
                  onValueChange={(value) => handleFilterChange('scope', value)}
                >
                  <SelectTrigger id="scope-filter" className="h-8">
                    <SelectValue placeholder="All Scopes" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All Scopes</SelectItem>
                    <SelectItem value="user">User (Global)</SelectItem>
                    <SelectItem value="local">Local (Project)</SelectItem>
                  </SelectContent>
                </Select>
              </div>
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
