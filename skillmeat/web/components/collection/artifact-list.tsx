'use client';

import { useState } from 'react';
import { Package, Terminal, Bot, Server, Webhook, AlertCircle, HelpCircle } from 'lucide-react';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import { DeployDialog } from '@/components/collection/deploy-dialog';
import { UnifiedCardActions } from '@/components/shared/unified-card-actions';
import type { Artifact, ArtifactType } from '@/types/artifact';
import { useCliCopy } from '@/hooks';
import { generateBasicDeployCommand } from '@/lib/cli-commands';

interface ArtifactListProps {
  artifacts: Artifact[];
  isLoading?: boolean;
  onArtifactClick: (artifact: Artifact) => void;
  showCollectionColumn?: boolean;
  onCollectionClick?: (collectionId: string) => void;
  onMoveToCollection?: (artifact: Artifact) => void;
  onManageGroups?: (artifact: Artifact) => void;
  onEdit?: (artifact: Artifact) => void;
  onDelete?: (artifact: Artifact) => void;
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

// Icon colors for type differentiation (matches grid view badge colors)
const artifactTypeIconColors: Record<ArtifactType, string> = {
  skill: 'text-blue-700 dark:text-blue-400',
  command: 'text-purple-700 dark:text-purple-400',
  agent: 'text-green-700 dark:text-green-400',
  mcp: 'text-orange-700 dark:text-orange-400',
  hook: 'text-pink-700 dark:text-pink-400',
};

// Subtle row background tints for visual differentiation
const artifactTypeRowTints: Record<ArtifactType, string> = {
  skill: 'bg-blue-500/[0.02] dark:bg-blue-500/[0.03]',
  command: 'bg-purple-500/[0.02] dark:bg-purple-500/[0.03]',
  agent: 'bg-green-500/[0.02] dark:bg-green-500/[0.03]',
  mcp: 'bg-orange-500/[0.02] dark:bg-orange-500/[0.03]',
  hook: 'bg-pink-500/[0.02] dark:bg-pink-500/[0.03]',
};

// Left border accent colors for each artifact type
const artifactTypeBorderAccents: Record<ArtifactType, string> = {
  skill: 'border-l-blue-500',
  command: 'border-l-purple-500',
  agent: 'border-l-green-500',
  mcp: 'border-l-orange-500',
  hook: 'border-l-pink-500',
};

const statusColors: Record<string, string> = {
  active: 'bg-green-500/10 text-green-600 border-green-500/20',
  outdated: 'bg-yellow-500/10 text-yellow-600 border-yellow-500/20',
  conflict: 'bg-orange-500/10 text-orange-600 border-orange-500/20',
  error: 'bg-red-500/10 text-red-600 border-red-500/20',
};

function ArtifactListSkeleton({ showCollectionColumn }: { showCollectionColumn?: boolean }) {
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Name</TableHead>
          {showCollectionColumn && <TableHead>Collection</TableHead>}
          <TableHead>Type</TableHead>
          <TableHead>Status</TableHead>
          <TableHead>Version</TableHead>
          <TableHead>Scope</TableHead>
          <TableHead className="hidden md:table-cell">Deployments</TableHead>
          <TableHead className="hidden lg:table-cell">Last Updated</TableHead>
          <TableHead className="w-[50px]"></TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {[...Array(5)].map((_, i) => (
          <TableRow key={i}>
            <TableCell>
              <div className="space-y-2">
                <Skeleton className="h-4 w-32" />
                <Skeleton className="h-3 w-48" />
              </div>
            </TableCell>
            {showCollectionColumn && (
              <TableCell>
                <Skeleton className="h-5 w-20 rounded-full" />
              </TableCell>
            )}
            <TableCell>
              <Skeleton className="h-4 w-16" />
            </TableCell>
            <TableCell>
              <Skeleton className="h-5 w-16 rounded-full" />
            </TableCell>
            <TableCell>
              <Skeleton className="h-4 w-12" />
            </TableCell>
            <TableCell>
              <Skeleton className="h-4 w-12" />
            </TableCell>
            <TableCell className="hidden md:table-cell">
              <Skeleton className="h-4 w-8" />
            </TableCell>
            <TableCell className="hidden lg:table-cell">
              <Skeleton className="h-4 w-16" />
            </TableCell>
            <TableCell>
              <Skeleton className="h-8 w-8" />
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}

function formatRelativeTime(dateString: string): string {
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
}

export function ArtifactList({
  artifacts,
  isLoading,
  onArtifactClick,
  showCollectionColumn,
  onCollectionClick,
  onMoveToCollection,
  onManageGroups,
  onEdit,
  onDelete,
}: ArtifactListProps) {
  const [deleteArtifact, setDeleteArtifact] = useState<Artifact | null>(null);
  const [deployArtifact, setDeployArtifact] = useState<Artifact | null>(null);
  const { copy } = useCliCopy();

  const handleDelete = (artifact: Artifact) => {
    setDeleteArtifact(artifact);
  };

  const handleDeploy = (artifact: Artifact) => {
    setDeployArtifact(artifact);
  };

  const handleCopyCliCommand = (artifactName: string) => {
    const command = generateBasicDeployCommand(artifactName);
    copy(command);
  };

  const confirmDelete = () => {
    if (deleteArtifact) {
      onDelete?.(deleteArtifact);
      setDeleteArtifact(null);
    }
  };

  if (isLoading) {
    return <ArtifactListSkeleton showCollectionColumn={showCollectionColumn} />;
  }

  if (artifacts.length === 0) {
    return (
      <div className="py-12 text-center" data-testid="artifact-list-empty">
        <Package className="mx-auto h-12 w-12 text-muted-foreground/50" />
        <h3 className="mt-4 text-lg font-semibold">No artifacts found</h3>
        <p className="mt-2 text-sm text-muted-foreground">
          Try adjusting your filters or add new artifacts to your collection.
        </p>
      </div>
    );
  }

  return (
    <>
      <div className="rounded-md border" data-testid="artifact-list">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Name</TableHead>
              {showCollectionColumn && <TableHead>Collection</TableHead>}
              <TableHead>Type</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Version</TableHead>
              <TableHead>Scope</TableHead>
              <TableHead className="hidden md:table-cell">Deployments</TableHead>
              <TableHead className="hidden lg:table-cell">Last Updated</TableHead>
              <TableHead className="w-[50px]"></TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {artifacts.map((artifact, index) => {
              const Icon = artifactTypeIcons[artifact.type] || HelpCircle;
              const iconColor =
                artifactTypeIconColors[artifact.type] || 'text-gray-500 dark:text-gray-400';
              const rowTint =
                artifactTypeRowTints[artifact.type] || 'bg-gray-500/[0.02] dark:bg-gray-500/[0.03]';
              const borderAccent = artifactTypeBorderAccents[artifact.type] || 'border-l-gray-400';
              const typeLabel = artifactTypeLabels[artifact.type] || artifact.type || 'Unknown';
              return (
                <TableRow
                  key={`${artifact.id}-${index}`}
                  className={`cursor-pointer border-l-2 ${borderAccent} ${rowTint}`}
                  onClick={() => onArtifactClick(artifact)}
                  role="button"
                  tabIndex={0}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' || e.key === ' ') {
                      e.preventDefault();
                      onArtifactClick(artifact);
                    }
                  }}
                  aria-label={`View details for ${artifact.name}`}
                  data-testid="artifact-row"
                >
                  <TableCell>
                    <div className="space-y-1">
                      <div className="flex items-center gap-2 font-medium">
                        {artifact.name}
                        {artifact.upstream?.updateAvailable && (
                          <AlertCircle
                            className="h-3 w-3 text-yellow-600"
                            data-testid="outdated-indicator"
                          />
                        )}
                      </div>
                      <div className="text-xs text-muted-foreground">
                        {artifact.description || artifact.name}
                      </div>
                    </div>
                  </TableCell>
                  {showCollectionColumn && (
                    <TableCell>
                      {artifact.collection ? (
                        <Badge
                          variant="outline"
                          className="cursor-pointer hover:bg-accent"
                          onClick={(e) => {
                            e.stopPropagation();
                            artifact.collection && onCollectionClick?.(artifact.collection);
                          }}
                        >
                          {artifact.collection}
                        </Badge>
                      ) : (
                        <span className="text-xs text-muted-foreground">-</span>
                      )}
                    </TableCell>
                  )}
                  <TableCell>
                    <div className="flex items-center gap-2" data-testid="type-badge">
                      <Icon className={`h-4 w-4 ${iconColor}`} aria-hidden="true" />
                      <span className="text-sm">{typeLabel}</span>
                    </div>
                  </TableCell>
                  <TableCell>
                    <Badge
                      className={statusColors[artifact.syncStatus]}
                      variant="outline"
                      data-testid="status-badge"
                    >
                      {artifact.syncStatus}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    <code className="rounded bg-muted px-1.5 py-0.5 text-xs">
                      {artifact.version || 'N/A'}
                    </code>
                  </TableCell>
                  <TableCell>
                    <Badge variant="secondary" className="text-xs capitalize">
                      {artifact.scope}
                    </Badge>
                  </TableCell>
                  <TableCell className="hidden md:table-cell">
                    <div className="text-sm">{artifact.usageStats?.totalDeployments ?? 0}</div>
                  </TableCell>
                  <TableCell className="hidden lg:table-cell">
                    <div className="text-sm text-muted-foreground">
                      {formatRelativeTime(artifact.updatedAt)}
                    </div>
                  </TableCell>
                  <TableCell>
                    <UnifiedCardActions
                      artifact={artifact}
                      alwaysVisible={true}
                      onDeploy={() => handleDeploy(artifact)}
                      onMoveToCollection={
                        onMoveToCollection ? () => onMoveToCollection(artifact) : undefined
                      }
                      onAddToGroup={onManageGroups ? () => onManageGroups(artifact) : undefined}
                      onEdit={onEdit ? () => onEdit(artifact) : undefined}
                      onDelete={handleDelete ? () => handleDelete(artifact) : undefined}
                      onCopyCliCommand={() => handleCopyCliCommand(artifact.name)}
                    />
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </div>

      {/* Deploy Dialog */}
      <DeployDialog
        artifact={deployArtifact}
        isOpen={!!deployArtifact}
        onClose={() => setDeployArtifact(null)}
        onSuccess={() => setDeployArtifact(null)}
      />

      {/* Delete Confirmation Dialog */}
      <AlertDialog
        open={!!deleteArtifact}
        onOpenChange={(open) => !open && setDeleteArtifact(null)}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Artifact</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete "{deleteArtifact?.name}"? This action cannot be
              undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={confirmDelete}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
}
