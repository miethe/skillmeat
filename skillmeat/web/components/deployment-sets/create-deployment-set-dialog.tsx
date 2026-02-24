'use client';

import { useEffect, useState } from 'react';
import { useCreateDeploymentSet, useToast } from '@/hooks';
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
import { Badge } from '@/components/ui/badge';
import { X } from 'lucide-react';
import { COLOR_OPTIONS } from '@/lib/group-constants';

interface CreateDeploymentSetDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

/**
 * Dialog for creating a new Deployment Set.
 *
 * Fields: name (required), description, color preset, icon (emoji), tags.
 * Calls useCreateDeploymentSet on submit and closes on success.
 */
export function CreateDeploymentSetDialog({ open, onOpenChange }: CreateDeploymentSetDialogProps) {
  const { toast } = useToast();
  const createSet = useCreateDeploymentSet();

  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [color, setColor] = useState('');
  const [icon, setIcon] = useState('');
  const [tagInput, setTagInput] = useState('');
  const [tags, setTags] = useState<string[]>([]);

  // Reset form when dialog opens/closes
  useEffect(() => {
    if (!open) {
      return;
    }
    setName('');
    setDescription('');
    setColor('');
    setIcon('');
    setTagInput('');
    setTags([]);
  }, [open]);

  const handleAddTag = () => {
    const trimmed = tagInput.trim();
    if (trimmed && !tags.includes(trimmed)) {
      setTags((prev) => [...prev, trimmed]);
    }
    setTagInput('');
  };

  const handleTagInputKeyDown = (event: React.KeyboardEvent<HTMLInputElement>) => {
    if (event.key === 'Enter' || event.key === ',') {
      event.preventDefault();
      handleAddTag();
    }
  };

  const handleRemoveTag = (tag: string) => {
    setTags((prev) => prev.filter((t) => t !== tag));
  };

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
          <div className="space-y-2">
            <Label>Color</Label>
            <div className="flex flex-wrap gap-2" role="group" aria-label="Color presets">
              {COLOR_OPTIONS.map((option) => (
                <button
                  key={option.value}
                  type="button"
                  aria-label={option.label}
                  aria-pressed={color === option.value}
                  className={`h-7 w-7 rounded-full border-2 transition-all ${
                    color === option.value
                      ? 'scale-110 border-foreground'
                      : 'border-transparent hover:border-muted-foreground'
                  }`}
                  style={{ backgroundColor: option.hex }}
                  onClick={() => setColor(color === option.value ? '' : option.value)}
                />
              ))}
            </div>
          </div>

          {/* Icon */}
          <div className="space-y-2">
            <Label htmlFor="ds-icon">Icon (emoji or identifier)</Label>
            <Input
              id="ds-icon"
              placeholder="e.g. 🚀 or deploy"
              value={icon}
              onChange={(e) => setIcon(e.target.value)}
              className="w-40"
            />
          </div>

          {/* Tags */}
          <div className="space-y-2">
            <Label htmlFor="ds-tags">Tags</Label>
            <div className="flex gap-2">
              <Input
                id="ds-tags"
                placeholder="Add a tag and press Enter"
                value={tagInput}
                onChange={(e) => setTagInput(e.target.value)}
                onKeyDown={handleTagInputKeyDown}
              />
              <Button type="button" variant="outline" size="sm" onClick={handleAddTag}>
                Add
              </Button>
            </div>
            {tags.length > 0 && (
              <div className="flex flex-wrap gap-1" role="list" aria-label="Added tags">
                {tags.map((tag) => (
                  <Badge key={tag} variant="secondary" className="gap-1" role="listitem">
                    {tag}
                    <button
                      type="button"
                      aria-label={`Remove tag ${tag}`}
                      onClick={() => handleRemoveTag(tag)}
                      className="rounded-sm hover:text-destructive focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                    >
                      <X className="h-3 w-3" aria-hidden="true" />
                    </button>
                  </Badge>
                ))}
              </div>
            )}
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
