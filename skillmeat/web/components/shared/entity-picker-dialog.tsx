'use client';

import React, { useCallback, useEffect, useRef, useState } from 'react';
import { ChevronDown, Loader2, Package, Search, X } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Skeleton } from '@/components/ui/skeleton';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { useDebounce, useIntersectionObserver } from '@/hooks';
import { cn } from '@/lib/utils';

// ---------------------------------------------------------------------------
// Public interfaces
// ---------------------------------------------------------------------------

/**
 * Normalized result shape returned by each tab's `useData` hook.
 * Callers wrap their query hooks to conform to this interface.
 */
export interface InfiniteDataResult<T> {
  /** Flat list of items loaded so far across all pages */
  items: T[];
  /** True while the first page is loading */
  isLoading: boolean;
  /** True when more pages are available */
  hasNextPage: boolean;
  /** Trigger loading the next page */
  fetchNextPage: () => void;
  /** True while a subsequent page is loading */
  isFetchingNextPage: boolean;
}

/**
 * Definition for a single tab inside EntityPickerDialog.
 *
 * @template T - The entity type rendered within this tab
 */
export interface EntityPickerTab<T> {
  /** Unique stable identifier for this tab */
  id: string;
  /** Human-readable label rendered in the tab strip */
  label: string;
  /** Lucide-compatible icon component shown beside the label */
  icon: React.ComponentType<{ className?: string }>;
  /**
   * Hook factory called with the current search + type filter.
   * Must return an `InfiniteDataResult<T>`.
   */
  useData: (params: { search: string; typeFilter?: string[] }) => InfiniteDataResult<T>;
  /**
   * Renders a single list card.
   * @param item - The entity to render
   * @param isSelected - Whether this entity is in the current selection
   */
  renderCard: (item: T, isSelected: boolean) => React.ReactNode;
  /** Extracts the stable entity identifier used for selection tracking */
  getId: (item: T) => string;
  /** Optional type filter pill definitions shown below the search bar */
  typeFilters?: {
    value: string;
    label: string;
    icon?: React.ComponentType<{ className?: string }>;
  }[];
}

/**
 * Props for EntityPickerDialog.
 *
 * @template T - The entity type handled by the active tab
 */
export interface EntityPickerDialogProps<T = unknown> {
  /** Controls dialog visibility */
  open: boolean;
  /** Called when the dialog requests open state change */
  onOpenChange: (open: boolean) => void;
  /** One or more tabs defining entity types the user can pick from */
  tabs: EntityPickerTab<T>[];
  /** Single-select closes on first pick; multi-select accumulates until "Done" */
  mode: 'single' | 'multi';
  /**
   * Controlled selection value.
   * - `'single'` mode: a single entity ID string (or empty string for none)
   * - `'multi'` mode: an array of entity ID strings
   */
  value: string | string[];
  /**
   * Called when the selection commits.
   * Receives the same shape as `value`.
   */
  onChange: (value: string | string[]) => void;
  /** Dialog title shown in the header */
  title?: string;
  /** Supplementary description shown below the title */
  description?: string;
}

/**
 * Props for EntityPickerTrigger.
 */
export interface EntityPickerTriggerProps {
  /** Accessible label and button text used as the field caption */
  label: string;
  /** Current selection value (mirrors EntityPickerDialogProps.value) */
  value: string | string[];
  /** Named items for selected IDs — used to render display names and remove badges */
  items?: { id: string; name: string }[];
  /** Must match the mode of the companion EntityPickerDialog */
  mode: 'single' | 'multi';
  /** Called when the user clicks the trigger to open the picker dialog */
  onClick: () => void;
  /**
   * Multi-mode only: called when the user removes an individual item badge.
   * @param id - The entity ID to remove
   */
  onRemove?: (id: string) => void;
  /** Placeholder text shown when nothing is selected */
  placeholder?: string;
  /** Disables all interactions */
  disabled?: boolean;
  /** Additional CSS classes for the outermost wrapper */
  className?: string;
}

// ---------------------------------------------------------------------------
// Internal sub-components
// ---------------------------------------------------------------------------

/** Grid of skeleton cards shown during initial data load */
function GridSkeleton({ count = 6 }: { count?: number }) {
  return (
    <div className="grid grid-cols-2 gap-2 sm:grid-cols-3" aria-label="Loading items" aria-busy="true">
      {Array.from({ length: count }).map((_, i) => (
        <div
          key={i}
          className="flex min-w-[160px] flex-col gap-2 rounded-lg border border-l-[3px] border-l-muted p-3"
        >
          <div className="flex items-center gap-1.5">
            <Skeleton className="h-4 w-4 rounded" />
            <Skeleton className="h-4 flex-1 rounded" />
          </div>
          <Skeleton className="h-3 w-full rounded" />
          <Skeleton className="h-3 w-2/3 rounded" />
          <div className="mt-auto pt-1">
            <Skeleton className="h-4 w-1/2 rounded" />
          </div>
        </div>
      ))}
    </div>
  );
}

/** Empty state shown when item list is empty after loading */
function EmptyState({ message }: { message: string }) {
  return (
    <div className="flex flex-col items-center justify-center py-12 text-center">
      <Package className="h-9 w-9 text-muted-foreground/30" aria-hidden="true" />
      <p className="mt-3 text-sm text-muted-foreground">{message}</p>
    </div>
  );
}

/** Inline search input with search icon and clear button */
interface SearchInputProps {
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
}

function SearchInput({ value, onChange, placeholder = 'Search\u2026' }: SearchInputProps) {
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    // Auto-focus on mount (dialog already traps focus; this targets the input specifically)
    const timer = setTimeout(() => inputRef.current?.focus(), 0);
    return () => clearTimeout(timer);
  }, []);

  return (
    <div className="relative">
      <Search
        className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground"
        aria-hidden="true"
      />
      <Input
        ref={inputRef}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className="pl-9 pr-9"
        aria-label={placeholder}
        autoComplete="off"
        spellCheck={false}
      />
      {value && (
        <button
          type="button"
          onClick={() => onChange('')}
          aria-label="Clear search"
          className={cn(
            'absolute right-3 top-1/2 -translate-y-1/2 rounded-sm',
            'text-muted-foreground hover:text-foreground',
            'focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring',
          )}
        >
          <X className="h-4 w-4" aria-hidden="true" />
        </button>
      )}
    </div>
  );
}

/** Toggleable type-filter pill row */
interface TypeFilterPillsProps {
  filters: NonNullable<EntityPickerTab<unknown>['typeFilters']>;
  active: Set<string>;
  onToggle: (value: string) => void;
}

function TypeFilterPills({ filters, active, onToggle }: TypeFilterPillsProps) {
  return (
    <div className="flex flex-wrap gap-1.5" role="group" aria-label="Filter by type">
      {filters.map(({ value, label, icon: Icon }) => {
        const isActive = active.has(value);
        return (
          <button
            key={value}
            type="button"
            onClick={() => onToggle(value)}
            aria-pressed={isActive}
            className={cn(
              'inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-medium transition-colors',
              'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
              isActive
                ? 'border-primary bg-primary text-primary-foreground'
                : 'border-border bg-transparent text-muted-foreground hover:border-foreground/40 hover:text-foreground',
            )}
          >
            {Icon && <Icon className="h-3 w-3" aria-hidden="true" />}
            {label}
          </button>
        );
      })}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Tab content inner component — handles data fetching + rendering per tab
// ---------------------------------------------------------------------------

interface TabContentProps<T> {
  tab: EntityPickerTab<T>;
  selectedIds: Set<string>;
  onSelect: (id: string) => void;
}

function TabContent<T>({ tab, selectedIds, onSelect }: TabContentProps<T>) {
  const [search, setSearch] = useState('');
  const [activeTypeFilters, setActiveTypeFilters] = useState<Set<string>>(new Set());

  const debouncedSearch = useDebounce(search, 300);

  const toggleTypeFilter = useCallback((value: string) => {
    setActiveTypeFilters((prev) => {
      const next = new Set(prev);
      if (next.has(value)) {
        next.delete(value);
      } else {
        next.add(value);
      }
      return next;
    });
  }, []);

  const typeFilterArray = activeTypeFilters.size > 0 ? Array.from(activeTypeFilters) : undefined;

  const { items, isLoading, hasNextPage, fetchNextPage, isFetchingNextPage } = tab.useData({
    search: debouncedSearch,
    typeFilter: typeFilterArray,
  });

  // Infinite scroll sentinel
  const { targetRef, isIntersecting } = useIntersectionObserver({
    rootMargin: '100px',
    enabled: !!hasNextPage && !isFetchingNextPage,
  });

  useEffect(() => {
    if (isIntersecting) {
      fetchNextPage();
    }
  }, [isIntersecting, fetchNextPage]);

  const isEmpty = !isLoading && items.length === 0;
  const hasTypeFilters = !!tab.typeFilters && tab.typeFilters.length > 0;

  return (
    <div className="flex flex-col gap-3">
      <SearchInput value={search} onChange={setSearch} placeholder={`Search ${tab.label.toLowerCase()}\u2026`} />

      {hasTypeFilters && tab.typeFilters && (
        <TypeFilterPills
          filters={tab.typeFilters}
          active={activeTypeFilters}
          onToggle={toggleTypeFilter}
        />
      )}

      <ScrollArea className="h-[340px]">
        {isLoading ? (
          <GridSkeleton count={6} />
        ) : isEmpty ? (
          <EmptyState
            message={
              debouncedSearch || activeTypeFilters.size > 0
                ? 'No results match your filters'
                : `No ${tab.label.toLowerCase()} found`
            }
          />
        ) : (
          <>
            <div
              className="grid grid-cols-2 gap-2 sm:grid-cols-3"
              role="list"
              aria-label={tab.label}
            >
              {items.map((item) => {
                const id = tab.getId(item);
                const isSelected = selectedIds.has(id);
                return (
                  <div
                    key={id}
                    role="listitem"
                    className="relative min-w-[160px] cursor-pointer"
                    onClick={() => onSelect(id)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' || e.key === ' ') {
                        e.preventDefault();
                        onSelect(id);
                      }
                    }}
                    tabIndex={0}
                    aria-pressed={isSelected}
                  >
                    {tab.renderCard(item, isSelected)}
                    {/* Selection ring overlay */}
                    {isSelected && (
                      <div
                        className="pointer-events-none absolute inset-0 rounded-lg ring-2 ring-primary ring-offset-1"
                        aria-hidden="true"
                      />
                    )}
                  </div>
                );
              })}
            </div>

            {/* Infinite scroll sentinel */}
            {hasNextPage && (
              <div ref={targetRef} className="flex justify-center py-4">
                {isFetchingNextPage && (
                  <div className="flex items-center gap-2 text-sm text-muted-foreground">
                    <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
                    Loading more...
                  </div>
                )}
              </div>
            )}
          </>
        )}
      </ScrollArea>
    </div>
  );
}

// ---------------------------------------------------------------------------
// EntityPickerDialog
// ---------------------------------------------------------------------------

/**
 * EntityPickerDialog — Generic tabbed entity picker dialog.
 *
 * Supports an arbitrary number of tabs, each backed by its own data hook.
 * In `single` mode, selecting an entity immediately commits the change and
 * closes the dialog. In `multi` mode, selections accumulate and are committed
 * when the user clicks "Done".
 *
 * Features:
 * - Tabbed navigation with icons
 * - Per-tab search with 300ms debounce
 * - Optional type filter pills per tab
 * - Infinite scroll via `useIntersectionObserver`
 * - Skeleton loading + empty state
 * - Selection ring overlay on picked cards
 * - WCAG 2.1 AA: keyboard navigation, ARIA labels, focus management
 *
 * @example
 * ```tsx
 * <EntityPickerDialog
 *   open={open}
 *   onOpenChange={setOpen}
 *   tabs={[artifactTab]}
 *   mode="multi"
 *   value={selectedIds}
 *   onChange={setSelectedIds}
 *   title="Select Artifacts"
 * />
 * ```
 */
export function EntityPickerDialog<T = unknown>({
  open,
  onOpenChange,
  tabs,
  mode,
  value,
  onChange,
  title = 'Select',
  description,
}: EntityPickerDialogProps<T>) {
  const [activeTabId, setActiveTabId] = useState<string>(() => tabs[0]?.id ?? '');

  // Internal multi-select accumulator; for single mode we bypass this
  const [pendingSelection, setPendingSelection] = useState<Set<string>>(new Set());

  // Sync pendingSelection from external value when dialog opens
  useEffect(() => {
    if (open) {
      const ids = Array.isArray(value) ? value : value ? [value] : [];
      setPendingSelection(new Set(ids));
      setActiveTabId(tabs[0]?.id ?? '');
    }
  }, [open]); // eslint-disable-line react-hooks/exhaustive-deps

  const handleSelect = useCallback(
    (id: string) => {
      if (mode === 'single') {
        onChange(id);
        onOpenChange(false);
      } else {
        setPendingSelection((prev) => {
          const next = new Set(prev);
          if (next.has(id)) {
            next.delete(id);
          } else {
            next.add(id);
          }
          return next;
        });
      }
    },
    [mode, onChange, onOpenChange],
  );

  const handleDone = useCallback(() => {
    if (mode === 'multi') {
      onChange(Array.from(pendingSelection));
    }
    onOpenChange(false);
  }, [mode, onChange, onOpenChange, pendingSelection]);

  const handleClose = useCallback(() => {
    onOpenChange(false);
  }, [onOpenChange]);

  if (tabs.length === 0) return null;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent
        className="sm:max-w-3xl"
        aria-label={title}
      >
        <DialogHeader>
          <DialogTitle>{title}</DialogTitle>
          {description && <DialogDescription>{description}</DialogDescription>}
        </DialogHeader>

        <Tabs
          value={activeTabId}
          onValueChange={setActiveTabId}
          className="mt-1"
        >
          {/* Tab strip */}
          <TabsList
            className={cn('grid w-full', `grid-cols-${tabs.length}`)}
            aria-label="Entity type"
          >
            {tabs.map((tab) => {
              const Icon = tab.icon;
              return (
                <TabsTrigger key={tab.id} value={tab.id} className="gap-1.5">
                  <Icon className="h-3.5 w-3.5" aria-hidden="true" />
                  {tab.label}
                </TabsTrigger>
              );
            })}
          </TabsList>

          {/* Tab panels */}
          {tabs.map((tab) => (
            <TabsContent
              key={tab.id}
              value={tab.id}
              className="mt-3 focus-visible:outline-none"
            >
              <TabContent
                tab={tab}
                selectedIds={pendingSelection}
                onSelect={handleSelect}
              />
            </TabsContent>
          ))}
        </Tabs>

        {/* Footer actions */}
        <div className="flex items-center justify-between pt-1">
          {mode === 'multi' && (
            <span className="text-sm text-muted-foreground">
              {pendingSelection.size > 0
                ? `${pendingSelection.size} selected`
                : 'Nothing selected'}
            </span>
          )}
          <div className={cn('flex gap-2', mode === 'single' && 'ml-auto')}>
            {mode === 'multi' && (
              <Button variant="ghost" onClick={handleClose}>
                Cancel
              </Button>
            )}
            <Button variant="outline" onClick={handleDone}>
              Done
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}

// ---------------------------------------------------------------------------
// EntityPickerTrigger
// ---------------------------------------------------------------------------

/**
 * EntityPickerTrigger — Button/field trigger that opens an EntityPickerDialog.
 *
 * Renders a form-field-height button showing the current selection. In
 * `single` mode it shows the selected item name (or placeholder). In `multi`
 * mode it shows removable badge chips and a count summary.
 *
 * @example Single mode
 * ```tsx
 * <EntityPickerTrigger
 *   label="Primary Agent"
 *   value={selectedId}
 *   items={[{ id: selectedId, name: 'My Agent' }]}
 *   mode="single"
 *   onClick={() => setPickerOpen(true)}
 *   placeholder="Select an agent..."
 * />
 * ```
 *
 * @example Multi mode
 * ```tsx
 * <EntityPickerTrigger
 *   label="Supporting Skills"
 *   value={selectedIds}
 *   items={resolvedItems}
 *   mode="multi"
 *   onClick={() => setPickerOpen(true)}
 *   onRemove={(id) => setSelectedIds((prev) => prev.filter((x) => x !== id))}
 * />
 * ```
 */
export function EntityPickerTrigger({
  label,
  value,
  items = [],
  mode,
  onClick,
  onRemove,
  placeholder = 'Select\u2026',
  disabled = false,
  className,
}: EntityPickerTriggerProps) {
  // Normalize value to array for internal logic
  const selectedIds: string[] = Array.isArray(value)
    ? value
    : value
      ? [value]
      : [];

  const itemMap = new Map(items.map((i) => [i.id, i.name]));

  // Single-mode display
  if (mode === 'single') {
    const selectedId = selectedIds[0];
    const selectedName = selectedId ? (itemMap.get(selectedId) ?? selectedId.slice(0, 8)) : null;

    return (
      <div className={cn('flex flex-col gap-1.5', className)}>
        {label && (
          <span className="text-sm font-medium leading-none">{label}</span>
        )}
        <Button
          type="button"
          variant="outline"
          onClick={onClick}
          disabled={disabled}
          aria-label={label ?? placeholder}
          className={cn(
            'flex h-9 w-full items-center justify-between gap-2 px-3 font-normal',
            !selectedName && 'text-muted-foreground',
          )}
        >
          <span className="flex-1 truncate text-left text-sm">
            {selectedName ?? placeholder}
          </span>
          <ChevronDown className="h-4 w-4 shrink-0 text-muted-foreground" aria-hidden="true" />
        </Button>
      </div>
    );
  }

  // Multi-mode display
  const count = selectedIds.length;

  return (
    <div className={cn('flex flex-col gap-1.5', className)}>
      {label && (
        <span className="text-sm font-medium leading-none">{label}</span>
      )}

      {/* Trigger button */}
      <Button
        type="button"
        variant="outline"
        onClick={onClick}
        disabled={disabled}
        aria-label={`${label ?? 'Picker'}: ${count > 0 ? `${count} selected` : placeholder}`}
        className={cn(
          'flex h-9 w-full items-center justify-between gap-2 px-3 font-normal',
          count === 0 && 'text-muted-foreground',
        )}
      >
        <span className="flex items-center gap-1.5 text-sm">
          {count > 0 ? (
            <>
              <span
                className="inline-flex h-5 min-w-[20px] items-center justify-center rounded-full bg-primary px-1.5 text-xs font-semibold text-primary-foreground"
                aria-label={`${count} selected`}
              >
                {count}
              </span>
              <span>selected</span>
            </>
          ) : (
            placeholder
          )}
        </span>
        <ChevronDown className="h-4 w-4 shrink-0 text-muted-foreground" aria-hidden="true" />
      </Button>

      {/* Removable badges for each selected item */}
      {count > 0 && (
        <div
          className="flex flex-wrap gap-1.5"
          role="list"
          aria-label={`${label ?? 'Selected'} items`}
        >
          {selectedIds.map((id) => {
            const name = itemMap.get(id) ?? id.slice(0, 8);
            return (
              <Badge
                key={id}
                variant="secondary"
                className="flex items-center gap-1 pr-1 text-xs"
                role="listitem"
              >
                <span className="max-w-[140px] truncate">{name}</span>
                {onRemove && (
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation();
                      onRemove(id);
                    }}
                    disabled={disabled}
                    aria-label={`Remove ${name}`}
                    className={cn(
                      'ml-0.5 flex h-3.5 w-3.5 shrink-0 items-center justify-center rounded-full',
                      'text-muted-foreground transition-colors',
                      'hover:bg-foreground/10 hover:text-foreground',
                      'focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring',
                      disabled && 'cursor-not-allowed opacity-50',
                    )}
                  >
                    <X className="h-2.5 w-2.5" aria-hidden="true" />
                  </button>
                )}
              </Badge>
            );
          })}
        </div>
      )}
    </div>
  );
}
