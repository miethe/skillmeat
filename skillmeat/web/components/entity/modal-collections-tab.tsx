'use client';

import { useState } from 'react';
import { FolderOpen, Plus, X, MoreHorizontal, FolderPlus } from 'lucide-react';
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
import {
  useCollectionContext,
  useRemoveArtifactFromCollection,
  useToast,
} from '@/hooks';
import { useQueryClient } from '@tanstack/react-query';
import { MoveCopyDialog } from '@/components/collection/move-copy-dialog';
import { CreateCollectionDialog } from '@/components/collection/create-collection-dialog';
import type { Entity } from '@/types/entity';
import type { Artifact } from '@/types/artifact';

interface ModalCollectionsTabProps {
  entity: Entity;
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
 * <ModalCollectionsTab entity={entity} />
 * ```
 */
export function ModalCollectionsTab({ entity }: ModalCollectionsTabProps) {
  const [showAddDialog, setShowAddDialog] = useState(false);
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const { isLoadingCollections } = useCollectionContext();
  const removeFromCollection = useRemoveArtifactFromCollection();
  const queryClient = useQueryClient();
  const { toast } = useToast();

  // Convert Entity to Artifact format for MoveCopyDialog
  const artifactForDialog: Artifact = {
    id: entity.id,
    name: entity.name,
    type: entity.type,
    scope: 'user', // Entities are typically user-scoped
    status: 'active',
    version: entity.version,
    source: entity.source,
    metadata: {
      description: entity.description,
      version: entity.version,
      tags: entity.tags,
    },
    upstreamStatus: {
      hasUpstream: !!entity.source,
      isOutdated: entity.status === 'outdated',
    },
    usageStats: {
      totalDeployments: 0,
      activeProjects: entity.projectPath ? 1 : 0,
      usageCount: 0,
    },
    createdAt: entity.deployedAt || new Date().toISOString(),
    updatedAt: entity.modifiedAt || new Date().toISOString(),
    aliases: entity.aliases,
    collection: entity.collection
      ? {
          id: entity.collection,
          name: entity.collection,
        }
      : undefined,
  };

  // Use entity's collections array directly (populated by artifactToEntity)
  const artifactCollections = entity.collections || [];

  const handleRemoveFromCollection = async (collectionId: string) => {
    try {
      await removeFromCollection.mutateAsync({
        collectionId,
        artifactId: entity.id,
      });

      // Invalidate artifacts queries to refresh entity.collections
      queryClient.invalidateQueries({ queryKey: ['artifacts'] });

      toast({
        title: 'Removed from Collection',
        description: `${entity.name} has been removed from the collection.`,
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
              <Button
                variant="outline"
                size="sm"
                onClick={() => setShowAddDialog(true)}
              >
                <Plus className="mr-2 h-4 w-4" />
                Add to Collection
              </Button>
              <button
                onClick={() => setShowCreateDialog(true)}
                className="text-sm text-muted-foreground hover:text-foreground transition-colors"
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

                {/* Groups within collection - Placeholder for Phase 5 */}
                {/* Future enhancement: Show groups as badges when group data is available */}
              </div>
            ))}
          </div>
        )}
      </ScrollArea>

      {/* Add to Collection dialog */}
      <MoveCopyDialog
        open={showAddDialog}
        onOpenChange={setShowAddDialog}
        artifacts={[artifactForDialog]}
        sourceCollectionId={entity.collection}
        onSuccess={() => {
          setShowAddDialog(false);
          // Invalidate artifacts queries to refresh entity.collections
          queryClient.invalidateQueries({ queryKey: ['artifacts'] });
          toast({
            title: 'Added to Collection',
            description: `${entity.name} has been added to the collection.`,
          });
        }}
      />

      {/* Create Collection dialog */}
      <CreateCollectionDialog
        open={showCreateDialog}
        onOpenChange={setShowCreateDialog}
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
            <Skeleton className="h-4 w-full" />
          </div>
        ))}
      </div>
    </div>
  );
}
