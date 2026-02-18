'use client';

import { useState } from 'react';
import { Search, Filter, X } from 'lucide-react';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuLabel,
  DropdownMenuRadioGroup,
  DropdownMenuRadioItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { EntityStatus } from '@/types/entity';
import { Badge } from '@/components/ui/badge';
import { GroupFilterSelect } from '@/components/shared/group-filter-select';
import { useCollectionContext } from '@/hooks';

interface EntityFiltersProps {
  searchQuery: string;
  onSearchChange: (query: string) => void;
  statusFilter: EntityStatus | null;
  onStatusFilterChange: (status: EntityStatus | null) => void;
  tagFilter: string[];
  onTagFilterChange: (tags: string[]) => void;
  availableTags?: string[];
  /** Currently selected group ID for filtering (optional) */
  groupId?: string;
  /** Callback when group filter changes (optional) */
  onGroupFilterChange?: (groupId: string | undefined) => void;
}

const STATUS_OPTIONS: { value: EntityStatus | 'all'; label: string }[] = [
  { value: 'all', label: 'All Status' },
  { value: 'synced', label: 'Synced' },
  { value: 'modified', label: 'Modified' },
  { value: 'outdated', label: 'Outdated' },
  { value: 'conflict', label: 'Conflict' },
];

export function EntityFilters({
  searchQuery,
  onSearchChange,
  statusFilter,
  onStatusFilterChange,
  tagFilter,
  onTagFilterChange,
  groupId,
  onGroupFilterChange,
}: EntityFiltersProps) {
  const [tagInputValue, setTagInputValue] = useState('');
  const { selectedCollectionId } = useCollectionContext();

  const handleStatusChange = (value: string) => {
    if (value === 'all') {
      onStatusFilterChange(null);
    } else {
      onStatusFilterChange(value as EntityStatus);
    }
  };

  const handleAddTag = (tag: string) => {
    if (tag && !tagFilter.includes(tag)) {
      onTagFilterChange([...tagFilter, tag]);
    }
  };

  const handleRemoveTag = (tag: string) => {
    onTagFilterChange(tagFilter.filter((t) => t !== tag));
  };

  const handleTagInputKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' || e.key === ',') {
      e.preventDefault();
      const tag = tagInputValue.trim();
      if (tag) {
        handleAddTag(tag);
        setTagInputValue('');
      }
    }
  };

  return (
    <div className="flex flex-col gap-3 border-b bg-muted/20 p-4">
      {/* Search and Status Filter */}
      <div className="flex gap-3">
        {/* Search */}
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 transform text-muted-foreground" />
          <Input
            placeholder="Search entities..."
            value={searchQuery}
            onChange={(e) => onSearchChange(e.target.value)}
            className="pl-9"
          />
        </div>

        {/* Status Filter Dropdown */}
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="outline" className="gap-2">
              <Filter className="h-4 w-4" />
              {statusFilter
                ? STATUS_OPTIONS.find((o) => o.value === statusFilter)?.label
                : 'All Status'}
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-48">
            <DropdownMenuLabel>Filter by Status</DropdownMenuLabel>
            <DropdownMenuSeparator />
            <DropdownMenuRadioGroup
              value={statusFilter || 'all'}
              onValueChange={handleStatusChange}
            >
              {STATUS_OPTIONS.map((option) => (
                <DropdownMenuRadioItem key={option.value} value={option.value}>
                  {option.label}
                </DropdownMenuRadioItem>
              ))}
            </DropdownMenuRadioGroup>
          </DropdownMenuContent>
        </DropdownMenu>

        {/* Group Filter - Always shown when collection context and handler are available */}
        {selectedCollectionId && selectedCollectionId !== 'all' && onGroupFilterChange && (
          <GroupFilterSelect
            collectionId={selectedCollectionId}
            value={groupId}
            onChange={onGroupFilterChange}
            className="w-48"
          />
        )}
      </div>

      {/* Tag Filter */}
      <div className="flex items-center gap-2">
        <div className="flex flex-1 flex-wrap items-center gap-2">
          <span className="text-sm text-muted-foreground">Tags:</span>

          {/* Selected tags */}
          {tagFilter.map((tag) => (
            <Badge key={tag} variant="secondary" className="gap-1">
              {tag}
              <button onClick={() => handleRemoveTag(tag)} className="hover:text-destructive">
                <X className="h-3 w-3" />
              </button>
            </Badge>
          ))}

          {/* Tag input */}
          <Input
            placeholder="Add tag filter..."
            value={tagInputValue}
            onChange={(e) => setTagInputValue(e.target.value)}
            onKeyDown={handleTagInputKeyDown}
            className="h-7 w-40 text-sm"
          />
        </div>

        {/* Clear filters */}
        {(searchQuery || statusFilter || tagFilter.length > 0 || groupId) && (
          <Button
            variant="ghost"
            size="sm"
            onClick={() => {
              onSearchChange('');
              onStatusFilterChange(null);
              onTagFilterChange([]);
              onGroupFilterChange?.(undefined);
            }}
          >
            Clear All
          </Button>
        )}
      </div>
    </div>
  );
}
