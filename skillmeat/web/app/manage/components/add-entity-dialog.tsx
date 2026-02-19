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
import { Blocks, Info } from 'lucide-react';

interface AddEntityDialogProps {
  entityType: ArtifactType | 'all';
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function AddEntityDialog({ entityType, open, onOpenChange }: AddEntityDialogProps) {
  // When entityType is 'all' or invalid, default to 'skill' for the add form
  const effectiveType: ArtifactType =
    entityType === 'all' || !ARTIFACT_TYPES[entityType as ArtifactType] ? 'skill' : entityType;
  const config = ARTIFACT_TYPES[effectiveType];
  const isComposite = effectiveType === 'composite';

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[90vh] max-w-2xl overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Add New {config.label}</DialogTitle>
          <DialogDescription>
            Add a new {config.label.toLowerCase()} to your collection from GitHub or a local source.
          </DialogDescription>
        </DialogHeader>

        {/* Composite-specific informational callout */}
        {isComposite && (
          <div
            className="flex items-start gap-3 rounded-lg border border-indigo-200 bg-indigo-50 px-4 py-3 dark:border-indigo-800 dark:bg-indigo-950/40"
            role="note"
            aria-label="Plugin import information"
          >
            <div className="flex shrink-0 items-center gap-1.5">
              <Blocks
                className="h-4 w-4 text-indigo-600 dark:text-indigo-400"
                aria-hidden="true"
              />
              <Info
                className="h-3.5 w-3.5 text-indigo-500 dark:text-indigo-400"
                aria-hidden="true"
              />
            </div>
            <div className="space-y-1">
              <p className="text-sm font-medium text-indigo-800 dark:text-indigo-200">
                Plugin Import
              </p>
              <p className="text-xs leading-relaxed text-indigo-700 dark:text-indigo-300">
                Plugins are composite artifacts that bundle multiple child artifacts (skills,
                commands, agents) together. When you import a plugin, all of its member artifacts
                are automatically added to your collection. Existing artifacts with matching names
                are linked rather than duplicated.
              </p>
              <p className="text-xs text-indigo-600/80 dark:text-indigo-400/80">
                For a full breakdown of members before importing, use the marketplace importer
                instead.
              </p>
            </div>
          </div>
        )}

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
