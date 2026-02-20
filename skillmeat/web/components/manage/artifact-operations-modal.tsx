/**
 * Artifact Operations Modal Component
 *
 * Operations-focused modal for the /manage page, emphasizing health status,
 * sync state, and deployment management. Opens when clicking an artifact
 * on the manage page.
 *
 * Built on BaseArtifactModal for consistent dialog structure, header, and
 * tab navigation. This component provides the operations-specific tab
 * content and business logic.
 *
 * Key differences from the collection-focused modal:
 * - Status tab is the default (not Overview)
 * - Emphasizes health indicators and sync status
 * - Focuses on deployments and operations
 * - Shows "Collection Details" cross-navigation button
 *
 * @example Basic usage
 * ```tsx
 * <ArtifactOperationsModal
 *   artifact={selectedArtifact}
 *   open={isOpen}
 *   onClose={() => setIsOpen(false)}
 * />
 * ```
 *
 * @example With initial tab and URL state
 * ```tsx
 * <ArtifactOperationsModal
 *   artifact={selectedArtifact}
 *   open={isOpen}
 *   onClose={() => setIsOpen(false)}
 *   initialTab="deployments"
 *   onTabChange={(tab) => updateUrlState(tab)}
 *   returnTo="/collection?artifact=skill:canvas"
 * />
 * ```
 */

'use client';

import * as React from 'react';
import { useState, useEffect, useMemo } from 'react';
import { useRouter } from 'next/navigation';
import {
  Activity,
  Info,
  FileText,
  RefreshCcw,
  Rocket,
  History,
  GitBranch,
  Calendar,
  Tag,
  User,
  RotateCcw,
  Loader2,
  FolderOpen,
  Github,
  ExternalLink,
  MoreVertical,
  Trash2,
  Plus,
  Blocks,
  Link2,
} from 'lucide-react';
import { useQuery, useQueries, useQueryClient } from '@tanstack/react-query';
import { Dialog, DialogContent } from '@/components/ui/dialog';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { ScrollArea } from '@/components/ui/scroll-area';
import { cn } from '@/lib/utils';

// Shared components
import { BaseArtifactModal } from '@/components/shared/base-artifact-modal';
import { TabContentWrapper } from '@/components/shared/tab-content-wrapper';
import { CrossNavigationButtons } from '@/components/shared/cross-navigation-buttons';
import { HealthIndicator } from '@/components/shared/health-indicator';
import { StatusBadge } from '@/components/shared/status-badge';
import { DeploymentBadgeStack } from '@/components/shared/deployment-badge-stack';
import type { Tab } from '@/components/shared/tab-navigation';

// Entity components (reused)
import { PluginMembersTab } from '@/components/entity/plugin-members-tab';
import {
  LinkedArtifactsSection,
  type LinkedArtifactReference,
} from '@/components/entity/linked-artifacts-section';
import { ArtifactLinkingDialog } from '@/components/entity';
import { FileTree } from '@/components/entity/file-tree';
import { ContentPane } from '@/components/entity/content-pane';
import { SyncStatusTab } from '@/components/sync-status';
import { DeploymentCard, DeploymentCardSkeleton } from '@/components/deployments/deployment-card';
import { DeployButton } from '@/components/shared/deploy-button';
import { ModalCollectionsTab } from '@/components/entity/modal-collections-tab';
import { ProjectSelectorForDiff } from '@/components/entity/project-selector-for-diff';
import { TagSelectorPopover } from '@/components/collection/tag-selector-popover';
import { getTagColor } from '@/lib/utils/tag-colors';
import { Badge } from '@/components/ui/badge';

// Types
import type { Artifact, ArtifactType } from '@/types/artifact';
import type { FileListResponse, FileContentResponse } from '@/types/files';
import type { ArtifactDeploymentInfo } from '@/types/deployments';
import type { Deployment } from '@/components/deployments/deployment-card';

// Hooks and API
import {
  useToast,
  deploymentKeys,
  useProjects,
  useEntityLifecycle,
  useSources,
  useTags,
  useArtifactAssociations,
} from '@/hooks';
import { apiRequest } from '@/lib/api';
import { listDeployments, removeProjectDeployment } from '@/lib/api/deployments';
import { hasValidUpstreamSource } from '@/lib/sync-utils';

// ============================================================================
// Types
// ============================================================================

interface OperationsLinkedArtifactsResponse {
  linked_artifacts: LinkedArtifactReference[];
  unlinked_references: string[];
}

export type OperationsModalTab =
  | 'status'
  | 'overview'
  | 'plugin'
  | 'contents'
  | 'links'
  | 'sync'
  | 'deployments'
  | 'collections'
  | 'sources'
  | 'history';

export interface ArtifactOperationsModalProps {
  /** The artifact to display in the modal */
  artifact: Artifact | null;
  /** Whether the modal is open */
  open: boolean;
  /** Handler for closing the modal */
  onClose: () => void;
  /** Initial tab to display (defaults to 'status') */
  initialTab?: OperationsModalTab;
  /** Callback when tab changes (for URL state sync) */
  onTabChange?: (tab: OperationsModalTab) => void;
  /** URL to return to if navigated from another page */
  returnTo?: string;
  /** Whether artifact data is currently loading */
  isLoading?: boolean;
  /** Handler for delete action from modal header */
  onDelete?: () => void;
}

// ============================================================================
// Skeleton Components
// ============================================================================

/**
 * OperationsModalHeaderSkeleton - Loading skeleton for operations modal header
 */
function OperationsModalHeaderSkeleton() {
  return (
    <div className="flex items-start justify-between gap-4 border-b px-6 py-4">
      <div className="flex items-center gap-3">
        <Skeleton className="h-10 w-10 rounded-lg" />
        <div className="space-y-2">
          <Skeleton className="h-5 w-48" />
          <Skeleton className="h-4 w-64" />
        </div>
      </div>
      <div className="flex items-center gap-2">
        <Skeleton className="h-6 w-6 rounded-full" />
        <Skeleton className="h-6 w-16 rounded-full" />
        <Skeleton className="h-9 w-9 rounded-md" />
        <Skeleton className="h-9 w-24 rounded-md" />
      </div>
    </div>
  );
}

/**
 * StatusTabSkeleton - Loading skeleton for status tab content
 */
function StatusTabSkeleton() {
  return (
    <div className="grid gap-6 p-6 md:grid-cols-2">
      <div className="rounded-lg border p-4">
        <Skeleton className="mb-4 h-5 w-32" />
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <Skeleton className="h-4 w-24" />
            <Skeleton className="h-6 w-6 rounded-full" />
          </div>
          <div className="flex items-center justify-between">
            <Skeleton className="h-4 w-20" />
            <Skeleton className="h-6 w-16 rounded-full" />
          </div>
        </div>
      </div>
      <div className="rounded-lg border p-4">
        <Skeleton className="mb-4 h-5 w-32" />
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <Skeleton className="h-4 w-20" />
            <Skeleton className="h-4 w-16" />
          </div>
          <div className="flex items-center justify-between">
            <Skeleton className="h-4 w-28" />
            <Skeleton className="h-5 w-20 rounded-md" />
          </div>
        </div>
      </div>
      <div className="rounded-lg border p-4 md:col-span-2">
        <Skeleton className="mb-4 h-5 w-36" />
        <div className="flex gap-2">
          <Skeleton className="h-6 w-28 rounded-full" />
          <Skeleton className="h-6 w-24 rounded-full" />
        </div>
        <div className="mt-4 flex justify-end">
          <Skeleton className="h-9 w-36 rounded-md" />
        </div>
      </div>
      <div className="rounded-lg border p-4 md:col-span-2">
        <Skeleton className="mb-4 h-5 w-28" />
        <div className="flex flex-wrap gap-2">
          <Skeleton className="h-9 w-40 rounded-md" />
          <Skeleton className="h-9 w-44 rounded-md" />
          <Skeleton className="h-9 w-28 rounded-md" />
        </div>
      </div>
    </div>
  );
}

interface HistoryEntry {
  id: string;
  type: 'deploy' | 'sync' | 'rollback' | 'update';
  direction: 'upstream' | 'downstream';
  timestamp: string;
  version?: string;
  filesChanged?: number;
  user?: string;
}

// ============================================================================
// Tab Configuration
// ============================================================================

const PLUGIN_TAB: Tab = {
  value: 'plugin',
  label: 'Plugin Members',
  icon: Blocks,
};

function getTabs(artifact: Artifact | null): Tab[] {
  const deploymentCount = artifact?.deployments?.length || 0;
  const collectionsCount = artifact?.collections?.length || 0;
  const isComposite = artifact?.type === 'composite';

  const baseTabs: Tab[] = [
    { value: 'status', label: 'Status', icon: Activity },
    { value: 'overview', label: 'Overview', icon: Info },
    { value: 'contents', label: 'Contents', icon: FileText },
    { value: 'links', label: 'Links', icon: Link2 },
    { value: 'sync', label: 'Sync Status', icon: RefreshCcw },
    {
      value: 'deployments',
      label: 'Deployments',
      icon: Rocket,
      badge: deploymentCount > 0 ? deploymentCount : undefined,
    },
    {
      value: 'collections',
      label: 'Collections',
      icon: FolderOpen,
      badge: collectionsCount > 0 ? collectionsCount : undefined,
    },
    { value: 'sources', label: 'Sources', icon: Github },
    { value: 'history', label: 'Version History', icon: History },
  ];

  if (!isComposite) return baseTabs;

  // Insert Plugin Members tab after Overview (index 2, after status and overview)
  return [baseTabs[0]!, baseTabs[1]!, PLUGIN_TAB, ...baseTabs.slice(2)];
}

// ============================================================================
// Helper Functions
// ============================================================================

/**
 * Generate mock history entries based on artifact metadata
 */
function generateMockHistory(artifact: Artifact): HistoryEntry[] {
  const history: HistoryEntry[] = [];

  if (artifact.deployedAt) {
    history.push({
      id: `deploy-${artifact.deployedAt}`,
      type: 'deploy',
      direction: 'downstream',
      timestamp: artifact.deployedAt,
      version: artifact.version,
      filesChanged: Math.floor(Math.random() * 5) + 1,
      user: 'You',
    });
  }

  if (artifact.modifiedAt && artifact.modifiedAt !== artifact.deployedAt) {
    history.push({
      id: `sync-${artifact.modifiedAt}`,
      type: 'sync',
      direction: 'upstream',
      timestamp: artifact.modifiedAt,
      version: artifact.version,
      filesChanged: Math.floor(Math.random() * 4) + 1,
      user: 'You',
    });
  }

  if (artifact.upstream?.lastChecked) {
    history.push({
      id: `update-${artifact.upstream.lastChecked}`,
      type: 'update',
      direction: 'upstream',
      timestamp: artifact.upstream.lastChecked,
      version: artifact.upstream.version,
      user: 'System',
    });
  }

  return history.sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime());
}

/**
 * Format relative time for display
 */
function formatRelativeTime(date: Date): string {
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
}

/**
 * Get history entry type icon
 */
function getHistoryTypeIcon(type: HistoryEntry['type']) {
  switch (type) {
    case 'deploy':
      return Rocket;
    case 'sync':
      return RefreshCcw;
    case 'rollback':
      return RotateCcw;
    case 'update':
      return GitBranch;
    default:
      return History;
  }
}

/**
 * Get history entry type color
 */
function getHistoryTypeColor(type: HistoryEntry['type']) {
  switch (type) {
    case 'deploy':
      return 'text-green-600 dark:text-green-400';
    case 'sync':
      return 'text-blue-600 dark:text-blue-400';
    case 'rollback':
      return 'text-orange-600 dark:text-orange-400';
    case 'update':
      return 'text-purple-600 dark:text-purple-400';
    default:
      return 'text-gray-600 dark:text-gray-400';
  }
}

// ============================================================================
// Component
// ============================================================================

/**
 * ArtifactOperationsModal - Operations-focused modal for manage page
 *
 * Uses BaseArtifactModal for consistent dialog structure, header with
 * artifact icon, and tab navigation. Provides operations-specific
 * tab content including status, sync, deployments, and history.
 *
 * @param artifact - The artifact to display
 * @param open - Whether the modal is open
 * @param onClose - Handler for closing the modal
 * @param initialTab - Initial tab to display (defaults to 'status')
 * @param onTabChange - Callback when tab changes
 * @param returnTo - URL to return to if navigated from another page
 */
export function ArtifactOperationsModal({
  artifact,
  open,
  onClose,
  initialTab = 'status',
  onTabChange,
  returnTo,
  isLoading = false,
  onDelete,
}: ArtifactOperationsModalProps) {
  const router = useRouter();
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const { syncEntity, refetch } = useEntityLifecycle();

  // State
  const [activeTab, setActiveTab] = useState<OperationsModalTab>(initialTab);
  const [selectedPath, setSelectedPath] = useState<string | null>(null);
  const [isSyncing, setIsSyncing] = useState(false);
  const [selectedProjectForDiff, setSelectedProjectForDiff] = useState<string | null>(null);
  const [showLinkingDialog, setShowLinkingDialog] = useState(false);
  const [sourceEntry, setSourceEntry] = useState<{
    sourceId: string;
    entryPath: string;
    sourceName: string;
  } | null>(null);
  const [isLoadingSource, setIsLoadingSource] = useState(false);

  // Sync activeTab with initialTab when modal opens
  useEffect(() => {
    if (open && initialTab) {
      setActiveTab(initialTab);
    }
  }, [open, initialTab]);

  // Reset selectedPath when artifact changes or modal closes
  useEffect(() => {
    setSelectedPath(null);
  }, [artifact?.id, open]);

  // Reset selectedProjectForDiff when artifact changes or modal closes
  useEffect(() => {
    setSelectedProjectForDiff(null);
  }, [artifact?.id, open]);

  // Auto-detect project for diff when artifact has deployments
  const deployments = artifact?.deployments;
  useEffect(() => {
    if (!selectedProjectForDiff && deployments && deployments.length > 0) {
      const firstProjectPath = deployments[0]?.project_path;
      if (firstProjectPath) {
        setSelectedProjectForDiff(firstProjectPath);
      }
    }
  }, [selectedProjectForDiff, deployments]);

  // ========================================================================
  // Queries
  // ========================================================================

  // Fetch file list from API
  const {
    data: filesData,
    isLoading: isFilesLoading,
    error: filesError,
  } = useQuery<FileListResponse>({
    queryKey: ['artifact-files', artifact?.id],
    queryFn: async () => {
      if (!artifact?.id) {
        throw new Error('Missing artifact ID');
      }
      const params = new URLSearchParams();
      if (artifact.collection) {
        params.set('collection', artifact.collection);
      }
      return await apiRequest<FileListResponse>(
        `/artifacts/${encodeURIComponent(artifact.id)}/files?${params.toString()}`
      );
    },
    enabled: !!artifact?.id && activeTab === 'contents',
    staleTime: 5 * 60 * 1000,
  });

  // Fetch file content when a file is selected
  const {
    data: contentData,
    isLoading: isContentLoading,
    error: contentError,
  } = useQuery<FileContentResponse>({
    queryKey: ['artifact-file-content', artifact?.id, selectedPath],
    queryFn: async () => {
      if (!artifact?.id || !selectedPath) {
        throw new Error('Missing artifact ID or file path');
      }
      const params = new URLSearchParams();
      if (artifact.collection) {
        params.set('collection', artifact.collection);
      }
      return await apiRequest<FileContentResponse>(
        `/artifacts/${encodeURIComponent(artifact.id)}/files/${encodeURIComponent(selectedPath)}?${params.toString()}`
      );
    },
    enabled: !!artifact?.id && !!selectedPath,
    staleTime: 5 * 60 * 1000,
  });

  // Fetch projects for deployments
  const { data: projects, isLoading: isProjectsLoading } = useProjects();

  // Fetch deployments for all registered projects
  const deploymentQueries = useQueries({
    queries: (projects || []).map((project) => ({
      queryKey: deploymentKeys.list(project.path),
      queryFn: () => listDeployments(project.path),
      staleTime: 2 * 60 * 1000,
      enabled: !!projects && projects.length > 0,
    })),
  });

  const isDeploymentsLoading = isProjectsLoading || deploymentQueries.some((q) => q.isLoading);

  const allDeployments = useMemo((): ArtifactDeploymentInfo[] => {
    if (!projects || projects.length === 0) return [];
    const combined: ArtifactDeploymentInfo[] = [];
    deploymentQueries.forEach((query) => {
      if (query.data?.deployments) {
        combined.push(...query.data.deployments);
      }
    });
    return combined;
  }, [deploymentQueries, projects]);

  const artifactDeployments = useMemo(() => {
    if (!allDeployments || allDeployments.length === 0 || !artifact) return [];
    const filtered = allDeployments.filter(
      (d) => d.artifact_name === artifact.name && d.artifact_type === artifact.type
    );
    return filtered.map((d): Deployment => {
      let status: 'current' | 'outdated' | 'error' = 'current';
      if (d.sync_status === 'outdated' || d.sync_status === 'modified') {
        status = 'outdated';
      }
      return {
        ...d,
        id: `${d.project_path}::${d.artifact_path}`,
        status,
        latest_version: artifact.version,
        deployed_version: d.collection_sha?.substring(0, 7),
      };
    });
  }, [allDeployments, artifact]);

  const historyEntries = useMemo(() => {
    if (!artifact) return [];
    return generateMockHistory(artifact);
  }, [artifact]);

  // Derive collection ID for association queries (mirrors pattern from ArtifactDetailsModal)
  const collectionId = artifact?.collections?.[0]?.id ?? artifact?.collection ?? 'default';

  // Fetch linked artifacts (manual links)
  const {
    data: linkedArtifactsData,
    isLoading: isLinkedArtifactsLoading,
    error: linkedArtifactsError,
    refetch: refetchLinkedArtifacts,
  } = useQuery({
    queryKey: ['linked-artifacts', artifact?.id],
    queryFn: async () => {
      if (!artifact?.id) throw new Error('Missing artifact ID');
      const params = new URLSearchParams();
      if (artifact.collection) params.set('collection', artifact.collection);
      return await apiRequest<OperationsLinkedArtifactsResponse>(
        `/artifacts/${encodeURIComponent(artifact.id)}/linked-artifacts?${params.toString()}`
      );
    },
    enabled: !!artifact?.id && activeTab === 'links',
    staleTime: 2 * 60 * 1000,
    gcTime: 10 * 60 * 1000,
  });

  // Fetch parent composite associations
  const {
    data: associationsData,
    isLoading: isAssociationsLoading,
  } = useArtifactAssociations(artifact?.id ?? '', collectionId);

  const handleLinkChange = () => {
    void refetchLinkedArtifacts();
    queryClient.invalidateQueries({ queryKey: ['artifacts'] });
  };

  // Fetch marketplace sources for Sources tab
  const { data: sourcesData } = useSources(100);

  // Fetch tags (for loading state display, TagSelectorPopover handles its own data)
  const { isLoading: isTagsLoading } = useTags(100);

  // ========================================================================
  // Handlers
  // ========================================================================

  // Find source catalog entry when Sources tab is active
  useEffect(() => {
    if (!artifact?.source || !open || activeTab !== 'sources') {
      return;
    }

    const findSourceEntry = async () => {
      setIsLoadingSource(true);
      try {
        const allSources = sourcesData?.pages?.flatMap((page) => page.items) || [];
        const artifactSource = artifact.source || '';

        for (const source of allSources) {
          const repoPattern = `${source.owner}/${source.repo_name}`;
          if (artifactSource.includes(repoPattern) || artifactSource.includes(source.repo_url)) {
            try {
              const catalogResponse = await apiRequest<{
                items: Array<{ name: string; artifact_type: string; path: string }>;
              }>(
                `/marketplace/sources/${source.id}/artifacts?search=${encodeURIComponent(artifact.name)}&limit=10`
              );

              const entry = catalogResponse.items?.find(
                (e) => e.name === artifact.name && e.artifact_type === artifact.type
              );

              if (entry) {
                setSourceEntry({
                  sourceId: source.id,
                  entryPath: entry.path,
                  sourceName: `${source.owner}/${source.repo_name}`,
                });
                setIsLoadingSource(false);
                return;
              }
            } catch {
              // Continue to next source
            }
          }
        }

        setSourceEntry(null);
      } catch (error) {
        console.error('Failed to find source entry:', error);
        setSourceEntry(null);
      } finally {
        setIsLoadingSource(false);
      }
    };

    findSourceEntry();
  }, [artifact, open, activeTab, sourcesData]);

  const handleTabChange = (tab: string) => {
    const typedTab = tab as OperationsModalTab;
    setActiveTab(typedTab);
    onTabChange?.(typedTab);
  };

  const handleFileSelect = (path: string) => {
    setSelectedPath(path);
  };

  const handleSyncAll = async () => {
    if (!artifact) return;

    setIsSyncing(true);
    try {
      for (const deployment of artifactDeployments) {
        if (deployment.project_path) {
          await syncEntity(artifact.id, deployment.project_path);
        }
      }
      toast({
        title: 'Sync Complete',
        description: `Synced ${artifact.name} to all ${artifactDeployments.length} deployments.`,
      });
      refetch();
    } catch (error) {
      console.error('Sync failed:', error);
      toast({
        title: 'Sync Failed',
        description: error instanceof Error ? error.message : 'Failed to sync artifact',
        variant: 'destructive',
      });
    } finally {
      setIsSyncing(false);
    }
  };

  const encodeProjectId = (projectPath: string): string => btoa(projectPath);

  const handleDeploymentRemove = async (deployment: Deployment, removeFiles: boolean) => {
    if (!artifact) return;

    try {
      const projectId = encodeProjectId(deployment.project_path);
      await removeProjectDeployment(
        projectId,
        deployment.artifact_name,
        deployment.artifact_type,
        removeFiles
      );
      await queryClient.invalidateQueries({
        queryKey: deploymentKeys.list(deployment.project_path),
      });
      toast({
        title: 'Deployment Removed',
        description: `Successfully removed "${deployment.artifact_name}" from project`,
      });
    } catch (error) {
      console.error('Failed to remove deployment:', error);
      toast({
        title: 'Removal Failed',
        description: error instanceof Error ? error.message : 'Failed to remove deployment',
        variant: 'destructive',
      });
    }
  };

  const handleReturn = () => {
    if (returnTo) {
      onClose();
      router.push(returnTo);
    }
  };

  // ========================================================================
  // Render
  // ========================================================================

  // Early return if no artifact and not loading
  if (!artifact && !isLoading) {
    return null;
  }

  // Show loading skeleton when modal is open but artifact is loading
  if (isLoading || !artifact) {
    const defaultTabs = getTabs(null);
    return (
      <Dialog open={open} onOpenChange={(isOpen) => !isOpen && onClose()}>
        <DialogContent className="flex h-[90vh] max-h-[90vh] min-h-0 max-w-5xl flex-col overflow-hidden p-0 lg:max-w-6xl">
          <OperationsModalHeaderSkeleton />
          <div className="border-b px-6">
            <div className="flex gap-2 py-2">
              {defaultTabs.map((tab) => (
                <Skeleton key={tab.value} className="h-8 w-24 rounded-md" />
              ))}
            </div>
          </div>
          <StatusTabSkeleton />
        </DialogContent>
      </Dialog>
    );
  }

  // Header actions for BaseArtifactModal
  const headerActions = (
    <div className="flex items-center gap-2">
      <HealthIndicator artifact={artifact} size="lg" />
      <StatusBadge status={artifact.syncStatus} size="md" />
      <CrossNavigationButtons
        currentPage="manage"
        artifactId={artifact.id}
        collectionId={artifact.collection}
        onNavigate={onClose}
      />
      <Button
        variant="default"
        size="sm"
        onClick={handleSyncAll}
        disabled={isSyncing || artifactDeployments.length === 0}
        className="gap-2"
      >
        {isSyncing ? (
          <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
        ) : (
          <RefreshCcw className="h-4 w-4" aria-hidden="true" />
        )}
        Sync All
      </Button>
      {onDelete && (
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button
              variant="ghost"
              size="icon"
              className="h-8 w-8"
              aria-label={`Actions for ${artifact.name}`}
            >
              <MoreVertical className="h-4 w-4" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuItem
              className="text-destructive focus:text-destructive"
              onClick={onDelete}
            >
              <Trash2 className="mr-2 h-4 w-4" />
              Delete Artifact
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      )}
    </div>
  );

  return (
    <>
    <BaseArtifactModal
      artifact={artifact}
      open={open}
      onClose={onClose}
      activeTab={activeTab}
      onTabChange={handleTabChange}
      tabs={getTabs(artifact)}
      headerActions={headerActions}
      returnTo={returnTo}
      onReturn={handleReturn}
    >
      {/* Status Tab (Default) */}
      <TabContentWrapper value="status">
        <div className="grid gap-6 md:grid-cols-2">
          {/* Health Summary Card */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                <Activity className="h-4 w-4" aria-hidden="true" />
                Health Summary
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">Overall Health</span>
                <HealthIndicator artifact={artifact} size="lg" showTooltip />
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">Sync Status</span>
                <StatusBadge status={artifact.syncStatus} size="md" />
              </div>
              {artifact.upstream?.updateAvailable && (
                <Alert>
                  <GitBranch className="h-4 w-4" />
                  <AlertDescription>A newer version is available upstream.</AlertDescription>
                </Alert>
              )}
            </CardContent>
          </Card>

          {/* Sync Summary Card */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                <RefreshCcw className="h-4 w-4" aria-hidden="true" />
                Sync Summary
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">Last Synced</span>
                <span className="text-sm">
                  {artifact.upstream?.lastChecked
                    ? formatRelativeTime(new Date(artifact.upstream.lastChecked))
                    : 'Never'}
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">Current Version</span>
                <code className="rounded bg-muted px-2 py-1 text-xs">
                  {artifact.version || 'unknown'}
                </code>
              </div>
              {artifact.upstream?.version && (
                <div className="flex items-center justify-between">
                  <span className="text-sm text-muted-foreground">Upstream Version</span>
                  <code className="rounded bg-muted px-2 py-1 text-xs">
                    {artifact.upstream.version}
                  </code>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Deployments Summary Card */}
          <Card className="md:col-span-2">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                <Rocket className="h-4 w-4" aria-hidden="true" />
                Deployments ({artifactDeployments.length})
              </CardTitle>
            </CardHeader>
            <CardContent>
              {artifactDeployments.length > 0 ? (
                <DeploymentBadgeStack deployments={artifact.deployments || []} maxBadges={5} />
              ) : (
                <p className="text-sm text-muted-foreground">Not deployed to any projects yet.</p>
              )}
              <div className="mt-4 flex justify-end">
                <DeployButton
                  artifact={artifact}
                  existingDeploymentPaths={artifactDeployments.map(
                    (d) => `${d.project_path}/${d.artifact_path}`
                  )}
                  onDeploySuccess={() => {
                    projects?.forEach((p) => {
                      queryClient.invalidateQueries({ queryKey: deploymentKeys.list(p.path) });
                    });
                  }}
                  variant="outline"
                  size="sm"
                  label="Deploy to Project"
                />
              </div>
            </CardContent>
          </Card>

          {/* Quick Actions Card */}
          <Card className="md:col-span-2">
            <CardHeader>
              <CardTitle className="text-base">Quick Actions</CardTitle>
            </CardHeader>
            <CardContent className="flex flex-wrap gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={handleSyncAll}
                disabled={isSyncing || artifactDeployments.length === 0}
              >
                {isSyncing ? (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                ) : (
                  <RefreshCcw className="mr-2 h-4 w-4" />
                )}
                Sync All Deployments
              </Button>
              <DeployButton
                artifact={artifact}
                existingDeploymentPaths={artifactDeployments.map(
                  (d) => `${d.project_path}/${d.artifact_path}`
                )}
                onDeploySuccess={() => {
                  projects?.forEach((p) => {
                    queryClient.invalidateQueries({ queryKey: deploymentKeys.list(p.path) });
                  });
                }}
                variant="outline"
                size="sm"
              />
              <Button variant="outline" size="sm" onClick={() => handleTabChange('history')}>
                <History className="mr-2 h-4 w-4" />
                View History
              </Button>
            </CardContent>
          </Card>
        </div>
      </TabContentWrapper>

      {/* Overview Tab */}
      <TabContentWrapper value="overview">
        <div className="space-y-6">
          {artifact.description && (
            <div>
              <h3 className="mb-2 text-sm font-medium">Description</h3>
              <p className="text-sm text-muted-foreground">{artifact.description}</p>
            </div>
          )}

          <div>
            <h3 className="mb-2 flex items-center gap-2 text-sm font-medium">
              <GitBranch className="h-4 w-4" aria-hidden="true" />
              Source
            </h3>
            <p className="rounded bg-muted px-3 py-2 font-mono text-sm">
              {artifact.source || 'Local'}
            </p>
          </div>

          {artifact.version && (
            <div>
              <h3 className="mb-2 text-sm font-medium">Version</h3>
              <p className="text-sm text-muted-foreground">{artifact.version}</p>
            </div>
          )}

          {artifact.author && (
            <div>
              <h3 className="mb-2 flex items-center gap-2 text-sm font-medium">
                <User className="h-4 w-4" aria-hidden="true" />
                Author
              </h3>
              <p className="text-sm text-muted-foreground">{artifact.author}</p>
            </div>
          )}

          <div>
            <h3 className="mb-2 flex items-center gap-2 text-sm font-medium">
              <Tag className="h-4 w-4" aria-hidden="true" />
              Tags
            </h3>
            {isTagsLoading ? (
              <div className="flex items-center gap-1">
                <div className="h-5 w-16 animate-pulse rounded-md bg-muted" />
                <div className="h-5 w-12 animate-pulse rounded-md bg-muted" />
              </div>
            ) : (
              <div className="flex flex-wrap items-center gap-1.5">
                {[...(artifact.tags ?? [])].sort((a, b) => a.localeCompare(b)).map((tag) => (
                  <Badge key={tag} colorStyle={getTagColor(tag)} className="text-xs">
                    {tag}
                  </Badge>
                ))}
                <TagSelectorPopover
                  artifactId={artifact.id}
                  trigger={
                    <Button variant="outline" size="sm" className="h-6 w-6 rounded-full p-0">
                      <Plus className="h-3 w-3" />
                    </Button>
                  }
                />
              </div>
            )}
          </div>

          <div>
            <h3 className="mb-2 flex items-center gap-2 text-sm font-medium">
              <Calendar className="h-4 w-4" aria-hidden="true" />
              Timestamps
            </h3>
            <div className="space-y-2 text-sm text-muted-foreground">
              {artifact.createdAt && (
                <div className="flex justify-between">
                  <span>Created:</span>
                  <span>{new Date(artifact.createdAt).toLocaleString()}</span>
                </div>
              )}
              {artifact.updatedAt && (
                <div className="flex justify-between">
                  <span>Updated:</span>
                  <span>{new Date(artifact.updatedAt).toLocaleString()}</span>
                </div>
              )}
              {artifact.deployedAt && (
                <div className="flex justify-between">
                  <span>Deployed:</span>
                  <span>{new Date(artifact.deployedAt).toLocaleString()}</span>
                </div>
              )}
            </div>
          </div>
        </div>
      </TabContentWrapper>

      {/* Plugin Members Tab — only rendered for composite artifacts */}
      {artifact.type === 'composite' && (
        <TabContentWrapper value="plugin">
          <PluginMembersTab
            compositeId={artifact.id}
            collectionId={artifact.collections?.[0]?.id ?? artifact.collection ?? 'default'}
            disabled={false}
          />
        </TabContentWrapper>
      )}

      {/* Contents Tab */}
      <TabContentWrapper value="contents" scrollable={false}>
        <div className="flex h-[calc(90vh-16rem)] min-h-0 gap-4">
          <div className="w-64 flex-shrink-0 overflow-hidden rounded-lg border">
            <div className="flex-shrink-0 border-b bg-muted/30 px-3 py-2">
              <p className="text-sm font-medium">Files</p>
            </div>
            <ScrollArea className="h-[calc(100%-2.5rem)]">
              {isFilesLoading ? (
                <div className="space-y-2 p-3">
                  <Skeleton className="h-4 w-full" />
                  <Skeleton className="h-4 w-3/4" />
                  <Skeleton className="h-4 w-1/2" />
                </div>
              ) : filesError ? (
                <div className="p-3 text-sm text-destructive">Failed to load files</div>
              ) : (
                <FileTree
                  entityId={artifact.id}
                  files={filesData?.files || []}
                  selectedPath={selectedPath}
                  onSelect={handleFileSelect}
                  readOnly
                />
              )}
            </ScrollArea>
          </div>

          <div className="min-w-0 flex-1 overflow-hidden rounded-lg border">
            <ContentPane
              path={selectedPath}
              content={contentData?.content ?? null}
              isLoading={isContentLoading}
              error={contentError instanceof Error ? contentError.message : null}
              readOnly
            />
          </div>
        </div>
      </TabContentWrapper>

      {/* Links Tab */}
      <TabContentWrapper value="links">
        <div className="space-y-8">
          {/* Parent Composites Section — shown when artifact belongs to one or more plugins */}
          {(isAssociationsLoading || (associationsData?.parents && associationsData.parents.length > 0)) && (
            <section aria-labelledby="ops-parent-composites-heading">
              <div className="mb-3 flex items-center gap-2">
                <Blocks className="h-4 w-4 text-muted-foreground" aria-hidden="true" />
                <h3 id="ops-parent-composites-heading" className="text-sm font-medium">
                  Member of Plugin
                  {!isAssociationsLoading && associationsData?.parents && associationsData.parents.length > 0 && (
                    <span className="ml-2 text-sm font-normal text-muted-foreground">
                      ({associationsData.parents.length})
                    </span>
                  )}
                </h3>
              </div>

              {isAssociationsLoading ? (
                <div
                  className="grid gap-3 sm:grid-cols-2"
                  aria-busy="true"
                  aria-label="Loading parent plugins"
                >
                  {[1, 2].map((i) => (
                    <div key={i} className="animate-pulse rounded-lg border p-4">
                      <div className="flex items-center gap-3">
                        <div className="h-8 w-8 rounded-md bg-muted" />
                        <div className="flex-1 space-y-2">
                          <div className="h-4 w-32 rounded bg-muted" />
                          <div className="h-3 w-20 rounded bg-muted" />
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div
                  className="grid gap-3 sm:grid-cols-2"
                  role="list"
                  aria-label="Parent plugin artifacts"
                >
                  {associationsData!.parents.map((parent) => (
                    <div
                      key={parent.artifact_id}
                      className="group rounded-lg border p-4 transition-colors hover:bg-muted/50"
                      role="listitem"
                    >
                      <div className="flex items-center gap-3">
                        <div className="flex h-8 w-8 items-center justify-center rounded-md bg-primary/10">
                          <Blocks className="h-4 w-4 text-primary" aria-hidden="true" />
                        </div>
                        <div className="min-w-0 flex-1">
                          <p className="truncate text-sm font-medium">
                            {parent.artifact_name}
                          </p>
                          <div className="mt-0.5 flex items-center gap-1.5">
                            <Badge variant="secondary" className="text-xs">
                              {parent.artifact_type}
                            </Badge>
                            <Badge variant="outline" className="text-xs">
                              {parent.relationship_type}
                            </Badge>
                          </div>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </section>
          )}

          {/* Linked Artifacts Section */}
          <LinkedArtifactsSection
            artifactId={artifact.id}
            linkedArtifacts={linkedArtifactsData?.linked_artifacts || []}
            unlinkedReferences={linkedArtifactsData?.unlinked_references || []}
            onLinkCreated={handleLinkChange}
            onLinkDeleted={handleLinkChange}
            onAddLinkClick={() => setShowLinkingDialog(true)}
            isLoading={isLinkedArtifactsLoading}
            error={
              linkedArtifactsError instanceof Error
                ? linkedArtifactsError.message
                : linkedArtifactsError
                  ? 'Failed to load linked artifacts'
                  : null
            }
            onRetry={() => void refetchLinkedArtifacts()}
          />
        </div>
      </TabContentWrapper>

      {/* Sync Status Tab */}
      <TabContentWrapper value="sync" scrollable={false}>
        <div className="flex h-[calc(90vh-16rem)] flex-col gap-4 overflow-hidden">
          {artifact.collection && (
            <div className="flex-shrink-0">
              <ProjectSelectorForDiff
                entityId={artifact.id}
                entityName={artifact.name}
                entityType={artifact.type as ArtifactType}
                collection={artifact.collection}
                onProjectSelected={(path) => setSelectedProjectForDiff(path)}
              />
            </div>
          )}
          <div className="min-h-0 flex-1 overflow-hidden">
            <SyncStatusTab
              entity={artifact}
              mode="collection"
              projectPath={selectedProjectForDiff || undefined}
              onClose={onClose}
            />
          </div>
        </div>
      </TabContentWrapper>

      {/* Deployments Tab */}
      <TabContentWrapper value="deployments">
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-medium">
              Active Deployments ({artifactDeployments.length})
            </h3>
            <DeployButton
              artifact={artifact}
              existingDeploymentPaths={artifactDeployments.map(
                (d) => `${d.project_path}/${d.artifact_path}`
              )}
              onDeploySuccess={() => {
                projects?.forEach((p) => {
                  queryClient.invalidateQueries({ queryKey: deploymentKeys.list(p.path) });
                });
              }}
              variant="outline"
              size="sm"
            />
          </div>

          {isDeploymentsLoading ? (
            <div className="space-y-3">
              <DeploymentCardSkeleton />
              <DeploymentCardSkeleton />
            </div>
          ) : artifactDeployments.length === 0 ? (
            <Card>
              <CardContent className="flex flex-col items-center justify-center py-8">
                <Rocket className="mb-4 h-12 w-12 text-muted-foreground/50" aria-hidden="true" />
                <p className="text-sm font-medium">No deployments yet</p>
                <p className="mt-1 text-sm text-muted-foreground">
                  Deploy this artifact to a project to get started.
                </p>
                <DeployButton
                  artifact={artifact}
                  onDeploySuccess={() => {
                    projects?.forEach((p) => {
                      queryClient.invalidateQueries({ queryKey: deploymentKeys.list(p.path) });
                    });
                  }}
                  variant="outline"
                  size="sm"
                  label="Deploy Now"
                  className="mt-4"
                />
              </CardContent>
            </Card>
          ) : (
            <div className="space-y-3">
              {artifactDeployments.map((deployment) => (
                <DeploymentCard
                  key={deployment.id}
                  deployment={deployment}
                  projects={projects}
                  projectPath={deployment.project_path}
                  onUpdate={() => {
                    if (deployment.project_path) {
                      syncEntity(artifact.id, deployment.project_path);
                    }
                  }}
                  onRemove={(removeFiles) => handleDeploymentRemove(deployment, removeFiles)}
                />
              ))}
            </div>
          )}
        </div>
      </TabContentWrapper>

      {/* Collections Tab */}
      <TabContentWrapper value="collections">
        <ModalCollectionsTab artifact={artifact} context="operations" />
      </TabContentWrapper>

      {/* Sources Tab */}
      <TabContentWrapper value="sources">
        <div className="space-y-4">
          <div className="text-sm font-medium text-muted-foreground">Imported From</div>

          {isLoadingSource ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" aria-hidden="true" />
              <span className="sr-only">Loading source information</span>
            </div>
          ) : sourceEntry ? (
            <div
              className="cursor-pointer rounded-lg border p-4 transition-colors hover:bg-muted/50"
              onClick={() =>
                router.push(
                  `/marketplace/sources/${sourceEntry.sourceId}?artifact=${encodeURIComponent(sourceEntry.entryPath)}`
                )
              }
            >
              <div className="flex items-center gap-3">
                <Github className="h-5 w-5 text-muted-foreground" aria-hidden="true" />
                <div className="flex-1">
                  <div className="font-medium">{sourceEntry.sourceName}</div>
                  <div className="text-sm text-muted-foreground">{sourceEntry.entryPath}</div>
                  {artifact.version && (
                    <div className="mt-1 flex items-center gap-2 text-sm text-muted-foreground">
                      <Tag className="h-3 w-3" aria-hidden="true" />
                      <span>{artifact.version}</span>
                    </div>
                  )}
                </div>
                <ExternalLink className="h-4 w-4 text-muted-foreground" aria-hidden="true" />
              </div>
            </div>
          ) : hasValidUpstreamSource(artifact) ? (
            <div className="rounded-lg border p-4">
              <div className="flex items-center gap-3">
                <GitBranch className="h-5 w-5 text-muted-foreground" aria-hidden="true" />
                <div className="flex-1">
                  <div className="font-medium">Source</div>
                  <div className="text-sm text-muted-foreground">{artifact.source}</div>
                </div>
              </div>
              <p className="mt-2 text-xs text-muted-foreground">
                Unable to find the source entry in marketplace sources.
              </p>
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center py-8 text-center">
              <GitBranch className="h-12 w-12 text-muted-foreground/50" aria-hidden="true" />
              <p className="mt-4 text-sm text-muted-foreground">
                No upstream source information available.
              </p>
              <p className="mt-1 text-xs text-muted-foreground">
                This artifact was created locally or imported without source tracking.
              </p>
            </div>
          )}
        </div>
      </TabContentWrapper>

      {/* Version History Tab */}
      <TabContentWrapper value="history">
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-medium">Version History</h3>
          </div>

          {historyEntries.length === 0 ? (
            <Card>
              <CardContent className="flex flex-col items-center justify-center py-8">
                <History className="mb-4 h-12 w-12 text-muted-foreground/50" aria-hidden="true" />
                <p className="text-sm font-medium">No history available</p>
                <p className="mt-1 text-sm text-muted-foreground">
                  History will appear after deployments and syncs.
                </p>
              </CardContent>
            </Card>
          ) : (
            <div className="relative space-y-0 border-l-2 border-muted pl-6">
              {historyEntries.map((entry, index) => {
                const Icon = getHistoryTypeIcon(entry.type);
                const colorClass = getHistoryTypeColor(entry.type);

                return (
                  <div key={entry.id} className="relative pb-6 last:pb-0">
                    {/* Timeline dot */}
                    <div
                      className={cn(
                        'absolute -left-[1.625rem] flex h-4 w-4 items-center justify-center rounded-full border-2 bg-background',
                        colorClass.replace('text-', 'border-')
                      )}
                    >
                      <Icon className={cn('h-2.5 w-2.5', colorClass)} aria-hidden="true" />
                    </div>

                    {/* Entry content */}
                    <Card>
                      <CardContent className="p-4">
                        <div className="flex items-start justify-between">
                          <div>
                            <p className={cn('font-medium capitalize', colorClass)}>
                              {entry.type === 'deploy' && 'Deployed'}
                              {entry.type === 'sync' && 'Synced'}
                              {entry.type === 'rollback' && 'Rolled back'}
                              {entry.type === 'update' && 'Update checked'}
                            </p>
                            <p className="mt-1 text-sm text-muted-foreground">
                              {entry.user && `By ${entry.user}`}
                              {entry.filesChanged && ` - ${entry.filesChanged} files changed`}
                            </p>
                          </div>
                          <div className="text-right text-sm text-muted-foreground">
                            <p>{formatRelativeTime(new Date(entry.timestamp))}</p>
                            {entry.version && (
                              <code className="text-xs">{entry.version.substring(0, 7)}</code>
                            )}
                          </div>
                        </div>

                        {/* Rollback button for past versions */}
                        {index > 0 && entry.type === 'deploy' && (
                          <div className="mt-3 flex justify-end">
                            <Button
                              variant="outline"
                              size="sm"
                              className="gap-2"
                              disabled
                              title="Rollback functionality coming soon"
                            >
                              <RotateCcw className="h-3.5 w-3.5" aria-hidden="true" />
                              Rollback to this version
                            </Button>
                          </div>
                        )}
                      </CardContent>
                    </Card>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </TabContentWrapper>
    </BaseArtifactModal>

    {/* Artifact Linking Dialog */}
    <ArtifactLinkingDialog
      open={showLinkingDialog}
      onOpenChange={setShowLinkingDialog}
      artifactId={artifact.id}
      onSuccess={handleLinkChange}
    />
    </>
  );
}
