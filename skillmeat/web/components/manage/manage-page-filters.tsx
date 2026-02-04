'use client';

import * as React from 'react';
import { Search, X, FolderKanban } from 'lucide-react';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { TagFilterPopover } from '@/components/ui/tag-filter-popover';
import type { ArtifactType } from '@/types/artifact';

/**
 * Status filter options specific to the manage/operations page.
 * These reflect deployment and sync states rather than collection states.
 */
export type ManageStatusFilter = 'all' | 'needs-update' | 'has-drift' | 'deployed' | 'error';

/**
 * Status option configuration for the filter dropdown.
 */
interface StatusOption {
  value: ManageStatusFilter;
  label: string;
  description?: string;
}

const STATUS_OPTIONS: StatusOption[] = [
  { value: 'all', label: 'All Status' },
  { value: 'needs-update', label: 'Needs Update', description: 'Upstream has newer version' },
  { value: 'has-drift', label: 'Has Drift', description: 'Local changes detected' },
  { value: 'deployed', label: 'Deployed', description: 'Currently deployed to projects' },
  { value: 'error', label: 'Error', description: 'Sync or deployment errors' },
];

/**
 * Type filter options for artifact types.
 */
interface TypeOption {
  value: ArtifactType | 'all';
  label: string;
}

const TYPE_OPTIONS: TypeOption[] = [
  { value: 'all', label: 'All Types' },
  { value: 'skill', label: 'Skills' },
  { value: 'command', label: 'Commands' },
  { value: 'agent', label: 'Agents' },
  { value: 'mcp', label: 'MCP Servers' },
  { value: 'hook', label: 'Hooks' },
];

/**
 * Props for the ManagePageFilters component.
 */
export interface ManagePageFiltersProps {
  // Current filter values
  search: string;
  status: ManageStatusFilter;
  type: ArtifactType | 'all';
  project: string | null;
  tags: string[];

  // Callbacks
  onSearchChange: (search: string) => void;
  onStatusChange: (status: ManageStatusFilter) => void;
  onTypeChange: (type: ArtifactType | 'all') => void;
  onProjectChange: (project: string | null) => void;
  onTagsChange: (tags: string[]) => void;
  onClearAll: () => void;

  // Data
  availableProjects: string[];
  availableTags?: Array<{ name: string; artifact_count: number }>;
}

/**
 * ManagePageFilters component for filtering artifacts on the manage page.
 *
 * Provides comprehensive filtering options including:
 * - Project dropdown (filter by deployed project)
 * - Status filter (All, Needs Update, Has Drift, Deployed, Error)
 * - Type filter (skill, command, agent, mcp, hook)
 * - Search input with debounce
 * - Tag filter with multi-select popover
 *
 * @example
 * ```tsx
 * <ManagePageFilters
 *   search={search}
 *   status={status}
 *   type={type}
 *   project={project}
 *   tags={tags}
 *   onSearchChange={setSearch}
 *   onStatusChange={setStatus}
 *   onTypeChange={setType}
 *   onProjectChange={setProject}
 *   onTagsChange={setTags}
 *   onClearAll={handleClearAll}
 *   availableProjects={projects}
 * />
 * ```
 */
export function ManagePageFilters({
  search,
  status,
  type,
  project,
  tags,
  onSearchChange,
  onStatusChange,
  onTypeChange,
  onProjectChange,
  onTagsChange,
  onClearAll,
  availableProjects,
  availableTags,
}: ManagePageFiltersProps) {
  // Debounced search state
  const [searchInput, setSearchInput] = React.useState(search);
  const debounceTimerRef = React.useRef<NodeJS.Timeout | null>(null);

  // Sync searchInput with search prop when it changes externally
  React.useEffect(() => {
    setSearchInput(search);
  }, [search]);

  // Handle search input with debounce
  const handleSearchInputChange = (value: string) => {
    setSearchInput(value);

    // Clear existing timer
    if (debounceTimerRef.current) {
      clearTimeout(debounceTimerRef.current);
    }

    // Set new debounce timer (300ms)
    debounceTimerRef.current = setTimeout(() => {
      onSearchChange(value);
    }, 300);
  };

  // Cleanup debounce timer on unmount
  React.useEffect(() => {
    return () => {
      if (debounceTimerRef.current) {
        clearTimeout(debounceTimerRef.current);
      }
    };
  }, []);

  // Check if any filters are active
  const hasActiveFilters =
    search !== '' ||
    status !== 'all' ||
    type !== 'all' ||
    project !== null ||
    tags.length > 0;

  // Count active filters (excluding search)
  const activeFilterCount =
    (status !== 'all' ? 1 : 0) +
    (type !== 'all' ? 1 : 0) +
    (project !== null ? 1 : 0) +
    tags.length;

  return (
    <div className="space-y-3 border-b bg-muted/20 p-4" role="search" aria-label="Filter artifacts">
      {/* Primary Filter Row */}
      <div className="flex flex-wrap items-center gap-3">
        {/* Search Input */}
        <div className="relative min-w-[200px] flex-1">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" aria-hidden="true" />
          <Input
            placeholder="Search artifacts..."
            value={searchInput}
            onChange={(e) => handleSearchInputChange(e.target.value)}
            className="pl-9"
            aria-label="Search artifacts by name or description"
          />
          {searchInput && (
            <Button
              variant="ghost"
              size="sm"
              className="absolute right-1 top-1/2 h-6 w-6 -translate-y-1/2 p-0"
              onClick={() => {
                setSearchInput('');
                onSearchChange('');
              }}
              aria-label="Clear search"
            >
              <X className="h-3 w-3" aria-hidden="true" />
            </Button>
          )}
        </div>

        {/* Project Filter (Prominent) */}
        <Select
          value={project || 'all'}
          onValueChange={(value) => onProjectChange(value === 'all' ? null : value)}
        >
          <SelectTrigger className="w-[200px]" aria-label="Filter by project">
            <FolderKanban className="mr-2 h-4 w-4 text-muted-foreground" aria-hidden="true" />
            <SelectValue placeholder="All Projects" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Projects</SelectItem>
            {availableProjects.map((proj) => (
              <SelectItem key={proj} value={proj}>
                {proj}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        {/* Status Filter */}
        <Select
          value={status}
          onValueChange={(value) => onStatusChange(value as ManageStatusFilter)}
        >
          <SelectTrigger className="w-[160px]" aria-label="Filter by status">
            <SelectValue placeholder="All Status" />
          </SelectTrigger>
          <SelectContent>
            {STATUS_OPTIONS.map((option) => (
              <SelectItem key={option.value} value={option.value}>
                {option.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        {/* Type Filter */}
        <Select
          value={type}
          onValueChange={(value) => onTypeChange(value as ArtifactType | 'all')}
        >
          <SelectTrigger className="w-[140px]" aria-label="Filter by artifact type">
            <SelectValue placeholder="All Types" />
          </SelectTrigger>
          <SelectContent>
            {TYPE_OPTIONS.map((option) => (
              <SelectItem key={option.value} value={option.value}>
                {option.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        {/* Tags Filter Popover */}
        <TagFilterPopover
          selectedTags={tags}
          onChange={onTagsChange}
          availableTags={availableTags}
          className="h-9 text-sm"
        />

        {/* Clear All Button */}
        {hasActiveFilters && (
          <Button
            variant="ghost"
            size="sm"
            onClick={onClearAll}
            className="text-muted-foreground hover:text-foreground"
          >
            Clear All
          </Button>
        )}
      </div>

      {/* Active Filters Display (Chips) */}
      {activeFilterCount > 0 && (
        <div className="flex flex-wrap items-center gap-2" role="status" aria-live="polite" aria-label="Active filters">
          <span className="text-sm text-muted-foreground">Active filters:</span>

          {/* Project chip */}
          {project && (
            <Badge variant="secondary" className="gap-1">
              Project: {project}
              <button
                type="button"
                className="ml-1 rounded-full p-0.5 hover:bg-muted-foreground/20 focus:outline-none focus:ring-2 focus:ring-ring"
                onClick={() => onProjectChange(null)}
                aria-label={`Remove project filter: ${project}`}
              >
                <X className="h-3 w-3" aria-hidden="true" />
              </button>
            </Badge>
          )}

          {/* Status chip */}
          {status !== 'all' && (
            <Badge variant="secondary" className="gap-1">
              Status: {STATUS_OPTIONS.find((o) => o.value === status)?.label}
              <button
                type="button"
                className="ml-1 rounded-full p-0.5 hover:bg-muted-foreground/20 focus:outline-none focus:ring-2 focus:ring-ring"
                onClick={() => onStatusChange('all')}
                aria-label={`Remove status filter: ${STATUS_OPTIONS.find((o) => o.value === status)?.label}`}
              >
                <X className="h-3 w-3" aria-hidden="true" />
              </button>
            </Badge>
          )}

          {/* Type chip */}
          {type !== 'all' && (
            <Badge variant="secondary" className="gap-1">
              Type: {TYPE_OPTIONS.find((o) => o.value === type)?.label}
              <button
                type="button"
                className="ml-1 rounded-full p-0.5 hover:bg-muted-foreground/20 focus:outline-none focus:ring-2 focus:ring-ring"
                onClick={() => onTypeChange('all')}
                aria-label={`Remove type filter: ${TYPE_OPTIONS.find((o) => o.value === type)?.label}`}
              >
                <X className="h-3 w-3" aria-hidden="true" />
              </button>
            </Badge>
          )}

          {/* Tag chips */}
          {tags.map((tagName) => (
            <Badge key={tagName} variant="secondary" className="gap-1">
              {tagName}
              <button
                type="button"
                className="ml-1 rounded-full p-0.5 hover:bg-muted-foreground/20 focus:outline-none focus:ring-2 focus:ring-ring"
                onClick={() => onTagsChange(tags.filter((t) => t !== tagName))}
                aria-label={`Remove tag filter: ${tagName}`}
              >
                <X className="h-3 w-3" aria-hidden="true" />
              </button>
            </Badge>
          ))}
        </div>
      )}
    </div>
  );
}
