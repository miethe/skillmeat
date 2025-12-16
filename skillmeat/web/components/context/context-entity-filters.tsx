'use client';

import { Search, X } from 'lucide-react';
import { Input } from '@/components/ui/input';
import { Checkbox } from '@/components/ui/checkbox';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Switch } from '@/components/ui/switch';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import type { ContextEntityFilters, ContextEntityType } from '@/types/context-entity';

interface ContextEntityFiltersProps {
  filters: ContextEntityFilters;
  onFiltersChange: (filters: ContextEntityFilters) => void;
}

const ENTITY_TYPES: { value: ContextEntityType; label: string }[] = [
  { value: 'project_config', label: 'Project Config' },
  { value: 'spec_file', label: 'Spec File' },
  { value: 'rule_file', label: 'Rule File' },
  { value: 'context_file', label: 'Context File' },
  { value: 'progress_template', label: 'Progress Template' },
];

export function ContextEntityFilters({ filters, onFiltersChange }: ContextEntityFiltersProps) {
  const handleSearchChange = (value: string) => {
    onFiltersChange({
      ...filters,
      search: value || undefined,
    });
  };

  const handleEntityTypeToggle = (entityType: ContextEntityType) => {
    // If currently filtered by this type, clear the filter
    // Otherwise, set filter to this type
    onFiltersChange({
      ...filters,
      entity_type: filters.entity_type === entityType ? undefined : entityType,
    });
  };

  const handleCategoryChange = (value: string) => {
    onFiltersChange({
      ...filters,
      category: value === '' ? undefined : value,
    });
  };

  const handleAutoLoadToggle = (checked: boolean) => {
    onFiltersChange({
      ...filters,
      auto_load: checked,
    });
  };

  const handleClearFilters = () => {
    onFiltersChange({
      search: undefined,
      entity_type: undefined,
      category: undefined,
      auto_load: undefined,
    });
  };

  const hasActiveFilters =
    filters.search ||
    filters.entity_type ||
    filters.category ||
    filters.auto_load !== undefined;

  const activeFilterCount = [
    filters.search,
    filters.entity_type,
    filters.category,
    filters.auto_load !== undefined,
  ].filter(Boolean).length;

  return (
    <div className="space-y-6 p-4">
      {/* Search */}
      <div>
        <Label htmlFor="search" className="mb-2 block text-sm font-medium">
          Search
        </Label>
        <div className="relative">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            id="search"
            placeholder="Search by name or description..."
            value={filters.search || ''}
            onChange={(e) => handleSearchChange(e.target.value)}
            className="pl-9"
          />
        </div>
      </div>

      {/* Entity Type Filter */}
      <div>
        <Label className="mb-3 block text-sm font-medium">
          Entity Type
        </Label>
        <div className="space-y-3">
          {ENTITY_TYPES.map((type) => (
            <div key={type.value} className="flex items-center space-x-2">
              <Checkbox
                id={`type-${type.value}`}
                checked={filters.entity_type === type.value}
                onCheckedChange={() => handleEntityTypeToggle(type.value)}
              />
              <Label
                htmlFor={`type-${type.value}`}
                className="cursor-pointer text-sm font-normal leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70"
              >
                {type.label}
              </Label>
            </div>
          ))}
        </div>
      </div>

      {/* Category Filter */}
      <div>
        <Label htmlFor="category" className="mb-2 block text-sm font-medium">
          Category
        </Label>
        <Select
          value={filters.category || ''}
          onValueChange={handleCategoryChange}
        >
          <SelectTrigger id="category">
            <SelectValue placeholder="All Categories" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="">All Categories</SelectItem>
            <SelectItem value="api">API</SelectItem>
            <SelectItem value="frontend">Frontend</SelectItem>
            <SelectItem value="debugging">Debugging</SelectItem>
            <SelectItem value="testing">Testing</SelectItem>
            <SelectItem value="deployment">Deployment</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Auto-Load Toggle */}
      <div className="flex items-center justify-between">
        <Label htmlFor="auto-load" className="text-sm font-medium">
          Auto-load only
        </Label>
        <Switch
          id="auto-load"
          checked={filters.auto_load || false}
          onCheckedChange={handleAutoLoadToggle}
        />
      </div>

      {/* Clear Filters Button */}
      {hasActiveFilters && (
        <Button
          variant="outline"
          size="sm"
          onClick={handleClearFilters}
          className="w-full"
          aria-label={`Clear ${activeFilterCount} active ${activeFilterCount === 1 ? 'filter' : 'filters'}`}
        >
          <X className="mr-2 h-4 w-4" aria-hidden="true" />
          Clear {activeFilterCount} {activeFilterCount === 1 ? 'Filter' : 'Filters'}
        </Button>
      )}
    </div>
  );
}
