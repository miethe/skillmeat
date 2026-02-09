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
  Archive,
  FolderKanban,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';
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
  { value: 'gotcha', label: 'Gotchas', icon: Wrench },
  { value: 'style_rule', label: 'Style Rules', icon: Puzzle },
  { value: 'learning', label: 'Learnings', icon: Lightbulb },
] as const;

const STATUS_OPTIONS = [
  { value: 'all', label: 'All Active' },
  { value: 'candidate', label: 'Candidate' },
  { value: 'active', label: 'Active' },
  { value: 'stable', label: 'Stable' },
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
  return STATUS_OPTIONS.find((opt) => opt.value === value)?.label ?? 'All Active';
}

function getSortLabel(value: string): string {
  return SORT_OPTIONS.find((opt) => opt.value === value)?.label ?? 'Newest First';
}

function getProjectLabel(value: string | undefined, projects: Array<{ id: string; name: string }>): string {
  if (!value || value === 'all') return 'All Projects';
  return projects.find((p) => p.id === value)?.name ?? 'All Projects';
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
  /** Whether to include deprecated items in the results. */
  showDeprecated: boolean;
  /** Callback when the deprecated toggle changes. */
  onShowDeprecatedChange: (show: boolean) => void;
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
  /** Optional project filter for global memory page. */
  projectFilter?: string;
  /** Callback when the project filter changes. */
  onProjectFilterChange?: (id: string) => void;
  /** List of available projects for the dropdown. */
  projects?: Array<{ id: string; name: string }>;
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
 * Optional project filter is rendered when `projects` prop is provided.
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
 *   projectFilter={projectFilter}
 *   onProjectFilterChange={setProjectFilter}
 *   projects={projects}
 * />
 * ```
 */
export function MemoryFilterBar({
  typeFilter,
  onTypeFilterChange,
  statusFilter,
  onStatusFilterChange,
  showDeprecated,
  onShowDeprecatedChange,
  sortBy,
  onSortByChange,
  searchQuery,
  onSearchQueryChange,
  counts,
  projectFilter,
  onProjectFilterChange,
  projects,
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
                {type.icon && <type.icon className="mr-1.5 h-3.5 w-3.5" aria-hidden="true" />}
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
        {/* Project filter (optional) */}
        {projects && onProjectFilterChange && (
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="outline" size="sm" className="h-8" aria-label={`Filter by project: ${getProjectLabel(projectFilter, projects)}`}>
                <FolderKanban className="mr-2 h-3.5 w-3.5" aria-hidden="true" />
                {getProjectLabel(projectFilter, projects)}
                <ChevronDown className="ml-2 h-3.5 w-3.5" aria-hidden="true" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="start">
              <DropdownMenuRadioGroup value={projectFilter ?? 'all'} onValueChange={onProjectFilterChange}>
                <DropdownMenuRadioItem value="all">All Projects</DropdownMenuRadioItem>
                {projects.map((proj) => (
                  <DropdownMenuRadioItem key={proj.id} value={proj.id}>
                    {proj.name}
                  </DropdownMenuRadioItem>
                ))}
              </DropdownMenuRadioGroup>
            </DropdownMenuContent>
          </DropdownMenu>
        )}

        {/* Status filter */}
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="outline" size="sm" className="h-8" aria-label={`Filter by status: ${getStatusLabel(statusFilter)}`}>
              <Filter className="mr-2 h-3.5 w-3.5" aria-hidden="true" />
              {getStatusLabel(statusFilter)}
              <ChevronDown className="ml-2 h-3.5 w-3.5" aria-hidden="true" />
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

        {/* Deprecated toggle */}
        <Button
          variant="ghost"
          size="sm"
          className={cn('h-8', showDeprecated && 'bg-muted')}
          onClick={() => onShowDeprecatedChange(!showDeprecated)}
          aria-label={showDeprecated ? 'Hide deprecated items' : 'Show deprecated items'}
          aria-pressed={showDeprecated}
        >
          <Archive className="mr-2 h-3.5 w-3.5" aria-hidden="true" />
          Deprecated
        </Button>

        {/* Sort control */}
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="outline" size="sm" className="h-8" aria-label={`Sort by: ${getSortLabel(sortBy)}`}>
              <ArrowUpDown className="mr-2 h-3.5 w-3.5" aria-hidden="true" />
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
          <Search className="pointer-events-none absolute left-2.5 top-2 h-3.5 w-3.5 text-muted-foreground" aria-hidden="true" />
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
