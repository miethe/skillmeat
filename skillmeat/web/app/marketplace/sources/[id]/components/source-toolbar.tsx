'use client';

/**
 * SourceToolbar Component
 *
 * Unified toolbar for marketplace source detail page with:
 * - Search input (debounced)
 * - Type dropdown filter
 * - Sort dropdown
 * - Confidence range filter
 * - Include low-confidence toggle
 * - Select all checkbox
 * - View mode toggle (grid/list)
 */

import { useState, useEffect } from 'react';
import {
  Search,
  Grid3x3,
  List,
  ArrowUpDown,
  X,
  Sparkles,
  Bot,
  Terminal,
  Server,
  Webhook,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Checkbox } from '@/components/ui/checkbox';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
  DropdownMenuRadioGroup,
  DropdownMenuRadioItem,
} from '@/components/ui/dropdown-menu';
import type { ArtifactType } from '@/types/marketplace';

// ============================================================================
// Types
// ============================================================================

export type ViewMode = 'grid' | 'list';
export type SortOption =
  | 'confidence-desc'
  | 'confidence-asc'
  | 'name-asc'
  | 'name-desc'
  | 'date-added';

export interface SourceToolbarProps {
  // Search
  searchQuery: string;
  onSearchChange: (query: string) => void;

  // Type filter
  selectedType: ArtifactType | null;
  onTypeChange: (type: ArtifactType | null) => void;
  countsByType: Record<string, number>;

  // Sort
  sortOption: SortOption;
  onSortChange: (option: SortOption) => void;

  // Confidence filter
  minConfidence: number;
  maxConfidence: number;
  onMinConfidenceChange: (value: number) => void;
  onMaxConfidenceChange: (value: number) => void;
  includeBelowThreshold: boolean;
  onIncludeBelowThresholdChange: (value: boolean) => void;

  // Duplicate filter (P4.4b)
  showOnlyDuplicates: boolean;
  onShowOnlyDuplicatesChange: (value: boolean) => void;

  // Selection
  selectedCount: number;
  totalSelectableCount: number;
  allSelected: boolean;
  onSelectAll: () => void;

  // View mode
  viewMode: ViewMode;
  onViewModeChange: (mode: ViewMode) => void;

  // Clear filters
  hasActiveFilters: boolean;
  onClearFilters: () => void;
}

// ============================================================================
// Hooks
// ============================================================================

/**
 * Debounce hook for search input
 */
function useDebounce<T>(value: T, delay: number): T {
  const [debouncedValue, setDebouncedValue] = useState<T>(value);

  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedValue(value);
    }, delay);

    return () => {
      clearTimeout(handler);
    };
  }, [value, delay]);

  return debouncedValue;
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
  { value: 'mcp_server', label: 'MCP', Icon: Server },
  { value: 'hook', label: 'Hooks', Icon: Webhook },
];

const SORT_OPTIONS: Array<{ value: SortOption; label: string }> = [
  { value: 'confidence-desc', label: 'Confidence (High to Low)' },
  { value: 'confidence-asc', label: 'Confidence (Low to High)' },
  { value: 'name-asc', label: 'Name (A-Z)' },
  { value: 'name-desc', label: 'Name (Z-A)' },
  { value: 'date-added', label: 'Date Added' },
];

const VIEW_MODE_STORAGE_KEY = 'marketplace-source-view-mode';

// ============================================================================
// Component
// ============================================================================

export function SourceToolbar({
  searchQuery,
  onSearchChange,
  selectedType,
  onTypeChange,
  countsByType,
  sortOption,
  onSortChange,
  minConfidence,
  maxConfidence,
  onMinConfidenceChange,
  onMaxConfidenceChange,
  includeBelowThreshold,
  onIncludeBelowThresholdChange,
  showOnlyDuplicates,
  onShowOnlyDuplicatesChange,
  selectedCount,
  totalSelectableCount,
  allSelected,
  onSelectAll,
  viewMode,
  onViewModeChange,
  hasActiveFilters,
  onClearFilters,
}: SourceToolbarProps) {
  // Local search state for immediate UI feedback
  const [localSearch, setLocalSearch] = useState(searchQuery);

  // Local confidence state for debouncing
  const [localMin, setLocalMin] = useState(minConfidence);
  const [localMax, setLocalMax] = useState(maxConfidence);

  // Debounce search updates (300ms)
  const debouncedSearch = useDebounce(localSearch, 300);

  // Update parent when debounced search changes
  useEffect(() => {
    onSearchChange(debouncedSearch);
  }, [debouncedSearch, onSearchChange]);

  // Sync local search when external searchQuery changes
  useEffect(() => {
    setLocalSearch(searchQuery);
  }, [searchQuery]);

  // Sync local confidence when props change (e.g., clear filters)
  useEffect(() => {
    setLocalMin(minConfidence);
  }, [minConfidence]);

  useEffect(() => {
    setLocalMax(maxConfidence);
  }, [maxConfidence]);

  // Persist view mode to localStorage
  useEffect(() => {
    if (typeof window !== 'undefined') {
      localStorage.setItem(VIEW_MODE_STORAGE_KEY, viewMode);
    }
  }, [viewMode]);

  const handleMinChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = parseInt(e.target.value, 10);
    if (!isNaN(value) && value >= 0 && value <= 100) {
      setLocalMin(value);
      // Debounce the callback
      const timer = setTimeout(() => {
        onMinConfidenceChange(value);
      }, 300);
      return () => clearTimeout(timer);
    }
  };

  const handleMaxChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = parseInt(e.target.value, 10);
    if (!isNaN(value) && value >= 0 && value <= 100) {
      setLocalMax(value);
      // Debounce the callback
      const timer = setTimeout(() => {
        onMaxConfidenceChange(value);
      }, 300);
      return () => clearTimeout(timer);
    }
  };

  // Calculate total count
  const totalCount = Object.values(countsByType).reduce((sum, count) => sum + count, 0);

  return (
    <div className="border-b bg-muted/30 px-4 py-3">
      <div className="flex flex-col gap-3">
        {/* Row 1: Search, Type, Sort */}
        <div className="flex flex-wrap items-center gap-2">
          {/* Search Input */}
          <div className="relative w-full max-w-[200px]">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              type="search"
              placeholder="Search artifacts..."
              value={localSearch}
              onChange={(e) => setLocalSearch(e.target.value)}
              className="h-9 pl-9 pr-4"
              aria-label="Search artifacts"
            />
          </div>

          {/* Type Dropdown */}
          <Select
            value={selectedType || 'all'}
            onValueChange={(value) =>
              onTypeChange(value === 'all' ? null : (value as ArtifactType))
            }
          >
            <SelectTrigger className="h-9 w-[160px]">
              <SelectValue placeholder="All Types" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">
                <span className="flex items-center gap-2">
                  All Types
                  <span className="text-xs text-muted-foreground">({totalCount})</span>
                </span>
              </SelectItem>
              {ARTIFACT_TYPES.map((type) => {
                const count = countsByType[type.value] ?? 0;
                const Icon = type.Icon;
                return (
                  <SelectItem key={type.value} value={type.value}>
                    <span className="flex items-center gap-2">
                      <Icon className="h-4 w-4" />
                      {type.label}
                      <span className="text-xs text-muted-foreground">({count})</span>
                    </span>
                  </SelectItem>
                );
              })}
            </SelectContent>
          </Select>

          {/* Sort Dropdown */}
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="outline" size="sm" className="h-9 gap-2">
                <ArrowUpDown className="h-4 w-4" />
                <span className="hidden sm:inline">Sort by</span>
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="start" className="w-[200px]">
              <DropdownMenuLabel>Sort By</DropdownMenuLabel>
              <DropdownMenuSeparator />
              <DropdownMenuRadioGroup
                value={sortOption}
                onValueChange={(value) => onSortChange(value as SortOption)}
              >
                {SORT_OPTIONS.map((option) => (
                  <DropdownMenuRadioItem key={option.value} value={option.value}>
                    {option.label}
                  </DropdownMenuRadioItem>
                ))}
              </DropdownMenuRadioGroup>
            </DropdownMenuContent>
          </DropdownMenu>

          {/* Confidence Range */}
          <div className="flex items-center gap-2 rounded-md border bg-background px-3 py-1.5">
            <Label className="whitespace-nowrap text-sm font-medium">Confidence Range</Label>
            <Input
              type="number"
              min={0}
              max={100}
              value={localMin}
              onChange={handleMinChange}
              className="h-7 w-16 text-center text-sm"
              aria-label="Minimum confidence"
            />
            <span className="text-sm text-muted-foreground">to</span>
            <Input
              type="number"
              min={0}
              max={100}
              value={localMax}
              onChange={handleMaxChange}
              className="h-7 w-16 text-center text-sm"
              aria-label="Maximum confidence"
            />
            <span className="text-sm text-muted-foreground">%</span>
          </div>

          {/* Include Low-Confidence Toggle */}
          <div className="flex items-center gap-2 rounded-md border bg-background px-3 py-1.5">
            <Switch
              id="include-low-confidence"
              checked={includeBelowThreshold}
              onCheckedChange={onIncludeBelowThresholdChange}
              aria-describedby="low-confidence-help"
            />
            <Label
              htmlFor="include-low-confidence"
              className="cursor-pointer whitespace-nowrap text-sm font-medium"
            >
              Include low-confidence
            </Label>
          </div>

          {/* Show Only Duplicates Toggle (P4.4b) */}
          <div className="flex items-center gap-2 rounded-md border bg-background px-3 py-1.5">
            <Switch
              id="show-only-duplicates"
              checked={showOnlyDuplicates}
              onCheckedChange={onShowOnlyDuplicatesChange}
              aria-describedby="duplicates-filter-help"
            />
            <Label
              htmlFor="show-only-duplicates"
              className="cursor-pointer whitespace-nowrap text-sm font-medium"
            >
              Only duplicates
            </Label>
          </div>

          {/* Clear Filters */}
          {hasActiveFilters && (
            <Button variant="ghost" size="sm" onClick={onClearFilters} className="h-9 gap-2">
              <X className="h-4 w-4" />
              Clear
            </Button>
          )}

          {/* Spacer */}
          <div className="flex-1" />

          {/* Select All */}
          <div className="flex items-center gap-2 rounded-md border bg-background px-3 py-1.5">
            <Checkbox
              id="select-all"
              checked={allSelected && totalSelectableCount > 0}
              onCheckedChange={onSelectAll}
              disabled={totalSelectableCount === 0}
              aria-label="Select all importable artifacts"
            />
            <Label
              htmlFor="select-all"
              className="cursor-pointer whitespace-nowrap text-sm font-medium"
            >
              Select All
              {selectedCount > 0 && (
                <span className="ml-1 text-muted-foreground">({selectedCount})</span>
              )}
            </Label>
          </div>

          {/* View Mode Toggle */}
          <div
            className="flex items-center gap-1 rounded-md border bg-background p-1"
            role="group"
            aria-label="View mode"
          >
            <Button
              variant={viewMode === 'grid' ? 'secondary' : 'ghost'}
              size="sm"
              onClick={() => onViewModeChange('grid')}
              aria-label="Grid view"
              aria-pressed={viewMode === 'grid'}
              className="h-7 w-7 p-0"
            >
              <Grid3x3 className="h-4 w-4" />
            </Button>
            <Button
              variant={viewMode === 'list' ? 'secondary' : 'ghost'}
              size="sm"
              onClick={() => onViewModeChange('list')}
              aria-label="List view"
              aria-pressed={viewMode === 'list'}
              className="h-7 w-7 p-0"
            >
              <List className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}

/**
 * Hook to initialize view mode from localStorage
 */
export function useViewMode(): [ViewMode, (mode: ViewMode) => void] {
  const [viewMode, setViewMode] = useState<ViewMode>('grid');

  useEffect(() => {
    if (typeof window !== 'undefined') {
      const stored = localStorage.getItem(VIEW_MODE_STORAGE_KEY) as ViewMode | null;
      if (stored === 'grid' || stored === 'list') {
        setViewMode(stored);
      }
    }
  }, []);

  return [viewMode, setViewMode];
}
