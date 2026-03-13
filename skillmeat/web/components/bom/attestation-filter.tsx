'use client';

import * as React from 'react';
import { SlidersHorizontal, X } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import { Badge } from '@/components/ui/badge';
import { Checkbox } from '@/components/ui/checkbox';
import { Label } from '@/components/ui/label';
import { cn } from '@/lib/utils';

export interface AttestationFilterState {
  ownerScopes: string[]; // 'user' | 'team' | 'enterprise'
  dateRange: { from?: string; to?: string };
  artifactTypes: string[]; // 'skill' | 'command' | 'agent' | 'hook' | 'mcp'
}

export interface AttestationFilterProps {
  filters: AttestationFilterState;
  onFiltersChange: (filters: AttestationFilterState) => void;
  className?: string;
}

const OWNER_SCOPES = [
  { value: 'user', label: 'User' },
  { value: 'team', label: 'Team' },
  { value: 'enterprise', label: 'Enterprise' },
] as const;

const ARTIFACT_TYPES = [
  { value: 'skill', label: 'skill' },
  { value: 'command', label: 'command' },
  { value: 'agent', label: 'agent' },
  { value: 'hook', label: 'hook' },
  { value: 'mcp', label: 'mcp' },
] as const;

const DEFAULT_FILTERS: AttestationFilterState = {
  ownerScopes: OWNER_SCOPES.map((s) => s.value),
  dateRange: {},
  artifactTypes: ARTIFACT_TYPES.map((t) => t.value),
};

function isDefaultFilters(filters: AttestationFilterState): boolean {
  const allScopesSelected =
    filters.ownerScopes.length === OWNER_SCOPES.length &&
    OWNER_SCOPES.every((s) => filters.ownerScopes.includes(s.value));
  const allTypesSelected =
    filters.artifactTypes.length === ARTIFACT_TYPES.length &&
    ARTIFACT_TYPES.every((t) => filters.artifactTypes.includes(t.value));
  const noDateRange = !filters.dateRange.from && !filters.dateRange.to;
  return allScopesSelected && allTypesSelected && noDateRange;
}

function countActiveFilters(filters: AttestationFilterState): number {
  let count = 0;
  const missingScopeCount = OWNER_SCOPES.filter(
    (s) => !filters.ownerScopes.includes(s.value)
  ).length;
  if (missingScopeCount > 0) count += missingScopeCount;
  const missingTypeCount = ARTIFACT_TYPES.filter(
    (t) => !filters.artifactTypes.includes(t.value)
  ).length;
  if (missingTypeCount > 0) count += missingTypeCount;
  if (filters.dateRange.from || filters.dateRange.to) count += 1;
  return count;
}

/**
 * Popover filter panel for attestation list filtering.
 *
 * Filters by owner scope, date range, and artifact type.
 * Pure presentational — all state is managed by the parent.
 * Apply button triggers onFiltersChange; Clear resets to defaults.
 */
export function AttestationFilter({
  filters,
  onFiltersChange,
  className,
}: AttestationFilterProps) {
  const [open, setOpen] = React.useState(false);
  // Local draft state while the popover is open
  const [draft, setDraft] = React.useState<AttestationFilterState>(filters);

  // Sync draft when popover opens
  React.useEffect(() => {
    if (open) {
      setDraft(filters);
    }
  }, [open, filters]);

  const activeCount = countActiveFilters(filters);

  const toggleScope = (value: string) => {
    setDraft((prev) => ({
      ...prev,
      ownerScopes: prev.ownerScopes.includes(value)
        ? prev.ownerScopes.filter((s) => s !== value)
        : [...prev.ownerScopes, value],
    }));
  };

  const toggleType = (value: string) => {
    setDraft((prev) => ({
      ...prev,
      artifactTypes: prev.artifactTypes.includes(value)
        ? prev.artifactTypes.filter((t) => t !== value)
        : [...prev.artifactTypes, value],
    }));
  };

  const handleDateChange = (field: 'from' | 'to', value: string) => {
    setDraft((prev) => ({
      ...prev,
      dateRange: { ...prev.dateRange, [field]: value || undefined },
    }));
  };

  const handleClear = () => {
    setDraft(DEFAULT_FILTERS);
  };

  const handleApply = () => {
    onFiltersChange(draft);
    setOpen(false);
  };

  const handleOpenChange = (next: boolean) => {
    // Discard draft on close without applying
    if (!next) {
      setDraft(filters);
    }
    setOpen(next);
  };

  return (
    <Popover open={open} onOpenChange={handleOpenChange}>
      <PopoverTrigger asChild>
        <Button
          variant="outline"
          size="sm"
          aria-label="Filter attestations"
          className={cn('gap-2', className)}
        >
          <SlidersHorizontal className="h-4 w-4" />
          Filter
          {activeCount > 0 && (
            <Badge variant="secondary" className="ml-1 rounded-full px-2">
              {activeCount}
            </Badge>
          )}
        </Button>
      </PopoverTrigger>

      <PopoverContent align="end" className="w-80 p-0" role="dialog" aria-label="Filter attestations">
        {/* Header */}
        <div className="flex items-center justify-between border-b px-4 py-3">
          <span className="text-sm font-semibold">Filter Attestations</span>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setOpen(false)}
            className="h-6 w-6 p-0"
            aria-label="Close filter panel"
          >
            <X className="h-4 w-4" />
          </Button>
        </div>

        <div className="space-y-0 divide-y">
          {/* Owner Scope */}
          <fieldset className="px-4 py-3">
            <legend className="mb-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">
              Owner Scope
            </legend>
            <div className="space-y-2" role="group" aria-label="Owner scope filters">
              {OWNER_SCOPES.map((scope) => {
                const id = `attest-scope-${scope.value}`;
                return (
                  <div key={scope.value} className="flex items-center gap-2">
                    <Checkbox
                      id={id}
                      checked={draft.ownerScopes.includes(scope.value)}
                      onCheckedChange={() => toggleScope(scope.value)}
                    />
                    <Label htmlFor={id} className="cursor-pointer text-sm font-normal">
                      {scope.label}
                    </Label>
                  </div>
                );
              })}
            </div>
          </fieldset>

          {/* Date Range */}
          <fieldset className="px-4 py-3">
            <legend className="mb-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">
              Date Range
            </legend>
            <div className="grid grid-cols-2 gap-2" role="group" aria-label="Date range filters">
              <div className="space-y-1">
                <Label htmlFor="attest-date-from" className="text-xs text-muted-foreground">
                  From
                </Label>
                <input
                  id="attest-date-from"
                  type="date"
                  value={draft.dateRange.from ?? ''}
                  onChange={(e) => handleDateChange('from', e.target.value)}
                  max={draft.dateRange.to}
                  className={cn(
                    'flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1',
                    'text-sm shadow-sm transition-colors',
                    'placeholder:text-muted-foreground',
                    'focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring',
                    'disabled:cursor-not-allowed disabled:opacity-50'
                  )}
                  aria-label="Filter from date"
                />
              </div>
              <div className="space-y-1">
                <Label htmlFor="attest-date-to" className="text-xs text-muted-foreground">
                  To
                </Label>
                <input
                  id="attest-date-to"
                  type="date"
                  value={draft.dateRange.to ?? ''}
                  onChange={(e) => handleDateChange('to', e.target.value)}
                  min={draft.dateRange.from}
                  className={cn(
                    'flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1',
                    'text-sm shadow-sm transition-colors',
                    'placeholder:text-muted-foreground',
                    'focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring',
                    'disabled:cursor-not-allowed disabled:opacity-50'
                  )}
                  aria-label="Filter to date"
                />
              </div>
            </div>
          </fieldset>

          {/* Artifact Type */}
          <fieldset className="px-4 py-3">
            <legend className="mb-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">
              Artifact Type
            </legend>
            <div
              className="grid grid-cols-2 gap-x-4 gap-y-2"
              role="group"
              aria-label="Artifact type filters"
            >
              {ARTIFACT_TYPES.map((type) => {
                const id = `attest-type-${type.value}`;
                return (
                  <div key={type.value} className="flex items-center gap-2">
                    <Checkbox
                      id={id}
                      checked={draft.artifactTypes.includes(type.value)}
                      onCheckedChange={() => toggleType(type.value)}
                    />
                    <Label htmlFor={id} className="cursor-pointer font-mono text-sm font-normal">
                      {type.label}
                    </Label>
                  </div>
                );
              })}
            </div>
          </fieldset>
        </div>

        {/* Actions */}
        <div className="flex items-center justify-between border-t px-4 py-3">
          <Button
            variant="ghost"
            size="sm"
            onClick={handleClear}
            disabled={isDefaultFilters(draft)}
            className="h-8 text-muted-foreground hover:text-foreground"
          >
            Clear
          </Button>
          <Button size="sm" onClick={handleApply} className="h-8">
            Apply
          </Button>
        </div>
      </PopoverContent>
    </Popover>
  );
}
