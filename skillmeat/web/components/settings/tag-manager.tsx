'use client';

import { useState, useRef, useCallback } from 'react';
import { Search, Plus, Trash2, Check, X } from 'lucide-react';
import { cn } from '@/lib/utils';
import { useTags, useCreateTag, useUpdateTag, useDeleteTag, useToast } from '@/hooks';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Skeleton } from '@/components/ui/skeleton';
import { TagDeleteDialog } from './tag-delete-dialog';

// --- Color utilities ---

const TAG_COLORS = [
  '#6366f1',
  '#8b5cf6',
  '#d946ef',
  '#ec4899',
  '#f43f5e',
  '#ef4444',
  '#f97316',
  '#eab308',
  '#84cc16',
  '#22c55e',
  '#14b8a6',
  '#06b6d4',
  '#0ea5e9',
  '#3b82f6',
] as const;

function hashString(str: string): number {
  let hash = 0;
  for (let i = 0; i < str.length; i++) {
    const char = str.charCodeAt(i);
    hash = (hash << 5) - hash + char;
    hash = hash & hash;
  }
  return Math.abs(hash);
}

function getDefaultColor(name: string): string {
  const hash = hashString(name.toLowerCase());
  return TAG_COLORS[hash % TAG_COLORS.length] as string;
}

function generateSlug(name: string): string {
  return name
    .toLowerCase()
    .replace(/\s+/g, '-')
    .replace(/[^a-z0-9-]/g, '');
}

// --- Component ---

export function TagManager() {
  const { data, isLoading } = useTags(100);
  const createTag = useCreateTag();
  const updateTag = useUpdateTag();
  const deleteTag = useDeleteTag();
  const { toast } = useToast();

  const [searchQuery, setSearchQuery] = useState('');
  const [isCreating, setIsCreating] = useState(false);
  const [newTagName, setNewTagName] = useState('');
  const [newTagColor, setNewTagColor] = useState('#6366f1');
  const [editingTagId, setEditingTagId] = useState<string | null>(null);
  const [editingName, setEditingName] = useState('');
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [tagToDelete, setTagToDelete] = useState<{
    id: string;
    name: string;
    artifactCount: number;
  } | null>(null);

  const colorInputRefs = useRef<Record<string, HTMLInputElement | null>>({});
  const newColorInputRef = useRef<HTMLInputElement | null>(null);

  const tags = data?.items ?? [];

  const filteredTags = (searchQuery
    ? tags.filter(
        (tag) =>
          tag.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
          tag.slug.toLowerCase().includes(searchQuery.toLowerCase())
      )
    : tags).sort((a, b) => a.name.localeCompare(b.name));

  // --- Create ---

  const handleCreateSubmit = useCallback(async () => {
    const trimmed = newTagName.trim();
    if (!trimmed) return;

    try {
      await createTag.mutateAsync({
        name: trimmed,
        slug: generateSlug(trimmed),
        color: newTagColor,
      });
      toast({ title: 'Tag created', description: `"${trimmed}" has been created.` });
      setNewTagName('');
      setNewTagColor('#6366f1');
      setIsCreating(false);
    } catch (err) {
      toast({
        title: 'Failed to create tag',
        description: err instanceof Error ? err.message : 'An error occurred.',
        variant: 'destructive',
      });
    }
  }, [newTagName, newTagColor, createTag, toast]);

  const handleCreateCancel = useCallback(() => {
    setIsCreating(false);
    setNewTagName('');
    setNewTagColor('#6366f1');
  }, []);

  // --- Inline edit ---

  const startEditing = useCallback((tagId: string, currentName: string) => {
    setEditingTagId(tagId);
    setEditingName(currentName);
  }, []);

  const handleEditSave = useCallback(
    async (tagId: string) => {
      const trimmed = editingName.trim();
      if (!trimmed) {
        setEditingTagId(null);
        return;
      }

      try {
        await updateTag.mutateAsync({ id: tagId, data: { name: trimmed } });
        toast({ title: 'Tag updated', description: `Tag renamed to "${trimmed}".` });
      } catch (err) {
        toast({
          title: 'Failed to update tag',
          description: err instanceof Error ? err.message : 'An error occurred.',
          variant: 'destructive',
        });
      } finally {
        setEditingTagId(null);
      }
    },
    [editingName, updateTag, toast]
  );

  const handleEditKeyDown = useCallback(
    (e: React.KeyboardEvent, tagId: string) => {
      if (e.key === 'Enter') {
        e.preventDefault();
        handleEditSave(tagId);
      } else if (e.key === 'Escape') {
        setEditingTagId(null);
      }
    },
    [handleEditSave]
  );

  // --- Color edit ---

  const handleColorChange = useCallback(
    async (tagId: string, color: string) => {
      try {
        await updateTag.mutateAsync({ id: tagId, data: { color } });
        toast({ title: 'Tag color updated' });
      } catch (err) {
        toast({
          title: 'Failed to update color',
          description: err instanceof Error ? err.message : 'An error occurred.',
          variant: 'destructive',
        });
      }
    },
    [updateTag, toast]
  );

  // --- Delete ---

  const handleDeleteClick = useCallback(
    (tag: { id: string; name: string; artifact_count?: number }) => {
      setTagToDelete({
        id: tag.id,
        name: tag.name,
        artifactCount: tag.artifact_count ?? 0,
      });
      setDeleteDialogOpen(true);
    },
    []
  );

  const handleDeleteConfirm = useCallback(async () => {
    if (!tagToDelete) return;

    try {
      await deleteTag.mutateAsync(tagToDelete.id);
      toast({
        title: 'Tag deleted',
        description: `"${tagToDelete.name}" has been deleted.`,
      });
    } catch (err) {
      toast({
        title: 'Failed to delete tag',
        description: err instanceof Error ? err.message : 'An error occurred.',
        variant: 'destructive',
      });
      throw err;
    } finally {
      setTagToDelete(null);
    }
  }, [tagToDelete, deleteTag, toast]);

  // --- Render ---

  return (
    <Card>
      <CardHeader>
        <CardTitle>Tags</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Search and Create controls */}
        <div className="flex items-center gap-2">
          <div className="relative flex-1">
            <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Filter tags..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-8"
            />
          </div>
          <Button size="sm" onClick={() => setIsCreating(true)} disabled={isCreating}>
            <Plus className="mr-1 h-4 w-4" />
            Create Tag
          </Button>
        </div>

        {/* Table */}
        <div className="rounded-md border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-12">Color</TableHead>
                <TableHead>Name</TableHead>
                <TableHead className="hidden sm:table-cell">Slug</TableHead>
                <TableHead className="w-24 text-center">Artifacts</TableHead>
                <TableHead className="w-16" />
              </TableRow>
            </TableHeader>
            <TableBody>
              {/* Create row */}
              {isCreating && (
                <TableRow>
                  <TableCell>
                    <button
                      type="button"
                      className="flex h-6 w-6 items-center justify-center rounded-full border border-border"
                      style={{ backgroundColor: newTagColor }}
                      onClick={() => newColorInputRef.current?.click()}
                      aria-label="Pick tag color"
                    >
                      <input
                        ref={newColorInputRef}
                        type="color"
                        value={newTagColor}
                        onChange={(e) => setNewTagColor(e.target.value)}
                        className="sr-only"
                        tabIndex={-1}
                      />
                    </button>
                  </TableCell>
                  <TableCell colSpan={2}>
                    <Input
                      placeholder="Tag name..."
                      value={newTagName}
                      onChange={(e) => {
                        setNewTagName(e.target.value);
                        if (!e.target.value.trim()) {
                          setNewTagColor('#6366f1');
                        } else {
                          setNewTagColor(getDefaultColor(e.target.value.trim()));
                        }
                      }}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter') {
                          e.preventDefault();
                          handleCreateSubmit();
                        } else if (e.key === 'Escape') {
                          handleCreateCancel();
                        }
                      }}
                      autoFocus
                      className="h-8"
                    />
                  </TableCell>
                  <TableCell className="text-center">
                    <Badge variant="secondary">0</Badge>
                  </TableCell>
                  <TableCell>
                    <div className="flex items-center gap-1">
                      <Button
                        size="icon"
                        variant="ghost"
                        className="h-7 w-7"
                        onClick={handleCreateSubmit}
                        disabled={!newTagName.trim() || createTag.isPending}
                        aria-label="Save new tag"
                      >
                        <Check className="h-4 w-4" />
                      </Button>
                      <Button
                        size="icon"
                        variant="ghost"
                        className="h-7 w-7"
                        onClick={handleCreateCancel}
                        disabled={createTag.isPending}
                        aria-label="Cancel creating tag"
                      >
                        <X className="h-4 w-4" />
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              )}

              {/* Loading state */}
              {isLoading && (
                <>
                  {Array.from({ length: 4 }).map((_, i) => (
                    <TableRow key={`skeleton-${i}`}>
                      <TableCell>
                        <Skeleton className="h-6 w-6 rounded-full" />
                      </TableCell>
                      <TableCell>
                        <Skeleton className="h-4 w-32" />
                      </TableCell>
                      <TableCell className="hidden sm:table-cell">
                        <Skeleton className="h-4 w-24" />
                      </TableCell>
                      <TableCell className="text-center">
                        <Skeleton className="mx-auto h-5 w-8" />
                      </TableCell>
                      <TableCell>
                        <Skeleton className="h-7 w-7" />
                      </TableCell>
                    </TableRow>
                  ))}
                </>
              )}

              {/* Tag rows */}
              {!isLoading &&
                filteredTags.map((tag) => (
                  <TableRow key={tag.id}>
                    {/* Color swatch */}
                    <TableCell>
                      <button
                        type="button"
                        className="flex h-6 w-6 items-center justify-center rounded-full border border-border transition-transform hover:scale-110"
                        style={{ backgroundColor: tag.color || getDefaultColor(tag.name) }}
                        onClick={() => colorInputRefs.current[tag.id]?.click()}
                        aria-label={`Change color for ${tag.name}`}
                      >
                        <input
                          ref={(el) => {
                            colorInputRefs.current[tag.id] = el;
                          }}
                          type="color"
                          value={tag.color || getDefaultColor(tag.name)}
                          onChange={(e) => handleColorChange(tag.id, e.target.value)}
                          className="sr-only"
                          tabIndex={-1}
                        />
                      </button>
                    </TableCell>

                    {/* Name (inline editable) */}
                    <TableCell>
                      {editingTagId === tag.id ? (
                        <Input
                          value={editingName}
                          onChange={(e) => setEditingName(e.target.value)}
                          onBlur={() => handleEditSave(tag.id)}
                          onKeyDown={(e) => handleEditKeyDown(e, tag.id)}
                          autoFocus
                          className="h-8"
                        />
                      ) : (
                        <button
                          type="button"
                          className={cn(
                            'cursor-pointer rounded px-1 py-0.5 text-left text-sm font-medium',
                            'transition-colors hover:bg-muted'
                          )}
                          onClick={() => startEditing(tag.id, tag.name)}
                        >
                          {tag.name}
                        </button>
                      )}
                    </TableCell>

                    {/* Slug */}
                    <TableCell className="hidden sm:table-cell">
                      <span className="text-sm text-muted-foreground">{tag.slug}</span>
                    </TableCell>

                    {/* Artifact count */}
                    <TableCell className="text-center">
                      <Badge variant="secondary">{tag.artifact_count ?? 0}</Badge>
                    </TableCell>

                    {/* Actions */}
                    <TableCell>
                      <Button
                        size="icon"
                        variant="ghost"
                        className="h-7 w-7 text-muted-foreground hover:text-destructive"
                        onClick={() => handleDeleteClick(tag)}
                        aria-label={`Delete ${tag.name}`}
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}

              {/* Empty state */}
              {!isLoading && filteredTags.length === 0 && (
                <TableRow>
                  <TableCell colSpan={5} className="py-8 text-center text-muted-foreground">
                    {searchQuery
                      ? `No tags matching "${searchQuery}"`
                      : 'No tags yet. Create one to get started.'}
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </div>

        {/* Delete confirmation dialog */}
        <TagDeleteDialog
          open={deleteDialogOpen}
          onOpenChange={setDeleteDialogOpen}
          onConfirm={handleDeleteConfirm}
          tagName={tagToDelete?.name ?? null}
          artifactCount={tagToDelete?.artifactCount ?? 0}
        />
      </CardContent>
    </Card>
  );
}
