'use client';

/**
 * MemberSearchInput — Searchable artifact picker for composite members.
 *
 * Renders a text input that debounces search queries against the collection
 * artifacts endpoint.  Results appear in an accessible dropdown with keyboard
 * navigation (ArrowUp / ArrowDown / Enter / Escape).  Already-added artifacts
 * are filtered out via the `excludeIds` prop.
 *
 * @example
 * ```tsx
 * <MemberSearchInput
 *   excludeIds={currentMembers.map((m) => m.id)}
 *   onSelect={(artifact) => addMember(artifact)}
 *   placeholder="Search for an artifact…"
 * />
 * ```
 */

import React, { useCallback, useEffect, useId, useMemo, useRef, useState } from 'react';
import {
  Bot,
  Blocks,
  Loader2,
  Search,
  Server,
  Sparkles,
  Terminal,
  Webhook,
  X,
} from 'lucide-react';
import { Input } from '@/components/ui/input';
import { useDebounce, useInfiniteArtifacts } from '@/hooks';
import { mapApiResponseToArtifact } from '@/lib/api/mappers';
import type { Artifact, ArtifactType } from '@/types/artifact';
import { cn } from '@/lib/utils';

// ---------------------------------------------------------------------------
// Icon map per artifact type
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
  skill: 'Skill',
  command: 'Command',
  agent: 'Agent',
  mcp: 'MCP',
  hook: 'Hook',
  composite: 'Plugin',
};

const TYPE_COLORS: Record<ArtifactType, string> = {
  skill: 'text-purple-500',
  command: 'text-blue-500',
  agent: 'text-green-500',
  mcp: 'text-orange-500',
  hook: 'text-pink-500',
  composite: 'text-indigo-500',
};

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

export interface MemberSearchInputProps {
  /**
   * Artifact IDs already present in the composite.  These will be hidden from
   * the result list so the user cannot add duplicates.
   */
  excludeIds?: string[];

  /**
   * Called when the user selects an artifact from the dropdown.
   */
  onSelect: (artifact: Artifact) => void;

  /** Input placeholder text. */
  placeholder?: string;

  /** Additional class names applied to the root wrapper. */
  className?: string;

  /** Optionally disable the entire control. */
  disabled?: boolean;

  /** Accessible label for the search input. */
  inputAriaLabel?: string;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function MemberSearchInput({
  excludeIds = [],
  onSelect,
  placeholder = 'Search for an artifact\u2026',
  className,
  disabled = false,
  inputAriaLabel = 'Search artifacts to add as members',
}: MemberSearchInputProps) {
  const [query, setQuery] = useState('');
  const [isOpen, setIsOpen] = useState(false);
  const [activeIndex, setActiveIndex] = useState(-1);

  const debouncedQuery = useDebounce(query, 300);

  const inputRef = useRef<HTMLInputElement>(null);
  const listRef = useRef<HTMLUListElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  // Unique IDs for ARIA
  const inputId = useId();
  const listboxId = useId();

  // ---------------------------------------------------------------------------
  // Data fetching — server-side search via infinite artifacts hook (first page only)
  // ---------------------------------------------------------------------------

  const { data, isLoading, isFetching } = useInfiniteArtifacts({
    limit: 10,
    search: debouncedQuery || undefined,
    enabled: debouncedQuery.length >= 1,
  });

  // Derive visible results — flatten first page, filter already-added members,
  // and apply minimum query length guard.
  const showingQuery = debouncedQuery.length >= 1;
  const rawItems: Artifact[] = useMemo(() => {
    if (!data?.pages) return [];
    return data.pages.flatMap((page) =>
      page.items.map((item) => mapApiResponseToArtifact(item, 'collection'))
    );
  }, [data]);
  const results: Artifact[] = showingQuery
    ? rawItems.filter((a) => !excludeIds.includes(a.id))
    : [];

  const isSearching = (isLoading || isFetching) && showingQuery;
  const isEmpty = showingQuery && !isSearching && results.length === 0;

  // ---------------------------------------------------------------------------
  // Dropdown open/close logic
  // ---------------------------------------------------------------------------

  const openDropdown = useCallback(() => {
    if (!disabled) {
      setIsOpen(true);
    }
  }, [disabled]);

  const closeDropdown = useCallback(() => {
    setIsOpen(false);
    setActiveIndex(-1);
  }, []);

  // Close when focus leaves the container
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        closeDropdown();
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [closeDropdown]);

  // Open whenever there's a query
  useEffect(() => {
    if (query.length >= 1) {
      openDropdown();
    } else {
      closeDropdown();
    }
  }, [query, openDropdown, closeDropdown]);

  // Reset active index when results change
  useEffect(() => {
    setActiveIndex(-1);
  }, [results.length]);

  // ---------------------------------------------------------------------------
  // Keyboard navigation
  // ---------------------------------------------------------------------------

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLInputElement>) => {
      if (!isOpen) return;

      switch (e.key) {
        case 'ArrowDown': {
          e.preventDefault();
          setActiveIndex((prev) => {
            const next = prev < results.length - 1 ? prev + 1 : 0;
            scrollItemIntoView(next);
            return next;
          });
          break;
        }
        case 'ArrowUp': {
          e.preventDefault();
          setActiveIndex((prev) => {
            const next = prev > 0 ? prev - 1 : results.length - 1;
            scrollItemIntoView(next);
            return next;
          });
          break;
        }
        case 'Enter': {
          e.preventDefault();
          const selected = activeIndex >= 0 ? results[activeIndex] : undefined;
          if (selected) {
            handleSelect(selected);
          }
          break;
        }
        case 'Escape': {
          e.preventDefault();
          closeDropdown();
          inputRef.current?.blur();
          break;
        }
        case 'Tab': {
          closeDropdown();
          break;
        }
        default:
          break;
      }
    },
    [isOpen, results, activeIndex, closeDropdown] // eslint-disable-line react-hooks/exhaustive-deps
  );

  function scrollItemIntoView(index: number) {
    const listEl = listRef.current;
    if (!listEl) return;
    const itemEl = listEl.children[index] as HTMLElement | undefined;
    if (itemEl) {
      itemEl.scrollIntoView({ block: 'nearest' });
    }
  }

  // ---------------------------------------------------------------------------
  // Selection handler
  // ---------------------------------------------------------------------------

  function handleSelect(artifact: Artifact) {
    onSelect(artifact);
    setQuery('');
    closeDropdown();
    inputRef.current?.focus();
  }

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------

  const showDropdown = isOpen && (showingQuery || isSearching);

  return (
    <div ref={containerRef} className={cn('relative', className)}>
      {/* Search input */}
      <div className="relative">
        <Search
          className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground"
          aria-hidden="true"
        />
        <Input
          ref={inputRef}
          id={inputId}
          role="combobox"
          aria-label={inputAriaLabel}
          aria-expanded={showDropdown}
          aria-autocomplete="list"
          aria-controls={showDropdown ? listboxId : undefined}
          aria-activedescendant={
            activeIndex >= 0 ? `${listboxId}-option-${activeIndex}` : undefined
          }
          placeholder={placeholder}
          value={query}
          disabled={disabled}
          autoComplete="off"
          spellCheck={false}
          className={cn('pl-9', query.length > 0 && 'pr-9')}
          onChange={(e) => setQuery(e.target.value)}
          onFocus={() => {
            if (query.length >= 1) openDropdown();
          }}
          onKeyDown={handleKeyDown}
        />
        {/* Clear button */}
        {query.length > 0 && (
          <button
            type="button"
            tabIndex={-1}
            aria-label="Clear search"
            onClick={() => {
              setQuery('');
              closeDropdown();
              inputRef.current?.focus();
            }}
            className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground focus:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          >
            <X className="h-3.5 w-3.5" />
          </button>
        )}
        {/* Loading spinner — shown when searching and no clear button would overlap */}
        {isSearching && query.length === 0 && (
          <Loader2
            className="absolute right-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 animate-spin text-muted-foreground"
            aria-hidden="true"
          />
        )}
      </div>

      {/* Dropdown */}
      {showDropdown && (
        <div
          className={cn(
            'absolute z-50 mt-1 w-full rounded-md border bg-popover text-popover-foreground shadow-lg',
            'overflow-hidden'
          )}
        >
          {/* Loading state */}
          {isSearching && (
            <div className="flex items-center gap-2 px-3 py-2.5 text-sm text-muted-foreground">
              <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden="true" />
              <span>Searching\u2026</span>
            </div>
          )}

          {/* Empty state */}
          {isEmpty && (
            <div className="px-3 py-2.5 text-sm text-muted-foreground">
              No matching artifacts found.
            </div>
          )}

          {/* Results list */}
          {!isSearching && results.length > 0 && (
            <ul
              ref={listRef}
              id={listboxId}
              role="listbox"
              aria-label="Artifact search results"
              className="max-h-60 overflow-y-auto py-1"
            >
              {results.map((artifact, index) => {
                const Icon = ARTIFACT_ICONS[artifact.type] ?? Sparkles;
                const colorClass = TYPE_COLORS[artifact.type] ?? 'text-muted-foreground';
                const isActive = index === activeIndex;

                return (
                  <li
                    key={artifact.id}
                    id={`${listboxId}-option-${index}`}
                    role="option"
                    aria-selected={isActive}
                    className={cn(
                      'flex cursor-pointer select-none items-center gap-2.5 px-3 py-2 text-sm',
                      'transition-colors',
                      isActive
                        ? 'bg-accent text-accent-foreground'
                        : 'hover:bg-accent/60 hover:text-accent-foreground'
                    )}
                    onMouseDown={(e) => {
                      // Prevent input blur before click fires
                      e.preventDefault();
                    }}
                    onClick={() => handleSelect(artifact)}
                    onMouseEnter={() => setActiveIndex(index)}
                  >
                    {/* Type icon */}
                    <Icon
                      className={cn('h-3.5 w-3.5 shrink-0', colorClass)}
                      aria-hidden="true"
                    />

                    {/* Name */}
                    <span className="flex-1 truncate font-medium">{artifact.name}</span>

                    {/* Type badge */}
                    <span
                      className={cn(
                        'shrink-0 rounded px-1.5 py-0.5 text-xs font-medium',
                        'bg-muted text-muted-foreground'
                      )}
                      aria-label={`Type: ${ARTIFACT_TYPE_LABELS[artifact.type]}`}
                    >
                      {ARTIFACT_TYPE_LABELS[artifact.type]}
                    </span>
                  </li>
                );
              })}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}
