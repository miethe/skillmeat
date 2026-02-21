'use client';

import { useState } from 'react';
import { Package } from 'lucide-react';
import type { Artifact } from '@/types/artifact';
import {
  ArtifactBrowseCard,
  ArtifactBrowseCardSkeleton,
} from '@/components/collection/artifact-browse-card';
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
  /** @deprecated Not currently used by ArtifactBrowseCard - kept for API stability */
  onMoveToCollection?: (artifact: Artifact) => void;
  onManageGroups?: (artifact: Artifact) => void;
  /** @deprecated Not currently used by ArtifactBrowseCard - kept for API stability */
  onEdit?: (artifact: Artifact) => void;
  onDelete?: (artifact: Artifact) => void;
  /** Handler when a tag badge is clicked (for filtering) */
  onTagClick?: (tagName: string) => void;
  /** Handler when a group badge is clicked (for filtering) */
  onGroupClick?: (groupId: string) => void;
  /** Handler for navigating to the Manage page for this artifact */
  onManage?: (artifact: Artifact) => void;
  /** Set of selected artifact IDs for bulk operations */
  selectedArtifactIds?: Set<string>;
  /** Called when user toggles artifact selection */
  onToggleArtifactSelect?: (artifact: Artifact) => void;
}

function ArtifactGridSkeleton() {
  return (
    <div
      className="grid auto-rows-fr grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3"
      data-testid="artifact-grid-skeleton"
    >
      {[...Array(6)].map((_, i) => (
        <ArtifactBrowseCardSkeleton key={i} />
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
  onMoveToCollection: _onMoveToCollection,
  onManageGroups,
  onEdit: _onEdit,
  onDelete,
  onTagClick,
  onGroupClick,
  onManage,
  selectedArtifactIds,
  onToggleArtifactSelect,
}: ArtifactGridProps) {
  const [deleteArtifact, setDeleteArtifact] = useState<Artifact | null>(null);
  const [deployArtifact, setDeployArtifact] = useState<Artifact | null>(null);

  // Note: handleDelete is kept for the delete confirmation dialog flow
  // even though ArtifactBrowseCard doesn't currently expose a delete action
  void _onMoveToCollection; // Preserved for API stability
  void _onEdit; // Preserved for API stability

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
        {artifacts.map((artifact, index) => (
          <ArtifactBrowseCard
            key={`${artifact.id || artifact.name}-${artifact.type}-${index}`}
            artifact={artifact}
            onClick={() => onArtifactClick(artifact)}
            onQuickDeploy={() => handleDeploy(artifact)}
            onAddToGroup={onManageGroups ? () => onManageGroups(artifact) : undefined}
            onViewDetails={() => onArtifactClick(artifact)}
            showCollectionBadge={showCollectionBadge}
            onCollectionClick={onCollectionClick}
            onTagClick={onTagClick}
            onGroupClick={onGroupClick}
            onManage={onManage}
            isSelected={selectedArtifactIds?.has(artifact.id) ?? false}
            onToggleSelect={onToggleArtifactSelect}
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

      {/* Delete Confirmation Dialog - kept for future use when delete is added to card */}
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
