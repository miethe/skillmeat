'use client';

import { useState } from 'react';
import {
  Package,
  Terminal,
  Bot,
  Server,
  Webhook,
  ExternalLink,
  Calendar,
  User,
  FileText,
  TrendingUp,
  AlertCircle,
  CheckCircle,
  XCircle,
  Tag,
  Copy,
  Trash2,
  RefreshCw,
  Upload,
} from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { DeployDialog } from './deploy-dialog';
import { SyncDialog } from './sync-dialog';
import { VersionTreeView } from './version-tree';
import { useVersionGraph, useArtifactTags } from '@/hooks';
import type { Artifact, ArtifactType } from '@/types/artifact';

interface ArtifactDetailProps {
  artifact: Artifact | null;
  isOpen: boolean;
  onClose: () => void;
  isLoading?: boolean;
  onTagClick?: (tagSlug: string) => void;
}

const artifactTypeIcons: Record<ArtifactType, React.ComponentType<{ className?: string }>> = {
  skill: Package,
  command: Terminal,
  agent: Bot,
  mcp: Server,
  hook: Webhook,
};

const artifactTypeLabels: Record<ArtifactType, string> = {
  skill: 'Skill',
  command: 'Command',
  agent: 'Agent',
  mcp: 'MCP Server',
  hook: 'Hook',
};

const statusIcons: Record<string, React.ComponentType<{ className?: string }>> = {
  synced: CheckCircle,
  modified: AlertCircle,
  outdated: AlertCircle,
  conflict: AlertCircle,
  error: XCircle,
};

const statusColors: Record<string, string> = {
  synced: 'text-green-600',
  modified: 'text-blue-600',
  outdated: 'text-yellow-600',
  conflict: 'text-orange-600',
  error: 'text-red-600',
};

function DetailSkeleton() {
  return (
    <div className="space-y-6">
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

function formatDate(dateString: string): string {
  return new Date(dateString).toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  });
}

function formatRelativeTime(dateString: string): string {
  const date = new Date(dateString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);
  const diffDays = Math.floor(diffMs / 86400000);

  if (diffMins < 1) return 'just now';
  if (diffMins < 60) return `${diffMins} minutes ago`;
  if (diffHours < 24) return `${diffHours} hours ago`;
  if (diffDays < 30) return `${diffDays} days ago`;
  return formatDate(dateString);
}

export function ArtifactDetail({
  artifact,
  isOpen,
  onClose,
  isLoading,
  onTagClick,
}: ArtifactDetailProps) {
  const [isDeployDialogOpen, setIsDeployDialogOpen] = useState(false);
  const [isSyncDialogOpen, setIsSyncDialogOpen] = useState(false);

  // Fetch version graph when modal is open
  const artifactId = artifact ? `${artifact.type}:${artifact.name}` : '';
  const { data: versionGraph, isLoading: isVersionGraphLoading } = useVersionGraph(artifactId);

  // Fetch tags for the artifact
  const { data: tags } = useArtifactTags(artifact?.id);

  const Icon = artifact ? artifactTypeIcons[artifact.type] : Package;
  const StatusIcon = (
    artifact ? statusIcons[artifact.syncStatus] : CheckCircle
  ) as React.ComponentType<{ className?: string }>;

  return (
    <>
      <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
        <DialogContent className="flex max-h-[90vh] max-w-2xl flex-col overflow-hidden p-0">
          {isLoading || !artifact ? (
            <div className="p-6">
              <DetailSkeleton />
            </div>
          ) : (
            <>
              {/* Header Section - Fixed */}
              <div className="border-b px-6 pb-4 pt-6">
                <DialogHeader>
                  <div className="flex items-start gap-4">
                    <div className="flex-shrink-0 rounded-lg bg-primary/10 p-3">
                      <Icon className="h-6 w-6 text-primary" />
                    </div>
                    <div className="min-w-0 flex-1 space-y-2">
                      <DialogTitle className="text-2xl">{artifact.name}</DialogTitle>
                      <DialogDescription>
                        {artifactTypeLabels[artifact.type]} · {artifact.name}
                      </DialogDescription>
                      <div className="flex items-center gap-2 pt-1">
                        <StatusIcon className={`h-4 w-4 ${statusColors[artifact.syncStatus]}`} />
                        <Badge variant="outline" className="capitalize">
                          {artifact.syncStatus}
                        </Badge>
                        <Badge variant="secondary" className="capitalize">
                          {artifact.scope}
                        </Badge>
                      </div>
                    </div>
                  </div>
                </DialogHeader>
              </div>

              {/* Scrollable Content with Tabs */}
              <Tabs defaultValue="overview" className="flex flex-1 flex-col px-6">
                <TabsList className="h-auto w-full justify-start rounded-none border-b bg-transparent p-0">
                  <TabsTrigger
                    value="overview"
                    className="rounded-none border-b-2 border-transparent data-[state=active]:border-primary data-[state=active]:bg-transparent"
                  >
                    Overview
                  </TabsTrigger>
                  <TabsTrigger
                    value="versions"
                    className="rounded-none border-b-2 border-transparent data-[state=active]:border-primary data-[state=active]:bg-transparent"
                  >
                    Version History
                  </TabsTrigger>
                </TabsList>

                <TabsContent value="overview" className="mt-0 flex-1">
                  <ScrollArea className="h-full">
                    <div className="space-y-6 py-4">
                      {/* Description */}
                      {artifact.description && (
                        <div>
                          <p className="text-sm leading-relaxed text-muted-foreground">
                            {artifact.description}
                          </p>
                        </div>
                      )}

                      {/* Metadata Grid */}
                      <div className="space-y-4">
                        <h3 className="text-sm font-semibold text-foreground">Metadata</h3>
                        <div className="grid grid-cols-2 gap-4">
                          <MetadataItem
                            icon={<Package className="h-4 w-4" />}
                            label="Version"
                            value={artifact.version || 'N/A'}
                          />
                          <MetadataItem
                            icon={<User className="h-4 w-4" />}
                            label="Author"
                            value={artifact.author || 'Unknown'}
                          />
                          <MetadataItem
                            icon={<FileText className="h-4 w-4" />}
                            label="License"
                            value={artifact.license || 'N/A'}
                          />
                          <MetadataItem
                            icon={<Calendar className="h-4 w-4" />}
                            label="Created"
                            value={formatDate(artifact.createdAt)}
                          />
                        </div>
                      </div>

                      {/* Tags from API */}
                      {tags && tags.length > 0 && (
                        <div className="space-y-3">
                          <h3 className="flex items-center gap-2 text-sm font-semibold text-foreground">
                            <Tag className="h-4 w-4" />
                            Tags
                          </h3>
                          <div className="flex flex-wrap gap-2">
                            {tags.map((tag) => (
                              <Badge
                                key={tag.id}
                                variant="secondary"
                                colorStyle={tag.color}
                                className="cursor-pointer hover:opacity-80"
                                onClick={() => onTagClick?.(tag.slug)}
                              >
                                {tag.name}
                              </Badge>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Legacy tags from metadata (fallback) */}
                      {(!tags || tags.length === 0) &&
                        artifact.tags &&
                        artifact.tags.length > 0 && (
                          <div className="space-y-3">
                            <h3 className="flex items-center gap-2 text-sm font-semibold text-foreground">
                              <Tag className="h-4 w-4" />
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

                      {/* Upstream Status */}
                      <div className="space-y-4">
                        <h3 className="text-sm font-semibold text-foreground">Upstream Status</h3>
                        <div className="space-y-3 rounded-lg border bg-muted/50 p-4">
                          {artifact.upstream?.enabled ? (
                            <>
                              <div className="flex items-center justify-between gap-4">
                                <span className="text-sm text-muted-foreground">Source</span>
                                {artifact.source && (
                                  <a
                                    href={artifact.upstream.url}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="flex items-center gap-1 text-sm font-medium text-primary hover:underline"
                                  >
                                    {artifact.source}
                                    <ExternalLink className="h-3 w-3" />
                                  </a>
                                )}
                              </div>
                              <div className="flex items-center justify-between gap-4">
                                <span className="text-sm text-muted-foreground">
                                  Current Version
                                </span>
                                <code className="rounded border bg-background px-2 py-1 text-xs">
                                  {artifact.version || 'N/A'}
                                </code>
                              </div>
                              {artifact.upstream.updateAvailable && (
                                <div className="flex items-center justify-between gap-4">
                                  <span className="text-sm text-muted-foreground">
                                    Latest Version
                                  </span>
                                  <code className="rounded border border-yellow-500/20 bg-yellow-500/10 px-2 py-1 text-xs text-yellow-600">
                                    {artifact.upstream.version}
                                  </code>
                                </div>
                              )}
                              {artifact.upstream.lastChecked && (
                                <div className="flex items-center justify-between gap-4">
                                  <span className="text-sm text-muted-foreground">
                                    Last Checked
                                  </span>
                                  <span className="text-sm font-medium">
                                    {formatRelativeTime(artifact.upstream.lastChecked)}
                                  </span>
                                </div>
                              )}
                            </>
                          ) : (
                            <p className="text-sm text-muted-foreground">
                              No upstream source configured
                            </p>
                          )}
                        </div>
                      </div>

                      {/* Usage Stats */}
                      {artifact.usageStats && (
                        <div className="space-y-4">
                          <h3 className="flex items-center gap-2 text-sm font-semibold text-foreground">
                            <TrendingUp className="h-4 w-4" />
                            Usage Statistics
                          </h3>
                          <div className="grid grid-cols-2 gap-3">
                            <StatCard
                              label="Total Deployments"
                              value={artifact.usageStats.totalDeployments}
                            />
                            <StatCard
                              label="Active Projects"
                              value={artifact.usageStats.activeProjects}
                            />
                            <StatCard label="Usage Count" value={artifact.usageStats.usageCount} />
                            <StatCard
                              label="Last Used"
                              value={
                                artifact.usageStats.lastUsed
                                  ? formatRelativeTime(artifact.usageStats.lastUsed)
                                  : 'Never'
                              }
                            />
                          </div>
                        </div>
                      )}

                      {/* Aliases */}
                      {artifact.aliases && artifact.aliases.length > 0 && (
                        <div className="space-y-3">
                          <h3 className="text-sm font-semibold text-foreground">Aliases</h3>
                          <div className="flex flex-wrap gap-2">
                            {artifact.aliases.map((alias) => (
                              <code
                                key={alias}
                                className="rounded border bg-muted px-3 py-1.5 text-xs"
                              >
                                {alias}
                              </code>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  </ScrollArea>
                </TabsContent>

                <TabsContent value="versions" className="mt-0 flex-1">
                  <ScrollArea className="h-full">
                    <div className="py-4">
                      <VersionTreeView graph={versionGraph} isLoading={isVersionGraphLoading} />
                    </div>
                  </ScrollArea>
                </TabsContent>
              </Tabs>

              {/* Actions Footer - Fixed */}
              <div className="border-t bg-muted/30 px-6 py-4">
                <div className="space-y-3">
                  <h3 className="text-sm font-semibold text-foreground">Actions</h3>
                  <div className="grid grid-cols-2 gap-2">
                    {/* Deploy Button */}
                    <Button
                      variant="default"
                      className="justify-start"
                      onClick={() => setIsDeployDialogOpen(true)}
                    >
                      <Upload className="mr-2 h-4 w-4" />
                      Deploy
                    </Button>

                    {/* Sync Button */}
                    {artifact.upstream?.enabled && (
                      <Button
                        variant={artifact.upstream.updateAvailable ? 'default' : 'outline'}
                        className="justify-start"
                        onClick={() => setIsSyncDialogOpen(true)}
                      >
                        <RefreshCw className="mr-2 h-4 w-4" />
                        {artifact.upstream.updateAvailable ? 'Update' : 'Sync'}
                      </Button>
                    )}

                    <Button variant="outline" className="justify-start">
                      <Copy className="mr-2 h-4 w-4" />
                      Duplicate
                    </Button>
                    <Button
                      variant="outline"
                      className="justify-start text-destructive hover:text-destructive"
                    >
                      <Trash2 className="mr-2 h-4 w-4" />
                      Remove
                    </Button>
                  </div>
                </div>
              </div>
            </>
          )}
        </DialogContent>
      </Dialog>

      {/* Deploy Dialog */}
      <DeployDialog
        artifact={artifact}
        isOpen={isDeployDialogOpen}
        onClose={() => setIsDeployDialogOpen(false)}
        onSuccess={() => {
          setIsDeployDialogOpen(false);
        }}
      />

      {/* Sync Dialog */}
      <SyncDialog
        artifact={artifact}
        isOpen={isSyncDialogOpen}
        onClose={() => setIsSyncDialogOpen(false)}
        onSuccess={() => {
          setIsSyncDialogOpen(false);
        }}
      />
    </>
  );
}

function MetadataItem({
  icon,
  label,
  value,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
}) {
  return (
    <div className="space-y-1">
      <div className="flex items-center gap-1 text-xs text-muted-foreground">
        {icon}
        <span>{label}</span>
      </div>
      <p className="truncate text-sm font-medium" title={value}>
        {value}
      </p>
    </div>
  );
}

function StatCard({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="space-y-1 rounded-lg border p-3">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="text-lg font-semibold">{value}</p>
    </div>
  );
}
