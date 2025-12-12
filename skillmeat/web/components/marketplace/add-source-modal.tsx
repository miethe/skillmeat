/**
 * Add Source Modal (Placeholder)
 *
 * Multi-step wizard for adding a new GitHub source.
 * This is a placeholder - full implementation will include 4 steps.
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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { useState } from 'react';
import { useCreateSource } from '@/hooks/useMarketplaceSources';
import { Loader2 } from 'lucide-react';
import type { TrustLevel } from '@/types/marketplace';

interface AddSourceModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess?: () => void;
}

export function AddSourceModal({
  open,
  onOpenChange,
  onSuccess,
}: AddSourceModalProps) {
  const [repoUrl, setRepoUrl] = useState('');
  const [ref, setRef] = useState('main');
  const [rootHint, setRootHint] = useState('');
  const [trustLevel, setTrustLevel] = useState<TrustLevel>('basic');

  const createSource = useCreateSource();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    try {
      await createSource.mutateAsync({
        repo_url: repoUrl,
        ref,
        root_hint: rootHint || undefined,
        trust_level: trustLevel,
      });

      // Reset form
      setRepoUrl('');
      setRef('main');
      setRootHint('');
      setTrustLevel('basic');

      onSuccess?.();
    } catch (error) {
      // Error handled by mutation
    }
  };

  const isValidUrl = repoUrl.match(/^https:\/\/github\.com\/[^/]+\/[^/]+$/);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <form onSubmit={handleSubmit}>
          <DialogHeader>
            <DialogTitle>Add GitHub Source</DialogTitle>
            <DialogDescription>
              Add a GitHub repository to scan for Claude Code artifacts.
            </DialogDescription>
          </DialogHeader>

          <div className="grid gap-4 py-4">
            <div className="grid gap-2">
              <Label htmlFor="repo-url">Repository URL</Label>
              <Input
                id="repo-url"
                placeholder="https://github.com/owner/repo"
                value={repoUrl}
                onChange={(e) => setRepoUrl(e.target.value)}
                required
              />
              {repoUrl && !isValidUrl && (
                <p className="text-xs text-destructive">
                  Enter a valid GitHub URL (https://github.com/owner/repo)
                </p>
              )}
            </div>

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
              <Label htmlFor="root-hint">Root Directory (optional)</Label>
              <Input
                id="root-hint"
                placeholder="skills/"
                value={rootHint}
                onChange={(e) => setRootHint(e.target.value)}
              />
              <p className="text-xs text-muted-foreground">
                Subdirectory to start scanning from
              </p>
            </div>

            <div className="grid gap-2">
              <Label htmlFor="trust-level">Trust Level</Label>
              <Select value={trustLevel} onValueChange={(v) => setTrustLevel(v as TrustLevel)}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="basic">Basic</SelectItem>
                  <SelectItem value="verified">Verified</SelectItem>
                  <SelectItem value="official">Official</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              disabled={!isValidUrl || createSource.isPending}
            >
              {createSource.isPending ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Adding...
                </>
              ) : (
                'Add Source'
              )}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
