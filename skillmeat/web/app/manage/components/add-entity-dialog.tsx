'use client';

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { EntityForm } from '@/components/entity/entity-form';
import { EntityType, ENTITY_TYPES } from '@/types/entity';

interface AddEntityDialogProps {
  entityType: EntityType;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function AddEntityDialog({ entityType, open, onOpenChange }: AddEntityDialogProps) {
  const config = ENTITY_TYPES[entityType];

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Add New {config.label}</DialogTitle>
          <DialogDescription>
            Add a new {config.label.toLowerCase()} to your collection from GitHub or a local source.
          </DialogDescription>
        </DialogHeader>

        <EntityForm
          mode="create"
          entityType={entityType}
          onSuccess={() => onOpenChange(false)}
          onCancel={() => onOpenChange(false)}
        />
      </DialogContent>
    </Dialog>
  );
}
