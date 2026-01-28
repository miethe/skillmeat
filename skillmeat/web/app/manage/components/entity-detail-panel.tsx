'use client';

import { useState, useMemo } from 'react';
import {
  Calendar,
  Tag,
  GitBranch,
  AlertCircle,
  CheckCircle2,
  Clock,
  Loader2,
  RotateCcw,
  ArrowUp,
  ArrowDown,
  FileText,
  User,
} from 'lucide-react';
import * as LucideIcons from 'lucide-react';
import { LucideIcon } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import { Sheet, SheetContent, SheetHeader, SheetTitle } from '@/components/ui/sheet';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Artifact, ARTIFACT_TYPES } from '@/types/artifact';
import { useEntityLifecycle, useToast } from '@/hooks';
import { DiffViewer } from '@/components/entity/diff-viewer';
import { RollbackDialog } from '@/components/entity/rollback-dialog';
import { apiRequest } from '@/lib/api';
import type { ArtifactDiffResponse, ArtifactSyncRequest } from '@/sdk';

interface EntityDetailPanelProps {
  entity: Artifact | null;
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

// Helper function to format relative time
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

// Generate mock history entries based on entity metadata
function generateMockHistory(entity: Artifact): HistoryEntry[] {
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
    if (entity.syncStatus === 'modified' || entity.syncStatus === 'outdated') {
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
  if (entity.syncStatus === 'conflict' && entity.modifiedAt) {
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

export function EntityDetailPanel({ entity, open, onClose }: EntityDetailPanelProps) {
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
    (entity.syncStatus === 'modified' || entity.syncStatus === 'outdated') &&
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
    staleTime: 5 * 60 * 1000, // Cache for 5 minutes (improved from 30s)
    gcTime: 30 * 60 * 1000, // Keep in cache for 30 minutes
  });

  if (!entity) {
    return null;
  }

  const config = ARTIFACT_TYPES[entity.type];
  const IconComponent = (LucideIcons as any)[config.icon] as LucideIcon;

  const handleDeploy = async () => {
    if (!entity.projectPath) {
      alert('Please select a project to deploy to');
      return;
    }

    setIsDeploying(true);
    try {
      await deployEntity(entity.id, entity.projectPath);
    } catch (error) {
      console.error('Deploy failed:', error);
      alert('Failed to deploy entity');
    } finally {
      setIsDeploying(false);
    }
  };

  const handleSync = async () => {
    if (!entity.projectPath) {
      alert('Please select a project to sync with');
      return;
    }

    setIsSyncing(true);
    try {
      await syncEntity(entity.id, entity.projectPath);
    } catch (error) {
      console.error('Sync failed:', error);
      alert('Failed to sync entity');
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

  const getStatusIcon = () => {
    switch (entity.syncStatus) {
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
    switch (entity.syncStatus) {
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

  return (
    <Sheet open={open} onOpenChange={(open) => !open && onClose()}>
      <SheetContent side="right" className="w-full sm:max-w-2xl" onClose={onClose}>
        <SheetHeader>
          <SheetTitle className="flex items-center gap-3">
            {IconComponent && <IconComponent className={`h-5 w-5 ${config.color}`} />}
            <span className="flex-1">{entity.name}</span>
            <Badge variant="outline" className="gap-1">
              {config.label}
            </Badge>
          </SheetTitle>
        </SheetHeader>

        <Tabs
          value={activeTab}
          onValueChange={setActiveTab}
          className="mt-6 flex h-[calc(100vh-8rem)] flex-col"
        >
          <TabsList className="grid w-full grid-cols-3">
            <TabsTrigger value="overview">Overview</TabsTrigger>
            <TabsTrigger value="sync">Sync Status</TabsTrigger>
            <TabsTrigger value="history">History</TabsTrigger>
          </TabsList>

          {/* Overview Tab */}
          <TabsContent value="overview" className="flex-1 overflow-hidden">
            <ScrollArea className="h-full pr-4">
              <div className="space-y-6">
                {/* Status */}
                <div>
                  <h3 className="mb-2 flex items-center gap-2 text-sm font-medium">
                    {getStatusIcon()}
                    Status
                  </h3>
                  <div className="flex items-center gap-2">
                    <Badge variant={entity.syncStatus === 'synced' ? 'default' : 'secondary'}>
                      {getStatusLabel()}
                    </Badge>
                  </div>
                </div>

                {/* Description */}
                {entity.description && (
                  <div>
                    <h3 className="mb-2 text-sm font-medium">Description</h3>
                    <p className="text-sm text-muted-foreground">{entity.description}</p>
                  </div>
                )}

                {/* Source */}
                <div>
                  <h3 className="mb-2 flex items-center gap-2 text-sm font-medium">
                    <GitBranch className="h-4 w-4" />
                    Source
                  </h3>
                  <p className="rounded bg-muted px-3 py-2 font-mono text-sm">
                    {entity.source || 'Unknown'}
                  </p>
                </div>

                {/* Version */}
                {entity.version && (
                  <div>
                    <h3 className="mb-2 text-sm font-medium">Version</h3>
                    <p className="text-sm text-muted-foreground">{entity.version}</p>
                  </div>
                )}

                {/* Tags */}
                {entity.tags && entity.tags.length > 0 && (
                  <div>
                    <h3 className="mb-2 flex items-center gap-2 text-sm font-medium">
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
                    <h3 className="mb-2 text-sm font-medium">Aliases</h3>
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
                  <h3 className="mb-2 flex items-center gap-2 text-sm font-medium">
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
                  <h3 className="mb-2 text-sm font-medium">Location</h3>
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
                        <code className="break-all rounded bg-muted px-2 py-1 text-xs">
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
          <TabsContent value="sync" className="flex-1 overflow-hidden">
            <ScrollArea className="h-full pr-4">
              <div className="space-y-6">
                <div>
                  <h3 className="mb-2 text-sm font-medium">Sync Status</h3>
                  <div className="mb-4 flex items-center gap-2">
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
                      {isDeploying ? 'Deploying...' : 'Deploy to Project'}
                    </Button>
                    <Button
                      onClick={handleSync}
                      disabled={isSyncing || !entity.projectPath}
                      variant="outline"
                      size="sm"
                    >
                      {isSyncing ? 'Syncing...' : 'Sync with Upstream'}
                    </Button>
                  </div>
                </div>

                {/* Diff Viewer */}
                {(entity.syncStatus === 'modified' || entity.syncStatus === 'outdated') &&
                  entity.projectPath && (
                    <div>
                      <h3 className="mb-2 text-sm font-medium">Changes</h3>
                      {isDiffLoading ? (
                        <div className="flex items-center justify-center rounded-lg border bg-muted/20 p-8">
                          <div className="flex items-center gap-2 text-muted-foreground">
                            <Loader2 className="h-4 w-4 animate-spin" />
                            <span className="text-sm">Loading diff...</span>
                          </div>
                        </div>
                      ) : diffError ? (
                        <div className="rounded-lg border border-red-500/20 bg-red-500/10 p-4">
                          <p className="text-sm text-red-700 dark:text-red-400">
                            Failed to load diff:{' '}
                            {diffError instanceof Error ? diffError.message : 'Unknown error'}
                          </p>
                        </div>
                      ) : diffData &&
                        (diffData as unknown as ArtifactDiffResponse).files &&
                        Array.isArray((diffData as unknown as ArtifactDiffResponse).files) &&
                        (diffData as unknown as ArtifactDiffResponse).files.length > 0 ? (
                        <div className="overflow-hidden rounded-lg border bg-background">
                          <DiffViewer
                            files={(diffData as unknown as ArtifactDiffResponse).files}
                            leftLabel={entity.collection ? 'Collection' : 'Current'}
                            rightLabel={entity.projectPath ? 'Project' : 'Upstream'}
                          />
                        </div>
                      ) : diffData && !(diffData as unknown as ArtifactDiffResponse).has_changes ? (
                        <div className="rounded-lg border bg-muted/20 p-4">
                          <p className="text-center text-sm text-muted-foreground">
                            No changes detected
                          </p>
                        </div>
                      ) : null}
                    </div>
                  )}

                {entity.syncStatus === 'outdated' && (
                  <div className="rounded-lg border border-blue-500/20 bg-blue-500/10 p-4">
                    <p className="text-sm text-blue-700 dark:text-blue-400">
                      A newer version is available upstream. Click "Sync with Upstream" to update.
                    </p>
                  </div>
                )}

                {entity.syncStatus === 'conflict' && (
                  <div className="rounded-lg border border-red-500/20 bg-red-500/10 p-4">
                    <p className="text-sm text-red-700 dark:text-red-400">
                      There are conflicting changes between local and upstream versions. Manual
                      resolution may be required.
                    </p>
                  </div>
                )}
              </div>
            </ScrollArea>
          </TabsContent>

          {/* History Tab */}
          <TabsContent value="history" className="flex-1 overflow-hidden">
            <ScrollArea className="h-full pr-4">
              <div className="space-y-4">
                {/* Rollback Section */}
                {(entity.syncStatus === 'modified' || entity.syncStatus === 'conflict') &&
                  entity.projectPath && (
                    <div className="rounded-lg border bg-muted/20 p-4">
                      <h3 className="mb-2 flex items-center gap-2 text-sm font-medium">
                        <RotateCcw className="h-4 w-4" />
                        Rollback to Collection Version
                      </h3>
                      <p className="mb-4 text-sm text-muted-foreground">
                        Your local version has been modified. You can rollback to the collection
                        version to discard all local changes.
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
                    <h3 className="mb-4 text-sm font-medium">Sync History</h3>
                    <div className="relative space-y-0">
                      {/* Timeline line */}
                      <div className="absolute bottom-0 left-4 top-0 w-px bg-border" />

                      {historyEntries.map((entry) => (
                        <div
                          key={entry.id}
                          className="pl-13 group relative -ml-2 rounded-lg py-2 pb-6 pl-11 pr-2 transition-colors last:pb-0 hover:bg-muted/30"
                        >
                          {/* Timeline dot and icon */}
                          <div
                            className={`absolute left-4 top-2 z-10 flex h-8 w-8 items-center justify-center rounded-full border-2 bg-background ${
                              entry.type === 'deploy'
                                ? 'border-green-500'
                                : entry.type === 'sync'
                                  ? 'border-blue-500'
                                  : 'border-orange-500'
                            }`}
                          >
                            {entry.direction === 'downstream' ? (
                              <ArrowDown className="h-4 w-4" />
                            ) : (
                              <ArrowUp className="h-4 w-4" />
                            )}
                          </div>

                          {/* Entry content */}
                          <div className="flex items-start justify-between gap-4">
                            <div className="min-w-0 flex-1">
                              <div className="mb-1 flex items-center gap-2">
                                <span
                                  className={`text-sm font-medium ${getHistoryTypeColor(entry.type)}`}
                                >
                                  {getHistoryTypeLabel(entry.type)}
                                </span>
                                {entry.filesChanged && (
                                  <Badge variant="secondary" className="text-xs">
                                    <FileText className="mr-1 h-3 w-3" />
                                    {entry.filesChanged}{' '}
                                    {entry.filesChanged === 1 ? 'file' : 'files'}
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
                                minute: '2-digit',
                              })}
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                ) : (
                  // Empty state
                  <div className="py-12 text-center">
                    <Clock className="mx-auto mb-4 h-12 w-12 text-muted-foreground opacity-50" />
                    <h3 className="mb-2 text-lg font-semibold">No sync history yet</h3>
                    <p className="mx-auto max-w-sm text-sm text-muted-foreground">
                      Sync operations and deployments will appear here once you start managing this
                      entity.
                    </p>
                  </div>
                )}
              </div>
            </ScrollArea>
          </TabsContent>
        </Tabs>

        {/* Rollback Confirmation Dialog */}
        <RollbackDialog
          entity={entity}
          open={showRollbackDialog}
          onOpenChange={setShowRollbackDialog}
          onConfirm={handleRollback}
        />
      </SheetContent>
    </Sheet>
  );
}
