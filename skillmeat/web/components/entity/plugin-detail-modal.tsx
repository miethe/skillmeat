'use client';

/**
 * PluginDetailModal — Standalone detail modal for composite/plugin artifacts.
 *
 * Extends the BaseArtifactModal pattern with a plugin-specific tab layout:
 *   - Overview: metadata, status, description, source, version, timestamps
 *   - Members: manage plugin members via PluginMembersTab
 *   - Sync: sync status and upstream diff via SyncStatusTab
 *   - Deployments: where this plugin is deployed (DeploymentCard grid)
 *   - Collections: collection membership via ModalCollectionsTab
 *
 * Integration note: unified-entity-modal.tsx already handles composite-type
 * artifacts inline. This standalone component is for contexts that render
 * plugin modals independently (e.g. plugin card click handlers, plugin browse
 * pages) without routing through UnifiedEntityModal.
 *
 * Deployment fetching mirrors the unified-entity-modal pattern: query all
 * registered projects in parallel via useQueries, then filter client-side by
 * artifact name + type.
 *
 * Accessibility: WCAG 2.1 AA. All interactive regions have aria labels.
 * Focus is trapped inside the Dialog by Radix UI.
 *
 * @example
 * ```tsx
 * <PluginDetailModal
 *   artifact={pluginArtifact}
 *   open={isOpen}
 *   onClose={() => setIsOpen(false)}
 * />
 * ```
 */

import { useState, useEffect, useCallback, useMemo } from 'react';
import {
  Calendar,
  GitBranch,
  FolderOpen,
  Rocket,
  Users,
  Tag,
  User,
  RefreshCw,
  Trash2,
  Pencil,
  ArrowRight,
  CheckCircle2,
  Clock,
  AlertCircle,
  MoreVertical,
} from 'lucide-react';
import { usePathname, useRouter } from 'next/navigation';
import { useQueries, useQueryClient } from '@tanstack/react-query';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { TabsContent } from '@/components/ui/tabs';
import { BaseArtifactModal } from '@/components/shared/base-artifact-modal';
import type { Tab } from '@/components/shared/tab-navigation';
import { PluginMembersTab } from '@/components/entity/plugin-members-tab';
import { SyncStatusTab } from '@/components/sync-status';
import { ModalCollectionsTab } from '@/components/entity/modal-collections-tab';
import { DeploymentCard, DeploymentCardSkeleton } from '@/components/deployments/deployment-card';
import type { Deployment } from '@/components/deployments/deployment-card';
import { ArtifactDeletionDialog } from '@/components/entity/artifact-deletion-dialog';
import { ArtifactInstanceIndicator } from '@/components/entity/artifact-instance-indicator';
import { getCollectionColor } from '@/lib/utils/collection-colors';
import { getTagColor } from '@/lib/utils/tag-colors';
import { listDeployments, removeProjectDeployment } from '@/lib/api/deployments';
import { deploymentKeys, useToast, useProjects } from '@/hooks';
import type { Artifact } from '@/types/artifact';
import { ARTIFACT_TYPES } from '@/types/artifact';
import type { ArtifactDeploymentInfo } from '@/types/deployments';

// ============================================================================
// Types
// ============================================================================

export type PluginDetailTab =
  | 'overview'
  | 'members'
  | 'sync'
  | 'deployments'
  | 'collections';

export interface PluginDetailModalProps {
  /** The composite/plugin artifact to display. Should have type === 'composite'. */
  artifact?: Artifact | null;
  /** Whether the modal is open. */
  open: boolean;
  /** Close handler called when the dialog is dismissed. */
  onClose: () => void;
  /** Initial tab to show. Defaults to 'members' for plugins. */
  initialTab?: PluginDetailTab;
  /** Callback when the active tab changes. Useful for URL state sync. */
  onTabChange?: (tab: PluginDetailTab) => void;
  /** Handler called when artifact is deleted. */
  onDelete?: () => void;
  /** Handler to navigate to a deployment from the Deployments tab. */
  onNavigateToDeployment?: (projectPath: string, artifactId: string) => void;
}

// ============================================================================
// Tab configuration (static — shared across renders)
// ============================================================================

const PLUGIN_TABS: Tab[] = [
  { value: 'overview', label: 'Overview' },
  { value: 'members', label: 'Members', icon: Users },
  { value: 'sync', label: 'Sync Status', icon: RefreshCw },
  { value: 'deployments', label: 'Deployments', icon: Rocket },
  { value: 'collections', label: 'Collections', icon: FolderOpen },
];

// ============================================================================
// Helpers
// ============================================================================

function formatDateTime(iso: string | undefined): string {
  if (!iso) return 'Unknown';
  const d = new Date(iso);
  return isNaN(d.getTime())
    ? iso
    : d.toLocaleDateString(undefined, {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      });
}

function getSyncStatusIcon(status: string | undefined) {
  switch (status) {
    case 'synced':
      return <CheckCircle2 className="h-4 w-4 text-green-500" aria-hidden="true" />;
    case 'modified':
      return <Pencil className="h-4 w-4 text-yellow-500" aria-hidden="true" />;
    case 'outdated':
      return <Clock className="h-4 w-4 text-orange-500" aria-hidden="true" />;
    case 'conflict':
    case 'error':
      return <AlertCircle className="h-4 w-4 text-red-500" aria-hidden="true" />;
    default:
      return <AlertCircle className="h-4 w-4 text-muted-foreground" aria-hidden="true" />;
  }
}

function getSyncStatusLabel(status: string | undefined): string {
  switch (status) {
    case 'synced':
      return 'Synced';
    case 'modified':
      return 'Modified';
    case 'outdated':
      return 'Outdated';
    case 'conflict':
      return 'Conflict';
    case 'error':
      return 'Error';
    default:
      return status ?? 'Unknown';
  }
}

/** Encode a project path as base64 for use as API project ID */
function encodeProjectId(projectPath: string): string {
  return btoa(projectPath);
}

// ============================================================================
// Overview Tab Content
// ============================================================================

interface PluginOverviewTabProps {
  artifact: Artifact;
  onDeleteClick?: () => void;
}

function PluginOverviewTab({ artifact, onDeleteClick }: PluginOverviewTabProps) {
  const config = ARTIFACT_TYPES[artifact.type];

  return (
    <ScrollArea className="h-[calc(90vh-12rem)]">
      <div className="space-y-6 py-4">
        {/* Action Buttons */}
        {onDeleteClick && (
          <div className="flex justify-end">
            <Button
              variant="outline"
              size="sm"
              className="text-destructive hover:bg-destructive/10 hover:text-destructive"
              onClick={onDeleteClick}
              aria-label="Delete plugin"
            >
              <Trash2 className="mr-2 h-4 w-4" aria-hidden="true" />
              Delete
            </Button>
          </div>
        )}

        {/* Status */}
        {artifact.syncStatus && (
          <div>
            <h3 className="mb-2 flex items-center gap-2 text-sm font-medium">
              {getSyncStatusIcon(artifact.syncStatus)}
              Status
            </h3>
            <Badge
              variant={artifact.syncStatus === 'synced' ? 'default' : 'secondary'}
              aria-label={`Sync status: ${getSyncStatusLabel(artifact.syncStatus)}`}
            >
              {getSyncStatusLabel(artifact.syncStatus)}
            </Badge>
          </div>
        )}

        {/* Description */}
        {artifact.description && (
          <div>
            <h3 className="mb-2 text-sm font-medium">Description</h3>
            <p className="text-sm text-muted-foreground">{artifact.description}</p>
          </div>
        )}

        {/* Collections */}
        {artifact.collections && artifact.collections.length > 0 && (
          <div>
            <h3 className="mb-2 flex items-center gap-2 text-sm font-medium">
              <FolderOpen className="h-4 w-4" aria-hidden="true" />
              Collections
            </h3>
            <div className="flex flex-wrap items-center gap-2" role="list" aria-label="Collections">
              {artifact.collections.map((collection) => (
                <Badge
                  key={collection.id || collection.name}
                  colorStyle={getCollectionColor(collection.name)}
                  role="listitem"
                >
                  {collection.name}
                </Badge>
              ))}
            </div>
          </div>
        )}

        {/* Tags */}
        {artifact.tags && artifact.tags.length > 0 && (
          <div>
            <h3 className="mb-2 flex items-center gap-2 text-sm font-medium">
              <Tag className="h-4 w-4" aria-hidden="true" />
              Tags
            </h3>
            <div className="flex flex-wrap gap-2" role="list" aria-label="Tags">
              {artifact.tags.map((tag) => {
                const tagName = typeof tag === 'string' ? tag : (tag as { name: string }).name;
                return (
                  <Badge
                    key={tagName}
                    colorStyle={getTagColor(tagName)}
                    role="listitem"
                  >
                    {tagName}
                  </Badge>
                );
              })}
            </div>
          </div>
        )}

        {/* Source */}
        <div>
          <h3 className="mb-2 flex items-center gap-2 text-sm font-medium">
            <GitBranch className="h-4 w-4" aria-hidden="true" />
            Source
          </h3>
          <p className="rounded bg-muted px-3 py-2 font-mono text-sm" aria-label="Source path">
            {artifact.source || 'Unknown'}
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

        {/* Type label */}
        {config && (
          <div>
            <h3 className="mb-2 text-sm font-medium">Type</h3>
            <Badge variant="outline">{config.label}</Badge>
          </div>
        )}

        {/* Timestamps */}
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <div>
            <h3 className="mb-1 flex items-center gap-2 text-xs font-medium text-muted-foreground">
              <Calendar className="h-3.5 w-3.5" aria-hidden="true" />
              Created
            </h3>
            <p className="text-sm">{formatDateTime(artifact.createdAt)}</p>
          </div>
          <div>
            <h3 className="mb-1 flex items-center gap-2 text-xs font-medium text-muted-foreground">
              <Calendar className="h-3.5 w-3.5" aria-hidden="true" />
              Last Updated
            </h3>
            <p className="text-sm">{formatDateTime(artifact.updatedAt)}</p>
          </div>
          {artifact.deployedAt && (
            <div>
              <h3 className="mb-1 flex items-center gap-2 text-xs font-medium text-muted-foreground">
                <Rocket className="h-3.5 w-3.5" aria-hidden="true" />
                Last Deployed
              </h3>
              <p className="text-sm">{formatDateTime(artifact.deployedAt)}</p>
            </div>
          )}
        </div>
      </div>
    </ScrollArea>
  );
}

// ============================================================================
// Deployments Tab Content
// ============================================================================

interface PluginDeploymentsTabProps {
  artifact: Artifact;
  onNavigateToDeployment?: (projectPath: string, artifactId: string) => void;
}

function PluginDeploymentsTab({ artifact, onNavigateToDeployment }: PluginDeploymentsTabProps) {
  const { toast } = useToast();
  const queryClient = useQueryClient();

  // Fetch all registered projects, then query deployments for each — mirrors
  // the pattern used by UnifiedEntityModal to aggregate across all projects.
  const { data: projects, isLoading: isProjectsLoading } = useProjects();

  const deploymentQueries = useQueries({
    queries: (projects || []).map((project) => ({
      queryKey: deploymentKeys.list(project.path),
      queryFn: () => listDeployments(project.path),
      staleTime: 2 * 60 * 1000,
      enabled: !!projects && projects.length > 0,
    })),
  });

  const isDeploymentsLoading =
    isProjectsLoading || deploymentQueries.some((q) => q.isLoading);
  const deploymentsError = deploymentQueries.find((q) => q.error)?.error;

  // Combine all deployments from all projects
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

  // Filter and shape to Deployment type — matches artifact by name + type
  const artifactDeployments = useMemo((): Deployment[] => {
    if (!allDeployments.length) return [];
    return allDeployments
      .filter(
        (d) =>
          d.artifact_name === artifact.name && d.artifact_type === artifact.type
      )
      .map((d): Deployment => {
        let status: 'current' | 'outdated' | 'error' = 'current';
        if (d.sync_status === 'outdated' || d.sync_status === 'modified') {
          status = 'outdated';
        }
        return {
          ...d,
          id: `${d.project_path}::${d.artifact_path}`,
          status,
          latest_version: artifact.version,
        };
      });
  }, [allDeployments, artifact.name, artifact.type, artifact.version]);

  const handleDeploymentRemove = useCallback(
    async (deployment: Deployment, removeFiles: boolean) => {
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
          title: 'Deployment removed',
          description: `${artifact.name} was removed from ${deployment.project_path}.`,
        });
      } catch {
        toast({
          title: 'Failed to remove deployment',
          description: 'An error occurred while removing the deployment.',
          variant: 'destructive',
        });
      }
    },
    [artifact.name, queryClient, toast]
  );

  return (
    <ScrollArea className="h-[calc(90vh-12rem)]">
      <div className="space-y-4 py-4">
        {/* Summary line */}
        {!isDeploymentsLoading && !deploymentsError && artifactDeployments.length > 0 && (
          <p className="text-sm text-muted-foreground">
            {artifactDeployments.length}{' '}
            {artifactDeployments.length === 1 ? 'deployment' : 'deployments'}
          </p>
        )}

        {/* Loading skeletons */}
        {isDeploymentsLoading && (
          <div className="space-y-3">
            <DeploymentCardSkeleton />
            <DeploymentCardSkeleton />
          </div>
        )}

        {/* Error state */}
        {!isDeploymentsLoading && deploymentsError && (
          <div
            className="flex flex-col items-center justify-center rounded-md border border-destructive/30 bg-destructive/5 px-6 py-8 text-center"
            role="alert"
          >
            <AlertCircle className="mb-2 h-8 w-8 text-destructive/60" aria-hidden="true" />
            <p className="text-sm font-medium text-destructive">Failed to load deployments</p>
            <p className="mt-1 text-xs text-muted-foreground">
              Could not retrieve deployment information.
            </p>
          </div>
        )}

        {/* Empty state */}
        {!isDeploymentsLoading && !deploymentsError && artifactDeployments.length === 0 && (
          <div
            className="flex flex-col items-center justify-center rounded-md border border-dashed border-border/60 px-6 py-10 text-center"
            role="status"
            aria-label="No deployments"
          >
            <Rocket className="mb-3 h-9 w-9 text-muted-foreground/30" aria-hidden="true" />
            <p className="text-sm font-medium text-muted-foreground">
              Not deployed anywhere
            </p>
            <p className="mt-1 text-xs text-muted-foreground/60">
              Deploy this plugin to a project to see it here.
            </p>
          </div>
        )}

        {/* Deployment cards grid */}
        {!isDeploymentsLoading && !deploymentsError && artifactDeployments.length > 0 && (
          <div
            className="grid grid-cols-1 gap-4 md:grid-cols-2"
            role="list"
            aria-label={`${artifactDeployments.length} deployment${artifactDeployments.length !== 1 ? 's' : ''}`}
          >
            {artifactDeployments.map((deployment) => (
              <div
                key={deployment.id}
                role="listitem"
                className="cursor-pointer"
                onClick={() =>
                  onNavigateToDeployment?.(
                    deployment.project_path,
                    `${deployment.artifact_type}:${deployment.artifact_name}`
                  )
                }
              >
                <DeploymentCard
                  deployment={deployment}
                  projects={projects}
                  onRemove={(removeFiles) => handleDeploymentRemove(deployment, removeFiles)}
                  onViewSource={() => {
                    // Already viewing source — no-op
                  }}
                />
              </div>
            ))}
          </div>
        )}
      </div>
    </ScrollArea>
  );
}

// ============================================================================
// PluginDetailModal
// ============================================================================

/**
 * Standalone detail modal for composite/plugin artifacts.
 *
 * Tab layout (plugin-specific):
 *   1. Overview     — metadata, status, description, source, timestamps
 *   2. Members      — drag-reorder member list via PluginMembersTab
 *   3. Sync Status  — SyncStatusTab (collection mode)
 *   4. Deployments  — project deployment cards with remove action
 *   5. Collections  — collection membership via ModalCollectionsTab
 */
export function PluginDetailModal({
  artifact,
  open,
  onClose,
  initialTab = 'members',
  onTabChange,
  onDelete,
  onNavigateToDeployment,
}: PluginDetailModalProps) {
  const pathname = usePathname();
  const router = useRouter();

  const [activeTab, setActiveTab] = useState<PluginDetailTab>(initialTab);
  const [showDeletionDialog, setShowDeletionDialog] = useState(false);

  // Sync activeTab when modal opens or initialTab changes
  useEffect(() => {
    if (open && initialTab) {
      setActiveTab(initialTab);
    }
  }, [open, initialTab]);

  const handleTabChange = useCallback(
    (tab: string) => {
      const typed = tab as PluginDetailTab;
      setActiveTab(typed);
      onTabChange?.(typed);
    },
    [onTabChange]
  );

  const handleCrossNavigation = useCallback(() => {
    if (!artifact) return;
    onClose();
    if (pathname === '/collection' || pathname?.startsWith('/collection')) {
      router.push(`/manage?artifact=${artifact.id}`);
    } else if (pathname === '/manage' || pathname?.startsWith('/manage')) {
      router.push(`/collection?artifact=${artifact.id}`);
    }
  }, [artifact, onClose, pathname, router]);

  // Guard: require a non-null artifact
  if (!artifact) return null;

  // Header actions: instance indicator + cross-navigation + optional delete
  const headerActions = (
    <div className="flex items-center gap-2">
      <ArtifactInstanceIndicator artifact={artifact} />

      {(pathname === '/collection' ||
        pathname?.startsWith('/collection') ||
        pathname === '/manage' ||
        pathname?.startsWith('/manage')) && (
        <Button
          variant="ghost"
          size="sm"
          onClick={handleCrossNavigation}
          className="gap-1"
          aria-label={
            pathname === '/collection' || pathname?.startsWith('/collection')
              ? 'Navigate to manage page'
              : 'Navigate to collection page'
          }
        >
          {pathname === '/collection' || pathname?.startsWith('/collection')
            ? 'Manage Plugin'
            : 'View Full Details'}
          <ArrowRight className="h-4 w-4" aria-hidden="true" />
        </Button>
      )}

      {onDelete && (
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button
              variant="ghost"
              size="icon"
              className="h-8 w-8"
              aria-label={`Actions for ${artifact.name}`}
            >
              <MoreVertical className="h-4 w-4" aria-hidden="true" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuItem
              className="text-destructive focus:text-destructive"
              onClick={() => setShowDeletionDialog(true)}
            >
              <Trash2 className="mr-2 h-4 w-4" aria-hidden="true" />
              Delete Plugin
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
        tabs={PLUGIN_TABS}
        headerActions={headerActions}
      >
        {/* Overview Tab */}
        <TabsContent value="overview" className="mt-0 flex-1">
          <PluginOverviewTab
            artifact={artifact}
            onDeleteClick={onDelete ? () => setShowDeletionDialog(true) : undefined}
          />
        </TabsContent>

        {/* Members Tab */}
        <TabsContent value="members" className="mt-0 flex-1">
          <ScrollArea className="h-[calc(90vh-12rem)]">
            <div className="py-4">
              <PluginMembersTab
                compositeId={artifact.id}
                collectionId={artifact.collection || 'default'}
              />
            </div>
          </ScrollArea>
        </TabsContent>

        {/* Sync Status Tab */}
        <TabsContent value="sync" className="mt-0 flex-1">
          <ScrollArea className="h-[calc(90vh-12rem)]">
            <div className="py-4">
              <SyncStatusTab
                entity={artifact}
                mode="collection"
                onClose={onClose}
              />
            </div>
          </ScrollArea>
        </TabsContent>

        {/* Deployments Tab */}
        <TabsContent value="deployments" className="mt-0 flex-1">
          <PluginDeploymentsTab
            artifact={artifact}
            onNavigateToDeployment={onNavigateToDeployment}
          />
        </TabsContent>

        {/* Collections Tab */}
        <TabsContent value="collections" className="mt-0 flex-1">
          <ScrollArea className="h-[calc(90vh-12rem)]">
            <div className="py-4">
              <ModalCollectionsTab artifact={artifact} />
            </div>
          </ScrollArea>
        </TabsContent>
      </BaseArtifactModal>

      {/* Artifact deletion dialog */}
      {onDelete && (
        <ArtifactDeletionDialog
          artifact={artifact}
          open={showDeletionDialog}
          onOpenChange={setShowDeletionDialog}
          context="collection"
          onSuccess={() => {
            setShowDeletionDialog(false);
            onDelete();
            onClose();
          }}
        />
      )}
    </>
  );
}
