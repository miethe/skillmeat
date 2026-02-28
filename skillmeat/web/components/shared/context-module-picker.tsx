'use client';

/**
 * ContextModulePicker — Popover-based multi-select for context modules.
 *
 * Displays a searchable list of context modules within a Popover. Supports
 * inherited (global) modules shown in a locked "Inherited" section, and
 * user-selected modules shown as removable Badge chips below the trigger.
 *
 * Data source: accepts an optional `modules` prop for pre-loaded data, or
 * falls back to `useContextModules` hook when a `projectId` is provided.
 * When neither is available the list is empty (ready for future API wiring).
 *
 * @example
 * ```tsx
 * <ContextModulePicker
 *   value={selectedIds}
 *   onChange={setSelectedIds}
 *   inheritedModules={globalModuleIds}
 *   projectId={currentProjectId}
 *   label="Context Modules"
 * />
 * ```
 */

import React, { useCallback, useMemo, useRef, useState } from 'react';
import { Check, ChevronDown, Lock, Package, Search, X } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Checkbox } from '@/components/ui/checkbox';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import { ScrollArea } from '@/components/ui/scroll-area';
import { cn } from '@/lib/utils';
import { useContextModules, useDebounce } from '@/hooks';
import type { ContextModuleResponse } from '@/sdk/models/ContextModuleResponse';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface ContextModulePickerProps {
  /** IDs of the currently selected (user-added) modules. */
  value: string[];
  /** Callback fired whenever the selection changes. */
  onChange: (value: string[]) => void;
  /**
   * IDs of globally inherited modules. These are shown in a separate
   * "Inherited" section and cannot be toggled by the user.
   */
  inheritedModules?: string[];
  /**
   * Optional pre-loaded list of modules. When provided, the hook-based fetch
   * is skipped entirely.
   */
  modules?: ContextModuleResponse[];
  /**
   * Project ID used to fetch modules when `modules` prop is not supplied.
   * When omitted, the component renders with an empty list until wired up.
   */
  projectId?: string;
  /** Placeholder text shown in the trigger button when nothing is selected. */
  placeholder?: string;
  /** Label rendered above the trigger button. */
  label?: string;
  /** Disable all interactions. */
  disabled?: boolean;
  /** Additional class names applied to the root wrapper. */
  className?: string;
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

interface ModuleItemRowProps {
  module: ContextModuleResponse;
  checked: boolean;
  onToggle: (id: string) => void;
}

function ModuleItemRow({ module, checked, onToggle }: ModuleItemRowProps) {
  const checkboxId = `ctx-module-${module.id}`;

  return (
    <div
      className={cn(
        'flex cursor-pointer select-none items-start gap-3 rounded-md px-3 py-2.5',
        'transition-colors hover:bg-accent hover:text-accent-foreground',
        checked && 'bg-accent/50'
      )}
      onClick={() => onToggle(module.id)}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          onToggle(module.id);
        }
      }}
      role="option"
      aria-selected={checked}
      tabIndex={0}
    >
      <Checkbox
        id={checkboxId}
        checked={checked}
        onCheckedChange={() => onToggle(module.id)}
        aria-label={`Select ${module.name}`}
        className="mt-0.5 shrink-0"
        // Prevent double-toggle from the parent div click handler
        onClick={(e) => e.stopPropagation()}
      />
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-1.5">
          <span className="truncate text-sm font-medium leading-tight">
            {module.name}
          </span>
          {module.priority !== undefined && module.priority > 0 && (
            <span
              className="shrink-0 rounded px-1 py-0.5 text-[10px] font-medium leading-none bg-muted text-muted-foreground"
              aria-label={`Priority ${module.priority}`}
            >
              P{module.priority}
            </span>
          )}
        </div>
        {module.description && (
          <p className="mt-0.5 line-clamp-2 text-xs text-muted-foreground">
            {module.description}
          </p>
        )}
        {Array.isArray(module.memory_items) &&
          (module.memory_items as unknown[]).length > 0 && (
            <p className="mt-0.5 text-[10px] text-muted-foreground/70">
              {(module.memory_items as unknown[]).length} memory{' '}
              {(module.memory_items as unknown[]).length === 1 ? 'item' : 'items'}
            </p>
          )}
      </div>
      {checked && (
        <Check
          className="mt-0.5 h-4 w-4 shrink-0 text-primary"
          aria-hidden="true"
        />
      )}
    </div>
  );
}

interface InheritedModuleRowProps {
  module: ContextModuleResponse;
}

function InheritedModuleRow({ module }: InheritedModuleRowProps) {
  return (
    <div
      className="flex cursor-default select-none items-start gap-3 rounded-md px-3 py-2.5 opacity-70"
      aria-disabled="true"
    >
      <Lock
        className="mt-0.5 h-3.5 w-3.5 shrink-0 text-muted-foreground"
        aria-hidden="true"
      />
      <div className="min-w-0 flex-1">
        <span className="truncate text-sm font-medium leading-tight">
          {module.name}
        </span>
        {module.description && (
          <p className="mt-0.5 line-clamp-2 text-xs text-muted-foreground">
            {module.description}
          </p>
        )}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export function ContextModulePicker({
  value,
  onChange,
  inheritedModules = [],
  modules: modulesProp,
  projectId,
  placeholder = 'Select context modules\u2026',
  label,
  disabled = false,
  className,
}: ContextModulePickerProps) {
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState('');
  const searchRef = useRef<HTMLInputElement>(null);

  const debouncedSearch = useDebounce(search, 300);

  // ---------------------------------------------------------------------------
  // Data: prefer prop, fall back to hook
  // ---------------------------------------------------------------------------

  const {
    data: hookData,
    isLoading,
  } = useContextModules(projectId ?? '', { limit: 100 });

  const allModules: ContextModuleResponse[] = useMemo(() => {
    if (modulesProp !== undefined) return modulesProp;
    return hookData?.items ?? [];
  }, [modulesProp, hookData]);

  // ---------------------------------------------------------------------------
  // Filtering
  // ---------------------------------------------------------------------------

  const normalizedSearch = debouncedSearch.trim().toLowerCase();

  const inheritedSet = useMemo(
    () => new Set(inheritedModules),
    [inheritedModules]
  );

  const selectedSet = useMemo(() => new Set(value), [value]);

  // Partition into inherited / available (non-inherited) modules
  const inheritedModuleObjects = useMemo(
    () => allModules.filter((m) => inheritedSet.has(m.id)),
    [allModules, inheritedSet]
  );

  const availableModules = useMemo(
    () => allModules.filter((m) => !inheritedSet.has(m.id)),
    [allModules, inheritedSet]
  );

  // Apply search filter
  const filteredAvailable = useMemo(() => {
    if (!normalizedSearch) return availableModules;
    return availableModules.filter(
      (m) =>
        m.name.toLowerCase().includes(normalizedSearch) ||
        (m.description ?? '').toLowerCase().includes(normalizedSearch)
    );
  }, [availableModules, normalizedSearch]);

  const filteredInherited = useMemo(() => {
    if (!normalizedSearch) return inheritedModuleObjects;
    return inheritedModuleObjects.filter(
      (m) =>
        m.name.toLowerCase().includes(normalizedSearch) ||
        (m.description ?? '').toLowerCase().includes(normalizedSearch)
    );
  }, [inheritedModuleObjects, normalizedSearch]);

  const totalVisible = filteredAvailable.length + filteredInherited.length;
  const isEmpty = !isLoading && totalVisible === 0;

  // ---------------------------------------------------------------------------
  // Selection handlers
  // ---------------------------------------------------------------------------

  const handleToggle = useCallback(
    (id: string) => {
      if (selectedSet.has(id)) {
        onChange(value.filter((v) => v !== id));
      } else {
        onChange([...value, id]);
      }
    },
    [selectedSet, value, onChange]
  );

  const handleRemoveBadge = useCallback(
    (id: string, e: React.MouseEvent) => {
      e.stopPropagation();
      onChange(value.filter((v) => v !== id));
    },
    [value, onChange]
  );

  // ---------------------------------------------------------------------------
  // Derive labels for selected badges
  // ---------------------------------------------------------------------------

  const selectedModules = useMemo(
    () =>
      allModules.filter((m) => selectedSet.has(m.id) && !inheritedSet.has(m.id)),
    [allModules, selectedSet, inheritedSet]
  );

  // ---------------------------------------------------------------------------
  // Focus search on open
  // ---------------------------------------------------------------------------

  const handleOpenChange = useCallback(
    (nextOpen: boolean) => {
      if (disabled) return;
      setOpen(nextOpen);
      if (nextOpen) {
        // Defer so the popover content mounts first
        setTimeout(() => searchRef.current?.focus(), 0);
      } else {
        setSearch('');
      }
    },
    [disabled]
  );

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------

  const triggerLabel =
    value.length === 0
      ? placeholder
      : `${value.length} module${value.length === 1 ? '' : 's'} selected`;

  return (
    <div className={cn('space-y-2', className)}>
      {/* Label */}
      {label && (
        <p className="text-sm font-medium leading-none">{label}</p>
      )}

      {/* Trigger */}
      <Popover open={open} onOpenChange={handleOpenChange}>
        <PopoverTrigger asChild>
          <button
            type="button"
            disabled={disabled}
            aria-label={label ? `${label}: ${triggerLabel}` : triggerLabel}
            aria-expanded={open}
            aria-haspopup="listbox"
            className={cn(
              'flex w-full items-center justify-between rounded-md border border-input bg-background px-3 py-2 text-sm',
              'ring-offset-background transition-colors',
              'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2',
              'hover:bg-accent hover:text-accent-foreground',
              disabled && 'cursor-not-allowed opacity-50',
              open && 'ring-2 ring-ring ring-offset-2'
            )}
          >
            <span
              className={cn(
                'truncate',
                value.length === 0 && 'text-muted-foreground'
              )}
            >
              {triggerLabel}
            </span>
            <ChevronDown
              className={cn(
                'ml-2 h-4 w-4 shrink-0 text-muted-foreground transition-transform duration-200',
                open && 'rotate-180'
              )}
              aria-hidden="true"
            />
          </button>
        </PopoverTrigger>

        <PopoverContent
          className="w-80 p-0"
          align="start"
          sideOffset={4}
          onOpenAutoFocus={(e) => e.preventDefault()}
        >
          {/* Search */}
          <div className="flex items-center border-b px-3 py-2 gap-2">
            <Search
              className="h-3.5 w-3.5 shrink-0 text-muted-foreground"
              aria-hidden="true"
            />
            <input
              ref={searchRef}
              type="search"
              placeholder="Search modules\u2026"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              aria-label="Search context modules"
              autoComplete="off"
              spellCheck={false}
              className={cn(
                'w-full bg-transparent text-sm outline-none placeholder:text-muted-foreground',
                'focus:outline-none'
              )}
            />
            {search && (
              <button
                type="button"
                tabIndex={-1}
                aria-label="Clear search"
                onClick={() => setSearch('')}
                className="text-muted-foreground hover:text-foreground focus:outline-none"
              >
                <X className="h-3 w-3" />
              </button>
            )}
          </div>

          {/* Module list */}
          <ScrollArea className="max-h-72">
            <div
              role="listbox"
              aria-label={label ? `${label} options` : 'Context module options'}
              aria-multiselectable="true"
              className="py-1"
            >
              {/* Loading */}
              {isLoading && (
                <div className="flex flex-col gap-2 p-3">
                  {[1, 2, 3].map((i) => (
                    <div
                      key={i}
                      className="h-10 animate-pulse rounded-md bg-muted"
                    />
                  ))}
                </div>
              )}

              {/* Empty state */}
              {!isLoading && isEmpty && (
                <div className="flex flex-col items-center gap-2 py-8 text-center">
                  <Package
                    className="h-8 w-8 text-muted-foreground/40"
                    aria-hidden="true"
                  />
                  <p className="text-sm text-muted-foreground">
                    {normalizedSearch
                      ? 'No modules match your search'
                      : 'No context modules available'}
                  </p>
                </div>
              )}

              {/* Inherited section */}
              {!isLoading && filteredInherited.length > 0 && (
                <div>
                  <div className="flex items-center gap-1.5 px-3 py-1.5">
                    <Lock
                      className="h-3 w-3 text-muted-foreground/60"
                      aria-hidden="true"
                    />
                    <span className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground/60">
                      Inherited
                    </span>
                  </div>
                  {filteredInherited.map((module) => (
                    <InheritedModuleRow key={module.id} module={module} />
                  ))}
                </div>
              )}

              {/* Divider between inherited and available */}
              {!isLoading &&
                filteredInherited.length > 0 &&
                filteredAvailable.length > 0 && (
                  <div className="my-1 mx-3 border-t" />
                )}

              {/* Available (selectable) section */}
              {!isLoading && filteredAvailable.length > 0 && (
                <div>
                  {inheritedModuleObjects.length > 0 && (
                    <div className="px-3 py-1.5">
                      <span className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground/60">
                        Available
                      </span>
                    </div>
                  )}
                  {filteredAvailable.map((module) => (
                    <ModuleItemRow
                      key={module.id}
                      module={module}
                      checked={selectedSet.has(module.id)}
                      onToggle={handleToggle}
                    />
                  ))}
                </div>
              )}
            </div>
          </ScrollArea>

          {/* Footer: selection count */}
          {value.length > 0 && (
            <div className="border-t px-3 py-2">
              <p className="text-xs text-muted-foreground">
                {value.length} module{value.length === 1 ? '' : 's'} selected
              </p>
            </div>
          )}
        </PopoverContent>
      </Popover>

      {/* Selected badges */}
      {selectedModules.length > 0 && (
        <div
          className="flex flex-wrap gap-1.5"
          role="list"
          aria-label="Selected context modules"
        >
          {selectedModules.map((module) => (
            <Badge
              key={module.id}
              variant="secondary"
              className="flex items-center gap-1 pr-1.5"
              role="listitem"
            >
              <span className="max-w-[160px] truncate text-xs">
                {module.name}
              </span>
              <button
                type="button"
                onClick={(e) => handleRemoveBadge(module.id, e)}
                disabled={disabled}
                aria-label={`Remove ${module.name}`}
                className={cn(
                  'ml-0.5 flex h-3.5 w-3.5 shrink-0 items-center justify-center rounded-full',
                  'text-muted-foreground transition-colors',
                  'hover:bg-foreground/10 hover:text-foreground',
                  'focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring',
                  disabled && 'cursor-not-allowed opacity-50'
                )}
              >
                <X className="h-2.5 w-2.5" />
              </button>
            </Badge>
          ))}
        </div>
      )}
    </div>
  );
}
