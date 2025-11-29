'use client';

import { useState } from 'react';
import { GitBranch } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import type { ConflictInfo } from '@/hooks/useSync';

export interface ConflictResolverProps {
  conflicts: ConflictInfo[];
  onResolve: (strategy: 'ours' | 'theirs' | 'manual') => void;
  onCancel: () => void;
}

export function ConflictResolver({ conflicts, onResolve, onCancel }: ConflictResolverProps) {
  const [selectedStrategy, setSelectedStrategy] = useState<'ours' | 'theirs' | null>(null);

  const handleResolve = () => {
    if (selectedStrategy) {
      onResolve(selectedStrategy);
    }
  };

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-start gap-3">
        <div className="rounded-lg bg-yellow-500/10 p-2">
          <GitBranch className="h-5 w-5 text-yellow-600" />
        </div>
        <div className="min-w-0 flex-1">
          <h3 className="font-semibold">Conflicts Detected</h3>
          <p className="mt-1 text-sm text-muted-foreground">
            {conflicts.length} file{conflicts.length !== 1 ? 's' : ''} have conflicts that need to
            be resolved before syncing.
          </p>
        </div>
      </div>

      {/* Conflicts List */}
      <div className="max-h-60 space-y-2 overflow-y-auto">
        {conflicts.map((conflict, index) => (
          <ConflictItem key={index} conflict={conflict} />
        ))}
      </div>

      {/* Resolution Strategy */}
      <div className="space-y-3 border-t pt-4">
        <h4 className="text-sm font-medium">Choose Resolution Strategy</h4>

        <div className="space-y-2">
          {/* Keep Local (Ours) */}
          <button
            onClick={() => setSelectedStrategy('ours')}
            className={`w-full rounded-lg border p-3 text-left transition-colors ${
              selectedStrategy === 'ours'
                ? 'border-primary bg-primary/5'
                : 'hover:border-primary/50'
            }`}
          >
            <div className="flex items-start gap-3">
              <div
                className={`mt-0.5 flex h-5 w-5 items-center justify-center rounded-full border-2 ${
                  selectedStrategy === 'ours'
                    ? 'border-primary bg-primary'
                    : 'border-muted-foreground'
                }`}
              >
                {selectedStrategy === 'ours' && (
                  <div className="h-2 w-2 rounded-full bg-primary-foreground" />
                )}
              </div>
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2">
                  <span className="font-medium">Keep Local Version</span>
                  <Badge variant="outline" className="text-xs">
                    Ours
                  </Badge>
                </div>
                <p className="mt-1 text-xs text-muted-foreground">
                  Keep your local changes and discard upstream changes
                </p>
              </div>
            </div>
          </button>

          {/* Use Upstream (Theirs) */}
          <button
            onClick={() => setSelectedStrategy('theirs')}
            className={`w-full rounded-lg border p-3 text-left transition-colors ${
              selectedStrategy === 'theirs'
                ? 'border-primary bg-primary/5'
                : 'hover:border-primary/50'
            }`}
          >
            <div className="flex items-start gap-3">
              <div
                className={`mt-0.5 flex h-5 w-5 items-center justify-center rounded-full border-2 ${
                  selectedStrategy === 'theirs'
                    ? 'border-primary bg-primary'
                    : 'border-muted-foreground'
                }`}
              >
                {selectedStrategy === 'theirs' && (
                  <div className="h-2 w-2 rounded-full bg-primary-foreground" />
                )}
              </div>
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2">
                  <span className="font-medium">Use Upstream Version</span>
                  <Badge variant="outline" className="text-xs">
                    Theirs
                  </Badge>
                </div>
                <p className="mt-1 text-xs text-muted-foreground">
                  Overwrite local changes with upstream version
                </p>
              </div>
            </div>
          </button>
        </div>
      </div>

      {/* Actions */}
      <div className="flex items-center justify-end gap-2 border-t pt-4">
        <Button variant="outline" onClick={onCancel}>
          Cancel
        </Button>
        <Button onClick={handleResolve} disabled={!selectedStrategy}>
          Resolve Conflicts
        </Button>
      </div>
    </div>
  );
}

function ConflictItem({ conflict }: { conflict: ConflictInfo }) {
  const typeColors = {
    modified: 'text-yellow-600',
    deleted: 'text-red-600',
    added: 'text-green-600',
  };

  const typeLabels = {
    modified: 'Modified',
    deleted: 'Deleted',
    added: 'Added',
  };

  return (
    <div className="space-y-2 rounded-lg border p-3">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <code className="rounded bg-muted px-2 py-1 font-mono text-xs">
              {conflict.filePath}
            </code>
            <Badge variant="outline" className={`text-xs ${typeColors[conflict.conflictType]}`}>
              {typeLabels[conflict.conflictType]}
            </Badge>
          </div>
          <p className="mt-1 text-xs text-muted-foreground">{conflict.description}</p>
        </div>
      </div>

      {/* Version Comparison */}
      <div className="grid grid-cols-2 gap-2 text-xs">
        <div className="space-y-1">
          <span className="text-muted-foreground">Local</span>
          <code className="block rounded bg-muted px-2 py-1">{conflict.currentVersion}</code>
        </div>
        <div className="space-y-1">
          <span className="text-muted-foreground">Upstream</span>
          <code className="block rounded bg-muted px-2 py-1">{conflict.upstreamVersion}</code>
        </div>
      </div>
    </div>
  );
}
