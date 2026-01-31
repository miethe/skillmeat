'use client';

import { useState } from 'react';
import { Package } from 'lucide-react';
import type { Artifact } from '@/types/artifact';
import { UnifiedCard, UnifiedCardSkeleton } from '@/components/shared/unified-card';
import { UnifiedCardActions } from '@/components/shared/unified-card-actions';
import { useCliCopy } from '@/hooks';
import { generateBasicDeployCommand } from '@/lib/cli-commands';
import { Badge } from '@/components/ui/badge';
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
  onCopyCliCommand,
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
  onCopyCliCommand?: () => void;
}) {
  return (
    <div className="group relative">
      <UnifiedCard item={artifact} onClick={onClick} />

      {/* Collection Badge - Top Right */}
      {showCollectionBadge && artifact.collection && (
        <Badge
          variant="outline"
          className="absolute right-2 top-2 z-10 cursor-pointer bg-background/95 text-xs backdrop-blur hover:bg-accent"
          onClick={(e) => {
            e.stopPropagation();
            artifact.collection && onCollectionClick?.(artifact.collection);
          }}
        >
          {artifact.collection}
        </Badge>
      )}

      {/* Actions Menu - Top Right (below collection badge if present) */}
      <div
        className={
          showCollectionBadge && artifact.collection
            ? 'absolute right-2 top-10'
            : 'absolute right-2 top-2'
        }
      >
        <UnifiedCardActions
          artifact={artifact}
          onDeploy={onDeploy}
          onMoveToCollection={onMoveToCollection}
          onAddToGroup={onManageGroups}
          onEdit={onEdit}
          onDelete={onDelete}
          onCopyCliCommand={onCopyCliCommand}
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
            onCopyCliCommand={() => handleCopyCliCommand(artifact.name)}
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
