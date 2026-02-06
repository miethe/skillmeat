'use client';

/**
 * MemoryFilterBar Component
 *
 * Standalone, reusable filter bar for the Memory Inbox view.
 * Renders two rows:
 *   Row 1 - Type tabs with count badges
 *   Row 2 - Status dropdown, sort dropdown, and search input
 *
 * Extracted from memory-page-content.tsx for reuse and testability.
 */

import { useCallback } from 'react';
import {
  Search,
  Filter,
  ArrowUpDown,
  ChevronDown,
  ShieldAlert,
  GitBranch,
  Wrench,
  Puzzle,
  Lightbulb,
  Palette,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuRadioGroup,
  DropdownMenuRadioItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const MEMORY_TYPES = [
  { value: 'all', label: 'All', icon: null },
  { value: 'constraint', label: 'Constraints', icon: ShieldAlert },
  { value: 'decision', label: 'Decisions', icon: GitBranch },
  { value: 'fix', label: 'Fixes', icon: Wrench },
  { value: 'pattern', label: 'Patterns', icon: Puzzle },
  { value: 'learning', label: 'Learnings', icon: Lightbulb },
  { value: 'style_rule', label: 'Style Rules', icon: Palette },
] as const;

const STATUS_OPTIONS = [
  { value: 'all', label: 'All Statuses' },
  { value: 'candidate', label: 'Candidate' },
  { value: 'active', label: 'Active' },
  { value: 'stable', label: 'Stable' },
  { value: 'deprecated', label: 'Deprecated' },
] as const;

const SORT_OPTIONS = [
  { value: 'newest', label: 'Newest First' },
  { value: 'oldest', label: 'Oldest First' },
  { value: 'confidence-desc', label: 'Highest Confidence' },
  { value: 'confidence-asc', label: 'Lowest Confidence' },
  { value: 'most-used', label: 'Most Used' },
] as const;

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function getStatusLabel(value: string): string {
  return STATUS_OPTIONS.find((opt) => opt.value === value)?.label ?? 'All Statuses';
}

function getSortLabel(value: string): string {
  return SORT_OPTIONS.find((opt) => opt.value === value)?.label ?? 'Newest First';
}

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

export interface MemoryFilterBarProps {
  /** Currently active type tab value (e.g. "all", "constraint"). */
  typeFilter: string;
  /** Callback when the type tab changes. */
  onTypeFilterChange: (type: string) => void;
  /** Currently active status filter value. */
  statusFilter: string;
  /** Callback when the status filter changes. */
  onStatusFilterChange: (status: string) => void;
  /** Currently active sort value. */
  sortBy: string;
  /** Callback when the sort value changes. */
  onSortByChange: (sort: string) => void;
  /** Current search query string. */
  searchQuery: string;
  /** Callback when the search query changes. */
  onSearchQueryChange: (query: string) => void;
  /** Type counts for badge display (keyed by type value). */
  counts?: Record<string, number>;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

/**
 * MemoryFilterBar -- filter controls for the memory inbox.
 *
 * Renders type tabs (row 1) and status/sort/search controls (row 2),
 * each separated by `border-b`. Parent is responsible for state management.
 *
 * @example
 * ```tsx
 * <MemoryFilterBar
 *   typeFilter={typeFilter}
 *   onTypeFilterChange={setTypeFilter}
 *   statusFilter={statusFilter}
 *   onStatusFilterChange={setStatusFilter}
 *   sortBy={sortBy}
 *   onSortByChange={setSortBy}
 *   searchQuery={searchQuery}
 *   onSearchQueryChange={setSearchQuery}
 *   counts={counts}
 * />
 * ```
 */
export function MemoryFilterBar({
  typeFilter,
  onTypeFilterChange,
  statusFilter,
  onStatusFilterChange,
  sortBy,
  onSortByChange,
  searchQuery,
  onSearchQueryChange,
  counts,
}: MemoryFilterBarProps) {
  const handleSearchChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      onSearchQueryChange(e.target.value);
    },
    [onSearchQueryChange]
  );

  return (
    <>
      {/* ---------------------------------------------------------------- */}
      {/* Row 1: Type Tabs                                                 */}
      {/* ---------------------------------------------------------------- */}
      <div className="border-b px-6 py-2">
        <Tabs value={typeFilter} onValueChange={onTypeFilterChange}>
          <TabsList className="h-9 bg-transparent p-0" aria-label="Filter by memory type">
            {MEMORY_TYPES.map((type) => (
              <TabsTrigger
                key={type.value}
                value={type.value}
                className="data-[state=active]:bg-muted"
              >
                {type.icon && <type.icon className="mr-1.5 h-3.5 w-3.5" />}
                {type.label}
                <Badge variant="secondary" className="ml-1.5 px-1.5 py-0 text-[10px]">
                  {counts?.[type.value] ?? 0}
                </Badge>
              </TabsTrigger>
            ))}
          </TabsList>
        </Tabs>
      </div>

      {/* ---------------------------------------------------------------- */}
      {/* Row 2: Status + Sort + Search                                    */}
      {/* ---------------------------------------------------------------- */}
      <div
        className="flex items-center gap-3 border-b px-6 py-2"
        role="toolbar"
        aria-label="Memory filters"
      >
        {/* Status filter */}
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="outline" size="sm" className="h-8">
              <Filter className="mr-2 h-3.5 w-3.5" />
              {getStatusLabel(statusFilter)}
              <ChevronDown className="ml-2 h-3.5 w-3.5" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="start">
            <DropdownMenuRadioGroup value={statusFilter} onValueChange={onStatusFilterChange}>
              {STATUS_OPTIONS.map((opt) => (
                <DropdownMenuRadioItem key={opt.value} value={opt.value}>
                  {opt.label}
                </DropdownMenuRadioItem>
              ))}
            </DropdownMenuRadioGroup>
          </DropdownMenuContent>
        </DropdownMenu>

        {/* Sort control */}
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="outline" size="sm" className="h-8">
              <ArrowUpDown className="mr-2 h-3.5 w-3.5" />
              {getSortLabel(sortBy)}
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="start">
            <DropdownMenuRadioGroup value={sortBy} onValueChange={onSortByChange}>
              {SORT_OPTIONS.map((opt) => (
                <DropdownMenuRadioItem key={opt.value} value={opt.value}>
                  {opt.label}
                </DropdownMenuRadioItem>
              ))}
            </DropdownMenuRadioGroup>
          </DropdownMenuContent>
        </DropdownMenu>

        {/* Spacer */}
        <div className="flex-1" />

        {/* Search */}
        <div className="relative w-64">
          <Search className="pointer-events-none absolute left-2.5 top-2 h-3.5 w-3.5 text-muted-foreground" />
          <Input
            placeholder="Search memories..."
            value={searchQuery}
            onChange={handleSearchChange}
            className="h-8 pl-8 text-sm"
            aria-label="Search memories"
          />
        </div>
      </div>
    </>
  );
}
