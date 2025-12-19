/**
 * List of merge conflicts
 */
'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { AlertTriangle, FileText, FileX, FilePlus } from 'lucide-react';
import type { ConflictMetadata } from '@/types/merge';
import { cn } from '@/lib/utils';

interface ConflictListProps {
  conflicts: ConflictMetadata[];
  selectedConflict?: ConflictMetadata;
  onSelectConflict: (conflict: ConflictMetadata) => void;
  resolvedConflicts?: Set<string>;
}

export function ConflictList({
  conflicts,
  selectedConflict,
  onSelectConflict,
  resolvedConflicts = new Set(),
}: ConflictListProps) {
  const getConflictIcon = (type: ConflictMetadata['conflictType']) => {
    switch (type) {
      case 'deletion':
        return FileX;
      case 'add_add':
        return FilePlus;
      case 'both_modified':
      case 'content':
      default:
        return FileText;
    }
  };

  const getConflictColor = (type: ConflictMetadata['conflictType']) => {
    switch (type) {
      case 'deletion':
        return 'text-red-600';
      case 'add_add':
        return 'text-yellow-600';
      case 'both_modified':
        return 'text-orange-600';
      case 'content':
      default:
        return 'text-blue-600';
    }
  };

  const getConflictTypeLabel = (type: ConflictMetadata['conflictType']) => {
    switch (type) {
      case 'deletion':
        return 'Deletion Conflict';
      case 'add_add':
        return 'Both Added';
      case 'both_modified':
        return 'Both Modified';
      case 'content':
      default:
        return 'Content Conflict';
    }
  };

  if (conflicts.length === 0) {
    return (
      <Card>
        <CardContent className="py-12 text-center text-muted-foreground">
          <FileText className="h-12 w-12 mx-auto mb-4 opacity-50" />
          <p>No conflicts to resolve</p>
        </CardContent>
      </Card>
    );
  }

  const unresolvedConflicts = conflicts.filter(
    (c) => !resolvedConflicts.has(c.filePath)
  );
  const resolvedCount = conflicts.length - unresolvedConflicts.length;

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <AlertTriangle className="h-5 w-5 text-yellow-600" />
            <CardTitle className="text-lg">
              Conflicts ({unresolvedConflicts.length} remaining)
            </CardTitle>
          </div>
          {resolvedCount > 0 && (
            <Badge variant="default" className="bg-green-600">
              {resolvedCount} resolved
            </Badge>
          )}
        </div>
      </CardHeader>
      <CardContent>
        <ScrollArea className="h-[400px] pr-4">
          <div className="space-y-2">
            {conflicts.map((conflict, index) => {
              const Icon = getConflictIcon(conflict.conflictType);
              const isResolved = resolvedConflicts.has(conflict.filePath);
              const isSelected =
                selectedConflict?.filePath === conflict.filePath;

              return (
                <button
                  key={index}
                  onClick={() => onSelectConflict(conflict)}
                  className={cn(
                    'w-full text-left rounded-lg border p-3 transition-colors',
                    'hover:bg-accent hover:border-accent-foreground/20',
                    isSelected && 'border-primary bg-primary/5',
                    isResolved && 'opacity-50'
                  )}
                >
                  <div className="flex items-start gap-3">
                    <Icon
                      className={cn(
                        'h-5 w-5 flex-shrink-0 mt-0.5',
                        getConflictColor(conflict.conflictType),
                        isResolved && 'opacity-50'
                      )}
                    />
                    <div className="flex-1 min-w-0 space-y-2">
                      <div className="flex items-start justify-between gap-2">
                        <span
                          className={cn(
                            'font-mono text-sm truncate',
                            isResolved && 'line-through'
                          )}
                        >
                          {conflict.filePath}
                        </span>
                        {isResolved && (
                          <Badge variant="default" className="bg-green-600 text-xs">
                            Resolved
                          </Badge>
                        )}
                      </div>
                      <div className="flex items-center gap-2 flex-wrap">
                        <Badge variant="outline" className="text-xs">
                          {getConflictTypeLabel(conflict.conflictType)}
                        </Badge>
                        {conflict.isBinary && (
                          <Badge variant="secondary" className="text-xs">
                            Binary File
                          </Badge>
                        )}
                        {conflict.autoMergeable ? (
                          <Badge variant="default" className="bg-green-600 text-xs">
                            Auto-mergeable
                          </Badge>
                        ) : (
                          <Badge variant="destructive" className="text-xs">
                            Manual Required
                          </Badge>
                        )}
                      </div>
                    </div>
                  </div>
                </button>
              );
            })}
          </div>
        </ScrollArea>
      </CardContent>
    </Card>
  );
}
