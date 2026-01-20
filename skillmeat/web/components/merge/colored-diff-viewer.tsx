/**
 * Three-way diff viewer for merge conflicts
 */
'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Badge } from '@/components/ui/badge';
import { FileText } from 'lucide-react';
import { cn } from '@/lib/utils';

interface DiffViewerProps {
  filePath: string;
  baseContent?: string[];
  localContent?: string[];
  remoteContent?: string[];
  isBinary?: boolean;
}

export function ColoredDiffViewer({
  filePath,
  baseContent = [],
  localContent = [],
  remoteContent = [],
  isBinary = false,
}: DiffViewerProps) {
  if (isBinary) {
    return (
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <FileText className="h-5 w-5" />
            <CardTitle className="text-lg">Diff Viewer</CardTitle>
          </div>
          <p className="truncate font-mono text-sm text-muted-foreground">{filePath}</p>
        </CardHeader>
        <CardContent className="py-12 text-center text-muted-foreground">
          <FileText className="mx-auto mb-4 h-12 w-12 opacity-50" />
          <p>Binary file - diff not available</p>
        </CardContent>
      </Card>
    );
  }

  const renderDiffColumn = (title: string, content: string[], colorClass: string) => {
    return (
      <div className="flex-1 overflow-hidden rounded-lg border">
        <div className={cn('border-b p-2 text-sm font-semibold', colorClass)}>{title}</div>
        <ScrollArea className="h-[400px]">
          <div className="font-mono text-xs">
            {content.length === 0 ? (
              <div className="p-4 text-center text-muted-foreground">No content</div>
            ) : (
              content.map((line, index) => (
                <div key={index} className="flex transition-colors hover:bg-accent/50">
                  <div className="w-12 flex-shrink-0 border-r bg-muted/30 py-1 pr-2 text-right text-muted-foreground">
                    {index + 1}
                  </div>
                  <div className="flex-1 whitespace-pre-wrap break-all px-2 py-1">
                    {line || ' '}
                  </div>
                </div>
              ))
            )}
          </div>
        </ScrollArea>
      </div>
    );
  };

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center gap-2">
          <FileText className="h-5 w-5" />
          <CardTitle className="text-lg">Three-Way Diff Viewer</CardTitle>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <p className="flex-1 truncate font-mono text-sm text-muted-foreground">{filePath}</p>
          <div className="flex items-center gap-2">
            <Badge variant="outline" className="text-xs">
              <div className="mr-1 h-2 w-2 rounded-full bg-yellow-600" />
              Base
            </Badge>
            <Badge variant="outline" className="text-xs">
              <div className="mr-1 h-2 w-2 rounded-full bg-blue-600" />
              Local
            </Badge>
            <Badge variant="outline" className="text-xs">
              <div className="mr-1 h-2 w-2 rounded-full bg-green-600" />
              Remote
            </Badge>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-3 gap-2">
          {renderDiffColumn('Base (Common Ancestor)', baseContent, 'bg-yellow-100')}
          {renderDiffColumn('Local (Your Changes)', localContent, 'bg-blue-100')}
          {renderDiffColumn('Remote (Incoming)', remoteContent, 'bg-green-100')}
        </div>
        <div className="mt-4 space-y-2 rounded-lg bg-muted p-3">
          <p className="text-sm font-semibold">Legend:</p>
          <div className="grid grid-cols-2 gap-2 text-xs">
            <div className="flex items-center gap-2">
              <div className="h-3 w-3 rounded bg-green-600" />
              <span>Remote additions (from upstream)</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="h-3 w-3 rounded bg-blue-600" />
              <span>Local changes (your edits)</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="h-3 w-3 rounded bg-red-600" />
              <span>Conflicts (both modified)</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="h-3 w-3 rounded bg-yellow-600" />
              <span>Removals (deletions)</span>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
