/**
 * ContextModulesTab Component (UI-4.4)
 *
 * Tab panel for managing context modules within the memory management page.
 * Lists existing modules as cards, supports creating new modules via an
 * inline form modal, and provides edit/delete/preview actions per module.
 *
 * Context modules define named configurations that select which memory items
 * to include in a context pack. Each module has selectors (memory_types,
 * min_confidence, file_patterns, workflow_stages) and a priority for ordering.
 */

'use client';

import * as React from 'react';
import { useState, useCallback, useEffect } from 'react';
import {
  Plus,
  Pencil,
  Trash2,
  Eye,
  Layers,
  AlertTriangle,
  RefreshCw,
  Loader2,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from '@/components/ui/card';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from '@/components/ui/dialog';
import { Label } from '@/components/ui/label';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Skeleton } from '@/components/ui/skeleton';
import { cn } from '@/lib/utils';
import { ConfirmActionDialog } from './confirm-action-dialog';

// Hooks that are being created in parallel -- import from where they WILL be
import {
  useContextModules,
  useCreateContextModule,
  useDeleteContextModule,
} from '@/hooks/use-context-modules';

import type { ContextModuleResponse } from '@/sdk/models/ContextModuleResponse';

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

export interface ContextModulesTabProps {
  /** Project ID to load context modules for. */
  projectId: string;
}

// ---------------------------------------------------------------------------
// Form State
// ---------------------------------------------------------------------------

interface ModuleFormState {
  name: string;
  description: string;
  priority: number;
}

interface ModuleFormErrors {
  name?: string;
  priority?: string;
}

const INITIAL_FORM_STATE: ModuleFormState = {
  name: '',
  description: '',
  priority: 5,
};

// ---------------------------------------------------------------------------
// Selector Summary Helper
// ---------------------------------------------------------------------------

/**
 * Builds a human-readable summary of selector criteria for display
 * in module cards as badge chips.
 */
function buildSelectorSummary(
  selectors: Record<string, unknown> | null | undefined
): string[] {
  if (!selectors || Object.keys(selectors).length === 0) {
    return [];
  }

  const chips: string[] = [];

  if (Array.isArray(selectors.memory_types) && selectors.memory_types.length > 0) {
    chips.push(`Types: ${selectors.memory_types.join(', ')}`);
  }

  if (typeof selectors.min_confidence === 'number') {
    chips.push(`Min confidence: ${selectors.min_confidence}`);
  }

  if (Array.isArray(selectors.file_patterns) && selectors.file_patterns.length > 0) {
    chips.push(`Patterns: ${selectors.file_patterns.length}`);
  }

  if (Array.isArray(selectors.workflow_stages) && selectors.workflow_stages.length > 0) {
    chips.push(`Stages: ${selectors.workflow_stages.join(', ')}`);
  }

  return chips;
}

// ---------------------------------------------------------------------------
// Skeleton for loading state
// ---------------------------------------------------------------------------

function ModuleCardSkeleton() {
  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <Skeleton className="h-5 w-40" />
          <Skeleton className="h-5 w-12 rounded-full" />
        </div>
        <Skeleton className="h-4 w-64 mt-1" />
      </CardHeader>
      <CardContent>
        <div className="flex items-center gap-2">
          <Skeleton className="h-5 w-24 rounded-full" />
          <Skeleton className="h-5 w-32 rounded-full" />
        </div>
      </CardContent>
    </Card>
  );
}

const SKELETON_COUNT = 3;

// ---------------------------------------------------------------------------
// Module Card Sub-Component
// ---------------------------------------------------------------------------

interface ModuleCardProps {
  module: ContextModuleResponse;
  onEdit: (module: ContextModuleResponse) => void;
  onDelete: (module: ContextModuleResponse) => void;
  onPreview: (module: ContextModuleResponse) => void;
}

function ModuleCard({ module, onEdit, onDelete, onPreview }: ModuleCardProps) {
  const selectorChips = buildSelectorSummary(module.selectors);
  const memoryCount = Array.isArray(module.memory_items)
    ? module.memory_items.length
    : 0;

  return (
    <Card className="group transition-colors hover:bg-accent/30">
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2">
              <CardTitle className="text-base font-semibold leading-tight">
                {module.name}
              </CardTitle>
              <Badge variant="outline" className="shrink-0 text-xs">
                Priority {module.priority ?? 5}
              </Badge>
            </div>
            {module.description && (
              <CardDescription className="mt-1 line-clamp-2">
                {module.description}
              </CardDescription>
            )}
          </div>

          {/* Action buttons -- visible on hover/focus-within */}
          <div
            className={cn(
              'flex items-center gap-1 shrink-0 opacity-0 transition-opacity',
              'group-hover:opacity-100 group-focus-within:opacity-100'
            )}
          >
            <Button
              variant="ghost"
              size="icon"
              className="h-7 w-7"
              onClick={() => onPreview(module)}
              aria-label={`Preview pack for module: ${module.name}`}
            >
              <Eye className="h-3.5 w-3.5" aria-hidden="true" />
            </Button>
            <Button
              variant="ghost"
              size="icon"
              className="h-7 w-7"
              onClick={() => onEdit(module)}
              aria-label={`Edit module: ${module.name}`}
            >
              <Pencil className="h-3.5 w-3.5" aria-hidden="true" />
            </Button>
            <Button
              variant="ghost"
              size="icon"
              className="h-7 w-7"
              onClick={() => onDelete(module)}
              aria-label={`Delete module: ${module.name}`}
            >
              <Trash2 className="h-3.5 w-3.5 text-destructive" aria-hidden="true" />
            </Button>
          </div>
        </div>
      </CardHeader>

      <CardContent>
        <div className="flex flex-wrap items-center gap-2">
          {selectorChips.map((chip) => (
            <Badge key={chip} variant="secondary" className="text-xs font-normal">
              {chip}
            </Badge>
          ))}
          {selectorChips.length === 0 && (
            <span className="text-xs text-muted-foreground">No selectors configured</span>
          )}
          {memoryCount > 0 && (
            <Badge variant="outline" className="text-xs font-normal">
              {memoryCount} {memoryCount === 1 ? 'memory' : 'memories'}
            </Badge>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

// ---------------------------------------------------------------------------
// Create Module Form Modal
// ---------------------------------------------------------------------------

interface CreateModuleModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  projectId: string;
}

function CreateModuleModal({ open, onOpenChange, projectId }: CreateModuleModalProps) {
  const [form, setForm] = useState<ModuleFormState>({ ...INITIAL_FORM_STATE });
  const [errors, setErrors] = useState<ModuleFormErrors>({});

  // Reset form when dialog opens
  useEffect(() => {
    if (open) {
      setForm({ ...INITIAL_FORM_STATE });
      setErrors({});
    }
  }, [open]);

  const createMutation = useCreateContextModule({
    onSuccess: () => {
      onOpenChange(false);
    },
  });

  const isSubmitting = createMutation.isPending;

  const validate = useCallback((): boolean => {
    const newErrors: ModuleFormErrors = {};

    if (!form.name.trim()) {
      newErrors.name = 'Name is required';
    } else if (form.name.trim().length > 255) {
      newErrors.name = 'Name must be 255 characters or fewer';
    }

    if (form.priority < 0 || form.priority > 100) {
      newErrors.priority = 'Priority must be between 0 and 100';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  }, [form]);

  const handleSubmit = useCallback(
    (e: React.FormEvent) => {
      e.preventDefault();
      if (!validate()) return;

      createMutation.mutate({
        projectId,
        data: {
          name: form.name.trim(),
          description: form.description.trim() || null,
          priority: form.priority,
        },
      });
    },
    [form, projectId, validate, createMutation]
  );

  const updateField = useCallback(
    <K extends keyof ModuleFormState>(key: K, value: ModuleFormState[K]) => {
      setForm((prev) => ({ ...prev, [key]: value }));
      setErrors((prev) => ({ ...prev, [key]: undefined }));
    },
    []
  );

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>Create Context Module</DialogTitle>
          <DialogDescription>
            Define a new module that selects memories for context packs.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Name */}
          <div className="space-y-2">
            <Label htmlFor="module-name">
              Name <span className="text-destructive" aria-hidden="true">*</span>
            </Label>
            <Input
              id="module-name"
              placeholder="e.g. Architecture Decisions"
              value={form.name}
              onChange={(e) => updateField('name', e.target.value)}
              aria-required="true"
              aria-describedby={errors.name ? 'name-error' : undefined}
              aria-invalid={!!errors.name}
              className={cn(errors.name && 'border-destructive')}
            />
            {errors.name && (
              <p id="name-error" className="text-xs text-destructive" role="alert">
                {errors.name}
              </p>
            )}
          </div>

          {/* Description */}
          <div className="space-y-2">
            <Label htmlFor="module-description">Description</Label>
            <Textarea
              id="module-description"
              placeholder="What this module captures (optional)"
              value={form.description}
              onChange={(e) => updateField('description', e.target.value)}
              rows={3}
            />
          </div>

          {/* Priority */}
          <div className="space-y-2">
            <Label htmlFor="module-priority">Priority (0-100)</Label>
            <div className="flex items-center gap-3">
              <input
                id="module-priority"
                type="range"
                min={0}
                max={100}
                value={form.priority}
                onChange={(e) => updateField('priority', parseInt(e.target.value, 10))}
                className="flex-1 accent-current"
                aria-label="Module priority"
                aria-valuemin={0}
                aria-valuemax={100}
                aria-valuenow={form.priority}
                aria-valuetext={`Priority ${form.priority}`}
                aria-describedby={errors.priority ? 'priority-error' : undefined}
              />
              <span className="min-w-[2.5rem] rounded-md bg-muted px-2 py-1 text-center text-sm font-medium">
                {form.priority}
              </span>
            </div>
            {errors.priority && (
              <p id="priority-error" className="text-xs text-destructive" role="alert">
                {errors.priority}
              </p>
            )}
          </div>

          {/* Mutation error */}
          {createMutation.error && (
            <p className="text-sm text-destructive" role="alert">
              {createMutation.error.message || 'Failed to create module. Please try again.'}
            </p>
          )}

          {/* Footer */}
          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
              disabled={isSubmitting}
            >
              Cancel
            </Button>
            <Button type="submit" disabled={isSubmitting} aria-busy={isSubmitting}>
              {isSubmitting && (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" aria-hidden="true" />
              )}
              Create Module
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

// ---------------------------------------------------------------------------
// Main Component
// ---------------------------------------------------------------------------

/**
 * ContextModulesTab -- lists and manages context modules for a project.
 *
 * Shows module cards with selector summaries, priority badges, and
 * hover-revealed action buttons. Provides a create modal for new modules
 * and a confirmation dialog for deletion.
 *
 * @example
 * ```tsx
 * <ContextModulesTab projectId="proj-123" />
 * ```
 */
export function ContextModulesTab({ projectId }: ContextModulesTabProps) {
  // ---------------------------------------------------------------------------
  // Data
  // ---------------------------------------------------------------------------
  const {
    data: modulesData,
    isLoading,
    isError,
    error,
    refetch,
  } = useContextModules({ projectId });

  const modules = modulesData?.items ?? [];

  // ---------------------------------------------------------------------------
  // Modal state
  // ---------------------------------------------------------------------------
  const [createModalOpen, setCreateModalOpen] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<ContextModuleResponse | null>(null);

  // ---------------------------------------------------------------------------
  // Delete mutation
  // ---------------------------------------------------------------------------
  const deleteMutation = useDeleteContextModule({
    onSuccess: () => setDeleteTarget(null),
  });

  // ---------------------------------------------------------------------------
  // Handlers
  // ---------------------------------------------------------------------------
  const handleCreateNew = useCallback(() => {
    setCreateModalOpen(true);
  }, []);

  const handleEdit = useCallback((_module: ContextModuleResponse) => {
    // Edit functionality will be wired in a follow-up task.
    // For now this is a placeholder -- the button renders and is accessible.
  }, []);

  const handleDelete = useCallback((module: ContextModuleResponse) => {
    setDeleteTarget(module);
  }, []);

  const handleConfirmDelete = useCallback(() => {
    if (!deleteTarget) return;
    deleteMutation.mutate({
      projectId,
      moduleId: deleteTarget.id,
    });
  }, [deleteTarget, deleteMutation, projectId]);

  const handlePreview = useCallback((_module: ContextModuleResponse) => {
    // Preview Pack functionality will be wired in a follow-up task.
  }, []);

  // ---------------------------------------------------------------------------
  // Loading State
  // ---------------------------------------------------------------------------
  if (isLoading) {
    return (
      <div className="space-y-4 p-6" role="status" aria-label="Loading context modules">
        <div className="flex items-center justify-between">
          <Skeleton className="h-8 w-48" />
          <Skeleton className="h-9 w-32" />
        </div>
        {Array.from({ length: SKELETON_COUNT }).map((_, i) => (
          <ModuleCardSkeleton key={i} />
        ))}
        <span className="sr-only">Loading context modules...</span>
      </div>
    );
  }

  // ---------------------------------------------------------------------------
  // Error State
  // ---------------------------------------------------------------------------
  if (isError) {
    return (
      <div
        className="flex flex-col items-center justify-center py-16 text-center"
        role="alert"
      >
        <div className="rounded-full bg-destructive/10 p-4 mb-4">
          <AlertTriangle className="h-8 w-8 text-destructive" aria-hidden="true" />
        </div>
        <h3 className="text-lg font-semibold">Failed to load context modules</h3>
        <p className="mt-2 max-w-sm text-sm text-muted-foreground">
          {error?.message ?? 'An unexpected error occurred.'}
        </p>
        <Button variant="outline" className="mt-4" size="sm" onClick={() => refetch()}>
          <RefreshCw className="mr-2 h-4 w-4" aria-hidden="true" />
          Retry
        </Button>
      </div>
    );
  }

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------
  return (
    <div className="space-y-4 p-6">
      {/* Header row */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold tracking-tight">Context Modules</h2>
          <p className="text-sm text-muted-foreground">
            Configure modules that select memories for context packs
          </p>
        </div>
        <Button size="sm" onClick={handleCreateNew}>
          <Plus className="mr-2 h-4 w-4" aria-hidden="true" />
          New Module
        </Button>
      </div>

      {/* Module list or empty state */}
      {modules.length === 0 ? (
        /* Empty State */
        <div className="flex flex-col items-center justify-center py-16 text-center">
          <div className="rounded-full bg-muted p-4 mb-4">
            <Layers className="h-8 w-8 text-muted-foreground" aria-hidden="true" />
          </div>
          <h3 className="text-lg font-semibold">No context modules yet</h3>
          <p className="mt-2 max-w-sm text-sm text-muted-foreground">
            Context modules define which memories to include when building context
            packs. Create your first module to get started.
          </p>
          <Button className="mt-4" size="sm" onClick={handleCreateNew}>
            <Plus className="mr-2 h-4 w-4" aria-hidden="true" />
            Create First Module
          </Button>
        </div>
      ) : (
        /* Module Cards */
        <>
          <div className="sr-only" aria-live="polite" aria-atomic="true">
            {modules.length} {modules.length === 1 ? 'context module' : 'context modules'}{' '}
            displayed
          </div>
          <div
            className="space-y-3"
            role="list"
            aria-label="Context modules"
          >
            {modules.map((module) => (
              <div key={module.id} role="listitem">
                <ModuleCard
                  module={module}
                  onEdit={handleEdit}
                  onDelete={handleDelete}
                  onPreview={handlePreview}
                />
              </div>
            ))}
          </div>
        </>
      )}

      {/* Create Module Modal */}
      <CreateModuleModal
        open={createModalOpen}
        onOpenChange={setCreateModalOpen}
        projectId={projectId}
      />

      {/* Delete Confirmation Dialog */}
      <ConfirmActionDialog
        open={!!deleteTarget}
        onOpenChange={(open) => {
          if (!open) setDeleteTarget(null);
        }}
        title="Delete Context Module?"
        description={
          deleteTarget
            ? `This will permanently delete the "${deleteTarget.name}" module. Any memories associated with this module will not be affected.`
            : ''
        }
        confirmLabel="Delete"
        confirmVariant="destructive"
        onConfirm={handleConfirmDelete}
        isLoading={deleteMutation.isPending}
      />
    </div>
  );
}
