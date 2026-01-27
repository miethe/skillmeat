'use client';

/**
 * SearchModeToggle Component
 *
 * Toggle between 'sources' and 'artifacts' search modes for the marketplace.
 * Uses Tabs component for accessible mode switching.
 */

import { Building2, Package } from 'lucide-react';
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { cn } from '@/lib/utils';

// ============================================================================
// Types
// ============================================================================

export type SearchMode = 'sources' | 'artifacts';

export interface SearchModeToggleProps {
  /** Current search mode */
  mode: SearchMode;
  /** Callback when mode changes */
  onModeChange: (mode: SearchMode) => void;
  /** Whether the toggle is disabled */
  disabled?: boolean;
  /** Additional CSS classes */
  className?: string;
}

// ============================================================================
// SearchModeToggle Component
// ============================================================================

/**
 * Search mode toggle for switching between sources and artifacts search.
 *
 * @example
 * ```tsx
 * <SearchModeToggle
 *   mode={searchMode}
 *   onModeChange={setSearchMode}
 * />
 * ```
 */
export function SearchModeToggle({
  mode,
  onModeChange,
  disabled = false,
  className,
}: SearchModeToggleProps) {
  return (
    <Tabs
      value={mode}
      onValueChange={(value) => onModeChange(value as SearchMode)}
      className={cn('w-auto', className)}
    >
      <TabsList
        className={cn('h-9', disabled && 'pointer-events-none opacity-50')}
        aria-label="Search mode"
      >
        <TabsTrigger
          value="sources"
          disabled={disabled}
          className="gap-1.5 px-3 text-sm"
          aria-label="Search sources"
        >
          <Building2 className="h-4 w-4" aria-hidden="true" />
          Sources
        </TabsTrigger>
        <TabsTrigger
          value="artifacts"
          disabled={disabled}
          className="gap-1.5 px-3 text-sm"
          aria-label="Search artifacts"
        >
          <Package className="h-4 w-4" aria-hidden="true" />
          Artifacts
        </TabsTrigger>
      </TabsList>
    </Tabs>
  );
}
