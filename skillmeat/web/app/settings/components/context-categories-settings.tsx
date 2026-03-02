'use client';

import * as React from 'react';
import { Plus, Pencil, Trash2, Lock } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from '@/components/ui/dialog';
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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Skeleton } from '@/components/ui/skeleton';
import {
  useEntityCategories,
  useCreateEntityCategory,
  useUpdateEntityCategory,
  useDeleteEntityCategory,
  type EntityCategory,
  type EntityCategoryCreateRequest,
  type EntityCategoryUpdateRequest,
} from '@/hooks';
import { useEntityTypeConfigs } from '@/hooks';
import { useToast } from '@/hooks';
import { ColorSelector } from '@/components/shared/color-selector';

// ---------------------------------------------------------------------------
// Slug helpers
// ---------------------------------------------------------------------------

function slugify(value: string): string {
  return value
    .toLowerCase()
    .trim()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '');
}

// ---------------------------------------------------------------------------
// Form state
// ---------------------------------------------------------------------------

interface CategoryFormState {
  name: string;
  slug: string;
  description: string;
  color: string;
  entity_type_slug: string;
}

const EMPTY_FORM: CategoryFormState = {
  name: '',
  slug: '',
  description: '',
  color: '',
  entity_type_slug: '',
};

function buildInitialFormState(category: EntityCategory | null): CategoryFormState {
  if (!category) return { ...EMPTY_FORM };
  return {
    name: category.name,
    slug: category.slug,
    description: category.description ?? '',
    color: category.color ?? '',
    entity_type_slug: category.entity_type_slug ?? '',
  };
}

// ---------------------------------------------------------------------------
// CategoryForm dialog
// ---------------------------------------------------------------------------

interface CategoryFormProps {
  open: boolean;
  onClose: () => void;
  editingCategory: EntityCategory | null;
}

function CategoryForm({ open, onClose, editingCategory }: CategoryFormProps) {
  const isEdit = editingCategory !== null;
  const isBuiltin = editingCategory?.is_builtin ?? false;

  const { data: entityTypeConfigs } = useEntityTypeConfigs();
  const createCategory = useCreateEntityCategory();
  const updateCategory = useUpdateEntityCategory();
  const { toast } = useToast();

  const [form, setForm] = React.useState<CategoryFormState>(() =>
    buildInitialFormState(editingCategory)
  );
  const [slugManuallyEdited, setSlugManuallyEdited] = React.useState(false);
  const [isSubmitting, setIsSubmitting] = React.useState(false);

  // Reinitialise form when dialog opens with a different category
  React.useEffect(() => {
    if (open) {
      setForm(buildInitialFormState(editingCategory));
      setSlugManuallyEdited(false);
    }
  }, [open, editingCategory]);

  const setField = React.useCallback(
    <K extends keyof CategoryFormState>(key: K, value: CategoryFormState[K]) => {
      setForm((prev) => ({ ...prev, [key]: value }));
    },
    []
  );

  const handleNameChange = React.useCallback(
    (value: string) => {
      setField('name', value);
      if (!slugManuallyEdited && !isEdit) {
        setField('slug', slugify(value));
      }
    },
    [setField, slugManuallyEdited, isEdit]
  );

  const handleSlugChange = React.useCallback(
    (value: string) => {
      setSlugManuallyEdited(true);
      setField('slug', value);
    },
    [setField]
  );

  const handleSubmit = React.useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault();
      if (!form.name.trim()) return;

      setIsSubmitting(true);
      try {
        if (isEdit && editingCategory) {
          const updateData: EntityCategoryUpdateRequest = {
            name: form.name || undefined,
            description: form.description || undefined,
            color: form.color || undefined,
            entity_type_slug: form.entity_type_slug || undefined,
          };
          await updateCategory.mutateAsync({ slug: editingCategory.slug, data: updateData });
          toast({
            title: 'Category updated',
            description: `"${form.name}" has been updated.`,
          });
        } else {
          const createData: EntityCategoryCreateRequest = {
            name: form.name,
            slug: form.slug || undefined,
            description: form.description || undefined,
            color: form.color || undefined,
            entity_type_slug: form.entity_type_slug || undefined,
          };
          await createCategory.mutateAsync(createData);
          toast({
            title: 'Category created',
            description: `"${form.name}" has been added.`,
          });
        }
        onClose();
      } catch (err) {
        toast({
          title: isEdit ? 'Update failed' : 'Create failed',
          description: err instanceof Error ? err.message : 'An error occurred',
          variant: 'destructive',
        });
      } finally {
        setIsSubmitting(false);
      }
    },
    [form, isEdit, editingCategory, createCategory, updateCategory, toast, onClose]
  );

  const dialogTitle = isEdit
    ? `Edit ${isBuiltin ? '(Built-in) ' : ''}${editingCategory?.name ?? 'Category'}`
    : 'Add Category';

  const dialogDescription = isBuiltin
    ? 'Built-in categories are read-only.'
    : isEdit
    ? 'Update the category details.'
    : 'Define a new category for organizing context entities.';

  const fieldsReadOnly = isBuiltin;

  return (
    <Dialog open={open} onOpenChange={(isOpen) => !isOpen && onClose()}>
      <DialogContent className="max-h-[90vh] max-w-lg overflow-y-auto">
        <DialogHeader>
          <DialogTitle>{dialogTitle}</DialogTitle>
          <DialogDescription>{dialogDescription}</DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-5" aria-label={dialogTitle}>
          {/* Name */}
          <div className="space-y-1.5">
            <Label htmlFor="cat-name">
              Name <span aria-hidden="true" className="text-destructive">*</span>
            </Label>
            <Input
              id="cat-name"
              value={form.name}
              onChange={(e) => handleNameChange(e.target.value)}
              placeholder="e.g. Architecture"
              disabled={fieldsReadOnly}
              required
            />
          </div>

          {/* Slug — create only */}
          {!isEdit && (
            <div className="space-y-1.5">
              <Label htmlFor="cat-slug">Slug</Label>
              <Input
                id="cat-slug"
                value={form.slug}
                onChange={(e) => handleSlugChange(e.target.value)}
                placeholder="auto-generated from name"
                disabled={fieldsReadOnly}
                aria-describedby="cat-slug-hint"
              />
              <p id="cat-slug-hint" className="text-xs text-muted-foreground">
                URL-friendly identifier. Auto-generated from name if left empty.
              </p>
            </div>
          )}

          {/* Description */}
          <div className="space-y-1.5">
            <Label htmlFor="cat-description">Description</Label>
            <Textarea
              id="cat-description"
              value={form.description}
              onChange={(e) => setField('description', e.target.value)}
              placeholder="Describe this category…"
              rows={2}
              disabled={fieldsReadOnly}
            />
          </div>

          {/* Color */}
          <div className="space-y-1.5">
            <ColorSelector
              label="Color"
              value={form.color}
              onChange={(hex) => setField('color', hex)}
              disabled={fieldsReadOnly}
            />
          </div>

          {/* Entity Type filter */}
          <div className="space-y-1.5">
            <Label htmlFor="cat-entity-type">Entity Type Filter</Label>
            <Select
              value={form.entity_type_slug || '__all__'}
              onValueChange={(v) => setField('entity_type_slug', v === '__all__' ? '' : v)}
              disabled={fieldsReadOnly}
            >
              <SelectTrigger id="cat-entity-type" aria-label="Entity type filter">
                <SelectValue placeholder="All entity types" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="__all__">All entity types</SelectItem>
                {entityTypeConfigs?.map((config) => (
                  <SelectItem key={config.slug} value={config.slug}>
                    {config.display_name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <p className="text-xs text-muted-foreground">
              Optionally restrict this category to a specific entity type.
            </p>
          </div>

          <DialogFooter>
            <Button type="button" variant="outline" onClick={onClose} disabled={isSubmitting}>
              Cancel
            </Button>
            <Button type="submit" disabled={isSubmitting || fieldsReadOnly}>
              {isSubmitting ? 'Saving…' : isEdit ? 'Save Changes' : 'Create'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

// ---------------------------------------------------------------------------
// CategoryRow
// ---------------------------------------------------------------------------

interface CategoryRowProps {
  category: EntityCategory;
  entityTypeName?: string;
  onEdit: (category: EntityCategory) => void;
  onDelete: (category: EntityCategory) => void;
}

function CategoryRow({ category, entityTypeName, onEdit, onDelete }: CategoryRowProps) {
  const truncatedDescription =
    category.description && category.description.length > 80
      ? `${category.description.slice(0, 80)}…`
      : category.description;

  return (
    <TableRow>
      {/* Color swatch */}
      <TableCell aria-label={`Color for ${category.name}`}>
        {category.color ? (
          <span
            className="block h-4 w-4 rounded-full border border-border/50"
            style={{ backgroundColor: category.color }}
            aria-label={category.color}
          />
        ) : (
          <span className="block h-4 w-4 rounded-full border border-dashed border-muted-foreground/40" />
        )}
      </TableCell>

      {/* Name */}
      <TableCell className="font-medium">{category.name}</TableCell>

      {/* Slug */}
      <TableCell className="hidden font-mono text-xs text-muted-foreground sm:table-cell">
        {category.slug}
      </TableCell>

      {/* Description */}
      <TableCell className="hidden text-sm text-muted-foreground md:table-cell">
        {truncatedDescription ?? <span className="italic">No description</span>}
      </TableCell>

      {/* Entity type filter */}
      <TableCell className="hidden text-sm lg:table-cell">
        {entityTypeName ? (
          <Badge variant="outline" className="text-xs">
            {entityTypeName}
          </Badge>
        ) : (
          <span className="text-xs text-muted-foreground">All types</span>
        )}
      </TableCell>

      {/* Built-in badge */}
      <TableCell>
        {category.is_builtin ? (
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
            aria-label={`Edit ${category.name}`}
            onClick={() => onEdit(category)}
          >
            <Pencil className="h-4 w-4" />
          </Button>
          <Button
            variant="ghost"
            size="icon"
            aria-label={
              category.is_builtin
                ? `Cannot delete built-in category ${category.name}`
                : `Delete ${category.name}`
            }
            disabled={category.is_builtin}
            onClick={() => !category.is_builtin && onDelete(category)}
          >
            <Trash2 className="h-4 w-4" />
          </Button>
        </div>
      </TableCell>
    </TableRow>
  );
}

// ---------------------------------------------------------------------------
// ContextCategoriesSettings
// ---------------------------------------------------------------------------

/**
 * Table listing all entity categories with create/edit/delete actions.
 * Built-in categories cannot be deleted.
 */
export function ContextCategoriesSettings() {
  const { data: categories, isLoading, error } = useEntityCategories();
  const { data: entityTypeConfigs } = useEntityTypeConfigs();
  const deleteCategory = useDeleteEntityCategory();
  const { toast } = useToast();

  const [formOpen, setFormOpen] = React.useState(false);
  const [editingCategory, setEditingCategory] = React.useState<EntityCategory | null>(null);
  const [deleteTarget, setDeleteTarget] = React.useState<EntityCategory | null>(null);

  // Build a lookup map for entity type display names
  const entityTypeNameBySlug = React.useMemo(() => {
    const map = new Map<string, string>();
    entityTypeConfigs?.forEach((config) => {
      map.set(config.slug, config.display_name);
    });
    return map;
  }, [entityTypeConfigs]);

  const handleEdit = React.useCallback((category: EntityCategory) => {
    setEditingCategory(category);
    setFormOpen(true);
  }, []);

  const handleCreate = React.useCallback(() => {
    setEditingCategory(null);
    setFormOpen(true);
  }, []);

  const handleFormClose = React.useCallback(() => {
    setFormOpen(false);
    setEditingCategory(null);
  }, []);

  const handleDeleteConfirm = React.useCallback(async () => {
    if (!deleteTarget) return;

    try {
      await deleteCategory.mutateAsync(deleteTarget.slug);
      toast({
        title: 'Category deleted',
        description: `"${deleteTarget.name}" has been removed.`,
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
  }, [deleteTarget, deleteCategory, toast]);

  if (isLoading) {
    return (
      <div className="space-y-2" role="status" aria-label="Loading categories">
        {[...Array(4)].map((_, i) => (
          <Skeleton key={i} className="h-12 w-full" />
        ))}
      </div>
    );
  }

  if (error) {
    return (
      <p className="text-sm text-destructive" role="alert">
        Failed to load categories:{' '}
        {error instanceof Error ? error.message : 'Unknown error'}
      </p>
    );
  }

  return (
    <div className="space-y-4">
      {/* Header row */}
      <div className="flex items-center justify-between">
        <p className="text-sm text-muted-foreground">
          {categories?.length ?? 0} categor{categories?.length !== 1 ? 'ies' : 'y'} configured
        </p>
        <Button onClick={handleCreate} size="sm">
          <Plus className="mr-2 h-4 w-4" />
          Add Category
        </Button>
      </div>

      {/* Table */}
      <div className="rounded-md border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-8" aria-label="Color" />
              <TableHead>Name</TableHead>
              <TableHead className="hidden sm:table-cell">Slug</TableHead>
              <TableHead className="hidden md:table-cell">Description</TableHead>
              <TableHead className="hidden lg:table-cell">Entity Type</TableHead>
              <TableHead className="w-24">Type</TableHead>
              <TableHead className="w-24 text-right">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {categories && categories.length > 0 ? (
              categories.map((category) => (
                <CategoryRow
                  key={category.slug}
                  category={category}
                  entityTypeName={
                    category.entity_type_slug
                      ? entityTypeNameBySlug.get(category.entity_type_slug)
                      : undefined
                  }
                  onEdit={handleEdit}
                  onDelete={setDeleteTarget}
                />
              ))
            ) : (
              <TableRow>
                <TableCell colSpan={7} className="py-8 text-center text-muted-foreground">
                  No categories found. Create one to start organizing context entities.
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </div>

      {/* Create / Edit form dialog */}
      <CategoryForm
        open={formOpen}
        onClose={handleFormClose}
        editingCategory={editingCategory}
      />

      {/* Delete confirmation dialog */}
      <AlertDialog open={!!deleteTarget} onOpenChange={(open) => !open && setDeleteTarget(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete category?</AlertDialogTitle>
            <AlertDialogDescription>
              This will permanently remove the &ldquo;{deleteTarget?.name}&rdquo; category. Context
              entities that use this category will lose this association. This action cannot be
              undone.
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
