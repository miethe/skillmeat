'use client';

import { useState, useMemo, useEffect } from 'react';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Folder, FileText, Bot, Plug, Code, Package, Search, ArrowUpDown, X, AlertCircle } from 'lucide-react';
import { cn } from '@/lib/utils';
import { buildArtifactKey } from '@/lib/skip-preferences';
import { useTrackDiscovery } from '@/lib/analytics';
import { TableSkeleton } from './skeletons';
import { ArtifactActions } from './ArtifactActions';
import type { DiscoveredArtifact, SkipPreference } from '@/types/discovery';

/**
 * Filter types for discovery artifacts
 */
type StatusFilter = 'all' | 'new' | 'in_collection' | 'in_project' | 'skipped';
type TypeFilter = 'all' | 'skill' | 'command' | 'agent' | 'mcp' | 'hook';
type SortField = 'name' | 'type' | 'discovered_at';
type SortOrder = 'asc' | 'desc';

/**
 * Discovery filters interface
 */
interface DiscoveryFilters {
  search: string;
  status: StatusFilter;
  type: TypeFilter;
}

/**
 * Discovery sort interface
 */
interface DiscoverySort {
  field: SortField;
  order: SortOrder;
}

/**
 * Props for DiscoveryTab component
 */
export interface DiscoveryTabProps {
  artifacts: DiscoveredArtifact[];
  isLoading?: boolean;
  skipPrefs?: SkipPreference[];
  projectId?: string;
  onImport?: (artifact: DiscoveredArtifact) => void;
  onToggleSkip?: (artifactKey: string, skip: boolean) => void;
  onViewDetails?: (artifact: DiscoveredArtifact) => void;
  /** Show token usage summary (for context entities) */
  showTokenUsage?: boolean;
  /** Function to calculate token count for an artifact */
  getTokenCount?: (artifact: DiscoveredArtifact) => number;
  /** Token warning threshold */
  tokenWarningThreshold?: number;
}

/**
 * Map artifact types to Lucide icons
 */
const artifactTypeIcons = {
  skill: Folder,
  command: FileText,
  agent: Bot,
  mcp: Plug,
  hook: Code,
};

/**
 * Map artifact types to color classes (matching project page patterns)
 */
const artifactTypeColors = {
  skill: 'bg-blue-500/10 text-blue-500 border-blue-500/20',
  command: 'bg-green-500/10 text-green-500 border-green-500/20',
  agent: 'bg-purple-500/10 text-purple-500 border-purple-500/20',
  mcp: 'bg-orange-500/10 text-orange-500 border-orange-500/20',
  hook: 'bg-pink-500/10 text-pink-500 border-pink-500/20',
};

/**
 * Get badge variant based on artifact status
 */
function getStatusBadgeVariant(status: string): 'default' | 'secondary' | 'outline' {
  switch (status) {
    case 'new':
      return 'default'; // Green
    case 'in_collection':
      return 'outline'; // Blue
    case 'in_project':
      return 'secondary'; // Purple
    case 'skipped':
      return 'secondary'; // Gray
    default:
      return 'outline';
  }
}

/**
 * Get status label text
 */
function getStatusLabel(status: string): string {
  switch (status) {
    case 'new':
      return 'New';
    case 'in_collection':
      return 'In Collection';
    case 'in_project':
      return 'In Project';
    case 'skipped':
      return 'Skipped';
    default:
      return 'Unknown';
  }
}

/**
 * Get badge color classes for status
 */
function getStatusColorClass(status: string): string {
  switch (status) {
    case 'new':
      return 'bg-green-500/10 text-green-500 border-green-500/20';
    case 'in_collection':
      return 'bg-blue-500/10 text-blue-500 border-blue-500/20';
    case 'in_project':
      return 'bg-purple-500/10 text-purple-500 border-purple-500/20';
    case 'skipped':
      return 'bg-gray-500/10 text-gray-500 border-gray-500/20';
    default:
      return 'bg-gray-500/10 text-gray-500 border-gray-500/20';
  }
}

/**
 * Format date as relative time
 */
function formatRelativeTime(dateString: string): string {
  const date = new Date(dateString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

  if (diffDays === 0) return 'Today';
  if (diffDays === 1) return 'Yesterday';
  if (diffDays < 7) return `${diffDays} days ago`;
  if (diffDays < 30) return `${Math.floor(diffDays / 7)} weeks ago`;
  if (diffDays < 365) return `${Math.floor(diffDays / 30)} months ago`;
  return `${Math.floor(diffDays / 365)} years ago`;
}

/**
 * Truncate source path for display
 */
function truncateSource(source?: string, maxLength: number = 40): string {
  if (!source) return '—';
  if (source.length <= maxLength) return source;

  // Try to show beginning and end of path
  const start = source.substring(0, maxLength / 2 - 2);
  const end = source.substring(source.length - maxLength / 2 + 2);
  return `${start}...${end}`;
}

/**
 * Determine artifact status based on skip preferences
 * In real implementation, this would also check collection and project membership
 */
function determineArtifactStatus(
  artifact: DiscoveredArtifact,
  skipPrefs?: SkipPreference[]
): string {
  const artifactKey = buildArtifactKey(artifact.type, artifact.name);

  if (skipPrefs?.some(pref => pref.artifact_key === artifactKey)) {
    return 'skipped';
  }

  // For now, default to 'new'
  // In real implementation, check collection and project membership via API/props
  return 'new';
}

/**
 * DiscoveryTab Component
 *
 * Displays all discovered artifacts in a table format on the Project Detail page.
 * Shows artifact metadata, status badges, and provides actions for import and skip.
 */
export function DiscoveryTab({
  artifacts,
  isLoading = false,
  skipPrefs = [],
  projectId = 'unknown',
  onImport,
  onToggleSkip,
  onViewDetails,
  showTokenUsage = false,
  getTokenCount,
  tokenWarningThreshold = 2000,
}: DiscoveryTabProps) {
  // Filter and sort state
  const [filters, setFilters] = useState<DiscoveryFilters>({
    search: '',
    status: 'all',
    type: 'all',
  });

  const [sort, setSort] = useState<DiscoverySort>({
    field: 'name',
    order: 'asc',
  });

  // Debounced search state
  const [debouncedSearch, setDebouncedSearch] = useState('');

  const tracking = useTrackDiscovery();

  // Track tab view on mount
  useEffect(() => {
    if (artifacts.length > 0) {
      tracking.trackTabView(projectId, artifacts.length);
    }
  }, [projectId, artifacts.length, tracking]);

  // Debounce search input (300ms)
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedSearch(filters.search);
    }, 300);

    return () => clearTimeout(timer);
  }, [filters.search]);

  // Filter and sort artifacts
  const filteredAndSortedArtifacts = useMemo(() => {
    let result = [...artifacts];

    // Apply search filter (debounced)
    if (debouncedSearch) {
      const searchLower = debouncedSearch.toLowerCase();
      result = result.filter((artifact) =>
        artifact.name.toLowerCase().includes(searchLower)
      );
    }

    // Apply status filter
    if (filters.status !== 'all') {
      result = result.filter((artifact) => {
        const status = determineArtifactStatus(artifact, skipPrefs);
        return status === filters.status;
      });
    }

    // Apply type filter
    if (filters.type !== 'all') {
      result = result.filter((artifact) => artifact.type === filters.type);
    }

    // Apply sorting
    result.sort((a, b) => {
      let comparison = 0;

      switch (sort.field) {
        case 'name':
          comparison = a.name.localeCompare(b.name);
          break;
        case 'type':
          comparison = a.type.localeCompare(b.type);
          break;
        case 'discovered_at':
          comparison = new Date(a.discovered_at).getTime() - new Date(b.discovered_at).getTime();
          break;
      }

      return sort.order === 'asc' ? comparison : -comparison;
    });

    return result;
  }, [artifacts, debouncedSearch, filters.status, filters.type, sort, skipPrefs]);

  // Reset all filters to default
  const handleClearFilters = () => {
    setFilters({
      search: '',
      status: 'all',
      type: 'all',
    });
    setSort({
      field: 'name',
      order: 'asc',
    });
  };

  // Handle status filter change with tracking
  const handleStatusFilterChange = (value: StatusFilter) => {
    setFilters({ ...filters, status: value });
    if (value !== 'all') {
      tracking.trackFilterApplied('status', value);
    }
  };

  // Handle type filter change with tracking
  const handleTypeFilterChange = (value: TypeFilter) => {
    setFilters({ ...filters, type: value });
    if (value !== 'all') {
      tracking.trackFilterApplied('type', value);
    }
  };

  // Handle sort field change with tracking
  const handleSortFieldChange = (value: SortField) => {
    setSort({ ...sort, field: value });
    tracking.trackSortApplied(value, sort.order);
  };

  // Handle sort order change with tracking
  const handleSortOrderChange = (value: SortOrder) => {
    setSort({ ...sort, order: value });
    tracking.trackSortApplied(sort.field, value);
  };

  // Handle search with tracking
  const handleSearchChange = (value: string) => {
    setFilters({ ...filters, search: value });
    if (value && value.length > 0) {
      tracking.trackFilterApplied('search', value);
    }
  };

  // Check if any filters are active
  const hasActiveFilters = filters.search !== '' || filters.status !== 'all' || filters.type !== 'all' || sort.field !== 'name' || sort.order !== 'asc';

  // Calculate total token usage (for context entities with auto-load)
  const totalAutoLoadTokens = useMemo(() => {
    if (!showTokenUsage || !getTokenCount) return 0;

    return filteredAndSortedArtifacts.reduce((sum, artifact) => {
      // Only count artifacts that would be auto-loaded
      // This is a simplified check - in practice, you'd check the artifact's auto_load property
      const tokens = getTokenCount(artifact);
      return sum + tokens;
    }, 0);
  }, [filteredAndSortedArtifacts, showTokenUsage, getTokenCount]);

  if (isLoading) {
    return (
      <div className="rounded-md border p-4" aria-busy="true">
        <TableSkeleton rows={5} />
        <span className="sr-only" role="status" aria-live="polite">
          Loading discovered artifacts...
        </span>
      </div>
    );
  }

  if (artifacts.length === 0) {
    return (
      <div className="rounded-md border bg-card p-12 text-center" role="status">
        <Package className="mx-auto h-12 w-12 text-muted-foreground/50" aria-hidden="true" />
        <h3 className="mt-4 text-lg font-semibold">No Artifacts Discovered</h3>
        <p className="mt-2 text-sm text-muted-foreground">
          No artifacts have been discovered in this project yet. Run a discovery scan to find
          deployable artifacts.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4" role="region" aria-label="Discovered artifacts">
      {/* Token Warning Banner */}
      {showTokenUsage && totalAutoLoadTokens > tokenWarningThreshold && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>
            Auto-loaded entities use {totalAutoLoadTokens} tokens. Consider reducing auto-load
            entities to stay under {tokenWarningThreshold} tokens for optimal performance.
          </AlertDescription>
        </Alert>
      )}

      {/* Filter Controls */}
      <div className="space-y-4">
        {/* Search */}
        <div className="relative">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder="Search artifacts by name..."
            value={filters.search}
            onChange={(e) => handleSearchChange(e.target.value)}
            className="pl-9"
          />
        </div>

        {/* Filter and Sort Controls */}
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 md:grid-cols-4">
          {/* Status Filter */}
          <div>
            <label htmlFor="status-filter" className="mb-1.5 block text-sm font-medium">
              Status
            </label>
            <Select
              value={filters.status}
              onValueChange={(value) => handleStatusFilterChange(value as StatusFilter)}
            >
              <SelectTrigger id="status-filter">
                <SelectValue placeholder="All Statuses" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All</SelectItem>
                <SelectItem value="new">New</SelectItem>
                <SelectItem value="in_collection">In Collection</SelectItem>
                <SelectItem value="in_project">In Project</SelectItem>
                <SelectItem value="skipped">Skipped</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {/* Type Filter */}
          <div>
            <label htmlFor="type-filter" className="mb-1.5 block text-sm font-medium">
              Type
            </label>
            <Select
              value={filters.type}
              onValueChange={(value) => handleTypeFilterChange(value as TypeFilter)}
            >
              <SelectTrigger id="type-filter">
                <SelectValue placeholder="All Types" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All</SelectItem>
                <SelectItem value="skill">Skill</SelectItem>
                <SelectItem value="command">Command</SelectItem>
                <SelectItem value="agent">Agent</SelectItem>
                <SelectItem value="mcp">MCP</SelectItem>
                <SelectItem value="hook">Hook</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {/* Sort Field */}
          <div>
            <label htmlFor="sort-field" className="mb-1.5 block text-sm font-medium">
              Sort By
            </label>
            <Select
              value={sort.field}
              onValueChange={(value) => handleSortFieldChange(value as SortField)}
            >
              <SelectTrigger id="sort-field">
                <SelectValue placeholder="Name" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="name">Name</SelectItem>
                <SelectItem value="type">Type</SelectItem>
                <SelectItem value="discovered_at">Discovered</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {/* Sort Order */}
          <div>
            <label htmlFor="sort-order" className="mb-1.5 block text-sm font-medium">
              Order
            </label>
            <div className="flex gap-2">
              <Select
                value={sort.order}
                onValueChange={(value) => handleSortOrderChange(value as SortOrder)}
              >
                <SelectTrigger id="sort-order" className="flex-1">
                  <SelectValue placeholder="Ascending" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="asc">Ascending</SelectItem>
                  <SelectItem value="desc">Descending</SelectItem>
                </SelectContent>
              </Select>
              <Button
                variant="outline"
                size="icon"
                onClick={() => handleSortOrderChange(sort.order === 'asc' ? 'desc' : 'asc')}
                title="Toggle sort order"
              >
                <ArrowUpDown className="h-4 w-4" />
              </Button>
            </div>
          </div>
        </div>

        {/* Results Summary, Token Usage, and Clear Filters */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <p className="text-sm text-muted-foreground">
              Showing <span className="font-medium">{filteredAndSortedArtifacts.length}</span> of{' '}
              <span className="font-medium">{artifacts.length}</span> artifacts
            </p>
            {showTokenUsage && totalAutoLoadTokens > 0 && (
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <span>Auto-load: {totalAutoLoadTokens} tokens</span>
                {totalAutoLoadTokens > tokenWarningThreshold && (
                  <Badge variant="destructive" className="text-xs">
                    High usage
                  </Badge>
                )}
              </div>
            )}
          </div>
          {hasActiveFilters && (
            <Button
              variant="ghost"
              size="sm"
              onClick={handleClearFilters}
              className="gap-2"
            >
              <X className="h-4 w-4" />
              Clear Filters
            </Button>
          )}
        </div>
      </div>

      {/* Artifacts Table */}
      <div className="rounded-md border">
        <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Name</TableHead>
            <TableHead>Type</TableHead>
            <TableHead>Status</TableHead>
            <TableHead className="min-w-[200px]">Source</TableHead>
            <TableHead>Discovered</TableHead>
            <TableHead className="w-24 text-right">Actions</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {filteredAndSortedArtifacts.length === 0 ? (
            <TableRow>
              <TableCell colSpan={6} className="h-24 text-center">
                <p className="text-sm text-muted-foreground">
                  No artifacts match your filters. Try adjusting your search or filter criteria.
                </p>
              </TableCell>
            </TableRow>
          ) : (
            filteredAndSortedArtifacts.map((artifact) => {
            const Icon = artifactTypeIcons[artifact.type as keyof typeof artifactTypeIcons] || Package;
            const typeColorClass = artifactTypeColors[artifact.type as keyof typeof artifactTypeColors] || 'bg-gray-500/10 text-gray-500 border-gray-500/20';
            const status = determineArtifactStatus(artifact, skipPrefs);
            const statusColorClass = getStatusColorClass(status);
            const artifactKey = buildArtifactKey(artifact.type, artifact.name);
            const isSkipped = skipPrefs?.some(pref => pref.artifact_key === artifactKey);
            const isImported = status === 'in_collection' || status === 'in_project';

            return (
              <TableRow
                key={`${artifact.type}:${artifact.name}:${artifact.path}`}
                className="cursor-pointer hover:bg-accent/50"
                onClick={() => onViewDetails?.(artifact)}
                role="button"
                tabIndex={0}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    onViewDetails?.(artifact);
                  }
                }}
                aria-label={`View details for ${artifact.name}`}
              >
                <TableCell className="font-medium">{artifact.name}</TableCell>
                <TableCell>
                  <Badge
                    variant="outline"
                    className={cn('gap-1.5', typeColorClass)}
                    aria-label={`Type: ${artifact.type}`}
                  >
                    <Icon className="h-3 w-3" aria-hidden="true" />
                    {artifact.type}
                  </Badge>
                </TableCell>
                <TableCell>
                  <Badge
                    variant={getStatusBadgeVariant(status)}
                    className={cn(statusColorClass)}
                    aria-label={`Status: ${getStatusLabel(status)}`}
                  >
                    {getStatusLabel(status)}
                  </Badge>
                </TableCell>
                <TableCell>
                  <span
                    className="block truncate font-mono text-xs text-muted-foreground max-w-[200px]"
                    title={artifact.source || 'No source'}
                  >
                    {truncateSource(artifact.source)}
                  </span>
                </TableCell>
                <TableCell>
                  <span className="text-xs text-muted-foreground">
                    {formatRelativeTime(artifact.discovered_at)}
                  </span>
                </TableCell>
                <TableCell className="text-right">
                  <div className="flex items-center justify-end gap-2" onClick={(e) => e.stopPropagation()}>
                    <ArtifactActions
                      artifact={artifact}
                      isSkipped={isSkipped}
                      isImported={isImported}
                      onImport={() => onImport?.(artifact)}
                      onToggleSkip={(skip) => onToggleSkip?.(artifactKey, skip)}
                      onViewDetails={() => onViewDetails?.(artifact)}
                    />
                  </div>
                </TableCell>
              </TableRow>
            );
          })
          )}
        </TableBody>
      </Table>
      </div>
    </div>
  );
}
