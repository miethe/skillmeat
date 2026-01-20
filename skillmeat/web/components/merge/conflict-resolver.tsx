/**
 * Resolution controls for single conflict
 */
'use client';

import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { Label } from '@/components/ui/label';
import { FileText, GitMerge } from 'lucide-react';
import type { ConflictMetadata, ConflictResolveRequest } from '@/types/merge';
import { cn } from '@/lib/utils';

interface ConflictResolverProps {
  conflict: ConflictMetadata | null;
  onResolve: (resolution: ConflictResolveRequest) => void;
  isResolving?: boolean;
}

type ResolutionType = 'use_local' | 'use_remote' | 'use_base' | 'custom';

export function ConflictResolver({
  conflict,
  onResolve,
  isResolving = false,
}: ConflictResolverProps) {
  const [selectedResolution, setSelectedResolution] = useState<ResolutionType>('use_local');
  const [customContent, setCustomContent] = useState('');

  if (!conflict) {
    return (
      <Card>
        <CardContent className="py-12 text-center text-muted-foreground">
          <GitMerge className="mx-auto mb-4 h-12 w-12 opacity-50" />
          <p>Select a conflict to resolve</p>
        </CardContent>
      </Card>
    );
  }

  const handleResolve = () => {
    const resolution: ConflictResolveRequest = {
      filePath: conflict.filePath,
      resolution: selectedResolution,
    };

    if (selectedResolution === 'custom') {
      resolution.customContent = customContent;
    }

    onResolve(resolution);
  };

  const resolutionOptions: Array<{
    value: ResolutionType;
    label: string;
    description: string;
    disabled?: boolean;
  }> = [
    {
      value: 'use_local',
      label: 'Use Local Version',
      description: 'Keep the changes from your local collection',
    },
    {
      value: 'use_remote',
      label: 'Use Remote Version',
      description: 'Adopt the changes from the remote snapshot',
    },
    {
      value: 'use_base',
      label: 'Use Base Version',
      description: 'Revert to the common ancestor version',
    },
    {
      value: 'custom',
      label: 'Custom Resolution',
      description: 'Manually resolve the conflict',
      disabled: conflict.isBinary,
    },
  ];

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center gap-2">
          <FileText className="h-5 w-5 text-primary" />
          <CardTitle className="text-lg">Resolve Conflict</CardTitle>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Conflict Info */}
        <div className="space-y-2 rounded-lg border p-3">
          <p className="truncate font-mono text-sm">{conflict.filePath}</p>
          <div className="flex flex-wrap items-center gap-2">
            <Badge variant="outline" className="text-xs">
              {conflict.conflictType}
            </Badge>
            {conflict.isBinary && (
              <Badge variant="secondary" className="text-xs">
                Binary File
              </Badge>
            )}
            {!conflict.autoMergeable && (
              <Badge variant="destructive" className="text-xs">
                Manual Required
              </Badge>
            )}
          </div>
        </div>

        {/* Binary File Warning */}
        {conflict.isBinary && (
          <div className="rounded-lg border border-yellow-200 bg-yellow-50 p-3">
            <p className="text-sm text-yellow-900">
              This is a binary file. Custom resolution is not available. Please choose to use the
              local, remote, or base version.
            </p>
          </div>
        )}

        {/* Resolution Options */}
        <div className="space-y-3">
          <Label className="text-base font-semibold">Resolution Strategy</Label>
          <div className="space-y-2">
            {resolutionOptions.map((option) => (
              <button
                key={option.value}
                onClick={() => setSelectedResolution(option.value)}
                disabled={option.disabled}
                className={cn(
                  'w-full rounded-lg border p-3 text-left transition-colors',
                  'hover:border-accent-foreground/20 hover:bg-accent',
                  'disabled:cursor-not-allowed disabled:opacity-50',
                  selectedResolution === option.value && 'border-primary bg-primary/5'
                )}
              >
                <div className="flex items-start gap-3">
                  <div
                    className={cn(
                      'mt-0.5 h-4 w-4 flex-shrink-0 rounded-full border-2',
                      selectedResolution === option.value
                        ? 'border-primary bg-primary'
                        : 'border-muted-foreground'
                    )}
                  >
                    {selectedResolution === option.value && (
                      <div className="h-full w-full scale-50 rounded-full bg-white" />
                    )}
                  </div>
                  <div className="flex-1">
                    <p className="font-semibold">{option.label}</p>
                    <p className="text-sm text-muted-foreground">{option.description}</p>
                  </div>
                </div>
              </button>
            ))}
          </div>
        </div>

        {/* Custom Content Input */}
        {selectedResolution === 'custom' && !conflict.isBinary && (
          <div className="space-y-2">
            <Label htmlFor="custom-content">Custom Content</Label>
            <Textarea
              id="custom-content"
              placeholder="Enter the resolved content..."
              value={customContent}
              onChange={(e) => setCustomContent(e.target.value)}
              className="min-h-[200px] font-mono text-sm"
            />
            <p className="text-xs text-muted-foreground">
              Provide the fully resolved content for this file
            </p>
          </div>
        )}

        {/* Current Selection Indicator */}
        <div className="rounded-lg border border-blue-200 bg-blue-50 p-3">
          <p className="text-sm font-semibold text-blue-900">Current Resolution:</p>
          <p className="text-sm text-blue-700">
            {resolutionOptions.find((o) => o.value === selectedResolution)?.label}
          </p>
        </div>

        {/* Resolve Button */}
        <Button
          onClick={handleResolve}
          disabled={isResolving || (selectedResolution === 'custom' && !customContent.trim())}
          className="w-full"
        >
          {isResolving ? 'Resolving...' : 'Apply Resolution'}
        </Button>
      </CardContent>
    </Card>
  );
}
