'use client';

/**
 * SourceFilterBar Component
 *
 * Filter bar for marketplace sources list with:
 * - Artifact type filter (skill, command, agent, mcp, hook)
 * - Tags multi-select filter
 * - Trust level filter
 * - Clear individual and all filters
 */

import { X, Sparkles, Bot, Terminal, Server, Webhook, Filter } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
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

export interface SourceFilterBarProps {
  currentFilters: FilterState;
  onFilterChange: (filters: FilterState) => void;
  availableTags?: string[];
  trustLevels?: string[];
  className?: string;
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
// Component
// ============================================================================

export function SourceFilterBar({
  currentFilters,
  onFilterChange,
  availableTags = [],
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

  const handleTagToggle = (tag: string) => {
    const currentTags = currentFilters.tags || [];
    const newTags = currentTags.includes(tag)
      ? currentTags.filter((t) => t !== tag)
      : [...currentTags, tag];

    onFilterChange({
      ...currentFilters,
      tags: newTags.length > 0 ? newTags : undefined,
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
          <label
            htmlFor="trust-level-filter"
            className="text-sm font-medium text-muted-foreground"
          >
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

        {/* Tags Filter - Available Tags as clickable badges */}
        {availableTags.length > 0 && (
          <div className="flex items-center gap-2">
            <Filter className="h-4 w-4 text-muted-foreground" aria-hidden="true" />
            <span className="text-sm font-medium text-muted-foreground">Tags</span>
            <div className="flex flex-wrap gap-1.5">
              {availableTags.slice(0, 8).map((tag) => {
                const isSelected = currentFilters.tags?.includes(tag);
                return (
                  <Badge
                    key={tag}
                    variant={isSelected ? 'secondary' : 'outline'}
                    className={cn(
                      'cursor-pointer transition-colors',
                      isSelected
                        ? 'bg-secondary hover:bg-secondary/80'
                        : 'hover:bg-secondary/50'
                    )}
                    onClick={() => handleTagToggle(tag)}
                    role="button"
                    tabIndex={0}
                    aria-pressed={isSelected}
                    aria-label={`${isSelected ? 'Remove' : 'Add'} tag filter: ${tag}`}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' || e.key === ' ') {
                        e.preventDefault();
                        handleTagToggle(tag);
                      }
                    }}
                  >
                    {tag}
                  </Badge>
                );
              })}
            </div>
          </div>
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

          {/* Tag Badges */}
          {currentFilters.tags?.map((tag) => (
            <Badge key={tag} variant="secondary" className="gap-1">
              {tag}
              <button
                onClick={() => handleRemoveTag(tag)}
                className="rounded-full hover:text-destructive focus:outline-none focus:ring-2 focus:ring-ring"
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
