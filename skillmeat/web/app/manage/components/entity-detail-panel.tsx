'use client';

import { useState } from 'react';
import { X, Calendar, Tag, GitBranch, AlertCircle, CheckCircle2, Clock } from 'lucide-react';
import * as LucideIcons from 'lucide-react';
import { LucideIcon } from 'lucide-react';
import { Sheet, SheetContent, SheetHeader, SheetTitle } from '@/components/ui/sheet';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Entity, ENTITY_TYPES } from '@/types/entity';
import { useEntityLifecycle } from '@/hooks/useEntityLifecycle';
import { DiffViewer } from '@/components/entity/diff-viewer';

interface EntityDetailPanelProps {
  entity: Entity | null;
  open: boolean;
  onClose: () => void;
}

export function EntityDetailPanel({ entity, open, onClose }: EntityDetailPanelProps) {
  const [activeTab, setActiveTab] = useState('overview');
  const { deployEntity, syncEntity } = useEntityLifecycle();
  const [isDeploying, setIsDeploying] = useState(false);
  const [isSyncing, setIsSyncing] = useState(false);

  if (!entity) {
    return null;
  }

  const config = ENTITY_TYPES[entity.type];
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

        <Tabs value={activeTab} onValueChange={setActiveTab} className="mt-6 flex flex-col h-[calc(100vh-8rem)]">
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
          <TabsContent value="sync" className="flex-1 overflow-hidden">
            <ScrollArea className="h-full pr-4">
              <div className="space-y-6">
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

                {/* Diff Preview Placeholder */}
                {entity.status === 'modified' && (
                  <div>
                    <h3 className="text-sm font-medium mb-2">Changes</h3>
                    <div className="border rounded-lg p-4 bg-muted/20">
                      <p className="text-sm text-muted-foreground text-center">
                        Diff preview coming soon
                      </p>
                    </div>
                  </div>
                )}

                {entity.status === 'outdated' && (
                  <div className="bg-blue-500/10 border border-blue-500/20 rounded-lg p-4">
                    <p className="text-sm text-blue-700 dark:text-blue-400">
                      A newer version is available upstream. Click "Sync with Upstream" to update.
                    </p>
                  </div>
                )}

                {entity.status === 'conflict' && (
                  <div className="bg-red-500/10 border border-red-500/20 rounded-lg p-4">
                    <p className="text-sm text-red-700 dark:text-red-400">
                      There are conflicting changes between local and upstream versions.
                      Manual resolution may be required.
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
                <div className="text-center py-12">
                  <Clock className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
                  <h3 className="text-lg font-semibold mb-2">Version History</h3>
                  <p className="text-sm text-muted-foreground">
                    Version history tracking coming soon
                  </p>
                </div>
              </div>
            </ScrollArea>
          </TabsContent>
        </Tabs>
      </SheetContent>
    </Sheet>
  );
}
