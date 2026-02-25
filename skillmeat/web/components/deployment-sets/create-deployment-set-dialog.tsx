'use client';

import { useEffect, useState } from 'react';
import { useCreateDeploymentSet, useTags, useToast } from '@/hooks';
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
import { PRESET_COLORS } from '@/lib/color-constants';

interface CreateDeploymentSetDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

/**
 * Dialog for creating a new Deployment Set.
 *
 * Fields: name (required), description, color preset, icon (emoji), tags.
 * Tags use the shared tags API for search/autocomplete — users can select
 * existing tags or create new ones by typing a name.
 * Calls useCreateDeploymentSet on submit and closes on success.
 */
export function CreateDeploymentSetDialog({ open, onOpenChange }: CreateDeploymentSetDialogProps) {
  const { toast } = useToast();
  const createSet = useCreateDeploymentSet();

  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [color, setColor] = useState(PRESET_COLORS[0]?.hex ?? '');
  const [icon, setIcon] = useState('');
  const [tags, setTags] = useState<string[]>([]);

  // Pre-fetch tags for the autocomplete popover (API max limit is 100)
  const { data: tagsData } = useTags(100);
  const availableTags = tagsData?.items.map((t) => t.name) ?? [];

  // Reset form when dialog opens/closes
  useEffect(() => {
    if (!open) {
      return;
    }
    setName('');
    setDescription('');
    setColor(PRESET_COLORS[0]?.hex ?? '');
    setIcon('');
    setTags([]);
  }, [open]);

  const handleSave = async () => {
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
      await createSet.mutateAsync({
        name: trimmedName,
        description: description.trim() || null,
        color: color || null,
        icon: icon.trim() || null,
        tags: tags.length > 0 ? tags : null,
      });

      toast({
        title: 'Deployment set created',
        description: `"${trimmedName}" has been created successfully.`,
      });
      onOpenChange(false);
    } catch (err) {
      toast({
        title: 'Failed to create deployment set',
        description: err instanceof Error ? err.message : 'An unexpected error occurred.',
        variant: 'destructive',
      });
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>New Deployment Set</DialogTitle>
          <DialogDescription>
            Create a named set of artifacts, groups, or nested sets to deploy together.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-2">
          {/* Name */}
          <div className="space-y-2">
            <Label htmlFor="ds-name">
              Name <span aria-hidden="true">*</span>
            </Label>
            <Input
              id="ds-name"
              placeholder="e.g. Production Toolset"
              value={name}
              onChange={(e) => setName(e.target.value)}
              autoFocus
            />
          </div>

          {/* Description */}
          <div className="space-y-2">
            <Label htmlFor="ds-description">Description</Label>
            <Textarea
              id="ds-description"
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
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={createSet.isPending}>
            Cancel
          </Button>
          <Button onClick={handleSave} disabled={createSet.isPending}>
            {createSet.isPending ? 'Creating…' : 'Create Set'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
