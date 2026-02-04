'use client';

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { EntityForm } from '@/components/entity/entity-form';
import { ArtifactType, ARTIFACT_TYPES } from '@/types/artifact';

interface AddEntityDialogProps {
  entityType: ArtifactType | 'all';
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function AddEntityDialog({ entityType, open, onOpenChange }: AddEntityDialogProps) {
  // When entityType is 'all' or invalid, default to 'skill' for the add form
  const effectiveType: ArtifactType = entityType === 'all' || !ARTIFACT_TYPES[entityType as ArtifactType]
    ? 'skill'
    : entityType;
  const config = ARTIFACT_TYPES[effectiveType];

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[90vh] max-w-2xl overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Add New {config.label}</DialogTitle>
          <DialogDescription>
            Add a new {config.label.toLowerCase()} to your collection from GitHub or a local source.
          </DialogDescription>
        </DialogHeader>

        <EntityForm
          mode="create"
          entityType={effectiveType}
          onSuccess={() => onOpenChange(false)}
          onCancel={() => onOpenChange(false)}
        />
      </DialogContent>
    </Dialog>
  );
}
