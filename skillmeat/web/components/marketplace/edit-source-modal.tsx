/**
 * Edit Source Modal
 *
 * Modal for editing GitHub source configuration with pre-populated fields.
 */

'use client';

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
import { Switch } from '@/components/ui/switch';
import { Textarea } from '@/components/ui/textarea';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { useEffect, useState } from 'react';
import { useUpdateSource, useRescanSource } from '@/hooks';
import { Loader2 } from 'lucide-react';
import type { GitHubSource, TrustLevel } from '@/types/marketplace';

interface EditSourceModalProps {
  source: GitHubSource | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess?: () => void;
}

export function EditSourceModal({
  source,
  open,
  onOpenChange,
  onSuccess,
}: EditSourceModalProps) {
  const [ref, setRef] = useState('');
  const [rootHint, setRootHint] = useState('');
  const [trustLevel, setTrustLevel] = useState<TrustLevel>('basic');
  const [description, setDescription] = useState('');
  const [notes, setNotes] = useState('');
  const [enableFrontmatterDetection, setEnableFrontmatterDetection] = useState(false);

  const updateSource = useUpdateSource(source?.id || '');
  const rescanSource = useRescanSource(source?.id || '');

  // Pre-populate form when source changes
  useEffect(() => {
    if (source) {
      setRef(source.ref || 'main');
      setRootHint(source.root_hint || '');
      setTrustLevel(source.trust_level);
      setDescription(source.description || '');
      setNotes(source.notes || '');
      setEnableFrontmatterDetection(source.enable_frontmatter_detection || false);
    }
  }, [source]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!source) return;

    try {
      await updateSource.mutateAsync({
        ref,
        root_hint: rootHint || undefined,
        trust_level: trustLevel,
        description: description || undefined,
        notes: notes || undefined,
        enable_frontmatter_detection: enableFrontmatterDetection,
      });

      // Auto-trigger rescan after successful edit
      rescanSource.mutate({});

      onSuccess?.();
      onOpenChange(false);
    } catch (error) {
      // Error handled by mutation
    }
  };

  if (!source) return null;

  const isPending = updateSource.isPending || rescanSource.isPending;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg">
        <form onSubmit={handleSubmit}>
          <DialogHeader>
            <DialogTitle>Edit Source</DialogTitle>
            <DialogDescription>
              Edit {source.owner}/{source.repo_name} configuration. A rescan will be triggered after saving.
            </DialogDescription>
          </DialogHeader>

          <div className="grid gap-4 py-4">
            <div className="grid gap-2">
              <Label htmlFor="ref">Branch / Tag</Label>
              <Input
                id="ref"
                placeholder="main"
                value={ref}
                onChange={(e) => setRef(e.target.value)}
              />
            </div>

            <div className="grid gap-2">
              <Label htmlFor="root-hint">Root Directory</Label>
              <Input
                id="root-hint"
                placeholder="skills/"
                value={rootHint}
                onChange={(e) => setRootHint(e.target.value)}
              />
              <p className="text-xs text-muted-foreground">
                Subdirectory to start scanning from (optional)
              </p>
            </div>

            <div className="flex flex-row items-center justify-between rounded-lg border p-4">
              <div className="space-y-0.5">
                <Label htmlFor="frontmatter-detection" className="text-base">
                  Enable frontmatter detection
                </Label>
                <p className="text-xs text-muted-foreground">
                  Scan markdown files for artifact type hints in YAML frontmatter
                </p>
              </div>
              <Switch
                id="frontmatter-detection"
                checked={enableFrontmatterDetection}
                onCheckedChange={setEnableFrontmatterDetection}
              />
            </div>

            <div className="grid gap-2">
              <Label htmlFor="trust-level">Trust Level</Label>
              <Select value={trustLevel} onValueChange={(v) => setTrustLevel(v as TrustLevel)}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="untrusted">Untrusted</SelectItem>
                  <SelectItem value="basic">Basic</SelectItem>
                  <SelectItem value="verified">Verified</SelectItem>
                  <SelectItem value="official">Official</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="grid gap-2">
              <Label htmlFor="description">Description</Label>
              <Input
                id="description"
                placeholder="Short description for this source"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                maxLength={500}
              />
              <p className="text-xs text-muted-foreground">
                {description.length}/500 characters
              </p>
            </div>

            <div className="grid gap-2">
              <Label htmlFor="notes">Notes</Label>
              <Textarea
                id="notes"
                placeholder="Internal notes about this source..."
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                rows={3}
                maxLength={2000}
              />
              <p className="text-xs text-muted-foreground">
                {notes.length}/2000 characters
              </p>
            </div>
          </div>

          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
              disabled={isPending}
            >
              Cancel
            </Button>
            <Button type="submit" disabled={isPending}>
              {isPending ? (
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
