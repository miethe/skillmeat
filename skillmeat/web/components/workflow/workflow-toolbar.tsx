'use client';

import { useEffect, useRef, useState } from 'react';
import { LayoutGrid, List, Search, X } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { useDebounce } from '@/hooks';
import type { WorkflowFilters, WorkflowStatus } from '@/types/workflow';

// ============================================================================
// Types
// ============================================================================

interface WorkflowToolbarProps {
  filters: WorkflowFilters;
  onFiltersChange: (filters: WorkflowFilters) => void;
  view: 'grid' | 'list';
  onViewChange: (view: 'grid' | 'list') => void;
  className?: string;
}

// ============================================================================
// Constants
// ============================================================================

const STATUS_OPTIONS: { value: WorkflowStatus | 'all'; label: string }[] = [
  { value: 'all', label: 'All statuses' },
  { value: 'draft', label: 'Draft' },
  { value: 'active', label: 'Active' },
  { value: 'archived', label: 'Archived' },
  { value: 'deprecated', label: 'Deprecated' },
];

type SortKey = 'updated_desc' | 'updated_asc' | 'name_asc' | 'name_desc' | 'created_desc';

const SORT_OPTIONS: { value: SortKey; label: string }[] = [
  { value: 'updated_desc', label: 'Updated (newest)' },
  { value: 'updated_asc', label: 'Updated (oldest)' },
  { value: 'name_asc', label: 'Name (A-Z)' },
  { value: 'name_desc', label: 'Name (Z-A)' },
  { value: 'created_desc', label: 'Created (newest)' },
];

function sortKeyToFilters(
  key: SortKey
): Pick<WorkflowFilters, 'sortBy' | 'sortOrder'> {
  switch (key) {
    case 'updated_desc':
      return { sortBy: 'updated_at', sortOrder: 'desc' };
    case 'updated_asc':
      return { sortBy: 'updated_at', sortOrder: 'asc' };
    case 'name_asc':
      return { sortBy: 'name', sortOrder: 'asc' };
    case 'name_desc':
      return { sortBy: 'name', sortOrder: 'desc' };
    case 'created_desc':
      return { sortBy: 'created_at', sortOrder: 'desc' };
  }
}

function filtersToSortKey(filters: WorkflowFilters): SortKey {
  const { sortBy, sortOrder } = filters;
  if (sortBy === 'name' && sortOrder === 'asc') return 'name_asc';
  if (sortBy === 'name' && sortOrder === 'desc') return 'name_desc';
  if (sortBy === 'updated_at' && sortOrder === 'asc') return 'updated_asc';
  if (sortBy === 'created_at' && sortOrder === 'desc') return 'created_desc';
  return 'updated_desc';
}

// ============================================================================
// Component
// ============================================================================

export function WorkflowToolbar({
  filters,
  onFiltersChange,
  view,
  onViewChange,
  className,
}: WorkflowToolbarProps) {
  // Local search state — debounced before propagating up
  const [localSearch, setLocalSearch] = useState(filters.search ?? '');
  const debouncedSearch = useDebounce(localSearch, 300);
  const isInitialMount = useRef(true);

  // Sync debounced value → parent filters (skip first render to avoid
  // an extra update when the component mounts with an existing search value)
  useEffect(() => {
    if (isInitialMount.current) {
      isInitialMount.current = false;
      return;
    }
    onFiltersChange({ ...filters, search: debouncedSearch || undefined });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [debouncedSearch]);

  // Keep local state in sync if parent resets search externally
  useEffect(() => {
    if ((filters.search ?? '') !== localSearch) {
      setLocalSearch(filters.search ?? '');
    }
    // intentionally omit localSearch to avoid ping-pong
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filters.search]);

  const handleStatusChange = (value: string) => {
    const next: WorkflowFilters = { ...filters };
    if (value === 'all') {
      delete next.status;
    } else {
      next.status = value as WorkflowStatus;
    }
    onFiltersChange(next);
  };

  const handleSortChange = (value: string) => {
    onFiltersChange({
      ...filters,
      ...sortKeyToFilters(value as SortKey),
    });
  };

  const handleClearSearch = () => {
    setLocalSearch('');
    onFiltersChange({ ...filters, search: undefined });
  };

  const currentStatus = filters.status ?? 'all';
  const currentSort = filtersToSortKey(filters);

  return (
    <div
      role="search"
      aria-label="Filter and sort workflows"
      className={cn(
        // Layout
        'flex flex-wrap items-center gap-2 px-4 py-3',
        // Visual — subtle ruled border, muted fill
        'border-b border-border/60 bg-muted/30',
        className
      )}
    >
      {/* ── Search ─────────────────────────────────────────── */}
      <div className="relative min-w-[180px] flex-1">
        <Search
          className="pointer-events-none absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground"
          aria-hidden="true"
        />
        <Input
          type="search"
          placeholder="Search workflows..."
          value={localSearch}
          onChange={(e) => setLocalSearch(e.target.value)}
          aria-label="Search workflows"
          className={cn(
            'h-8 pl-8 text-sm',
            // Reserve space for the clear button only when there's text
            localSearch ? 'pr-7' : 'pr-3'
          )}
        />
        {localSearch && (
          <button
            type="button"
            onClick={handleClearSearch}
            aria-label="Clear search"
            className={cn(
              'absolute right-2 top-1/2 -translate-y-1/2',
              'text-muted-foreground transition-colors',
              'hover:text-foreground focus-visible:outline-none',
              'focus-visible:ring-1 focus-visible:ring-ring rounded-sm'
            )}
          >
            <X className="h-3.5 w-3.5" aria-hidden="true" />
          </button>
        )}
      </div>

      {/* ── Status filter ───────────────────────────────────── */}
      <Select value={currentStatus} onValueChange={handleStatusChange}>
        <SelectTrigger
          className="h-8 w-[140px] text-sm"
          aria-label="Filter by status"
        >
          <SelectValue placeholder="Status" />
        </SelectTrigger>
        <SelectContent>
          {STATUS_OPTIONS.map((opt) => (
            <SelectItem key={opt.value} value={opt.value} className="text-sm">
              {opt.label}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>

      {/* ── Sort ────────────────────────────────────────────── */}
      <Select value={currentSort} onValueChange={handleSortChange}>
        <SelectTrigger
          className="h-8 w-[172px] text-sm"
          aria-label="Sort workflows"
        >
          <SelectValue placeholder="Sort by" />
        </SelectTrigger>
        <SelectContent>
          {SORT_OPTIONS.map((opt) => (
            <SelectItem key={opt.value} value={opt.value} className="text-sm">
              {opt.label}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>

      {/* ── View toggle ─────────────────────────────────────── */}
      <div
        role="group"
        aria-label="View layout"
        className={cn(
          'flex items-center rounded-md border border-border/60',
          'bg-background overflow-hidden'
        )}
      >
        <Button
          variant="ghost"
          size="sm"
          onClick={() => onViewChange('grid')}
          aria-label="Grid view"
          aria-pressed={view === 'grid'}
          className={cn(
            'h-8 w-8 rounded-none border-0 p-0',
            'transition-colors',
            view === 'grid'
              ? 'bg-muted text-foreground'
              : 'text-muted-foreground hover:text-foreground hover:bg-muted/50'
          )}
        >
          <LayoutGrid className="h-3.5 w-3.5" aria-hidden="true" />
        </Button>
        <div className="w-px self-stretch bg-border/60" aria-hidden="true" />
        <Button
          variant="ghost"
          size="sm"
          onClick={() => onViewChange('list')}
          aria-label="List view"
          aria-pressed={view === 'list'}
          className={cn(
            'h-8 w-8 rounded-none border-0 p-0',
            'transition-colors',
            view === 'list'
              ? 'bg-muted text-foreground'
              : 'text-muted-foreground hover:text-foreground hover:bg-muted/50'
          )}
        >
          <List className="h-3.5 w-3.5" aria-hidden="true" />
        </Button>
      </div>
    </div>
  );
}
