'use client';

/**
 * Parameter Editor Modal Component
 *
 * Allows users to edit artifact parameters (source, version, scope, tags, aliases)
 * after import or within the bulk import flow.
 */

import { useState, useEffect } from 'react';
import { useForm, Controller } from 'react-hook-form';
import { Edit, Loader2 } from 'lucide-react';
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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { TagInput } from '@/components/ui/tag-input';
import { useToast, useTags } from '@/hooks';
import type { ArtifactType, ArtifactScope } from '@/types/artifact';

export interface ArtifactParameters {
  source?: string;
  version?: string;
  scope?: ArtifactScope;
  tags?: string[];
  aliases?: string[];
}

export interface ParameterEditorModalProps {
  artifact: {
    name: string;
    type: ArtifactType;
    source?: string;
    version?: string;
    scope?: ArtifactScope;
    tags?: string[];
    aliases?: string[];
  };
  open: boolean;
  onClose: () => void;
  onSave: (parameters: ArtifactParameters) => Promise<void>;
}

interface FormData {
  source: string;
  version: string;
  scope: ArtifactScope;
  tags: string[];
  aliases: string;
}

export function ParameterEditorModal({
  artifact,
  open,
  onClose,
  onSave,
}: ParameterEditorModalProps) {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const { toast } = useToast();

  // Fetch available tags for suggestions
  const { data: tagsData } = useTags();

  const {
    register,
    handleSubmit,
    reset,
    control,
    formState: { errors },
  } = useForm<FormData>({
    defaultValues: {
      source: artifact.source || '',
      version: artifact.version || '',
      scope: artifact.scope || 'user',
      tags: artifact.tags || [],
      aliases: artifact.aliases?.join(', ') || '',
    },
  });

  // Reset form when artifact changes
  useEffect(() => {
    reset({
      source: artifact.source || '',
      version: artifact.version || '',
      scope: artifact.scope || 'user',
      tags: artifact.tags || [],
      aliases: artifact.aliases?.join(', ') || '',
    });
  }, [artifact, reset]);

  const onSubmit = async (data: FormData) => {
    setIsSubmitting(true);

    try {
      const tagsById = new Map(
        (tagsData?.items || []).map((tag) => [tag.id, tag.name])
      );
      const normalizedTags = (data.tags || [])
        .map((tag) => tagsById.get(tag) || tag)
        .map((tag) => tag.trim())
        .filter(Boolean);

      // Tags are already an array from TagInput
      const parameters: ArtifactParameters = {
        source: data.source || undefined,
        version: data.version || undefined,
        scope: data.scope,
        tags: normalizedTags.length > 0 ? normalizedTags : undefined,
        aliases: data.aliases
          ? data.aliases
              .split(',')
              .map((a) => a.trim())
              .filter(Boolean)
          : undefined,
      };

      await onSave(parameters);

      toast({
        title: 'Parameters updated',
        description: `Updated parameters for ${artifact.name}`,
      });

      onClose();
    } catch (error) {
      toast({
        title: 'Update failed',
        description: error instanceof Error ? error.message : 'Failed to update parameters',
        variant: 'destructive',
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleClose = () => {
    if (!isSubmitting) {
      onClose();
    }
  };

  return (
    <Dialog open={open} onOpenChange={(isOpen) => !isOpen && handleClose()}>
      <DialogContent
        className="sm:max-w-[500px]"
      >
        <DialogHeader>
          <div className="flex items-center gap-3">
            <div className="rounded-lg bg-primary/10 p-2">
              <Edit className="h-5 w-5 text-primary" aria-hidden="true" />
            </div>
            <div>
              <DialogTitle>Edit Parameters</DialogTitle>
              <DialogDescription>
                Update parameters for {artifact.type}: {artifact.name}
              </DialogDescription>
            </div>
          </div>
        </DialogHeader>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4 py-4">
          {/* Artifact Info Display */}
          <div className="space-y-2 rounded-lg border p-3">
            <div className="flex items-center justify-between text-sm">
              <span className="text-muted-foreground">Artifact</span>
              <span className="font-medium">{artifact.name}</span>
            </div>
            <div className="flex items-center justify-between text-sm">
              <span className="text-muted-foreground">Type</span>
              <span className="rounded bg-muted px-2 py-0.5 text-xs capitalize">
                {artifact.type}
              </span>
            </div>
          </div>

          {/* Source */}
          <div className="space-y-2">
            <Label htmlFor="source">Source</Label>
            <Input
              id="source"
              placeholder="user/repo/path"
              {...register('source')}
              disabled={isSubmitting}
              aria-invalid={!!errors.source}
              aria-describedby={errors.source ? 'source-error' : 'source-hint'}
            />
            {errors.source && (
              <p id="source-error" className="text-xs text-destructive" role="alert">
                {errors.source.message}
              </p>
            )}
            <p id="source-hint" className="text-xs text-muted-foreground">
              GitHub source in format: user/repo/path
            </p>
          </div>

          {/* Version */}
          <div className="space-y-2">
            <Label htmlFor="version">Version</Label>
            <Input
              id="version"
              placeholder="latest or v1.0.0"
              {...register('version')}
              disabled={isSubmitting}
            />
            <p className="text-xs text-muted-foreground">
              Use &quot;latest&quot; or a specific version tag
            </p>
          </div>

          {/* Scope */}
          <div className="space-y-2">
            <Label htmlFor="scope">Scope</Label>
            <Controller
              name="scope"
              control={control}
              render={({ field }) => (
                <Select
                  value={field.value}
                  onValueChange={field.onChange}
                  disabled={isSubmitting}
                >
                  <SelectTrigger id="scope">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="user">User (Global)</SelectItem>
                    <SelectItem value="local">Local (Project)</SelectItem>
                  </SelectContent>
                </Select>
              )}
            />
            <p className="text-xs text-muted-foreground">
              User scope is global, local scope is per-project
            </p>
          </div>

          {/* Tags */}
          <div className="space-y-2">
            <Label htmlFor="tags">Tags</Label>
            <Controller
              name="tags"
              control={control}
              render={({ field }) => (
                <TagInput
                  value={field.value}
                  onChange={field.onChange}
                  suggestions={tagsData?.items || []}
                  allowCreate={true}
                  placeholder="Add tags..."
                  disabled={isSubmitting}
                />
              )}
            />
            <p className="text-xs text-muted-foreground">
              Type to search existing tags or create new ones
            </p>
          </div>

          {/* Aliases */}
          <div className="space-y-2">
            <Label htmlFor="aliases">Aliases</Label>
            <Input
              id="aliases"
              placeholder="shortname, alt-name"
              {...register('aliases')}
              disabled={isSubmitting}
            />
            <p className="text-xs text-muted-foreground">
              Separate multiple aliases with commas
            </p>
          </div>

          <DialogFooter>
            <Button type="button" variant="outline" onClick={handleClose} disabled={isSubmitting}>
              Cancel
            </Button>
            <Button type="submit" disabled={isSubmitting}>
              {isSubmitting ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Saving...
                </>
              ) : (
                'Save Changes'
              )}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
