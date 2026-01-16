'use client';

import { useState } from 'react';
import { Folders, Plus, Edit, Trash2, Package, X, Check, Copy } from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
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
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Skeleton } from '@/components/ui/skeleton';
import {
  useGroups,
  useCreateGroup,
  useUpdateGroup,
  useDeleteGroup,
  useToast,
} from '@/hooks';
import { CopyGroupDialog } from '@/components/collection/copy-group-dialog';
import type { Group } from '@/types/groups';

export interface ManageGroupsDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  collectionId: string;
}

export function ManageGroupsDialog({
  open,
  onOpenChange,
  collectionId,
}: ManageGroupsDialogProps) {
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [editingGroupId, setEditingGroupId] = useState<string | null>(null);
  const [deleteGroupId, setDeleteGroupId] = useState<string | null>(null);
  const [copyDialogOpen, setCopyDialogOpen] = useState(false);
  const [groupToCopy, setGroupToCopy] = useState<Group | null>(null);

  // Form state for create
  const [createName, setCreateName] = useState('');
  const [createDescription, setCreateDescription] = useState('');
  const [createErrors, setCreateErrors] = useState<{
    name?: string;
    description?: string;
  }>({});

  // Form state for edit
  const [editForms, setEditForms] = useState<
    Record<string, { name: string; description: string }>
  >({});
  const [editErrors, setEditErrors] = useState<
    Record<string, { name?: string; description?: string }>
  >({});

  const { toast } = useToast();
  const { data: groupsData, isLoading } = useGroups(collectionId);
  const createMutation = useCreateGroup();
  const updateMutation = useUpdateGroup();
  const deleteMutation = useDeleteGroup();

  const groups = groupsData?.groups || [];

  // Validation function
  const validateGroupForm = (
    name: string,
    description: string
  ): { name?: string; description?: string } => {
    const errors: { name?: string; description?: string } = {};

    if (!name.trim()) {
      errors.name = 'Group name is required';
    } else if (name.length < 1 || name.length > 255) {
      errors.name = 'Name must be between 1 and 255 characters';
    }

    if (description && description.length > 1000) {
      errors.description = 'Description must be less than 1000 characters';
    }

    return errors;
  };

  // Create handlers
  const handleCreateGroup = async () => {
    const errors = validateGroupForm(createName, createDescription);
    setCreateErrors(errors);

    if (Object.keys(errors).length > 0) {
      return;
    }

    try {
      await createMutation.mutateAsync({
        collection_id: collectionId,
        name: createName.trim(),
        description: createDescription.trim() || undefined,
        position: groups.length, // Append to end
      });

      toast({
        title: 'Group created',
        description: `Successfully created group "${createName}"`,
      });

      // Reset form
      setCreateName('');
      setCreateDescription('');
      setCreateErrors({});
      setShowCreateForm(false);
    } catch (error) {
      console.error('Failed to create group:', error);
      toast({
        title: 'Failed to create group',
        description: error instanceof Error ? error.message : 'An unexpected error occurred',
        variant: 'destructive',
      });
    }
  };

  const handleCancelCreate = () => {
    setCreateName('');
    setCreateDescription('');
    setCreateErrors({});
    setShowCreateForm(false);
  };

  // Edit handlers
  const handleStartEdit = (group: Group) => {
    setEditingGroupId(group.id);
    setEditForms({
      ...editForms,
      [group.id]: {
        name: group.name,
        description: group.description || '',
      },
    });
    setEditErrors({
      ...editErrors,
      [group.id]: {},
    });
  };

  const handleCancelEdit = (groupId: string) => {
    setEditingGroupId(null);
    const newEditForms = { ...editForms };
    delete newEditForms[groupId];
    setEditForms(newEditForms);

    const newEditErrors = { ...editErrors };
    delete newEditErrors[groupId];
    setEditErrors(newEditErrors);
  };

  const handleSaveEdit = async (group: Group) => {
    const formData = editForms[group.id];
    if (!formData) return;

    const errors = validateGroupForm(formData.name, formData.description);
    setEditErrors({
      ...editErrors,
      [group.id]: errors,
    });

    if (Object.keys(errors).length > 0) {
      return;
    }

    // Check if anything changed
    const hasChanges =
      formData.name.trim() !== group.name ||
      formData.description.trim() !== (group.description || '');

    if (!hasChanges) {
      toast({
        title: 'No changes',
        description: 'No changes were made to the group',
      });
      handleCancelEdit(group.id);
      return;
    }

    try {
      await updateMutation.mutateAsync({
        id: group.id,
        data: {
          name: formData.name.trim() !== group.name ? formData.name.trim() : undefined,
          description:
            formData.description.trim() !== (group.description || '')
              ? formData.description.trim() || undefined
              : undefined,
        },
      });

      toast({
        title: 'Group updated',
        description: `Successfully updated group "${formData.name}"`,
      });

      setEditingGroupId(null);
      handleCancelEdit(group.id);
    } catch (error) {
      console.error('Failed to update group:', error);
      toast({
        title: 'Failed to update group',
        description: error instanceof Error ? error.message : 'An unexpected error occurred',
        variant: 'destructive',
      });
    }
  };

  // Delete handlers
  const handleDeleteGroup = async () => {
    if (!deleteGroupId) return;

    const group = groups.find((g) => g.id === deleteGroupId);
    if (!group) return;

    try {
      await deleteMutation.mutateAsync({
        id: deleteGroupId,
        collectionId: collectionId,
      });

      toast({
        title: 'Group deleted',
        description: `Successfully deleted group "${group.name}"`,
      });

      setDeleteGroupId(null);
    } catch (error) {
      console.error('Failed to delete group:', error);
      toast({
        title: 'Failed to delete group',
        description: error instanceof Error ? error.message : 'An unexpected error occurred',
        variant: 'destructive',
      });
    }
  };

  // Copy handlers
  const handleStartCopy = (group: Group) => {
    setGroupToCopy(group);
    setCopyDialogOpen(true);
  };

  const handleCopySuccess = () => {
    setGroupToCopy(null);
  };

  const handleClose = () => {
    if (!createMutation.isPending && !updateMutation.isPending && !deleteMutation.isPending) {
      handleCancelCreate();
      setEditingGroupId(null);
      setEditForms({});
      setEditErrors({});
      onOpenChange(false);
    }
  };

  return (
    <>
      <Dialog open={open} onOpenChange={handleClose}>
        <DialogContent className="sm:max-w-[600px]">
          <DialogHeader>
            <div className="flex items-center gap-3">
              <div className="rounded-lg bg-primary/10 p-2">
                <Folders className="h-5 w-5 text-primary" />
              </div>
              <div>
                <DialogTitle>Manage Groups</DialogTitle>
                <DialogDescription>
                  Organize artifacts into groups within this collection
                </DialogDescription>
              </div>
            </div>
          </DialogHeader>

          <div className="space-y-4">
            {/* Groups List */}
            <div className="space-y-2">
              <Label className="text-sm font-medium">Groups</Label>

              {isLoading ? (
                <div className="space-y-2">
                  <Skeleton className="h-20 w-full" />
                  <Skeleton className="h-20 w-full" />
                  <Skeleton className="h-20 w-full" />
                </div>
              ) : groups.length === 0 ? (
                <div className="rounded-lg border border-dashed border-muted-foreground/25 p-8 text-center">
                  <Folders className="mx-auto h-8 w-8 text-muted-foreground/50" />
                  <p className="mt-2 text-sm text-muted-foreground">
                    No groups yet. Create one below.
                  </p>
                </div>
              ) : (
                <ScrollArea className={groups.length > 5 ? 'h-[300px]' : ''}>
                  <div className="space-y-2 pr-4">
                    {groups.map((group) => {
                      const isEditing = editingGroupId === group.id;
                      const formData = editForms[group.id];
                      const errors = editErrors[group.id] || {};

                      return (
                        <Card key={group.id}>
                          <CardContent className="p-4">
                            {isEditing ? (
                              // Edit mode
                              <div className="space-y-3">
                                <div className="space-y-2">
                                  <Label htmlFor={`edit-name-${group.id}`}>
                                    Name <span className="text-destructive">*</span>
                                  </Label>
                                  <Input
                                    id={`edit-name-${group.id}`}
                                    value={formData?.name || ''}
                                    onChange={(e) => {
                                      setEditForms({
                                        ...editForms,
                                        [group.id]: {
                                          ...formData!,
                                          name: e.target.value,
                                        },
                                      });
                                      if (errors.name) {
                                        setEditErrors({
                                          ...editErrors,
                                          [group.id]: { ...errors, name: undefined },
                                        });
                                      }
                                    }}
                                    disabled={updateMutation.isPending}
                                    className={errors.name ? 'border-destructive' : ''}
                                  />
                                  {errors.name && (
                                    <p className="text-sm text-destructive">{errors.name}</p>
                                  )}
                                </div>

                                <div className="space-y-2">
                                  <Label htmlFor={`edit-description-${group.id}`}>
                                    Description (Optional)
                                  </Label>
                                  <Textarea
                                    id={`edit-description-${group.id}`}
                                    value={formData?.description || ''}
                                    onChange={(e) => {
                                      setEditForms({
                                        ...editForms,
                                        [group.id]: {
                                          ...formData!,
                                          description: e.target.value,
                                        },
                                      });
                                      if (errors.description) {
                                        setEditErrors({
                                          ...editErrors,
                                          [group.id]: { ...errors, description: undefined },
                                        });
                                      }
                                    }}
                                    disabled={updateMutation.isPending}
                                    className={errors.description ? 'border-destructive' : ''}
                                    rows={2}
                                  />
                                  {errors.description && (
                                    <p className="text-sm text-destructive">{errors.description}</p>
                                  )}
                                </div>

                                <div className="flex gap-2">
                                  <Button
                                    size="sm"
                                    onClick={() => handleSaveEdit(group)}
                                    disabled={updateMutation.isPending}
                                  >
                                    <Check className="mr-2 h-4 w-4" />
                                    {updateMutation.isPending ? 'Saving...' : 'Save'}
                                  </Button>
                                  <Button
                                    size="sm"
                                    variant="outline"
                                    onClick={() => handleCancelEdit(group.id)}
                                    disabled={updateMutation.isPending}
                                  >
                                    <X className="mr-2 h-4 w-4" />
                                    Cancel
                                  </Button>
                                </div>
                              </div>
                            ) : (
                              // View mode
                              <div className="flex items-start justify-between gap-4">
                                <div className="flex-1 space-y-1">
                                  <div className="flex items-center gap-2">
                                    <h4 className="font-medium">{group.name}</h4>
                                    <Badge variant="secondary" className="text-xs">
                                      <Package className="mr-1 h-3 w-3" />
                                      {group.artifact_count}
                                    </Badge>
                                  </div>
                                  {group.description && (
                                    <p className="text-sm text-muted-foreground">
                                      {group.description}
                                    </p>
                                  )}
                                </div>

                                <div className="flex gap-1">
                                  <Button
                                    size="sm"
                                    variant="ghost"
                                    onClick={() => handleStartCopy(group)}
                                    disabled={
                                      editingGroupId !== null ||
                                      updateMutation.isPending ||
                                      deleteMutation.isPending
                                    }
                                    aria-label={`Copy group "${group.name}" to another collection`}
                                  >
                                    <Copy className="h-4 w-4" />
                                  </Button>
                                  <Button
                                    size="sm"
                                    variant="ghost"
                                    onClick={() => handleStartEdit(group)}
                                    disabled={
                                      editingGroupId !== null ||
                                      updateMutation.isPending ||
                                      deleteMutation.isPending
                                    }
                                  >
                                    <Edit className="h-4 w-4" />
                                  </Button>
                                  <Button
                                    size="sm"
                                    variant="ghost"
                                    onClick={() => setDeleteGroupId(group.id)}
                                    disabled={
                                      editingGroupId !== null ||
                                      updateMutation.isPending ||
                                      deleteMutation.isPending
                                    }
                                  >
                                    <Trash2 className="h-4 w-4 text-destructive" />
                                  </Button>
                                </div>
                              </div>
                            )}
                          </CardContent>
                        </Card>
                      );
                    })}
                  </div>
                </ScrollArea>
              )}
            </div>

            {/* Create Group Form */}
            <div className="space-y-2 border-t pt-4">
              {!showCreateForm ? (
                <Button
                  variant="outline"
                  onClick={() => setShowCreateForm(true)}
                  disabled={editingGroupId !== null || createMutation.isPending}
                  className="w-full"
                >
                  <Plus className="mr-2 h-4 w-4" />
                  Create Group
                </Button>
              ) : (
                <div className="space-y-3 rounded-lg border p-4">
                  <h4 className="font-medium">Create New Group</h4>

                  <div className="space-y-2">
                    <Label htmlFor="create-name">
                      Name <span className="text-destructive">*</span>
                    </Label>
                    <Input
                      id="create-name"
                      placeholder="My Group"
                      value={createName}
                      onChange={(e) => {
                        setCreateName(e.target.value);
                        if (createErrors.name) {
                          setCreateErrors((prev) => ({ ...prev, name: undefined }));
                        }
                      }}
                      disabled={createMutation.isPending}
                      className={createErrors.name ? 'border-destructive' : ''}
                      autoFocus
                    />
                    {createErrors.name && (
                      <p className="text-sm text-destructive">{createErrors.name}</p>
                    )}
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="create-description">Description (Optional)</Label>
                    <Textarea
                      id="create-description"
                      placeholder="A group for organizing artifacts..."
                      value={createDescription}
                      onChange={(e) => {
                        setCreateDescription(e.target.value);
                        if (createErrors.description) {
                          setCreateErrors((prev) => ({ ...prev, description: undefined }));
                        }
                      }}
                      disabled={createMutation.isPending}
                      className={createErrors.description ? 'border-destructive' : ''}
                      rows={2}
                    />
                    {createErrors.description && (
                      <p className="text-sm text-destructive">{createErrors.description}</p>
                    )}
                    <p className="text-xs text-muted-foreground">Maximum 1000 characters</p>
                  </div>

                  <div className="flex gap-2">
                    <Button onClick={handleCreateGroup} disabled={createMutation.isPending}>
                      {createMutation.isPending ? 'Creating...' : 'Create Group'}
                    </Button>
                    <Button
                      variant="outline"
                      onClick={handleCancelCreate}
                      disabled={createMutation.isPending}
                    >
                      Cancel
                    </Button>
                  </div>
                </div>
              )}
            </div>
          </div>
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation Dialog */}
      <AlertDialog
        open={deleteGroupId !== null}
        onOpenChange={(open) => !open && setDeleteGroupId(null)}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <div className="flex items-center gap-3">
              <div className="rounded-lg bg-destructive/10 p-2">
                <Trash2 className="h-5 w-5 text-destructive" />
              </div>
              <div>
                <AlertDialogTitle>Delete Group?</AlertDialogTitle>
                <AlertDialogDescription>
                  This will remove all artifacts from this group.
                </AlertDialogDescription>
              </div>
            </div>
          </AlertDialogHeader>

          <div className="rounded-lg border border-muted bg-muted/50 p-4">
            <p className="text-sm text-muted-foreground">
              <strong>Note:</strong> The artifacts themselves will not be deleted. They will remain
              in your collection and can be added to other groups.
            </p>
          </div>

          <AlertDialogFooter>
            <AlertDialogCancel disabled={deleteMutation.isPending}>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDeleteGroup}
              disabled={deleteMutation.isPending}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              {deleteMutation.isPending ? 'Deleting...' : 'Delete Group'}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Copy Group Dialog */}
      {groupToCopy && (
        <CopyGroupDialog
          open={copyDialogOpen}
          onOpenChange={setCopyDialogOpen}
          group={groupToCopy}
          sourceCollectionId={collectionId}
          onSuccess={handleCopySuccess}
        />
      )}
    </>
  );
}
