'use client';

import { useEffect, useState } from 'react';
import { useUpdateDeploymentSet, useTags, useToast } from '@/hooks';
import type { DeploymentSet } from '@/types/deployment-sets';
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
import { TagEditor } from '@/components/shared/tag-editor';
import { ColorSelector } from '@/components/shared/color-selector';
import { IconPicker } from '@/components/shared/icon-picker';

interface EditDeploymentSetDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  set: DeploymentSet | null;
}

/**
 * Dialog for editing an existing Deployment Set.
 *
 * Pre-fills all fields from the provided set. Tags use the shared tags API
 * for search/autocomplete — users can select existing tags or create new ones.
 * Calls useUpdateDeploymentSet on save. Closes on success.
 */
export function EditDeploymentSetDialog({ open, onOpenChange, set }: EditDeploymentSetDialogProps) {
  const { toast } = useToast();
  const updateSet = useUpdateDeploymentSet();

  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [color, setColor] = useState('');
  const [icon, setIcon] = useState('');
  const [tags, setTags] = useState<string[]>([]);

  // Pre-fetch tags for the autocomplete popover (API max limit is 100)
  const { data: tagsData } = useTags(100);
  const availableTags = tagsData?.items.map((t) => t.name) ?? [];

  // Sync form fields whenever the dialog opens or the set changes
  useEffect(() => {
    if (!open || !set) {
      return;
    }
    setName(set.name);
    setDescription(set.description ?? '');
    setColor(set.color ?? '');
    setIcon(set.icon ?? '');
    setTags(set.tags ?? []);
  }, [open, set]);

  const handleSave = async () => {
    if (!set) {
      return;
    }

    const trimmedName = name.trim();
    if (!trimmedName) {
      toast({
        title: 'Name required',
        description: 'Please enter a name for the deployment set.',
        variant: 'destructive',
      });
      return;
    }

    try {
      await updateSet.mutateAsync({
        id: set.id,
        data: {
          name: trimmedName,
          description: description.trim() || null,
          color: color || null,
          icon: icon.trim() || null,
          tags: tags.length > 0 ? tags : null,
        },
      });

      toast({
        title: 'Deployment set updated',
        description: `"${trimmedName}" has been updated.`,
      });
      onOpenChange(false);
    } catch (err) {
      toast({
        title: 'Update failed',
        description: err instanceof Error ? err.message : 'An unexpected error occurred.',
        variant: 'destructive',
      });
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>Edit Deployment Set</DialogTitle>
          <DialogDescription>Update the details for this deployment set.</DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-2">
          {/* Name */}
          <div className="space-y-2">
            <Label htmlFor="ds-edit-name">
              Name <span aria-hidden="true">*</span>
            </Label>
            <Input
              id="ds-edit-name"
              placeholder="e.g. Production Toolset"
              value={name}
              onChange={(e) => setName(e.target.value)}
              autoFocus
            />
          </div>

          {/* Description */}
          <div className="space-y-2">
            <Label htmlFor="ds-edit-description">Description</Label>
            <Textarea
              id="ds-edit-description"
              placeholder="Describe what this deployment set contains…"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={3}
              className="resize-none"
            />
          </div>

          {/* Color */}
          <ColorSelector
            label="Color"
            value={color}
            onChange={setColor}
          />

          {/* Icon */}
          <div className="space-y-2">
            <Label>Icon</Label>
            <IconPicker value={icon} onChange={setIcon} />
          </div>

          {/* Tags */}
          <div className="space-y-2">
            <Label>Tags</Label>
            <TagEditor
              tags={tags}
              onTagsChange={setTags}
              availableTags={availableTags}
            />
            <p className="text-xs text-muted-foreground">
              Search existing tags or type a new name to create one.
            </p>
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={updateSet.isPending}>
            Cancel
          </Button>
          <Button onClick={handleSave} disabled={updateSet.isPending}>
            {updateSet.isPending ? 'Saving…' : 'Save Changes'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
