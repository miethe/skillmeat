'use client';

import type { Group } from '@/types/groups';
import { useDeleteGroup, useToast } from '@/hooks';
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

interface GroupDeleteDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  group: Group | null;
}

export function GroupDeleteDialog({ open, onOpenChange, group }: GroupDeleteDialogProps) {
  const { toast } = useToast();
  const deleteGroup = useDeleteGroup();

  const handleDelete = async () => {
    if (!group) {
      return;
    }
    try {
      await deleteGroup.mutateAsync({
        id: group.id,
        collectionId: group.collection_id,
      });
      toast({
        title: 'Group deleted',
        description: `"${group.name}" was deleted.`,
      });
      onOpenChange(false);
    } catch (error) {
      toast({
        title: 'Delete failed',
        description: error instanceof Error ? error.message : 'Unexpected error.',
        variant: 'destructive',
      });
    }
  };

  return (
    <AlertDialog open={open} onOpenChange={onOpenChange}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>Delete group?</AlertDialogTitle>
          <AlertDialogDescription>
            {group
              ? `This deletes "${group.name}" and removes its artifact memberships. Artifacts remain in the collection.`
              : 'This deletes the selected group and removes its artifact memberships.'}
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel disabled={deleteGroup.isPending}>Cancel</AlertDialogCancel>
          <AlertDialogAction onClick={handleDelete} disabled={deleteGroup.isPending}>
            {deleteGroup.isPending ? 'Deleting...' : 'Delete Group'}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
