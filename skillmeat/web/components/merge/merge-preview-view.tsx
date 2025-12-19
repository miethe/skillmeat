/**
 * Preview merge changes view
 */
'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Skeleton } from '@/components/ui/skeleton';
import { FileText, FilePlus, FileMinus, FileWarning } from 'lucide-react';
import type { MergePreviewResponse } from '@/types/merge';

interface MergePreviewViewProps {
  preview: MergePreviewResponse | null;
  isLoading?: boolean;
}

export function MergePreviewView({ preview, isLoading }: MergePreviewViewProps) {
  if (isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-[100px]" />
        <Skeleton className="h-[200px]" />
      </div>
    );
  }

  if (!preview) {
    return (
      <Card>
        <CardContent className="py-12 text-center text-muted-foreground">
          <FileText className="h-12 w-12 mx-auto mb-4 opacity-50" />
          <p>No preview available</p>
        </CardContent>
      </Card>
    );
  }

  const totalChanges =
    preview.filesAdded.length +
    preview.filesRemoved.length +
    preview.filesChanged.length;

  return (
    <div className="space-y-4">
      {/* Statistics Summary */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Merge Preview Summary</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-4 gap-4">
            <div className="text-center">
              <p className="text-2xl font-bold">{totalChanges}</p>
              <p className="text-sm text-muted-foreground">Total Changes</p>
            </div>
            <div className="text-center">
              <p className="text-2xl font-bold text-green-600">
                {preview.filesAdded.length}
              </p>
              <p className="text-sm text-muted-foreground">Added</p>
            </div>
            <div className="text-center">
              <p className="text-2xl font-bold text-red-600">
                {preview.filesRemoved.length}
              </p>
              <p className="text-sm text-muted-foreground">Removed</p>
            </div>
            <div className="text-center">
              <p className="text-2xl font-bold text-amber-600">
                {preview.filesChanged.length}
              </p>
              <p className="text-sm text-muted-foreground">Changed</p>
            </div>
          </div>

          {preview.potentialConflicts.length > 0 && (
            <div className="mt-4 flex items-center gap-2 rounded-lg bg-yellow-50 p-3">
              <FileWarning className="h-5 w-5 text-yellow-600 flex-shrink-0" />
              <p className="text-sm text-yellow-900">
                {preview.potentialConflicts.length} potential conflict(s) detected
              </p>
            </div>
          )}

          {preview.canAutoMerge && (
            <div className="mt-2 flex items-center gap-2 rounded-lg bg-green-50 p-3">
              <FileText className="h-5 w-5 text-green-600 flex-shrink-0" />
              <p className="text-sm text-green-900">
                All changes can be automatically merged
              </p>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Files Added */}
      {preview.filesAdded.length > 0 && (
        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <FilePlus className="h-5 w-5 text-green-600" />
              <CardTitle className="text-lg">
                Files Added ({preview.filesAdded.length})
              </CardTitle>
            </div>
          </CardHeader>
          <CardContent>
            <ScrollArea className="h-[150px]">
              <div className="space-y-1">
                {preview.filesAdded.map((file, index) => (
                  <div
                    key={index}
                    className="flex items-center gap-2 rounded-md bg-green-50 p-2"
                  >
                    <Badge variant="default" className="bg-green-600 text-xs">
                      +
                    </Badge>
                    <span className="font-mono text-sm truncate">{file}</span>
                  </div>
                ))}
              </div>
            </ScrollArea>
          </CardContent>
        </Card>
      )}

      {/* Files Removed */}
      {preview.filesRemoved.length > 0 && (
        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <FileMinus className="h-5 w-5 text-red-600" />
              <CardTitle className="text-lg">
                Files Removed ({preview.filesRemoved.length})
              </CardTitle>
            </div>
          </CardHeader>
          <CardContent>
            <ScrollArea className="h-[150px]">
              <div className="space-y-1">
                {preview.filesRemoved.map((file, index) => (
                  <div
                    key={index}
                    className="flex items-center gap-2 rounded-md bg-red-50 p-2"
                  >
                    <Badge variant="destructive" className="text-xs">
                      -
                    </Badge>
                    <span className="font-mono text-sm truncate line-through">
                      {file}
                    </span>
                  </div>
                ))}
              </div>
            </ScrollArea>
          </CardContent>
        </Card>
      )}

      {/* Files Changed */}
      {preview.filesChanged.length > 0 && (
        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <FileText className="h-5 w-5 text-amber-600" />
              <CardTitle className="text-lg">
                Files Changed ({preview.filesChanged.length})
              </CardTitle>
            </div>
          </CardHeader>
          <CardContent>
            <ScrollArea className="h-[150px]">
              <div className="space-y-1">
                {preview.filesChanged.map((file, index) => (
                  <div
                    key={index}
                    className="flex items-center gap-2 rounded-md bg-amber-50 p-2"
                  >
                    <Badge variant="secondary" className="text-xs">
                      M
                    </Badge>
                    <span className="font-mono text-sm truncate">{file}</span>
                  </div>
                ))}
              </div>
            </ScrollArea>
          </CardContent>
        </Card>
      )}

      {/* Potential Conflicts */}
      {preview.potentialConflicts.length > 0 && (
        <Card className="border-yellow-200">
          <CardHeader>
            <div className="flex items-center gap-2">
              <FileWarning className="h-5 w-5 text-yellow-600" />
              <CardTitle className="text-lg">
                Potential Conflicts ({preview.potentialConflicts.length})
              </CardTitle>
            </div>
          </CardHeader>
          <CardContent>
            <ScrollArea className="h-[150px]">
              <div className="space-y-2">
                {preview.potentialConflicts.map((conflict, index) => (
                  <div
                    key={index}
                    className="flex items-center justify-between gap-2 rounded-md bg-yellow-50 p-2 border border-yellow-200"
                  >
                    <span className="font-mono text-sm truncate flex-1">
                      {conflict.filePath}
                    </span>
                    <div className="flex items-center gap-2 flex-shrink-0">
                      <Badge variant="outline" className="text-xs">
                        {conflict.conflictType}
                      </Badge>
                      {conflict.isBinary && (
                        <Badge variant="secondary" className="text-xs">
                          binary
                        </Badge>
                      )}
                      {!conflict.autoMergeable && (
                        <Badge variant="destructive" className="text-xs">
                          manual
                        </Badge>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </ScrollArea>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
