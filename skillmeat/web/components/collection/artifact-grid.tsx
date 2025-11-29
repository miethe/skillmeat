'use client';

import { Package } from 'lucide-react';
import type { Artifact } from '@/types/artifact';
import { UnifiedCard, UnifiedCardSkeleton } from '@/components/shared/unified-card';
import { Card, CardContent, CardHeader } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';

interface ArtifactGridProps {
  artifacts: Artifact[];
  isLoading?: boolean;
  onArtifactClick: (artifact: Artifact) => void;
}

function ArtifactCard({ artifact, onClick }: { artifact: Artifact; onClick: () => void }) {
  return <UnifiedCard item={artifact} onClick={onClick} />;
}

function ArtifactGridSkeleton() {
  return (
    <div
      className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3"
      data-testid="artifact-grid-skeleton"
    >
      {[...Array(6)].map((_, i) => (
        <UnifiedCardSkeleton key={i} />
      ))}
    </div>
  );
}

export function ArtifactGrid({ artifacts, isLoading, onArtifactClick }: ArtifactGridProps) {
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
    <div
      className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3"
      role="grid"
      aria-label="Artifact grid"
      data-testid="artifact-grid"
    >
      {artifacts.map((artifact) => (
        <ArtifactCard
          key={artifact.id}
          artifact={artifact}
          onClick={() => onArtifactClick(artifact)}
        />
      ))}
    </div>
  );
}
