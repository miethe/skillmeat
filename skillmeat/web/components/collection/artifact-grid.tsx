'use client';

import { useState } from 'react';
import { Package, MoreHorizontal, FolderPlus, Layers, Edit, Trash2, Rocket } from 'lucide-react';
import type { Artifact } from '@/types/artifact';
import { UnifiedCard, UnifiedCardSkeleton } from '@/components/shared/unified-card';
import { Badge } from '@/components/ui/badge';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Button } from '@/components/ui/button';
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

interface ArtifactGridProps {
  artifacts: Artifact[];
  isLoading?: boolean;
  onArtifactClick: (artifact: Artifact) => void;
  showCollectionBadge?: boolean;
  onCollectionClick?: (collectionId: string) => void;
  onMoveToCollection?: (artifact: Artifact) => void;
  onManageGroups?: (artifact: Artifact) => void;
  onEdit?: (artifact: Artifact) => void;
  onDelete?: (artifact: Artifact) => void;
}

interface ArtifactCardActionsProps {
  artifact: Artifact;
  collectionId?: string;
  onMoveToCollection?: () => void;
  onManageGroups?: () => void;
  onEdit?: () => void;
  onDelete?: () => void;
  onDeploy?: () => void;
}

function ArtifactCardActions({
  artifact,
  collectionId,
  onMoveToCollection,
  onManageGroups,
  onEdit,
  onDelete,
  onDeploy,
}: ArtifactCardActionsProps) {
  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button
          variant="ghost"
          size="icon"
          className="h-8 w-8 opacity-0 group-hover:opacity-100 transition-opacity md:opacity-0 touch:opacity-100"
          onClick={(e) => e.stopPropagation()}
          aria-label={`Actions for ${artifact.name}`}
        >
          <MoreHorizontal className="h-4 w-4" />
          <span className="sr-only">Open menu</span>
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" onClick={(e) => e.stopPropagation()}>
        <DropdownMenuItem onClick={onDeploy}>
          <Rocket className="mr-2 h-4 w-4" />
          Deploy to Project
        </DropdownMenuItem>
        <DropdownMenuSeparator />
        <DropdownMenuItem onClick={onMoveToCollection}>
          <FolderPlus className="mr-2 h-4 w-4" />
          {collectionId ? 'Move to Collection' : 'Add to Collection'}
        </DropdownMenuItem>
        <DropdownMenuItem onClick={onManageGroups}>
          <Layers className="mr-2 h-4 w-4" />
          Add to Group
        </DropdownMenuItem>
        <DropdownMenuSeparator />
        <DropdownMenuItem onClick={onEdit}>
          <Edit className="mr-2 h-4 w-4" />
          Edit
        </DropdownMenuItem>
        <DropdownMenuSeparator />
        <DropdownMenuItem
          onClick={onDelete}
          className="text-destructive focus:text-destructive"
        >
          <Trash2 className="mr-2 h-4 w-4" />
          Delete
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

function ArtifactCard({
  artifact,
  onClick,
  showCollectionBadge,
  onCollectionClick,
  onMoveToCollection,
  onManageGroups,
  onEdit,
  onDelete,
  onDeploy,
}: {
  artifact: Artifact;
  onClick: () => void;
  showCollectionBadge?: boolean;
  onCollectionClick?: (collectionId: string) => void;
  onMoveToCollection?: () => void;
  onManageGroups?: () => void;
  onEdit?: () => void;
  onDelete?: () => void;
  onDeploy?: () => void;
}) {
  return (
    <div className="relative group">
      <UnifiedCard item={artifact} onClick={onClick} />

      {/* Collection Badge - Top Right */}
      {showCollectionBadge && artifact.collection && (
        <Badge
          variant="outline"
          className="absolute top-2 right-2 cursor-pointer bg-background/95 backdrop-blur text-xs hover:bg-accent z-10"
          onClick={(e) => {
            e.stopPropagation();
            artifact.collection?.id && onCollectionClick?.(artifact.collection.id);
          }}
        >
          {artifact.collection?.name}
        </Badge>
      )}

      {/* Actions Menu - Top Right (below collection badge if present) */}
      <div className={showCollectionBadge && artifact.collection ? 'absolute top-10 right-2' : 'absolute top-2 right-2'}>
        <ArtifactCardActions
          artifact={artifact}
          collectionId={artifact.collection?.id}
          onDeploy={onDeploy}
          onMoveToCollection={onMoveToCollection}
          onManageGroups={onManageGroups}
          onEdit={onEdit}
          onDelete={onDelete}
        />
      </div>
    </div>
  );
}

function ArtifactGridSkeleton() {
  return (
    <div
      className="grid auto-rows-fr grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3"
      data-testid="artifact-grid-skeleton"
    >
      {[...Array(6)].map((_, i) => (
        <UnifiedCardSkeleton key={i} />
      ))}
    </div>
  );
}

export function ArtifactGrid({
  artifacts,
  isLoading,
  onArtifactClick,
  showCollectionBadge,
  onCollectionClick,
  onMoveToCollection,
  onManageGroups,
  onEdit,
  onDelete,
}: ArtifactGridProps) {
  const [deleteArtifact, setDeleteArtifact] = useState<Artifact | null>(null);
  const [deployArtifact, setDeployArtifact] = useState<Artifact | null>(null);

  const handleDelete = (artifact: Artifact) => {
    setDeleteArtifact(artifact);
  };

  const handleDeploy = (artifact: Artifact) => {
    setDeployArtifact(artifact);
  };

  const confirmDelete = () => {
    if (deleteArtifact) {
      onDelete?.(deleteArtifact);
      setDeleteArtifact(null);
    }
  };

  if (isLoading) {
    return <ArtifactGridSkeleton />;
  }

  if (artifacts.length === 0) {
    return (
      <div className="py-12 text-center" data-testid="artifact-grid-empty">
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
      <div
        className="grid auto-rows-fr grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3"
        role="grid"
        aria-label="Artifact grid"
        data-testid="artifact-grid"
      >
        {artifacts.map((artifact) => (
          <ArtifactCard
            key={artifact.id || `${artifact.name}-${artifact.type}`}
            artifact={artifact}
            onClick={() => onArtifactClick(artifact)}
            showCollectionBadge={showCollectionBadge}
            onCollectionClick={onCollectionClick}
            onDeploy={() => handleDeploy(artifact)}
            onMoveToCollection={onMoveToCollection ? () => onMoveToCollection(artifact) : undefined}
            onManageGroups={onManageGroups ? () => onManageGroups(artifact) : undefined}
            onEdit={onEdit ? () => onEdit(artifact) : undefined}
            onDelete={handleDelete ? () => handleDelete(artifact) : undefined}
          />
        ))}
      </div>

      {/* Deploy Dialog */}
      <DeployDialog
        artifact={deployArtifact}
        isOpen={!!deployArtifact}
        onClose={() => setDeployArtifact(null)}
        onSuccess={() => setDeployArtifact(null)}
      />

      {/* Delete Confirmation Dialog */}
      <AlertDialog open={!!deleteArtifact} onOpenChange={(open) => !open && setDeleteArtifact(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Artifact</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete "{deleteArtifact?.name}"? This action cannot be undone.
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
