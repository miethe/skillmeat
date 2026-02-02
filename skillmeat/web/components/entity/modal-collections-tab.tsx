'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { FolderOpen, Plus, X, MoreHorizontal, FolderPlus, Layers, ExternalLink } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Skeleton } from '@/components/ui/skeleton';
import { useCollectionContext, useRemoveArtifactFromCollection, useToast } from '@/hooks';
import { useQueryClient } from '@tanstack/react-query';
import { MoveCopyDialog } from '@/components/collection/move-copy-dialog';
import { CreateCollectionDialog } from '@/components/collection/create-collection-dialog';
import { AddToGroupDialog } from '@/components/collection/add-to-group-dialog';
import { GroupsDisplay } from './groups-display';
import type { Artifact } from '@/types/artifact';

interface ModalCollectionsTabProps {
  /**
   * The artifact to display collections for.
   * Canonical prop name - use this for new code.
   */
  artifact?: Artifact;
  /**
   * @deprecated Use `artifact` instead. This prop name is maintained for backward compatibility.
   * Will be removed in a future version.
   */
  entity?: Artifact;
  /**
   * Context determines which action buttons to show per collection.
   * - 'discovery': No extra navigation buttons (default behavior)
   * - 'operations': Shows "View in Collection" button per collection
   */
  context?: 'discovery' | 'operations';
  /**
   * Callback invoked before navigation (e.g., to close the modal).
   */
  onNavigate?: () => void;
}

/**
 * Collections Tab for Unified Entity Modal
 *
 * Displays which collections and groups the artifact belongs to.
 * Allows adding to additional collections and removing from current ones.
 *
 * Features:
 * - List of collections containing this artifact
 * - Groups within each collection (as badges)
 * - "Add to Collection" button opens MoveCopyDialog
 * - "Remove from Collection" via dropdown menu
 * - Empty state when artifact not in any collection
 * - Loading skeleton during data fetch
 *
 * @example
 * ```tsx
 * <ModalCollectionsTab artifact={artifact} />
 * ```
 */
export function ModalCollectionsTab({
  artifact,
  entity,
  context,
  onNavigate,
}: ModalCollectionsTabProps) {
  // Support both 'artifact' (canonical) and 'entity' (deprecated) prop names
  const resolvedArtifact = artifact ?? entity;
  const router = useRouter();

  const [showAddDialog, setShowAddDialog] = useState(false);
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [showGroupDialog, setShowGroupDialog] = useState(false);
  const { isLoadingCollections } = useCollectionContext();
  const removeFromCollection = useRemoveArtifactFromCollection();
  const queryClient = useQueryClient();
  const { toast } = useToast();

  // Early return if no artifact provided
  if (!resolvedArtifact) {
    return null;
  }

  // Artifact type now has flattened metadata - no conversion needed
  // The artifact is already in the correct format for child dialogs

  // Use artifact's collections array directly (already populated in Artifact type)
  const artifactCollections = resolvedArtifact.collections || [];

  const handleRemoveFromCollection = async (collectionId: string) => {
    try {
      await removeFromCollection.mutateAsync({
        collectionId,
        artifactId: resolvedArtifact.id,
      });

      // Invalidate artifacts queries to refresh artifact.collections
      queryClient.invalidateQueries({ queryKey: ['artifacts'] });

      toast({
        title: 'Removed from Collection',
        description: `${resolvedArtifact.name} has been removed from the collection.`,
      });
    } catch (error) {
      console.error('Failed to remove from collection:', error);
      toast({
        title: 'Removal Failed',
        description:
          error instanceof Error ? error.message : 'Failed to remove artifact from collection',
        variant: 'destructive',
      });
    }
  };

  const handleViewInCollection = (collectionId: string) => {
    onNavigate?.();
    const params = new URLSearchParams({
      collection: collectionId,
      artifact: resolvedArtifact.id,
      returnTo: '/manage',
    });
    router.push(`/collection?${params.toString()}`);
  };

  if (isLoadingCollections) {
    return <CollectionsTabSkeleton />;
  }

  return (
    <div className="space-y-4">
      {/* Header with Add button */}
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-medium">Collections & Groups</h3>
        <div className="flex gap-2">
          <Button variant="ghost" size="sm" onClick={() => setShowCreateDialog(true)}>
            <FolderPlus className="mr-2 h-4 w-4" />
            New
          </Button>
          <Button variant="outline" size="sm" onClick={() => setShowGroupDialog(true)}>
            <Layers className="mr-2 h-4 w-4" />
            Add to Group
          </Button>
          <Button variant="outline" size="sm" onClick={() => setShowAddDialog(true)}>
            <Plus className="mr-2 h-4 w-4" />
            Add to Collection
          </Button>
        </div>
      </div>

      {/* Collections list */}
      <ScrollArea className="h-[300px]">
        {artifactCollections.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-8 text-center">
            <FolderOpen className="h-12 w-12 text-muted-foreground/50" />
            <p className="mt-4 text-sm text-muted-foreground">
              This artifact is not in any collection.
            </p>
            <div className="mt-4 flex flex-col items-center gap-2">
              <Button variant="outline" size="sm" onClick={() => setShowAddDialog(true)}>
                <Plus className="mr-2 h-4 w-4" />
                Add to Collection
              </Button>
              <button
                onClick={() => setShowCreateDialog(true)}
                className="text-sm text-muted-foreground transition-colors hover:text-foreground"
              >
                or create a new one
              </button>
            </div>
          </div>
        ) : (
          <div className="space-y-3">
            {artifactCollections.map((collection) => (
              <div key={collection.id} className="rounded-lg border p-3">
                {/* Collection header */}
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <FolderOpen className="h-4 w-4 text-muted-foreground" />
                    <span className="font-medium">{collection.name}</span>
                    <Badge variant="secondary" className="text-xs">
                      {collection.artifact_count} artifact
                      {collection.artifact_count !== 1 ? 's' : ''}
                    </Badge>
                  </div>
                  <div className="flex items-center gap-1">
                    {context === 'operations' && (
                      <Button
                        variant="ghost"
                        size="sm"
                        className="h-8 text-xs"
                        onClick={() => handleViewInCollection(collection.id)}
                      >
                        <ExternalLink className="mr-1 h-3 w-3" />
                        View in Collection
                      </Button>
                    )}
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <Button variant="ghost" size="icon" className="h-8 w-8">
                          <MoreHorizontal className="h-4 w-4" />
                        </Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end">
                        <DropdownMenuItem
                          onClick={() => handleRemoveFromCollection(collection.id)}
                          className="text-destructive"
                        >
                          <X className="mr-2 h-4 w-4" />
                          Remove from Collection
                        </DropdownMenuItem>
                      </DropdownMenuContent>
                    </DropdownMenu>
                  </div>
                </div>

                {/* Groups within this collection */}
                <div className="mt-3 border-t pt-3">
                  <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
                    <Layers className="h-3 w-3" />
                    <span className="font-medium">Groups in {collection.name}</span>
                  </div>
                  <div className="mt-2">
                    <GroupsDisplay
                      collectionId={collection.id}
                      artifactId={resolvedArtifact.id}
                      maxBadges={3}
                    />
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </ScrollArea>

      {/* Add to Collection dialog */}
      <MoveCopyDialog
        open={showAddDialog}
        onOpenChange={setShowAddDialog}
        artifacts={[resolvedArtifact]}
        sourceCollectionId={resolvedArtifact.collection}
        onSuccess={() => {
          setShowAddDialog(false);
          // Invalidate artifacts queries to refresh artifact.collections
          queryClient.invalidateQueries({ queryKey: ['artifacts'] });
          toast({
            title: 'Added to Collection',
            description: `${resolvedArtifact.name} has been added to the collection.`,
          });
        }}
      />

      {/* Create Collection dialog */}
      <CreateCollectionDialog open={showCreateDialog} onOpenChange={setShowCreateDialog} />

      {/* Add to Group dialog */}
      <AddToGroupDialog
        open={showGroupDialog}
        onOpenChange={setShowGroupDialog}
        artifact={resolvedArtifact}
        onSuccess={() => {
          setShowGroupDialog(false);
          // Invalidate artifacts queries to refresh artifact.collections
          queryClient.invalidateQueries({ queryKey: ['artifacts'] });
          toast({
            title: 'Added to Group',
            description: `${resolvedArtifact.name} has been added to the group.`,
          });
        }}
      />
    </div>
  );
}

/**
 * Loading skeleton for Collections tab
 */
function CollectionsTabSkeleton() {
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <Skeleton className="h-5 w-32" />
        <Skeleton className="h-9 w-36" />
      </div>
      <div className="space-y-3">
        {[1, 2].map((i) => (
          <div key={i} className="space-y-2 rounded-lg border p-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Skeleton className="h-4 w-4" />
                <Skeleton className="h-5 w-32" />
                <Skeleton className="h-5 w-16" />
              </div>
              <Skeleton className="h-8 w-8" />
            </div>
            {/* Groups section skeleton */}
            <div className="mt-3 border-t pt-3">
              <div className="flex items-center gap-1.5">
                <Skeleton className="h-3 w-3" />
                <Skeleton className="h-3 w-24" />
              </div>
              <div className="mt-2">
                <Skeleton className="h-3 w-40" />
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
