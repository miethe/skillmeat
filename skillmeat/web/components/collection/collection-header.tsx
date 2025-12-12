'use client';

import { MoreVertical, Edit, Trash2 } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import type { Collection } from '@/types/collections';

interface CollectionHeaderProps {
  collection: Collection | null;
  artifactCount: number;
  isAllCollections: boolean;
  onEdit?: () => void;
  onDelete?: () => void;
}

export function CollectionHeader({
  collection,
  artifactCount,
  isAllCollections,
  onEdit,
  onDelete,
}: CollectionHeaderProps) {
  const title = isAllCollections ? 'All Collections' : collection?.name || 'Collection';
  const description = isAllCollections
    ? 'Browse artifacts across all collections'
    : collection?.version
      ? `Version ${collection.version}`
      : undefined;

  return (
    <div className="border-b bg-background px-6 py-4">
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1 space-y-1">
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold tracking-tight">{title}</h1>
            <Badge variant="secondary" className="text-sm">
              {artifactCount} {artifactCount === 1 ? 'artifact' : 'artifacts'}
            </Badge>
          </div>
          {description && <p className="text-sm text-muted-foreground">{description}</p>}
        </div>

        {/* Actions dropdown - only show for single collection */}
        {!isAllCollections && collection && (
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" size="icon" aria-label="Collection actions">
                <MoreVertical className="h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem onClick={onEdit} disabled={!onEdit}>
                <Edit className="mr-2 h-4 w-4" />
                Edit Collection
              </DropdownMenuItem>
              <DropdownMenuItem
                onClick={onDelete}
                disabled={!onDelete}
                className="text-destructive focus:text-destructive"
              >
                <Trash2 className="mr-2 h-4 w-4" />
                Delete Collection
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        )}
      </div>
    </div>
  );
}
