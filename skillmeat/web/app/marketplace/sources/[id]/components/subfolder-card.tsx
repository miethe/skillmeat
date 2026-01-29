'use client';

import { Folder, ChevronRight } from 'lucide-react';
import { Card } from '@/components/ui/card';
import { cn } from '@/lib/utils';
import type { FolderNode } from '@/lib/tree-builder';

/**
 * Props for SubfolderCard component.
 */
interface SubfolderCardProps {
  /** Folder node data */
  folder: FolderNode;
  /** Callback when card is clicked */
  onSelect: (path: string) => void;
}

/**
 * SubfolderCard component displays a single subfolder as a clickable card.
 *
 * Shows folder name, artifact count, and click-to-navigate affordance.
 * Entire card is interactive and keyboard accessible.
 *
 * @example
 * ```tsx
 * <SubfolderCard
 *   folder={folderNode}
 *   onSelect={(path) => console.log('Navigate to:', path)}
 * />
 * ```
 */
export function SubfolderCard({ folder, onSelect }: SubfolderCardProps) {
  /**
   * Handle card click - navigate to folder.
   */
  const handleClick = () => {
    onSelect(folder.fullPath);
  };

  /**
   * Handle keyboard navigation (Enter/Space).
   */
  const handleKeyDown = (e: React.KeyboardEvent<HTMLDivElement>) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      onSelect(folder.fullPath);
    }
  };

  // Format artifact count with correct singular/plural
  const artifactCountText =
    folder.totalArtifactCount === 1 ? '1 artifact' : `${folder.totalArtifactCount} artifacts`;

  // Build accessible label
  const ariaLabel = `Open ${folder.name} folder with ${folder.totalArtifactCount} ${folder.totalArtifactCount === 1 ? 'artifact' : 'artifacts'}`;

  return (
    <Card
      role="button"
      tabIndex={0}
      onClick={handleClick}
      onKeyDown={handleKeyDown}
      aria-label={ariaLabel}
      className={cn(
        'group cursor-pointer rounded-lg border p-4',
        'transition-all duration-200 hover:border-primary/50 hover:shadow-sm',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2'
      )}
    >
      {/* Header Row: Folder Icon + Name */}
      <div className="mb-2 flex items-center gap-2">
        <Folder className="h-5 w-5 text-muted-foreground transition-colors duration-200 group-hover:text-primary" />
        <h3 className="truncate text-sm font-medium">{folder.name}</h3>
      </div>

      {/* Stats Row: Artifact Count */}
      <div className="mb-2">
        <p className="text-xs text-muted-foreground">{artifactCountText}</p>
      </div>

      {/* Action Row: Click to Explore */}
      <div className="flex items-center gap-1 text-xs text-muted-foreground transition-colors duration-200 group-hover:text-primary">
        <span>Click to explore</span>
        <ChevronRight className="h-3 w-3" />
      </div>
    </Card>
  );
}
