'use client';

import { useEffect, useMemo, useState } from 'react';
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
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';

const GROUP_COLORS = ['slate', 'blue', 'green', 'amber', 'rose'] as const;
const GROUP_ICONS = ['layers', 'folder', 'tag', 'sparkles', 'book', 'wrench'] as const;

type GroupColor = (typeof GROUP_COLORS)[number];
type GroupIcon = (typeof GROUP_ICONS)[number];

interface GroupFormDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  collectionId: string;
  group?: Group | null;
  defaultPosition?: number;
}

function normalizeTags(input: string): string[] {
  if (!input.trim()) {
    return [];
  }
  const seen = new Set<string>();
  const tags: string[] = [];
  for (const raw of input.split(',')) {
    const tag = raw.trim().toLowerCase();
    if (!tag || seen.has(tag)) {
      continue;
    }
    tags.push(tag);
    seen.add(tag);
  }
  return tags;
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
  const [tagsInput, setTagsInput] = useState('');
  const [color, setColor] = useState<GroupColor>('slate');
  const [icon, setIcon] = useState<GroupIcon>('layers');

  useEffect(() => {
    if (!open) {
      return;
    }
    if (group) {
      setName(group.name);
      setDescription(group.description ?? '');
      setTagsInput((group.tags ?? []).join(', '));
      setColor((group.color as GroupColor) ?? 'slate');
      setIcon((group.icon as GroupIcon) ?? 'layers');
      return;
    }
    setName('');
    setDescription('');
    setTagsInput('');
    setColor('slate');
    setIcon('layers');
  }, [open, group]);

  const tags = useMemo(() => normalizeTags(tagsInput), [tagsInput]);
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

    try {
      if (isEditing && group) {
        await updateGroup.mutateAsync({
          id: group.id,
          data: {
            name: name.trim(),
            description: description.trim() || undefined,
            tags,
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
          tags,
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

          <div className="grid gap-2">
            <Label htmlFor="group-tags">Tags (comma separated)</Label>
            <Input
              id="group-tags"
              value={tagsInput}
              onChange={(event) => setTagsInput(event.target.value)}
              placeholder="frontend, critical, research"
            />
          </div>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div className="grid gap-2">
              <Label htmlFor="group-color">Color</Label>
              <Select value={color} onValueChange={(value) => setColor(value as GroupColor)}>
                <SelectTrigger id="group-color">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {GROUP_COLORS.map((option) => (
                    <SelectItem key={option} value={option}>
                      {option}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="grid gap-2">
              <Label htmlFor="group-icon">Icon</Label>
              <Select value={icon} onValueChange={(value) => setIcon(value as GroupIcon)}>
                <SelectTrigger id="group-icon">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {GROUP_ICONS.map((option) => (
                    <SelectItem key={option} value={option}>
                      {option}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
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
