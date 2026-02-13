'use client';

import { useEffect, useState } from 'react';
import type { Group } from '@/types/groups';
import { useCreateGroup, useToast, useUpdateGroup } from '@/hooks';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import {
  GroupMetadataEditor,
  type GroupColor,
  type GroupIcon,
  sanitizeGroupTags,
} from './group-metadata-editor';

interface GroupFormDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  collectionId: string;
  group?: Group | null;
  defaultPosition?: number;
}

export function GroupFormDialog({
  open,
  onOpenChange,
  collectionId,
  group = null,
  defaultPosition = 0,
}: GroupFormDialogProps) {
  const isEditing = !!group;
  const { toast } = useToast();
  const createGroup = useCreateGroup();
  const updateGroup = useUpdateGroup();

  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [tags, setTags] = useState<string[]>([]);
  const [color, setColor] = useState<GroupColor>('slate');
  const [icon, setIcon] = useState<GroupIcon>('layers');

  useEffect(() => {
    if (!open) {
      return;
    }
    if (group) {
      setName(group.name);
      setDescription(group.description ?? '');
      setTags(group.tags ?? []);
      setColor((group.color as GroupColor) ?? 'slate');
      setIcon((group.icon as GroupIcon) ?? 'layers');
      return;
    }
    setName('');
    setDescription('');
    setTags([]);
    setColor('slate');
    setIcon('layers');
  }, [open, group]);

  const isPending = createGroup.isPending || updateGroup.isPending;

  const handleSave = async () => {
    if (!name.trim()) {
      toast({
        title: 'Name required',
        description: 'Group name is required.',
        variant: 'destructive',
      });
      return;
    }

    const sanitizedTags = sanitizeGroupTags(tags);
    if (sanitizedTags.invalidTags.length > 0) {
      toast({
        title: 'Invalid tags removed',
        description: 'Use 1-32 characters from [a-z0-9_-].',
        variant: 'destructive',
      });
    }
    if (sanitizedTags.truncated) {
      toast({
        title: 'Tag limit reached',
        description: 'A group can have up to 20 tags.',
      });
    }

    try {
      if (isEditing && group) {
        await updateGroup.mutateAsync({
          id: group.id,
          data: {
            name: name.trim(),
            description: description.trim() || undefined,
            tags: sanitizedTags.tags,
            color,
            icon,
          },
        });
        toast({
          title: 'Group updated',
          description: `"${name.trim()}" was updated.`,
        });
      } else {
        await createGroup.mutateAsync({
          collection_id: collectionId,
          name: name.trim(),
          description: description.trim() || undefined,
          tags: sanitizedTags.tags,
          color,
          icon,
          position: defaultPosition,
        });
        toast({
          title: 'Group created',
          description: `"${name.trim()}" was created.`,
        });
      }
      onOpenChange(false);
    } catch (error) {
      toast({
        title: 'Save failed',
        description: error instanceof Error ? error.message : 'Unexpected error.',
        variant: 'destructive',
      });
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[560px]">
        <DialogHeader>
          <DialogTitle>{isEditing ? 'Edit Group' : 'Create Group'}</DialogTitle>
          <DialogDescription>
            {isEditing
              ? 'Update metadata used for group management and discovery.'
              : 'Create a new group and add metadata for better organization.'}
          </DialogDescription>
        </DialogHeader>

        <div className="grid gap-4 py-2">
          <div className="grid gap-2">
            <Label htmlFor="group-name">Name</Label>
            <Input
              id="group-name"
              value={name}
              onChange={(event) => setName(event.target.value)}
              placeholder="Group name"
              maxLength={255}
            />
          </div>

          <div className="grid gap-2">
            <Label htmlFor="group-description">Description</Label>
            <Textarea
              id="group-description"
              value={description}
              onChange={(event) => setDescription(event.target.value)}
              placeholder="What belongs in this group?"
              rows={3}
            />
          </div>

          <div className="rounded-lg border p-4">
            <GroupMetadataEditor
              tags={tags}
              onTagsChange={setTags}
              color={color}
              onColorChange={setColor}
              icon={icon}
              onIconChange={setIcon}
              availableTags={tags}
              disabled={isPending}
            />
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={isPending}>
            Cancel
          </Button>
          <Button onClick={handleSave} disabled={isPending}>
            {isPending ? 'Saving...' : isEditing ? 'Save Changes' : 'Create Group'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
