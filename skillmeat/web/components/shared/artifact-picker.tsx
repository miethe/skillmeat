'use client';

/**
 * ArtifactPicker — Searchable artifact selector popover.
 *
 * A Popover-based searchable selector backed by `useInfiniteArtifacts`.
 * Supports single and multi-select modes with optional type filtering.
 * Results are grouped by artifact type with keyboard navigation (arrow keys,
 * Enter to select, Escape to close).
 *
 * @example Single mode
 * ```tsx
 * <ArtifactPicker
 *   value={selectedId}
 *   onChange={(id) => setSelectedId(id as string)}
 *   mode="single"
 *   typeFilter={['agent']}
 *   placeholder="Select an agent…"
 *   label="Primary Agent"
 * />
 * ```
 *
 * @example Multi mode
 * ```tsx
 * <ArtifactPicker
 *   value={selectedIds}
 *   onChange={(ids) => setSelectedIds(ids as string[])}
 *   mode="multi"
 *   typeFilter={['skill', 'command']}
 *   placeholder="Add supporting tools…"
 *   label="Supporting Tools"
 * />
 * ```
 */

import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  Bot,
  Blocks,
  Check,
  ChevronDown,
  Loader2,
  Server,
  Sparkles,
  Terminal,
  Webhook,
  X,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover';
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from '@/components/ui/command';
import { useDebounce, useInfiniteArtifacts } from '@/hooks';
import { mapApiResponseToArtifact } from '@/lib/api/mappers';
import type { Artifact, ArtifactType } from '@/types/artifact';
import { cn } from '@/lib/utils';

// ---------------------------------------------------------------------------
// Type maps
// ---------------------------------------------------------------------------

const ARTIFACT_ICONS: Record<ArtifactType, React.ElementType> = {
  skill: Sparkles,
  command: Terminal,
  agent: Bot,
  mcp: Server,
  hook: Webhook,
  composite: Blocks,
};

const ARTIFACT_TYPE_LABELS: Record<ArtifactType, string> = {
  skill: 'Skills',
  command: 'Commands',
  agent: 'Agents',
  mcp: 'MCP Servers',
  hook: 'Hooks',
  composite: 'Composites',
};

const ARTIFACT_TYPE_SINGULAR: Record<ArtifactType, string> = {
  skill: 'Skill',
  command: 'Command',
  agent: 'Agent',
  mcp: 'MCP',
  hook: 'Hook',
  composite: 'Composite',
};

const TYPE_COLORS: Record<ArtifactType, string> = {
  skill: 'text-purple-500',
  command: 'text-blue-500',
  agent: 'text-green-500',
  mcp: 'text-orange-500',
  hook: 'text-pink-500',
  composite: 'text-indigo-500',
};

/** Display order for artifact type groups in the results list. */
const TYPE_ORDER: ArtifactType[] = ['skill', 'agent', 'command', 'mcp', 'hook', 'composite'];

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

export interface ArtifactPickerProps {
  /**
   * Currently selected artifact UUID(s).
   * - Single mode: a single UUID string (or empty string for none)
   * - Multi mode: an array of UUID strings
   */
  value: string | string[];

  /**
   * Called when the selection changes.
   * Receives the same shape as `value` (string in single mode, string[] in multi).
   */
  onChange: (value: string | string[]) => void;

  /** Selection mode. Default: 'single'. */
  mode?: 'single' | 'multi';

  /**
   * Restrict results to specific artifact types.
   * When omitted, all types are shown.
   */
  typeFilter?: ArtifactType[];

  /** Placeholder text shown in the trigger button when nothing is selected. */
  placeholder?: string;

  /** Accessible label shown above the trigger button. */
  label?: string;

  /** Optional class applied to the outermost wrapper element. */
  className?: string;

  /** Disable the picker entirely. */
  disabled?: boolean;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function ArtifactPicker({
  value,
  onChange,
  mode = 'single',
  typeFilter,
  placeholder = 'Select an artifact…',
  label,
  className,
  disabled = false,
}: ArtifactPickerProps) {
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState('');
  const debouncedSearch = useDebounce(search, 300);

  // Normalize value to an array of UUIDs for internal logic.
  const selectedUuids: string[] = useMemo(() => {
    if (mode === 'multi') {
      return Array.isArray(value) ? value : value ? [value] : [];
    }
    return typeof value === 'string' && value ? [value] : [];
  }, [value, mode]);

  // ---------------------------------------------------------------------------
  // Data fetching
  // ---------------------------------------------------------------------------

  const typeFilterString = typeFilter?.join(',');

  const { data, isLoading, isFetching } = useInfiniteArtifacts({
    limit: 50,
    search: debouncedSearch || undefined,
    artifact_type: typeFilterString || undefined,
  });

  const allArtifacts: Artifact[] = useMemo(() => {
    if (!data?.pages) return [];
    return data.pages.flatMap((page) =>
      page.items.map((item) => mapApiResponseToArtifact(item, 'collection'))
    );
  }, [data]);

  // Keep a name-lookup map by uuid so we can show selected artifact names.
  const artifactByUuid = useMemo(() => {
    const map = new Map<string, Artifact>();
    for (const a of allArtifacts) {
      map.set(a.uuid, a);
    }
    return map;
  }, [allArtifacts]);

  // Group results by type in display order.
  const groupedArtifacts = useMemo(() => {
    const groups: { type: ArtifactType; artifacts: Artifact[] }[] = [];
    const activeTypes = typeFilter ?? TYPE_ORDER;
    const ordered = TYPE_ORDER.filter((t) => activeTypes.includes(t));

    for (const type of ordered) {
      const items = allArtifacts.filter((a) => a.type === type);
      if (items.length > 0) {
        groups.push({ type, artifacts: items });
      }
    }
    return groups;
  }, [allArtifacts, typeFilter]);

  const isSearching = (isLoading || isFetching) && open;
  const isEmpty = !isSearching && open && allArtifacts.length === 0;

  // ---------------------------------------------------------------------------
  // Selection handlers
  // ---------------------------------------------------------------------------

  const handleSelect = useCallback(
    (artifact: Artifact) => {
      if (mode === 'single') {
        onChange(artifact.uuid);
        setOpen(false);
      } else {
        const next = selectedUuids.includes(artifact.uuid)
          ? selectedUuids.filter((id) => id !== artifact.uuid)
          : [...selectedUuids, artifact.uuid];
        onChange(next);
      }
    },
    [mode, onChange, selectedUuids]
  );

  const handleRemoveSingle = useCallback(() => {
    if (mode === 'single') {
      onChange('');
    }
  }, [mode, onChange]);

  const handleRemoveMulti = useCallback(
    (uuid: string) => {
      if (mode === 'multi') {
        onChange(selectedUuids.filter((id) => id !== uuid));
      }
    },
    [mode, onChange, selectedUuids]
  );

  // Reset search when popover closes.
  useEffect(() => {
    if (!open) {
      setSearch('');
    }
  }, [open]);

  // ---------------------------------------------------------------------------
  // Trigger label (single mode)
  // ---------------------------------------------------------------------------

  const selectedSingle = mode === 'single' && selectedUuids[0]
    ? artifactByUuid.get(selectedUuids[0])
    : undefined;

  const triggerLabel = selectedSingle ? selectedSingle.name : placeholder;
  const hasSingleSelection = !!selectedSingle;

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------

  return (
    <div className={cn('flex flex-col gap-2', className)}>
      {/* Optional field label */}
      {label && (
        <span className="text-sm font-medium leading-none text-foreground">{label}</span>
      )}

      {/* Trigger + popover */}
      <Popover open={open} onOpenChange={disabled ? undefined : setOpen}>
        <div className="flex items-center gap-2">
          <PopoverTrigger asChild>
            <Button
              variant="outline"
              role="combobox"
              aria-expanded={open}
              aria-label={label ?? placeholder}
              disabled={disabled}
              className={cn(
                'flex h-9 min-w-[200px] items-center justify-between gap-2 px-3 font-normal',
                !hasSingleSelection && 'text-muted-foreground'
              )}
            >
              {/* Single mode: show type icon when selected */}
              {selectedSingle && (
                (() => {
                  const Icon = ARTIFACT_ICONS[selectedSingle.type];
                  return (
                    <Icon
                      className={cn('h-3.5 w-3.5 shrink-0', TYPE_COLORS[selectedSingle.type])}
                      aria-hidden="true"
                    />
                  );
                })()
              )}

              <span className="flex-1 truncate text-left text-sm">{triggerLabel}</span>

              {/* Clear button (single mode, has selection) */}
              {hasSingleSelection && mode === 'single' ? (
                <button
                  type="button"
                  tabIndex={-1}
                  aria-label="Clear selection"
                  onClick={(e) => {
                    e.stopPropagation();
                    handleRemoveSingle();
                  }}
                  className="rounded-sm text-muted-foreground hover:text-foreground focus:outline-none"
                >
                  <X className="h-3.5 w-3.5" />
                </button>
              ) : (
                <ChevronDown
                  className={cn(
                    'h-4 w-4 shrink-0 text-muted-foreground transition-transform duration-200',
                    open && 'rotate-180'
                  )}
                  aria-hidden="true"
                />
              )}
            </Button>
          </PopoverTrigger>
        </div>

        <PopoverContent
          className="w-[320px] p-0"
          align="start"
          onOpenAutoFocus={(e) => e.preventDefault()}
        >
          <Command shouldFilter={false}>
            {/* Search input */}
            <CommandInput
              placeholder="Search artifacts…"
              value={search}
              onValueChange={setSearch}
              aria-label="Search artifacts"
            />

            <CommandList>
              {/* Loading state */}
              {isSearching && (
                <div className="flex items-center gap-2 px-3 py-2.5 text-sm text-muted-foreground">
                  <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden="true" />
                  <span>Searching…</span>
                </div>
              )}

              {/* Empty state */}
              {isEmpty && (
                <CommandEmpty>No artifacts found.</CommandEmpty>
              )}

              {/* Grouped results */}
              {!isSearching && groupedArtifacts.map(({ type, artifacts }) => {
                const Icon = ARTIFACT_ICONS[type];
                const groupColor = TYPE_COLORS[type];

                return (
                  <CommandGroup key={type} heading={ARTIFACT_TYPE_LABELS[type]}>
                    {artifacts.map((artifact) => {
                      const isSelected = selectedUuids.includes(artifact.uuid);

                      return (
                        <CommandItem
                          key={artifact.uuid}
                          value={artifact.uuid}
                          onSelect={() => handleSelect(artifact)}
                          className="flex items-center gap-2.5"
                        >
                          {/* Type icon */}
                          <Icon
                            className={cn('h-3.5 w-3.5 shrink-0', groupColor)}
                            aria-hidden="true"
                          />

                          {/* Name */}
                          <span className="flex-1 truncate text-sm">{artifact.name}</span>

                          {/* Type badge */}
                          <span
                            className="shrink-0 rounded px-1.5 py-0.5 text-xs font-medium bg-muted text-muted-foreground"
                            aria-label={`Type: ${ARTIFACT_TYPE_SINGULAR[type]}`}
                          >
                            {ARTIFACT_TYPE_SINGULAR[type]}
                          </span>

                          {/* Selection checkmark */}
                          <Check
                            className={cn(
                              'h-3.5 w-3.5 shrink-0 text-primary transition-opacity',
                              isSelected ? 'opacity-100' : 'opacity-0'
                            )}
                            aria-hidden="true"
                          />
                        </CommandItem>
                      );
                    })}
                  </CommandGroup>
                );
              })}
            </CommandList>
          </Command>
        </PopoverContent>
      </Popover>

      {/* Multi mode: selected badges below the trigger */}
      {mode === 'multi' && selectedUuids.length > 0 && (
        <div
          className="flex flex-wrap gap-1.5"
          role="list"
          aria-label="Selected artifacts"
        >
          {selectedUuids.map((uuid) => {
            // Best-effort name lookup — uuid may not be in current page of results.
            const artifact = artifactByUuid.get(uuid);
            const name = artifact?.name ?? uuid.slice(0, 8);
            const type = artifact?.type;
            const Icon = type ? ARTIFACT_ICONS[type] : null;
            const colorClass = type ? TYPE_COLORS[type] : 'text-muted-foreground';

            return (
              <Badge
                key={uuid}
                variant="secondary"
                className="flex items-center gap-1.5 pl-1.5 pr-1 text-xs"
                role="listitem"
              >
                {Icon && (
                  <Icon className={cn('h-3 w-3 shrink-0', colorClass)} aria-hidden="true" />
                )}
                <span className="max-w-[120px] truncate">{name}</span>
                <button
                  type="button"
                  aria-label={`Remove ${name}`}
                  onClick={() => handleRemoveMulti(uuid)}
                  className="ml-0.5 rounded-sm text-muted-foreground hover:text-foreground focus:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                >
                  <X className="h-3 w-3" />
                </button>
              </Badge>
            );
          })}
        </div>
      )}
    </div>
  );
}
