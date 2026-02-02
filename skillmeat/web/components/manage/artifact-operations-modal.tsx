/**
 * Artifact Operations Modal Component
 *
 * Operations-focused modal for the /manage page, emphasizing health status,
 * sync state, and deployment management. Opens when clicking an artifact
 * on the manage page.
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
import * as LucideIcons from 'lucide-react';
import {
  Activity,
  Info,
  FileText,
  RefreshCcw,
  Rocket,
  History,
  ArrowLeft,
  AlertCircle,
  GitBranch,
  Calendar,
  Tag,
  User,
  RotateCcw,
  Loader2,
} from 'lucide-react';
import { useQuery, useQueries, useQueryClient } from '@tanstack/react-query';
import { Dialog, DialogContent } from '@/components/ui/dialog';
import { Tabs, TabsContent } from '@/components/ui/tabs';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { ScrollArea } from '@/components/ui/scroll-area';
import { cn } from '@/lib/utils';

// Shared components
import { ModalHeader } from '@/components/shared/modal-header';
import { TabNavigation, type Tab } from '@/components/shared/tab-navigation';
import { TabContentWrapper } from '@/components/shared/tab-content-wrapper';
import { CrossNavigationButtons } from '@/components/shared/cross-navigation-buttons';
import { HealthIndicator } from '@/components/shared/health-indicator';
import { StatusBadge } from '@/components/shared/status-badge';
import { DeploymentBadgeStack } from '@/components/shared/deployment-badge-stack';

// Entity components (reused)
import { FileTree } from '@/components/entity/file-tree';
import { ContentPane } from '@/components/entity/content-pane';
import { SyncStatusTab } from '@/components/sync-status';
import { DeploymentCard, DeploymentCardSkeleton } from '@/components/deployments/deployment-card';
import { DeployDialog } from '@/components/collection/deploy-dialog';

// Types
import type { Artifact } from '@/types/artifact';
import { ARTIFACT_TYPES } from '@/types/artifact';
import type { FileListResponse, FileContentResponse } from '@/types/files';
import type { ArtifactDeploymentInfo } from '@/types/deployments';
import type { Deployment } from '@/components/deployments/deployment-card';

// Hooks and API
import {
  useToast,
  deploymentKeys,
  useProjects,
  useEntityLifecycle,
} from '@/hooks';
import { apiRequest } from '@/lib/api';
import { listDeployments, removeProjectDeployment } from '@/lib/api/deployments';

// ============================================================================
// Types
// ============================================================================

export type OperationsModalTab =
  | 'status'
  | 'overview'
  | 'contents'
  | 'sync'
  | 'deployments'
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

function getTabs(artifact: Artifact | null): Tab[] {
  const deploymentCount = artifact?.deployments?.length || 0;

  return [
    { value: 'status', label: 'Status', icon: Activity },
    { value: 'overview', label: 'Overview', icon: Info },
    { value: 'contents', label: 'Contents', icon: FileText },
    { value: 'sync', label: 'Sync Status', icon: RefreshCcw },
    {
      value: 'deployments',
      label: 'Deployments',
      icon: Rocket,
      badge: deploymentCount > 0 ? deploymentCount : undefined,
    },
    { value: 'history', label: 'Version History', icon: History },
  ];
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

  // Sort by timestamp (most recent first)
  return history.sort(
    (a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime()
  );
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
 * Provides comprehensive artifact management with emphasis on:
 * - Health status and sync indicators
 * - Deployment management across projects
 * - Version history with rollback options
 * - Quick sync and deploy actions
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
}: ArtifactOperationsModalProps) {
  const router = useRouter();
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const { syncEntity, refetch } = useEntityLifecycle();

  // State
  const [activeTab, setActiveTab] = useState<OperationsModalTab>(initialTab);
  const [selectedPath, setSelectedPath] = useState<string | null>(null);
  const [isSyncing, setIsSyncing] = useState(false);
  const [showDeployDialog, setShowDeployDialog] = useState(false);

  // Sync activeTab with initialTab when modal opens
  useEffect(() => {
    if (open && initialTab) {
      setActiveTab(initialTab);
    }
  }, [open, initialTab]);

  // Get artifact type config
  const config = artifact ? ARTIFACT_TYPES[artifact.type] : null;
  // Type-safe icon lookup with fallback
  const iconName = config?.icon ?? 'FileText';
  const IconLookup = (LucideIcons as any)[iconName] as
    | React.ComponentType<{ className?: string }>
    | undefined;
  const IconComponent = IconLookup || LucideIcons.FileText;

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

  // Combine deployment results
  const isDeploymentsLoading =
    isProjectsLoading || deploymentQueries.some((q) => q.isLoading);

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

  // Filter deployments by artifact
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

  // Generate history entries
  const historyEntries = useMemo(() => {
    if (!artifact) return [];
    return generateMockHistory(artifact);
  }, [artifact]);

  // Handle tab change
  const handleTabChange = (tab: string) => {
    const typedTab = tab as OperationsModalTab;
    setActiveTab(typedTab);
    onTabChange?.(typedTab);
  };

  // Handle file selection
  const handleFileSelect = (path: string) => {
    setSelectedPath(path);
  };

  // Handle sync all action
  const handleSyncAll = async () => {
    if (!artifact) return;

    setIsSyncing(true);
    try {
      // Sync to all deployments
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

  // Handle deployment remove
  const encodeProjectId = (projectPath: string): string => btoa(projectPath);

  const handleDeploymentRemove = async (
    deployment: Deployment,
    removeFiles: boolean
  ) => {
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

  // Handle return navigation
  const handleReturn = () => {
    if (returnTo) {
      onClose();
      router.push(returnTo);
    }
  };

  // Prepare artifact for deploy dialog
  const artifactForDeploy = useMemo((): Artifact | null => {
    if (!artifact) return null;
    return {
      ...artifact,
      scope: artifact.scope || 'user',
      syncStatus: artifact.syncStatus || 'synced',
      createdAt: artifact.createdAt || new Date().toISOString(),
      updatedAt: artifact.updatedAt || new Date().toISOString(),
    };
  }, [artifact]);

  // Early return if no artifact
  if (!artifact) {
    return null;
  }

  // Fallback for unknown artifact type
  if (!config) {
    return (
      <Dialog open={open} onOpenChange={(isOpen) => !isOpen && onClose()}>
        <DialogContent className="max-w-md">
          <ModalHeader
            icon={AlertCircle}
            iconClassName="text-yellow-500"
            title={artifact.name}
            description={`Artifact type "${artifact.type}" is not supported.`}
          />
          <div className="flex justify-end p-4">
            <Button variant="outline" onClick={onClose}>
              Close
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    );
  }

  return (
    <>
      <Dialog open={open} onOpenChange={(isOpen) => !isOpen && onClose()}>
        <DialogContent className="flex h-[90vh] max-h-[90vh] min-h-0 max-w-5xl flex-col overflow-hidden p-0 lg:max-w-6xl">
          {/* Header */}
          <ModalHeader
            icon={IconComponent}
            iconClassName={config.color}
            title={artifact.name}
            description={artifact.description}
            actions={
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
              </div>
            }
          />

          {/* Return button if returnTo is present */}
          {returnTo && (
            <div className="border-b px-6 py-2">
              <Button
                variant="ghost"
                size="sm"
                onClick={handleReturn}
                className="gap-2 text-muted-foreground hover:text-foreground"
              >
                <ArrowLeft className="h-4 w-4" aria-hidden="true" />
                Return to previous page
              </Button>
            </div>
          )}

          {/* Tabs */}
          <Tabs
            value={activeTab}
            onValueChange={handleTabChange}
            className="flex h-full min-h-0 flex-1 flex-col px-6"
          >
            <TabNavigation tabs={getTabs(artifact)} />

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
                        <AlertDescription>
                          A newer version is available upstream.
                        </AlertDescription>
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
                      <DeploymentBadgeStack
                        deployments={artifact.deployments || []}
                        maxBadges={5}
                      />
                    ) : (
                      <p className="text-sm text-muted-foreground">
                        Not deployed to any projects yet.
                      </p>
                    )}
                    <div className="mt-4 flex justify-end">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => setShowDeployDialog(true)}
                        className="gap-2"
                      >
                        <Rocket className="h-4 w-4" aria-hidden="true" />
                        Deploy to Project
                      </Button>
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
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setShowDeployDialog(true)}
                    >
                      <Rocket className="mr-2 h-4 w-4" />
                      Deploy to New Project
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleTabChange('history')}
                    >
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
                {/* Description */}
                {artifact.description && (
                  <div>
                    <h3 className="mb-2 text-sm font-medium">Description</h3>
                    <p className="text-sm text-muted-foreground">{artifact.description}</p>
                  </div>
                )}

                {/* Source */}
                <div>
                  <h3 className="mb-2 flex items-center gap-2 text-sm font-medium">
                    <GitBranch className="h-4 w-4" aria-hidden="true" />
                    Source
                  </h3>
                  <p className="rounded bg-muted px-3 py-2 font-mono text-sm">
                    {artifact.source || 'Local'}
                  </p>
                </div>

                {/* Version */}
                {artifact.version && (
                  <div>
                    <h3 className="mb-2 text-sm font-medium">Version</h3>
                    <p className="text-sm text-muted-foreground">{artifact.version}</p>
                  </div>
                )}

                {/* Author */}
                {artifact.author && (
                  <div>
                    <h3 className="mb-2 flex items-center gap-2 text-sm font-medium">
                      <User className="h-4 w-4" aria-hidden="true" />
                      Author
                    </h3>
                    <p className="text-sm text-muted-foreground">{artifact.author}</p>
                  </div>
                )}

                {/* Tags */}
                {artifact.tags && artifact.tags.length > 0 && (
                  <div>
                    <h3 className="mb-2 flex items-center gap-2 text-sm font-medium">
                      <Tag className="h-4 w-4" aria-hidden="true" />
                      Tags
                    </h3>
                    <div className="flex flex-wrap gap-2">
                      {artifact.tags.map((tag) => (
                        <Badge key={tag} variant="secondary">
                          {tag}
                        </Badge>
                      ))}
                    </div>
                  </div>
                )}

                {/* Timestamps */}
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

            {/* Contents Tab */}
            <TabsContent
              value="contents"
              className="mt-0 h-full min-h-0 flex-1 overflow-hidden data-[state=active]:flex data-[state=active]:flex-col"
            >
              <div className="flex h-full min-h-0 flex-1 gap-4 py-4">
                {/* File Tree */}
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
                      <div className="p-3 text-sm text-destructive">
                        Failed to load files
                      </div>
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

                {/* Content Pane */}
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
            </TabsContent>

            {/* Sync Status Tab */}
            <TabContentWrapper value="sync" scrollable={false}>
              <SyncStatusTab
                entity={artifact}
                mode="collection"
                onClose={onClose}
              />
            </TabContentWrapper>

            {/* Deployments Tab */}
            <TabContentWrapper value="deployments">
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <h3 className="text-sm font-medium">
                    Active Deployments ({artifactDeployments.length})
                  </h3>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setShowDeployDialog(true)}
                    className="gap-2"
                  >
                    <Rocket className="h-4 w-4" aria-hidden="true" />
                    Add Deployment
                  </Button>
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
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => setShowDeployDialog(true)}
                        className="mt-4 gap-2"
                      >
                        <Rocket className="h-4 w-4" aria-hidden="true" />
                        Deploy Now
                      </Button>
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
                        onRemove={(removeFiles) =>
                          handleDeploymentRemove(deployment, removeFiles)
                        }
                      />
                    ))}
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
          </Tabs>
        </DialogContent>
      </Dialog>

      {/* Deploy Dialog */}
      {artifactForDeploy && (
        <DeployDialog
          artifact={artifactForDeploy}
          isOpen={showDeployDialog}
          onClose={() => setShowDeployDialog(false)}
          existingDeploymentPaths={artifactDeployments.map(
            (d) => `${d.project_path}/${d.artifact_path}`
          )}
        />
      )}
    </>
  );
}
