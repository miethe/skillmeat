'use client';

import * as React from 'react';
import { Plus, Pencil, Trash2, Lock } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
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
import { Skeleton } from '@/components/ui/skeleton';
import { useEntityTypeConfigs, useDeleteEntityTypeConfig } from '@/hooks';
import { useToast } from '@/hooks';
import type { EntityTypeConfig } from '@/types/context-entity';
import { EntityTypeConfigForm } from './entity-type-config-form';

// ---------------------------------------------------------------------------
// EntityTypeConfigList
// ---------------------------------------------------------------------------

/**
 * Table listing all entity type configurations with create/edit/delete actions.
 * Built-in types cannot be deleted; only their content_template is editable.
 */
export function EntityTypeConfigList() {
  const { data: configs, isLoading, error } = useEntityTypeConfigs();
  const deleteConfig = useDeleteEntityTypeConfig();
  const { toast } = useToast();

  const [formOpen, setFormOpen] = React.useState(false);
  const [editingConfig, setEditingConfig] = React.useState<EntityTypeConfig | null>(null);
  const [deleteTarget, setDeleteTarget] = React.useState<EntityTypeConfig | null>(null);

  const handleEdit = React.useCallback((config: EntityTypeConfig) => {
    setEditingConfig(config);
    setFormOpen(true);
  }, []);

  const handleCreate = React.useCallback(() => {
    setEditingConfig(null);
    setFormOpen(true);
  }, []);

  const handleFormClose = React.useCallback(() => {
    setFormOpen(false);
    setEditingConfig(null);
  }, []);

  const handleDeleteConfirm = React.useCallback(async () => {
    if (!deleteTarget) return;

    try {
      await deleteConfig.mutateAsync(deleteTarget.slug);
      toast({
        title: 'Entity type deleted',
        description: `"${deleteTarget.display_name}" has been removed.`,
      });
    } catch (err) {
      toast({
        title: 'Delete failed',
        description: err instanceof Error ? err.message : 'An error occurred',
        variant: 'destructive',
      });
    } finally {
      setDeleteTarget(null);
    }
  }, [deleteTarget, deleteConfig, toast]);

  if (isLoading) {
    return (
      <div className="space-y-2" role="status" aria-label="Loading entity types">
        {[...Array(4)].map((_, i) => (
          <Skeleton key={i} className="h-12 w-full" />
        ))}
      </div>
    );
  }

  if (error) {
    return (
      <p className="text-sm text-destructive" role="alert">
        Failed to load entity type configurations:{' '}
        {error instanceof Error ? error.message : 'Unknown error'}
      </p>
    );
  }

  return (
    <div className="space-y-4">
      {/* Header row */}
      <div className="flex items-center justify-between">
        <p className="text-sm text-muted-foreground">
          {configs?.length ?? 0} entity type{configs?.length !== 1 ? 's' : ''} configured
        </p>
        <Button onClick={handleCreate} size="sm">
          <Plus className="mr-2 h-4 w-4" />
          Add Entity Type
        </Button>
      </div>

      {/* Table */}
      <div className="rounded-md border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-10" aria-label="Icon" />
              <TableHead>Name</TableHead>
              <TableHead className="hidden sm:table-cell">Slug</TableHead>
              <TableHead className="hidden md:table-cell">Description</TableHead>
              <TableHead className="w-24">Type</TableHead>
              <TableHead className="w-24 text-right">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {configs && configs.length > 0 ? (
              configs.map((config) => (
                <EntityTypeConfigRow
                  key={config.slug}
                  config={config}
                  onEdit={handleEdit}
                  onDelete={setDeleteTarget}
                />
              ))
            ) : (
              <TableRow>
                <TableCell colSpan={6} className="py-8 text-center text-muted-foreground">
                  No entity type configurations found.
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </div>

      {/* Create / Edit form dialog */}
      <EntityTypeConfigForm
        open={formOpen}
        onClose={handleFormClose}
        editingConfig={editingConfig}
      />

      {/* Delete confirmation dialog */}
      <AlertDialog open={!!deleteTarget} onOpenChange={(open) => !open && setDeleteTarget(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete entity type?</AlertDialogTitle>
            <AlertDialogDescription>
              This will permanently remove the &ldquo;{deleteTarget?.display_name}&rdquo; entity
              type configuration. This action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDeleteConfirm}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}

// ---------------------------------------------------------------------------
// EntityTypeConfigRow
// ---------------------------------------------------------------------------

interface EntityTypeConfigRowProps {
  config: EntityTypeConfig;
  onEdit: (config: EntityTypeConfig) => void;
  onDelete: (config: EntityTypeConfig) => void;
}

function EntityTypeConfigRow({ config, onEdit, onDelete }: EntityTypeConfigRowProps) {
  const truncatedDescription =
    config.description && config.description.length > 80
      ? `${config.description.slice(0, 80)}…`
      : config.description;

  return (
    <TableRow>
      {/* Icon */}
      <TableCell className="text-lg" aria-label={`Icon for ${config.display_name}`}>
        {config.icon ?? '📄'}
      </TableCell>

      {/* Name */}
      <TableCell className="font-medium">{config.display_name}</TableCell>

      {/* Slug */}
      <TableCell className="hidden font-mono text-xs text-muted-foreground sm:table-cell">
        {config.slug}
      </TableCell>

      {/* Description */}
      <TableCell className="hidden text-sm text-muted-foreground md:table-cell">
        {truncatedDescription ?? <span className="italic">No description</span>}
      </TableCell>

      {/* Built-in badge */}
      <TableCell>
        {config.is_builtin ? (
          <Badge variant="secondary" className="flex w-fit items-center gap-1">
            <Lock className="h-3 w-3" />
            Built-in
          </Badge>
        ) : (
          <Badge variant="outline">Custom</Badge>
        )}
      </TableCell>

      {/* Actions */}
      <TableCell className="text-right">
        <div className="flex items-center justify-end gap-1">
          <Button
            variant="ghost"
            size="icon"
            aria-label={`Edit ${config.display_name}`}
            onClick={() => onEdit(config)}
          >
            <Pencil className="h-4 w-4" />
          </Button>
          <Button
            variant="ghost"
            size="icon"
            aria-label={
              config.is_builtin
                ? `Cannot delete built-in type ${config.display_name}`
                : `Delete ${config.display_name}`
            }
            disabled={config.is_builtin}
            onClick={() => !config.is_builtin && onDelete(config)}
          >
            <Trash2 className="h-4 w-4" />
          </Button>
        </div>
      </TableCell>
    </TableRow>
  );
}
