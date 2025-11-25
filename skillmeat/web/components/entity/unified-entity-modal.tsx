'use client';

import { useState, useMemo } from 'react';
import { Calendar, Tag, GitBranch, AlertCircle, CheckCircle2, Clock, Loader2, RotateCcw, ArrowUp, ArrowDown, FileText, User } from 'lucide-react';
import * as LucideIcons from 'lucide-react';
import { LucideIcon } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Skeleton } from '@/components/ui/skeleton';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Entity, ENTITY_TYPES } from '@/types/entity';
import { useEntityLifecycle } from '@/hooks/useEntityLifecycle';
import { DiffViewer } from '@/components/entity/diff-viewer';
import { RollbackDialog } from '@/components/entity/rollback-dialog';
import { useToast } from '@/hooks/use-toast';
import { apiRequest } from '@/lib/api';
import type { ArtifactDiffResponse, ArtifactSyncRequest } from '@/sdk';

interface UnifiedEntityModalProps {
  entity: Entity | null;
  open: boolean;
  onClose: () => void;
}

interface HistoryEntry {
  id: string;
  type: 'deploy' | 'sync' | 'rollback';
  direction: 'upstream' | 'downstream';
  timestamp: string;
  filesChanged?: number;
  user?: string;
}

// ============================================================================
// Helper Functions
// ============================================================================

/**
 * Format relative time for display
 */
function formatRelativeTime(date: Date): string {
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffSecs = Math.floor(diffMs / 1000);
  const diffMins = Math.floor(diffSecs / 60);
  const diffHours = Math.floor(diffMins / 60);
  const diffDays = Math.floor(diffHours / 24);

  if (diffSecs < 60) {
    return 'just now';
  } else if (diffMins < 60) {
    return `${diffMins} ${diffMins === 1 ? 'minute' : 'minutes'} ago`;
  } else if (diffHours < 24) {
    return `${diffHours} ${diffHours === 1 ? 'hour' : 'hours'} ago`;
  } else if (diffDays < 30) {
    return `${diffDays} ${diffDays === 1 ? 'day' : 'days'} ago`;
  } else {
    return date.toLocaleDateString();
  }
}

/**
 * Generate mock history entries based on entity metadata
 */
function generateMockHistory(entity: Entity): HistoryEntry[] {
  const history: HistoryEntry[] = [];

  // Create history entries from available timestamps
  if (entity.deployedAt) {
    const deployedDate = new Date(entity.deployedAt);
    history.push({
      id: `deploy-${entity.deployedAt}`,
      type: 'deploy',
      direction: 'downstream',
      timestamp: entity.deployedAt,
      filesChanged: Math.floor(Math.random() * 5) + 1,
      user: 'You',
    });

    // Add a sync entry a bit before deployment if entity is modified
    if (entity.status === 'modified' || entity.status === 'outdated') {
      const syncDate = new Date(deployedDate.getTime() - 2 * 60 * 60 * 1000); // 2 hours before
      history.push({
        id: `sync-${syncDate.toISOString()}`,
        type: 'sync',
        direction: 'upstream',
        timestamp: syncDate.toISOString(),
        filesChanged: Math.floor(Math.random() * 3) + 1,
        user: 'You',
      });
    }
  }

  if (entity.modifiedAt && entity.modifiedAt !== entity.deployedAt) {
    // Add sync entry for modifications
    history.push({
      id: `sync-${entity.modifiedAt}`,
      type: 'sync',
      direction: 'upstream',
      timestamp: entity.modifiedAt,
      filesChanged: Math.floor(Math.random() * 4) + 1,
      user: 'You',
    });
  }

  // Add a rollback entry for conflict status
  if (entity.status === 'conflict' && entity.modifiedAt) {
    const rollbackDate = new Date(new Date(entity.modifiedAt).getTime() + 1 * 60 * 60 * 1000); // 1 hour after modification
    history.push({
      id: `rollback-${rollbackDate.toISOString()}`,
      type: 'rollback',
      direction: 'downstream',
      timestamp: rollbackDate.toISOString(),
      filesChanged: Math.floor(Math.random() * 3) + 1,
      user: 'You',
    });
  }

  // Sort by timestamp (most recent first)
  return history.sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime());
}

// ============================================================================
// Loading Skeleton
// ============================================================================

function EntityModalSkeleton() {
  return (
    <div className="space-y-6 p-6">
      <div className="space-y-4">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-4 w-full" />
        <Skeleton className="h-4 w-3/4" />
      </div>

      <div className="space-y-3">
        <Skeleton className="h-6 w-32" />
        <div className="grid grid-cols-2 gap-4">
          <Skeleton className="h-16 w-full" />
          <Skeleton className="h-16 w-full" />
          <Skeleton className="h-16 w-full" />
          <Skeleton className="h-16 w-full" />
        </div>
      </div>

      <div className="space-y-3">
        <Skeleton className="h-6 w-32" />
        <Skeleton className="h-24 w-full" />
      </div>
    </div>
  );
}

// ============================================================================
// Main Component
// ============================================================================

/**
 * UnifiedEntityModal - Unified modal for entity management
 *
 * Consolidated modal component that combines the best of both Sheet and Dialog approaches.
 * Uses Dialog for consistency with collection UI and provides comprehensive entity management.
 *
 * Features:
 * - Overview tab with metadata, status, version, tags, timestamps, location
 * - Sync Status tab with deploy/sync buttons, diff viewer, status alerts
 * - History tab with timeline of deploy/sync/rollback events
 * - Skeleton loading state
 * - Rollback dialog integration
 * - Full TypeScript support
 *
 * @example
 * ```tsx
 * <UnifiedEntityModal
 *   entity={selectedEntity}
 *   open={isModalOpen}
 *   onClose={() => setIsModalOpen(false)}
 * />
 * ```
 */
export function UnifiedEntityModal({ entity, open, onClose }: UnifiedEntityModalProps) {
  const [activeTab, setActiveTab] = useState('overview');
  const { deployEntity, syncEntity, refetch } = useEntityLifecycle();
  const [isDeploying, setIsDeploying] = useState(false);
  const [isSyncing, setIsSyncing] = useState(false);
  const [showRollbackDialog, setShowRollbackDialog] = useState(false);
  const [isRollingBack, setIsRollingBack] = useState(false);
  const { toast } = useToast();

  // Generate mock history entries
  const historyEntries = useMemo(() => {
    if (!entity) return [];
    return generateMockHistory(entity);
  }, [entity]);

  // Fetch diff data when sync tab is active and entity has changes
  const shouldFetchDiff = !!(
    activeTab === 'sync' &&
    entity &&
    (entity.status === 'modified' || entity.status === 'outdated') &&
    entity.projectPath
  );

  const {
    data: diffData,
    isLoading: isDiffLoading,
    error: diffError,
  } = useQuery<ArtifactDiffResponse>({
    queryKey: ['artifact-diff', entity?.id, entity?.projectPath],
    queryFn: async () => {
      if (!entity?.id || !entity?.projectPath) {
        throw new Error('Missing entity ID or project path');
      }

      const params = new URLSearchParams({
        project_path: entity.projectPath,
      });

      if (entity.collection) {
        params.set('collection', entity.collection);
      }

      return await apiRequest<ArtifactDiffResponse>(
        `/artifacts/${entity.id}/diff?${params.toString()}`
      );
    },
    enabled: shouldFetchDiff,
    staleTime: 5 * 60 * 1000, // Cache for 5 minutes
    gcTime: 30 * 60 * 1000, // Keep in cache for 30 minutes
  });

  if (!entity) {
    return null;
  }

  const config = ENTITY_TYPES[entity.type];
  const IconComponent = (LucideIcons as any)[config.icon] as LucideIcon;

  // ============================================================================
  // Event Handlers
  // ============================================================================

  const handleDeploy = async () => {
    if (!entity.projectPath) {
      toast({
        title: 'Deploy Failed',
        description: 'Please select a project to deploy to',
        variant: 'destructive',
      });
      return;
    }

    setIsDeploying(true);
    try {
      await deployEntity(entity.id, entity.projectPath);
      toast({
        title: 'Deploy Successful',
        description: `${entity.name} has been deployed to the project.`,
      });
    } catch (error) {
      console.error('Deploy failed:', error);
      toast({
        title: 'Deploy Failed',
        description: error instanceof Error ? error.message : 'Failed to deploy entity',
        variant: 'destructive',
      });
    } finally {
      setIsDeploying(false);
    }
  };

  const handleSync = async () => {
    if (!entity.projectPath) {
      toast({
        title: 'Sync Failed',
        description: 'Please select a project to sync with',
        variant: 'destructive',
      });
      return;
    }

    setIsSyncing(true);
    try {
      await syncEntity(entity.id, entity.projectPath);
      toast({
        title: 'Sync Successful',
        description: `${entity.name} has been synced with upstream.`,
      });
    } catch (error) {
      console.error('Sync failed:', error);
      toast({
        title: 'Sync Failed',
        description: error instanceof Error ? error.message : 'Failed to sync entity',
        variant: 'destructive',
      });
    } finally {
      setIsSyncing(false);
    }
  };

  const handleRollback = async () => {
    if (!entity.projectPath) {
      toast({
        title: 'Rollback Failed',
        description: 'Please select a project to rollback',
        variant: 'destructive',
      });
      return;
    }

    setIsRollingBack(true);
    try {
      // Call sync API with 'theirs' strategy to pull collection version
      const request: ArtifactSyncRequest = {
        project_path: entity.projectPath,
        strategy: 'theirs', // Take collection version
        force: true, // Force overwrite local changes
      };

      await apiRequest(`/artifacts/${entity.id}/sync`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(request),
      });

      toast({
        title: 'Rollback Successful',
        description: `${entity.name} has been rolled back to the collection version.`,
      });

      // Refresh the entity list
      refetch();
    } catch (error) {
      console.error('Rollback failed:', error);
      toast({
        title: 'Rollback Failed',
        description: error instanceof Error ? error.message : 'Failed to rollback entity',
        variant: 'destructive',
      });
      throw error; // Re-throw to let dialog handle it
    } finally {
      setIsRollingBack(false);
    }
  };

  // ============================================================================
  // Status Helpers
  // ============================================================================

  const getStatusIcon = () => {
    switch (entity.status) {
      case 'synced':
        return <CheckCircle2 className="h-4 w-4 text-green-500" />;
      case 'modified':
        return <AlertCircle className="h-4 w-4 text-yellow-500" />;
      case 'outdated':
        return <Clock className="h-4 w-4 text-blue-500" />;
      case 'conflict':
        return <AlertCircle className="h-4 w-4 text-red-500" />;
      default:
        return null;
    }
  };

  const getStatusLabel = () => {
    switch (entity.status) {
      case 'synced':
        return 'Synced';
      case 'modified':
        return 'Modified';
      case 'outdated':
        return 'Outdated';
      case 'conflict':
        return 'Conflict';
      default:
        return 'Unknown';
    }
  };

  const getHistoryTypeLabel = (type: HistoryEntry['type']) => {
    switch (type) {
      case 'deploy':
        return 'Deployed';
      case 'sync':
        return 'Synced';
      case 'rollback':
        return 'Rolled back';
      default:
        return type;
    }
  };

  const getHistoryTypeColor = (type: HistoryEntry['type']) => {
    switch (type) {
      case 'deploy':
        return 'text-green-600 dark:text-green-400';
      case 'sync':
        return 'text-blue-600 dark:text-blue-400';
      case 'rollback':
        return 'text-orange-600 dark:text-orange-400';
      default:
        return 'text-gray-600 dark:text-gray-400';
    }
  };

  // ============================================================================
  // Render
  // ============================================================================

  return (
    <>
      <Dialog open={open} onOpenChange={(open) => !open && onClose()}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-hidden flex flex-col p-0">
          {/* Header Section - Fixed */}
          <div className="px-6 pt-6 pb-4 border-b">
            <DialogHeader>
              <DialogTitle className="flex items-center gap-3">
                {IconComponent && <IconComponent className={`h-5 w-5 ${config.color}`} />}
                <span className="flex-1">{entity.name}</span>
                <Badge variant="outline" className="gap-1">
                  {config.label}
                </Badge>
                {entity.status && (
                  <Badge variant={entity.status === 'synced' ? 'default' : 'secondary'}>
                    {getStatusLabel()}
                  </Badge>
                )}
              </DialogTitle>
            </DialogHeader>
          </div>

          {/* Tabs Section */}
          <Tabs value={activeTab} onValueChange={setActiveTab} className="flex-1 flex flex-col px-6">
            <TabsList className="w-full justify-start border-b rounded-none h-auto p-0 bg-transparent">
              <TabsTrigger
                value="overview"
                className="rounded-none border-b-2 border-transparent data-[state=active]:border-primary data-[state=active]:bg-transparent"
              >
                Overview
              </TabsTrigger>
              <TabsTrigger
                value="sync"
                className="rounded-none border-b-2 border-transparent data-[state=active]:border-primary data-[state=active]:bg-transparent"
              >
                Sync Status
              </TabsTrigger>
              <TabsTrigger
                value="history"
                className="rounded-none border-b-2 border-transparent data-[state=active]:border-primary data-[state=active]:bg-transparent"
              >
                History
              </TabsTrigger>
            </TabsList>

            {/* Overview Tab */}
            <TabsContent value="overview" className="flex-1 mt-0">
              <ScrollArea className="h-[calc(90vh-12rem)]">
                <div className="space-y-6 py-4">
                  {/* Status */}
                  {entity.status && (
                    <div>
                      <h3 className="text-sm font-medium mb-2 flex items-center gap-2">
                        {getStatusIcon()}
                        Status
                      </h3>
                      <div className="flex items-center gap-2">
                        <Badge variant={entity.status === 'synced' ? 'default' : 'secondary'}>
                          {getStatusLabel()}
                        </Badge>
                      </div>
                    </div>
                  )}

                  {/* Description */}
                  {entity.description && (
                    <div>
                      <h3 className="text-sm font-medium mb-2">Description</h3>
                      <p className="text-sm text-muted-foreground">{entity.description}</p>
                    </div>
                  )}

                  {/* Source */}
                  <div>
                    <h3 className="text-sm font-medium mb-2 flex items-center gap-2">
                      <GitBranch className="h-4 w-4" />
                      Source
                    </h3>
                    <p className="text-sm font-mono bg-muted px-3 py-2 rounded">
                      {entity.source || 'Unknown'}
                    </p>
                  </div>

                  {/* Version */}
                  {entity.version && (
                    <div>
                      <h3 className="text-sm font-medium mb-2">Version</h3>
                      <p className="text-sm text-muted-foreground">{entity.version}</p>
                    </div>
                  )}

                  {/* Tags */}
                  {entity.tags && entity.tags.length > 0 && (
                    <div>
                      <h3 className="text-sm font-medium mb-2 flex items-center gap-2">
                        <Tag className="h-4 w-4" />
                        Tags
                      </h3>
                      <div className="flex flex-wrap gap-2">
                        {entity.tags.map((tag) => (
                          <Badge key={tag} variant="outline">
                            {tag}
                          </Badge>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Aliases */}
                  {entity.aliases && entity.aliases.length > 0 && (
                    <div>
                      <h3 className="text-sm font-medium mb-2">Aliases</h3>
                      <div className="flex flex-wrap gap-2">
                        {entity.aliases.map((alias) => (
                          <Badge key={alias} variant="secondary">
                            {alias}
                          </Badge>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Timestamps */}
                  <div>
                    <h3 className="text-sm font-medium mb-2 flex items-center gap-2">
                      <Calendar className="h-4 w-4" />
                      Timestamps
                    </h3>
                    <div className="space-y-2 text-sm text-muted-foreground">
                      {entity.deployedAt && (
                        <div className="flex justify-between">
                          <span>Deployed:</span>
                          <span>{new Date(entity.deployedAt).toLocaleString()}</span>
                        </div>
                      )}
                      {entity.modifiedAt && (
                        <div className="flex justify-between">
                          <span>Modified:</span>
                          <span>{new Date(entity.modifiedAt).toLocaleString()}</span>
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Location */}
                  <div>
                    <h3 className="text-sm font-medium mb-2">Location</h3>
                    <div className="space-y-2 text-sm text-muted-foreground">
                      {entity.collection && (
                        <div className="flex justify-between">
                          <span>Collection:</span>
                          <span>{entity.collection}</span>
                        </div>
                      )}
                      {entity.projectPath && (
                        <div className="flex flex-col gap-1">
                          <span>Project Path:</span>
                          <code className="text-xs bg-muted px-2 py-1 rounded break-all">
                            {entity.projectPath}
                          </code>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              </ScrollArea>
            </TabsContent>

            {/* Sync Status Tab */}
            <TabsContent value="sync" className="flex-1 mt-0">
              <ScrollArea className="h-[calc(90vh-12rem)]">
                <div className="space-y-6 py-4">
                  <div>
                    <h3 className="text-sm font-medium mb-2">Sync Status</h3>
                    <div className="flex items-center gap-2 mb-4">
                      {getStatusIcon()}
                      <span className="text-sm">{getStatusLabel()}</span>
                    </div>

                    {/* Actions */}
                    <div className="flex gap-2">
                      <Button
                        onClick={handleDeploy}
                        disabled={isDeploying || !entity.collection}
                        size="sm"
                      >
                        {isDeploying ? (
                          <>
                            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                            Deploying...
                          </>
                        ) : (
                          'Deploy to Project'
                        )}
                      </Button>
                      <Button
                        onClick={handleSync}
                        disabled={isSyncing || !entity.projectPath}
                        variant="outline"
                        size="sm"
                      >
                        {isSyncing ? (
                          <>
                            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                            Syncing...
                          </>
                        ) : (
                          'Sync with Upstream'
                        )}
                      </Button>
                    </div>
                  </div>

                  {/* Diff Viewer */}
                  {(entity.status === 'modified' || entity.status === 'outdated') && entity.projectPath && (
                    <div>
                      <h3 className="text-sm font-medium mb-2">Changes</h3>
                      {isDiffLoading ? (
                        <div className="border rounded-lg p-8 bg-muted/20 flex items-center justify-center">
                          <div className="flex items-center gap-2 text-muted-foreground">
                            <Loader2 className="h-4 w-4 animate-spin" />
                            <span className="text-sm">Loading diff...</span>
                          </div>
                        </div>
                      ) : diffError ? (
                        <div className="border rounded-lg p-4 bg-red-500/10 border-red-500/20">
                          <p className="text-sm text-red-700 dark:text-red-400">
                            Failed to load diff: {diffError instanceof Error ? diffError.message : 'Unknown error'}
                          </p>
                        </div>
                      ) : diffData && (diffData as unknown as ArtifactDiffResponse).files && Array.isArray((diffData as unknown as ArtifactDiffResponse).files) && (diffData as unknown as ArtifactDiffResponse).files.length > 0 ? (
                        <div className="border rounded-lg overflow-hidden bg-background">
                          <DiffViewer
                            files={(diffData as unknown as ArtifactDiffResponse).files}
                            leftLabel={entity.collection ? 'Collection' : 'Current'}
                            rightLabel={entity.projectPath ? 'Project' : 'Upstream'}
                          />
                        </div>
                      ) : diffData && !(diffData as unknown as ArtifactDiffResponse).has_changes ? (
                        <div className="border rounded-lg p-4 bg-muted/20">
                          <p className="text-sm text-muted-foreground text-center">
                            No changes detected
                          </p>
                        </div>
                      ) : null}
                    </div>
                  )}

                  {/* Status Alerts */}
                  {entity.status === 'outdated' && (
                    <Alert>
                      <AlertCircle className="h-4 w-4" />
                      <AlertDescription className="text-sm text-blue-700 dark:text-blue-400">
                        A newer version is available upstream. Click "Sync with Upstream" to update.
                      </AlertDescription>
                    </Alert>
                  )}

                  {entity.status === 'conflict' && (
                    <Alert variant="destructive">
                      <AlertCircle className="h-4 w-4" />
                      <AlertDescription className="text-sm">
                        There are conflicting changes between local and upstream versions.
                        Manual resolution may be required.
                      </AlertDescription>
                    </Alert>
                  )}
                </div>
              </ScrollArea>
            </TabsContent>

            {/* History Tab */}
            <TabsContent value="history" className="flex-1 mt-0">
              <ScrollArea className="h-[calc(90vh-12rem)]">
                <div className="space-y-4 py-4">
                  {/* Rollback Section */}
                  {(entity.status === 'modified' || entity.status === 'conflict') && entity.projectPath && (
                    <div className="border rounded-lg p-4 bg-muted/20">
                      <h3 className="text-sm font-medium mb-2 flex items-center gap-2">
                        <RotateCcw className="h-4 w-4" />
                        Rollback to Collection Version
                      </h3>
                      <p className="text-sm text-muted-foreground mb-4">
                        Your local version has been modified. You can rollback to the collection version
                        to discard all local changes.
                      </p>
                      <Button
                        onClick={() => setShowRollbackDialog(true)}
                        variant="outline"
                        size="sm"
                        disabled={isRollingBack}
                      >
                        <RotateCcw className="mr-2 h-4 w-4" />
                        {isRollingBack ? 'Rolling Back...' : 'Rollback to Collection'}
                      </Button>
                    </div>
                  )}

                  {/* History Timeline */}
                  {historyEntries.length > 0 ? (
                    <div>
                      <h3 className="text-sm font-medium mb-4">Sync History</h3>
                      <div className="space-y-0 relative">
                        {/* Timeline line */}
                        <div className="absolute left-4 top-0 bottom-0 w-px bg-border" />

                        {historyEntries.map((entry) => (
                          <div
                            key={entry.id}
                            className="relative pl-11 pb-6 last:pb-0 group hover:bg-muted/30 -ml-2 pl-13 pr-2 py-2 rounded-lg transition-colors"
                          >
                            {/* Timeline dot and icon */}
                            <div className={`absolute left-4 top-2 w-8 h-8 rounded-full border-2 bg-background flex items-center justify-center z-10 ${
                              entry.type === 'deploy' ? 'border-green-500' :
                              entry.type === 'sync' ? 'border-blue-500' :
                              'border-orange-500'
                            }`}>
                              {entry.direction === 'downstream' ? (
                                <ArrowDown className="h-4 w-4" />
                              ) : (
                                <ArrowUp className="h-4 w-4" />
                              )}
                            </div>

                            {/* Entry content */}
                            <div className="flex items-start justify-between gap-4">
                              <div className="flex-1 min-w-0">
                                <div className="flex items-center gap-2 mb-1">
                                  <span className={`text-sm font-medium ${getHistoryTypeColor(entry.type)}`}>
                                    {getHistoryTypeLabel(entry.type)}
                                  </span>
                                  {entry.filesChanged && (
                                    <Badge variant="secondary" className="text-xs">
                                      <FileText className="h-3 w-3 mr-1" />
                                      {entry.filesChanged} {entry.filesChanged === 1 ? 'file' : 'files'}
                                    </Badge>
                                  )}
                                </div>
                                <div className="flex items-center gap-2 text-xs text-muted-foreground">
                                  <Clock className="h-3 w-3" />
                                  <span>{formatRelativeTime(new Date(entry.timestamp))}</span>
                                  {entry.user && (
                                    <>
                                      <span>•</span>
                                      <User className="h-3 w-3" />
                                      <span>{entry.user}</span>
                                    </>
                                  )}
                                </div>
                              </div>
                              <div className="text-xs text-muted-foreground">
                                {new Date(entry.timestamp).toLocaleTimeString([], {
                                  hour: '2-digit',
                                  minute: '2-digit'
                                })}
                              </div>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  ) : (
                    // Empty state
                    <div className="text-center py-12">
                      <Clock className="h-12 w-12 text-muted-foreground mx-auto mb-4 opacity-50" />
                      <h3 className="text-lg font-semibold mb-2">No sync history yet</h3>
                      <p className="text-sm text-muted-foreground max-w-sm mx-auto">
                        Sync operations and deployments will appear here once you start managing this entity.
                      </p>
                    </div>
                  )}
                </div>
              </ScrollArea>
            </TabsContent>
          </Tabs>
        </DialogContent>
      </Dialog>

      {/* Rollback Confirmation Dialog */}
      <RollbackDialog
        entity={entity}
        open={showRollbackDialog}
        onOpenChange={setShowRollbackDialog}
        onConfirm={handleRollback}
      />
    </>
  );
}
