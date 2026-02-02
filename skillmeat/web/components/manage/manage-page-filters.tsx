'use client';

import * as React from 'react';
import { Search, X, Filter, FolderKanban, Check } from 'lucide-react';
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
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover';
import { ScrollArea } from '@/components/ui/scroll-area';
import { cn } from '@/lib/utils';
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
  availableTags: string[];
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
 *   availableTags={allTags}
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

  // Tag popover state
  const [tagPopoverOpen, setTagPopoverOpen] = React.useState(false);
  const [tagSearch, setTagSearch] = React.useState('');

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

  // Filter available tags by search
  const filteredTags = React.useMemo(() => {
    if (!tagSearch) return availableTags;
    return availableTags.filter((tag) =>
      tag.toLowerCase().includes(tagSearch.toLowerCase())
    );
  }, [availableTags, tagSearch]);

  // Toggle tag selection
  const toggleTag = (tagName: string) => {
    if (tags.includes(tagName)) {
      onTagsChange(tags.filter((t) => t !== tagName));
    } else {
      onTagsChange([...tags, tagName]);
    }
  };

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
    <div className="space-y-3 border-b bg-muted/20 p-4">
      {/* Primary Filter Row */}
      <div className="flex flex-wrap items-center gap-3">
        {/* Search Input */}
        <div className="relative min-w-[200px] flex-1">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder="Search artifacts..."
            value={searchInput}
            onChange={(e) => handleSearchInputChange(e.target.value)}
            className="pl-9"
            aria-label="Search artifacts"
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
              <X className="h-3 w-3" />
            </Button>
          )}
        </div>

        {/* Project Filter (Prominent) */}
        <Select
          value={project || 'all'}
          onValueChange={(value) => onProjectChange(value === 'all' ? null : value)}
        >
          <SelectTrigger className="w-[200px]" aria-label="Filter by project">
            <FolderKanban className="mr-2 h-4 w-4 text-muted-foreground" />
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
          <SelectTrigger className="w-[140px]" aria-label="Filter by type">
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
        <Popover open={tagPopoverOpen} onOpenChange={setTagPopoverOpen}>
          <PopoverTrigger asChild>
            <Button variant="outline" size="default" className="gap-2">
              <Filter className="h-4 w-4" />
              Tags
              {tags.length > 0 && (
                <Badge variant="secondary" className="ml-1 rounded-full px-2">
                  {tags.length}
                </Badge>
              )}
            </Button>
          </PopoverTrigger>
          <PopoverContent className="w-72 p-0" align="start">
            <div className="border-b p-3">
              <div className="mb-2 flex items-center justify-between">
                <span className="text-sm font-medium">Filter by tags</span>
                {tags.length > 0 && (
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => {
                      onTagsChange([]);
                      setTagSearch('');
                    }}
                    className="h-6 px-2 text-xs"
                  >
                    Clear all
                  </Button>
                )}
              </div>
              <div className="relative">
                <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder="Search tags..."
                  value={tagSearch}
                  onChange={(e) => setTagSearch(e.target.value)}
                  className="h-9 pl-8"
                />
              </div>
            </div>
            <ScrollArea className="h-60">
              <div className="p-2">
                {filteredTags.length === 0 ? (
                  <div className="py-4 text-center text-sm text-muted-foreground">
                    No tags found
                  </div>
                ) : (
                  filteredTags.map((tagName) => {
                    const isSelected = tags.includes(tagName);
                    return (
                      <div
                        key={tagName}
                        className={cn(
                          'flex cursor-pointer items-center justify-between rounded-md px-2 py-1.5 hover:bg-accent',
                          isSelected && 'bg-accent'
                        )}
                        onClick={() => toggleTag(tagName)}
                      >
                        <div className="flex items-center gap-2">
                          <div
                            className={cn(
                              'flex h-4 w-4 items-center justify-center rounded border',
                              isSelected ? 'border-primary bg-primary' : 'border-input'
                            )}
                          >
                            {isSelected && <Check className="h-3 w-3 text-primary-foreground" />}
                          </div>
                          <Badge variant="secondary">{tagName}</Badge>
                        </div>
                      </div>
                    );
                  })
                )}
              </div>
            </ScrollArea>
          </PopoverContent>
        </Popover>

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
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-sm text-muted-foreground">Active filters:</span>

          {/* Project chip */}
          {project && (
            <Badge variant="secondary" className="gap-1">
              Project: {project}
              <X
                className="h-3 w-3 cursor-pointer hover:opacity-70"
                onClick={() => onProjectChange(null)}
              />
            </Badge>
          )}

          {/* Status chip */}
          {status !== 'all' && (
            <Badge variant="secondary" className="gap-1">
              Status: {STATUS_OPTIONS.find((o) => o.value === status)?.label}
              <X
                className="h-3 w-3 cursor-pointer hover:opacity-70"
                onClick={() => onStatusChange('all')}
              />
            </Badge>
          )}

          {/* Type chip */}
          {type !== 'all' && (
            <Badge variant="secondary" className="gap-1">
              Type: {TYPE_OPTIONS.find((o) => o.value === type)?.label}
              <X
                className="h-3 w-3 cursor-pointer hover:opacity-70"
                onClick={() => onTypeChange('all')}
              />
            </Badge>
          )}

          {/* Tag chips */}
          {tags.map((tagName) => (
            <Badge key={tagName} variant="secondary" className="gap-1">
              {tagName}
              <X
                className="h-3 w-3 cursor-pointer hover:opacity-70"
                onClick={() => onTagsChange(tags.filter((t) => t !== tagName))}
              />
            </Badge>
          ))}
        </div>
      )}
    </div>
  );
}
