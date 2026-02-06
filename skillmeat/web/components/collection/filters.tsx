'use client';

import { Search } from 'lucide-react';
import { Input } from '@/components/ui/input';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { GroupFilterSelect } from '@/components/shared/group-filter-select';
import { TagFilterPopover, TagFilterBar } from '@/components/ui/tag-filter-popover';
import { ToolFilterPopover, ToolFilterBar } from '@/components/ui/tool-filter-popover';
import { useCollectionContext } from '@/hooks';
import type { ArtifactFilters, ArtifactSort, SortField, SortOrder } from '@/types/artifact';

interface FiltersProps {
  filters: ArtifactFilters;
  sort: ArtifactSort;
  onFiltersChange: (filters: ArtifactFilters) => void;
  onSortChange: (sort: ArtifactSort) => void;
}

export function Filters({ filters, sort, onFiltersChange, onSortChange }: FiltersProps) {
  const { selectedCollectionId } = useCollectionContext();

  const handleFilterChange = (key: keyof ArtifactFilters, value: string) => {
    onFiltersChange({
      ...filters,
      [key]: value === 'all' ? undefined : value,
    });
  };

  const handleTagsChange = (tags: string[]) => {
    onFiltersChange({
      ...filters,
      tags: tags.length > 0 ? tags : undefined,
    });
  };

  const handleToolsChange = (tools: string[]) => {
    onFiltersChange({
      ...filters,
      tools: tools.length > 0 ? tools : undefined,
    });
  };

  const handleSortFieldChange = (value: string) => {
    onSortChange({
      ...sort,
      field: value as SortField,
    });
  };

  const handleSortOrderChange = (value: string) => {
    onSortChange({
      ...sort,
      order: value as SortOrder,
    });
  };

  // Determine if we're in a specific collection context (not "All Collections")
  const isSpecificCollectionContext = selectedCollectionId && selectedCollectionId !== 'all';

  return (
    <div className="space-y-4">
      {/* Search */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
        <Input
          placeholder="Search artifacts by name, description, or tags..."
          value={filters.search || ''}
          onChange={(e) => handleFilterChange('search', e.target.value)}
          className="pl-9"
        />
      </div>

      {/* Filter Controls */}
      <div
        className={`grid grid-cols-1 gap-4 sm:grid-cols-2 ${
          isSpecificCollectionContext ? 'lg:grid-cols-7' : 'lg:grid-cols-6'
        }`}
      >
        {/* Type Filter */}
        <div>
          <label htmlFor="type-filter" className="mb-1.5 block text-sm font-medium">
            Type
          </label>
          <Select
            value={filters.type || 'all'}
            onValueChange={(value) => handleFilterChange('type', value)}
          >
            <SelectTrigger id="type-filter">
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
        <div>
          <label htmlFor="status-filter" className="mb-1.5 block text-sm font-medium">
            Status
          </label>
          <Select
            value={filters.status || 'all'}
            onValueChange={(value) => handleFilterChange('status', value)}
          >
            <SelectTrigger id="status-filter">
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
        <div>
          <label htmlFor="scope-filter" className="mb-1.5 block text-sm font-medium">
            Scope
          </label>
          <Select
            value={filters.scope || 'all'}
            onValueChange={(value) => handleFilterChange('scope', value)}
          >
            <SelectTrigger id="scope-filter">
              <SelectValue placeholder="All Scopes" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Scopes</SelectItem>
              <SelectItem value="user">User (Global)</SelectItem>
              <SelectItem value="local">Local (Project)</SelectItem>
            </SelectContent>
          </Select>
        </div>

        {/* Group Filter - Only show in specific collection context */}
        {isSpecificCollectionContext && selectedCollectionId && (
          <div>
            <label htmlFor="group-filter" className="mb-1.5 block text-sm font-medium">
              Group
            </label>
            <GroupFilterSelect
              collectionId={selectedCollectionId}
              value={filters.groupId}
              onChange={(groupId) => onFiltersChange({ ...filters, groupId })}
            />
          </div>
        )}

        {/* Tags Filter */}
        <div>
          <label className="mb-1.5 block text-sm font-medium">Tags</label>
          <TagFilterPopover
            selectedTags={filters.tags || []}
            onChange={handleTagsChange}
            className="w-full justify-start"
          />
        </div>

        {/* Tools Filter */}
        <div>
          <label className="mb-1.5 block text-sm font-medium">Tools</label>
          <ToolFilterPopover
            selectedTools={filters.tools || []}
            onChange={handleToolsChange}
            className="w-full justify-start"
          />
        </div>

        {/* Sort Controls */}
        <div>
          <label htmlFor="sort-field" className="mb-1.5 block text-sm font-medium">
            Sort By
          </label>
          <div className="flex gap-2">
            <Select value={sort.field} onValueChange={handleSortFieldChange}>
              <SelectTrigger id="sort-field" className="flex-1">
                <SelectValue placeholder="Name" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="name">Name</SelectItem>
                <SelectItem value="updatedAt">Last Updated</SelectItem>
                <SelectItem value="usageCount">Usage Count</SelectItem>
              </SelectContent>
            </Select>
            <Select value={sort.order} onValueChange={handleSortOrderChange}>
              <SelectTrigger id="sort-order" aria-label="Sort order">
                <SelectValue placeholder="A-Z" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="asc">A-Z</SelectItem>
                <SelectItem value="desc">Z-A</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>
      </div>

      {/* Selected Tags Bar */}
      <TagFilterBar selectedTags={filters.tags || []} onChange={handleTagsChange} />

      {/* Selected Tools Bar */}
      <ToolFilterBar selectedTools={filters.tools || []} onChange={handleToolsChange} />
    </div>
  );
}
