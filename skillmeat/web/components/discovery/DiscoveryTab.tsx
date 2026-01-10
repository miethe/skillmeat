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
import { Folder, FileText, Bot, Plug, Code, Package, Search, ArrowUpDown, X, AlertCircle, ChevronDown, ChevronRight, AlertTriangle, CheckCircle2 } from 'lucide-react';
import { cn } from '@/lib/utils';
import { buildArtifactKey } from '@/lib/skip-preferences';
import { useTrackDiscovery } from '@/lib/analytics';
import { TableSkeleton } from './skeletons';
import { ArtifactActions } from './ArtifactActions';
import type { DiscoveredArtifact, SkipPreference, MatchType } from '@/types/discovery';

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
  /** Callback to import only new artifacts (no matches) */
  onImportNewOnly?: (artifacts: DiscoveredArtifact[]) => void;
  /** Callback to open duplicate review modal */
  onReviewDuplicates?: (artifacts: DiscoveredArtifact[]) => void;
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
 * Get status label text with clearer messaging
 */
function getStatusLabel(status: string): string {
  switch (status) {
    case 'new':
      return 'New - Ready to Import';
    case 'in_collection':
      return 'Already in Collection';
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
 * Format date as relative time with improved granularity
 * Handles edge cases like invalid dates or future dates
 */
function formatRelativeTime(dateString: string): string {
  if (!dateString) return 'Unknown';

  const date = new Date(dateString);

  // Check for invalid date
  if (isNaN(date.getTime())) return 'Unknown';

  const now = new Date();
  const diffMs = now.getTime() - date.getTime();

  // Handle negative differences (future dates)
  if (diffMs < 0) return 'Just now';

  const diffMinutes = Math.floor(diffMs / (1000 * 60));
  const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

  if (diffMinutes < 1) return 'Just now';
  if (diffMinutes < 60) return `${diffMinutes}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffDays === 1) return 'Yesterday';
  if (diffDays < 7) return `${diffDays}d ago`;
  if (diffDays < 30) return `${Math.floor(diffDays / 7)}w ago`;
  if (diffDays < 365) return `${Math.floor(diffDays / 30)}mo ago`;
  return date.toLocaleDateString();
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
 * Determine artifact status based on collection_status and skip preferences
 * Uses backend-provided collection_status for accurate membership check
 */
function determineArtifactStatus(
  artifact: DiscoveredArtifact,
  skipPrefs?: SkipPreference[]
): string {
  const artifactKey = buildArtifactKey(artifact.type, artifact.name);

  // Check skip preferences first (user's explicit decision)
  if (skipPrefs?.some(pref => pref.artifact_key === artifactKey)) {
    return 'skipped';
  }

  // Use collection_status from backend if available
  if (artifact.collection_status) {
    if (artifact.collection_status.in_collection) {
      return 'in_collection';
    }
    // Not in collection means it's new and ready to import
    return 'new';
  }

  // Fallback: if no collection_status, assume new (legacy behavior)
  return 'new';
}

/**
 * Grouped artifacts by collection match type
 */
interface GroupedArtifacts {
  /** New artifacts with no collection match (type="none") */
  new: DiscoveredArtifact[];
  /** Possible duplicates: name_type or hash matches with confidence < 1.0 */
  possible_duplicates: DiscoveredArtifact[];
  /** Exact matches: identical content already in collection */
  exact_matches: DiscoveredArtifact[];
}

/**
 * Get the effective match type from collection_match or collection_status
 */
function getEffectiveMatchType(artifact: DiscoveredArtifact): MatchType {
  // Prefer collection_match (new P2-T1 hash-based matching)
  if (artifact.collection_match?.type) {
    return artifact.collection_match.type;
  }
  // Fallback to collection_status.match_type
  if (artifact.collection_status?.match_type) {
    return artifact.collection_status.match_type;
  }
  return 'none';
}

/**
 * Group artifacts by their collection match status
 */
function groupArtifacts(artifacts: DiscoveredArtifact[]): GroupedArtifacts {
  const groups: GroupedArtifacts = {
    new: [],
    possible_duplicates: [],
    exact_matches: [],
  };

  for (const artifact of artifacts) {
    const matchType = getEffectiveMatchType(artifact);

    switch (matchType) {
      case 'exact':
      case 'hash':
        // Exact hash match - already in collection
        groups.exact_matches.push(artifact);
        break;
      case 'name_type':
        // Name+type match but different content - possible duplicate
        groups.possible_duplicates.push(artifact);
        break;
      case 'none':
      default:
        // No match - new artifact ready to import
        groups.new.push(artifact);
        break;
    }
  }

  return groups;
}

/**
 * Get match info display for an artifact
 */
function getMatchInfo(artifact: DiscoveredArtifact): { name: string | null; confidence: number } {
  if (artifact.collection_match) {
    return {
      name: artifact.collection_match.matched_name,
      confidence: artifact.collection_match.confidence,
    };
  }
  if (artifact.collection_status?.matched_artifact_id) {
    // Extract name from artifact ID (format: type:name)
    const parts = artifact.collection_status.matched_artifact_id.split(':');
    const matchedName = parts.length > 1 ? parts[1] : artifact.collection_status.matched_artifact_id;
    return {
      name: matchedName ?? null,
      confidence: artifact.collection_status.match_type === 'exact' ? 1.0 : 0.85,
    };
  }
  return { name: null, confidence: 0 };
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
  onImportNewOnly,
  onReviewDuplicates,
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

  // Toggle for showing exact matches section
  const [showExactMatches, setShowExactMatches] = useState(false);

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

  // Group filtered artifacts by collection match status
  const groupedArtifacts = useMemo(() => {
    return groupArtifacts(filteredAndSortedArtifacts);
  }, [filteredAndSortedArtifacts]);

  // Check if there are any duplicates to review
  const hasDuplicatesToReview = groupedArtifacts.possible_duplicates.length > 0;

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

      {/* Action Buttons for Grouped View */}
      <div className="flex flex-wrap items-center gap-3">
        {/* Import New Only Button */}
        {groupedArtifacts.new.length > 0 && onImportNewOnly && (
          <Button
            onClick={() => onImportNewOnly(groupedArtifacts.new)}
            className="gap-2"
          >
            <Package className="h-4 w-4" />
            Import New Only ({groupedArtifacts.new.length})
          </Button>
        )}

        {/* Review Duplicates Button */}
        {hasDuplicatesToReview && onReviewDuplicates && (
          <Button
            variant="outline"
            onClick={() => onReviewDuplicates(groupedArtifacts.possible_duplicates)}
            className="gap-2 border-yellow-500/50 text-yellow-600 hover:bg-yellow-500/10 dark:text-yellow-400"
          >
            <AlertTriangle className="h-4 w-4" />
            Review Duplicates ({groupedArtifacts.possible_duplicates.length})
          </Button>
        )}
      </div>

      {/* No artifacts message */}
      {filteredAndSortedArtifacts.length === 0 && (
        <div className="rounded-md border bg-card p-8 text-center">
          <p className="text-sm text-muted-foreground">
            No artifacts match your filters. Try adjusting your search or filter criteria.
          </p>
        </div>
      )}

      {/* New Artifacts Section */}
      {groupedArtifacts.new.length > 0 && (
        <div className="space-y-3">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="h-5 w-5 text-green-500" />
            <h3 className="text-lg font-semibold">
              New Artifacts ({groupedArtifacts.new.length})
            </h3>
            <Badge variant="outline" className="bg-green-500/10 text-green-600 border-green-500/20 dark:text-green-400">
              Ready to Import
            </Badge>
          </div>
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
                {groupedArtifacts.new.map((artifact) => {
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
                })}
              </TableBody>
            </Table>
          </div>
        </div>
      )}

      {/* Possible Duplicates Section */}
      {groupedArtifacts.possible_duplicates.length > 0 && (
        <div className="space-y-3">
          <div className="flex items-center gap-2">
            <AlertTriangle className="h-5 w-5 text-yellow-500" />
            <h3 className="text-lg font-semibold">
              Possible Duplicates ({groupedArtifacts.possible_duplicates.length})
            </h3>
            <Badge variant="outline" className="bg-yellow-500/10 text-yellow-600 border-yellow-500/20 dark:text-yellow-400">
              Review Recommended
            </Badge>
          </div>
          <div className="rounded-md border border-yellow-500/30 bg-yellow-500/5">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Name</TableHead>
                  <TableHead>Type</TableHead>
                  <TableHead>Matches</TableHead>
                  <TableHead className="min-w-[200px]">Source</TableHead>
                  <TableHead>Discovered</TableHead>
                  <TableHead className="w-24 text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {groupedArtifacts.possible_duplicates.map((artifact) => {
                  const Icon = artifactTypeIcons[artifact.type as keyof typeof artifactTypeIcons] || Package;
                  const typeColorClass = artifactTypeColors[artifact.type as keyof typeof artifactTypeColors] || 'bg-gray-500/10 text-gray-500 border-gray-500/20';
                  const matchInfo = getMatchInfo(artifact);
                  const artifactKey = buildArtifactKey(artifact.type, artifact.name);
                  const isSkipped = skipPrefs?.some(pref => pref.artifact_key === artifactKey);

                  return (
                    <TableRow
                      key={`${artifact.type}:${artifact.name}:${artifact.path}`}
                      className="cursor-pointer hover:bg-yellow-500/10"
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
                        <div className="flex flex-col gap-1">
                          <span className="text-sm font-medium text-yellow-600 dark:text-yellow-400">
                            {matchInfo.name || 'Unknown'}
                          </span>
                          <span className="text-xs text-muted-foreground">
                            {Math.round(matchInfo.confidence * 100)}% confidence
                          </span>
                        </div>
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
                            isImported={false}
                            onImport={() => onImport?.(artifact)}
                            onToggleSkip={(skip) => onToggleSkip?.(artifactKey, skip)}
                            onViewDetails={() => onViewDetails?.(artifact)}
                          />
                        </div>
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          </div>
        </div>
      )}

      {/* Exact Matches Section (Collapsible) */}
      {groupedArtifacts.exact_matches.length > 0 && (
        <div className="space-y-3">
          <button
            type="button"
            onClick={() => setShowExactMatches(!showExactMatches)}
            className="flex w-full items-center gap-2 text-left"
            aria-expanded={showExactMatches}
            aria-controls="exact-matches-section"
          >
            {showExactMatches ? (
              <ChevronDown className="h-5 w-5 text-blue-500" />
            ) : (
              <ChevronRight className="h-5 w-5 text-blue-500" />
            )}
            <h3 className="text-lg font-semibold">
              Exact Matches ({groupedArtifacts.exact_matches.length})
            </h3>
            <Badge variant="outline" className="bg-blue-500/10 text-blue-600 border-blue-500/20 dark:text-blue-400">
              Already in Collection
            </Badge>
          </button>

          {showExactMatches && (
            <div id="exact-matches-section" className="rounded-md border border-blue-500/30 bg-blue-500/5">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Name</TableHead>
                    <TableHead>Type</TableHead>
                    <TableHead>Collection Match</TableHead>
                    <TableHead className="min-w-[200px]">Source</TableHead>
                    <TableHead>Discovered</TableHead>
                    <TableHead className="w-24 text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {groupedArtifacts.exact_matches.map((artifact) => {
                    const Icon = artifactTypeIcons[artifact.type as keyof typeof artifactTypeIcons] || Package;
                    const typeColorClass = artifactTypeColors[artifact.type as keyof typeof artifactTypeColors] || 'bg-gray-500/10 text-gray-500 border-gray-500/20';
                    const matchInfo = getMatchInfo(artifact);
                    const artifactKey = buildArtifactKey(artifact.type, artifact.name);
                    const isSkipped = skipPrefs?.some(pref => pref.artifact_key === artifactKey);

                    return (
                      <TableRow
                        key={`${artifact.type}:${artifact.name}:${artifact.path}`}
                        className="cursor-pointer hover:bg-blue-500/10"
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
                          <div className="flex flex-col gap-1">
                            <span className="text-sm font-medium text-blue-600 dark:text-blue-400">
                              {matchInfo.name || artifact.name}
                            </span>
                            <span className="text-xs text-muted-foreground">
                              Identical content
                            </span>
                          </div>
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
                              isImported={true}
                              onImport={() => onImport?.(artifact)}
                              onToggleSkip={(skip) => onToggleSkip?.(artifactKey, skip)}
                              onViewDetails={() => onViewDetails?.(artifact)}
                            />
                          </div>
                        </TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
