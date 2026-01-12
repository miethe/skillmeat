'use client';

import { useState, useMemo, useEffect } from 'react';
import {
  RefreshCw,
  Search,
  Filter,
  LayoutGrid,
  LayoutList,
  ChevronDown,
  Clock,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuRadioGroup,
  DropdownMenuRadioItem,
  DropdownMenuTrigger,
  DropdownMenuCheckboxItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
} from '@/components/ui/dropdown-menu';
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible';
import { cn } from '@/lib/utils';
import { useDeploymentList, useDeploymentSummary, useRefreshDeployments } from '@/hooks';
import { DeploymentCard, DeploymentCardSkeleton } from '@/components/deployments/deployment-card';
import type { ArtifactDeploymentInfo, ArtifactSyncStatus } from '@/types/deployments';
import type { ArtifactType } from '@/types/artifact';

type ViewMode = 'flat' | 'grouped';
type StatusFilter = 'all' | ArtifactSyncStatus;

// Artifact types for filtering
const ARTIFACT_TYPES: ArtifactType[] = ['skill', 'command', 'agent', 'mcp', 'hook'];

/**
 * Deployments Dashboard Page
 *
 * Displays a deployment-focused dashboard with:
 * - Summary stats (total, status counts)
 * - Filtering by status, type, and search
 * - View toggle (flat list vs grouped by project)
 * - Refresh functionality
 */
export default function DeploymentsPage() {
  // Data fetching
  const { data: listData, isLoading, isRefetching, refetch } = useDeploymentList();
  const { data: summary } = useDeploymentSummary();
  const refreshDeployments = useRefreshDeployments();

  // Filter state
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('all');
  const [typeFilters, setTypeFilters] = useState<Set<ArtifactType>>(new Set());
  const [searchQuery, setSearchQuery] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const [viewMode, setViewMode] = useState<ViewMode>('flat');

  // Debounce search input (300ms)
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedSearch(searchQuery);
    }, 300);

    return () => clearTimeout(timer);
  }, [searchQuery]);

  // Filter deployments
  const filteredDeployments = useMemo(() => {
    if (!listData?.deployments) return [];

    return listData.deployments.filter((deployment) => {
      // Status filter
      if (statusFilter !== 'all' && deployment.sync_status !== statusFilter) {
        return false;
      }

      // Type filter
      if (typeFilters.size > 0 && !typeFilters.has(deployment.artifact_type as ArtifactType)) {
        return false;
      }

      // Search filter (case-insensitive name match)
      if (debouncedSearch && !deployment.artifact_name.toLowerCase().includes(debouncedSearch.toLowerCase())) {
        return false;
      }

      return true;
    });
  }, [listData?.deployments, statusFilter, typeFilters, debouncedSearch]);

  // Group deployments by project path for grouped view
  const groupedDeployments = useMemo(() => {
    if (viewMode !== 'grouped') return {};

    const groups: Record<string, ArtifactDeploymentInfo[]> = {};
    filteredDeployments.forEach((deployment) => {
      const projectPath = deployment.artifact_path.split('/.claude/')[0] || 'Unknown Project';
      if (!groups[projectPath]) {
        groups[projectPath] = [];
      }
      groups[projectPath].push(deployment);
    });

    return groups;
  }, [filteredDeployments, viewMode]);

  // Toggle type filter
  const toggleTypeFilter = (type: ArtifactType) => {
    setTypeFilters((prev) => {
      const next = new Set(prev);
      if (next.has(type)) {
        next.delete(type);
      } else {
        next.add(type);
      }
      return next;
    });
  };

  // Clear all filters
  const clearFilters = () => {
    setStatusFilter('all');
    setTypeFilters(new Set());
    setSearchQuery('');
  };

  // Handle refresh
  const handleRefresh = () => {
    refetch();
    refreshDeployments();
  };

  // Format relative time
  const formatRelativeTime = (dateString: string): string => {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return 'just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 30) return `${diffDays}d ago`;
    return date.toLocaleDateString();
  };

  const hasActiveFilters = statusFilter !== 'all' || typeFilters.size > 0 || debouncedSearch !== '';

  return (
    <div className="flex h-screen flex-col">
      {/* Header */}
      <div className="border-b p-6">
        <div className="mb-4 flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold">Deployments</h1>
            <p className="mt-1 text-muted-foreground">
              Manage artifact deployments across your projects
            </p>
          </div>

          <div className="flex items-center gap-2">
            {/* Refresh button */}
            <Button
              variant="outline"
              size="icon"
              onClick={handleRefresh}
              disabled={isRefetching}
              title="Refresh deployments"
            >
              <RefreshCw className={cn('h-4 w-4', isRefetching && 'animate-spin')} />
            </Button>

            {/* View mode toggle */}
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="outline" size="icon" title="View mode">
                  {viewMode === 'flat' ? (
                    <LayoutGrid className="h-4 w-4" />
                  ) : (
                    <LayoutList className="h-4 w-4" />
                  )}
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <DropdownMenuRadioGroup
                  value={viewMode}
                  onValueChange={(v) => setViewMode(v as ViewMode)}
                >
                  <DropdownMenuRadioItem value="flat">
                    <LayoutGrid className="mr-2 h-4 w-4" />
                    By Artifact
                  </DropdownMenuRadioItem>
                  <DropdownMenuRadioItem value="grouped">
                    <LayoutList className="mr-2 h-4 w-4" />
                    By Project
                  </DropdownMenuRadioItem>
                </DropdownMenuRadioGroup>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </div>

        {/* Summary Stats */}
        {summary && (
          <div className="mb-4 flex flex-wrap items-center gap-3">
            {/* Total count */}
            <Badge variant="outline" className="px-3 py-1">
              Total: {summary.total}
            </Badge>

            {/* Status counts with color coding */}
            {summary.byStatus.synced > 0 && (
              <Badge
                variant="outline"
                className="border-green-500/20 bg-green-500/10 text-green-600 px-3 py-1"
              >
                Synced: {summary.byStatus.synced}
              </Badge>
            )}
            {summary.byStatus.modified > 0 && (
              <Badge
                variant="outline"
                className="border-yellow-500/20 bg-yellow-500/10 text-yellow-600 px-3 py-1"
              >
                Modified: {summary.byStatus.modified}
              </Badge>
            )}
            {summary.byStatus.outdated > 0 && (
              <Badge
                variant="outline"
                className="border-orange-500/20 bg-orange-500/10 text-orange-600 px-3 py-1"
              >
                Outdated: {summary.byStatus.outdated}
              </Badge>
            )}

            {/* Last updated */}
            <div className="ml-auto flex items-center gap-2 text-sm text-muted-foreground">
              <Clock className="h-4 w-4" />
              <span>Updated {formatRelativeTime(summary.lastUpdated)}</span>
            </div>
          </div>
        )}

        {/* Filters Bar */}
        <div className="sticky top-0 z-10 flex flex-wrap items-center gap-2 rounded-lg border bg-background p-3">
          {/* Search input */}
          <div className="relative flex-1 min-w-[200px]">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              placeholder="Search by name..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-9"
            />
          </div>

          {/* Status filter */}
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="outline" className="gap-2">
                <Filter className="h-4 w-4" />
                Status: {statusFilter === 'all' ? 'All' : statusFilter}
                <ChevronDown className="h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuLabel>Filter by Status</DropdownMenuLabel>
              <DropdownMenuSeparator />
              <DropdownMenuRadioGroup
                value={statusFilter}
                onValueChange={(v) => setStatusFilter(v as StatusFilter)}
              >
                <DropdownMenuRadioItem value="all">All</DropdownMenuRadioItem>
                <DropdownMenuRadioItem value="synced">Synced</DropdownMenuRadioItem>
                <DropdownMenuRadioItem value="modified">Modified</DropdownMenuRadioItem>
                <DropdownMenuRadioItem value="outdated">Outdated</DropdownMenuRadioItem>
              </DropdownMenuRadioGroup>
            </DropdownMenuContent>
          </DropdownMenu>

          {/* Type filter */}
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="outline" className="gap-2">
                <Filter className="h-4 w-4" />
                Type {typeFilters.size > 0 && `(${typeFilters.size})`}
                <ChevronDown className="h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuLabel>Filter by Type</DropdownMenuLabel>
              <DropdownMenuSeparator />
              {ARTIFACT_TYPES.map((type) => (
                <DropdownMenuCheckboxItem
                  key={type}
                  checked={typeFilters.has(type)}
                  onCheckedChange={() => toggleTypeFilter(type)}
                  className="capitalize"
                >
                  {type}
                </DropdownMenuCheckboxItem>
              ))}
            </DropdownMenuContent>
          </DropdownMenu>

          {/* Clear filters */}
          {hasActiveFilters && (
            <Button variant="ghost" size="sm" onClick={clearFilters}>
              Clear filters
            </Button>
          )}
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-auto p-6">
        {isLoading ? (
          // Loading skeletons
          <div className="grid gap-4 sm:grid-cols-1 md:grid-cols-2 lg:grid-cols-3">
            {Array.from({ length: 6 }).map((_, i) => (
              <DeploymentCardSkeleton key={i} />
            ))}
          </div>
        ) : filteredDeployments.length === 0 ? (
          // Empty state
          <div className="flex flex-col items-center justify-center py-12 text-center">
            <div className="rounded-full bg-muted p-6 mb-4">
              <LayoutGrid className="h-12 w-12 text-muted-foreground" />
            </div>
            <h3 className="text-lg font-semibold mb-2">No deployments found</h3>
            <p className="text-sm text-muted-foreground max-w-md">
              {hasActiveFilters
                ? 'No deployments match your current filters. Try adjusting your search criteria.'
                : 'You haven\'t deployed any artifacts yet. Deploy artifacts from your collection to get started.'}
            </p>
            {hasActiveFilters && (
              <Button variant="outline" onClick={clearFilters} className="mt-4">
                Clear filters
              </Button>
            )}
          </div>
        ) : viewMode === 'flat' ? (
          // Flat list view
          <div className="grid gap-4 sm:grid-cols-1 md:grid-cols-2 lg:grid-cols-3">
            {filteredDeployments.map((deployment) => (
              <DeploymentCard
                key={`${deployment.artifact_type}:${deployment.artifact_name}`}
                deployment={{
                  ...deployment,
                  id: `${deployment.artifact_type}:${deployment.artifact_name}`,
                  status: deployment.sync_status === 'synced' ? 'current' : 'outdated',
                }}
              />
            ))}
          </div>
        ) : (
          // Grouped by project view
          <div className="space-y-4">
            {Object.entries(groupedDeployments).map(([projectPath, deployments]) => (
              <Collapsible key={projectPath} defaultOpen>
                <div className="rounded-lg border bg-card">
                  <CollapsibleTrigger className="flex w-full items-center justify-between p-4 hover:bg-accent/50 transition-colors">
                    <div className="flex items-center gap-2">
                      <ChevronDown className="h-4 w-4 transition-transform [[data-state=closed]>&]:rotate-[-90deg]" />
                      <h3 className="font-semibold">{projectPath}</h3>
                      <Badge variant="secondary" className="ml-2">
                        {deployments.length}
                      </Badge>
                    </div>
                  </CollapsibleTrigger>
                  <CollapsibleContent>
                    <div className="grid gap-4 p-4 pt-0 sm:grid-cols-1 md:grid-cols-2 lg:grid-cols-3">
                      {deployments.map((deployment) => (
                        <DeploymentCard
                          key={`${deployment.artifact_type}:${deployment.artifact_name}`}
                          deployment={{
                            ...deployment,
                            id: `${deployment.artifact_type}:${deployment.artifact_name}`,
                            status: deployment.sync_status === 'synced' ? 'current' : 'outdated',
                          }}
                          projectPath={projectPath}
                        />
                      ))}
                    </div>
                  </CollapsibleContent>
                </div>
              </Collapsible>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
