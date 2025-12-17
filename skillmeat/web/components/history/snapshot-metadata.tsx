'use client';

import { useState } from 'react';
import { format, formatDistanceToNow } from 'date-fns';
import {
  Copy,
  Check,
  Clock,
  FolderOpen,
  FileStack,
  AlertTriangle,
  CheckCircle2,
  XCircle,
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Separator } from '@/components/ui/separator';
import type { Snapshot, RollbackSafetyAnalysis } from '@/types/snapshot';

interface SnapshotMetadataProps {
  snapshot: Snapshot;
  safetyAnalysis?: RollbackSafetyAnalysis;
  showSafetyAnalysis?: boolean;
  className?: string;
}

export function SnapshotMetadata({
  snapshot,
  safetyAnalysis,
  showSafetyAnalysis = true,
  className,
}: SnapshotMetadataProps) {
  const [copied, setCopied] = useState(false);

  const handleCopyId = async () => {
    try {
      await navigator.clipboard.writeText(snapshot.id);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (error) {
      console.error('Failed to copy ID:', error);
    }
  };

  const formattedTimestamp = format(new Date(snapshot.timestamp), 'MMMM d, yyyy \'at\' h:mm:ss a');
  const relativeTime = formatDistanceToNow(new Date(snapshot.timestamp), { addSuffix: true });

  return (
    <Card className={className}>
      <CardHeader>
        <CardTitle>Snapshot Details</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Snapshot ID */}
        <div className="space-y-2">
          <label className="text-sm font-medium text-muted-foreground">Snapshot ID</label>
          <div className="flex items-center gap-2">
            <code className="flex-1 rounded bg-muted px-3 py-2 text-sm font-mono">
              {snapshot.id}
            </code>
            <Button
              variant="outline"
              size="sm"
              onClick={handleCopyId}
              className="shrink-0"
            >
              {copied ? (
                <>
                  <Check className="h-4 w-4 mr-1" />
                  Copied!
                </>
              ) : (
                <>
                  <Copy className="h-4 w-4 mr-1" />
                  Copy
                </>
              )}
            </Button>
          </div>
        </div>

        <Separator />

        {/* Timestamp */}
        <div className="space-y-2">
          <label className="text-sm font-medium text-muted-foreground flex items-center gap-2">
            <Clock className="h-4 w-4" />
            Timestamp
          </label>
          <div className="space-y-1">
            <p className="text-sm">{formattedTimestamp}</p>
            <p className="text-xs text-muted-foreground">{relativeTime}</p>
          </div>
        </div>

        <Separator />

        {/* Message */}
        <div className="space-y-2">
          <label className="text-sm font-medium text-muted-foreground">Message</label>
          <p className="text-sm whitespace-pre-wrap">{snapshot.message}</p>
        </div>

        <Separator />

        {/* Collection Info */}
        <div className="grid grid-cols-2 gap-4">
          <div className="space-y-2">
            <label className="text-sm font-medium text-muted-foreground flex items-center gap-2">
              <FolderOpen className="h-4 w-4" />
              Collection
            </label>
            <p className="text-sm font-medium">{snapshot.collectionName}</p>
          </div>

          <div className="space-y-2">
            <label className="text-sm font-medium text-muted-foreground flex items-center gap-2">
              <FileStack className="h-4 w-4" />
              Artifacts
            </label>
            <Badge variant="secondary" className="w-fit">
              {snapshot.artifactCount} {snapshot.artifactCount === 1 ? 'artifact' : 'artifacts'}
            </Badge>
          </div>
        </div>

        {/* Safety Analysis */}
        {showSafetyAnalysis && safetyAnalysis && (
          <>
            <Separator />
            <div className="space-y-3">
              <label className="text-sm font-medium text-muted-foreground">
                Rollback Safety Analysis
              </label>

              {/* Safety Status */}
              <div className="flex items-center gap-2">
                {safetyAnalysis.isSafe ? (
                  <>
                    <CheckCircle2 className="h-5 w-5 text-green-600" />
                    <span className="text-sm font-medium text-green-600">Safe to restore</span>
                  </>
                ) : (
                  <>
                    <XCircle className="h-5 w-5 text-red-600" />
                    <span className="text-sm font-medium text-red-600">Conflicts detected</span>
                  </>
                )}
              </div>

              {/* Files with Conflicts */}
              {safetyAnalysis.filesWithConflicts.length > 0 && (
                <Alert variant="destructive">
                  <AlertTriangle className="h-4 w-4" />
                  <AlertDescription>
                    <p className="font-medium mb-2">
                      {safetyAnalysis.filesWithConflicts.length}{' '}
                      {safetyAnalysis.filesWithConflicts.length === 1 ? 'file has' : 'files have'}{' '}
                      conflicts:
                    </p>
                    <ul className="list-disc list-inside space-y-1 text-xs">
                      {safetyAnalysis.filesWithConflicts.map((file) => (
                        <li key={file} className="font-mono">
                          {file}
                        </li>
                      ))}
                    </ul>
                  </AlertDescription>
                </Alert>
              )}

              {/* Files Safe to Restore */}
              {safetyAnalysis.filesSafeToRestore.length > 0 && (
                <div className="rounded-lg border border-green-200 bg-green-50 p-3 dark:border-green-900 dark:bg-green-950">
                  <div className="flex items-start gap-2">
                    <CheckCircle2 className="h-4 w-4 text-green-600 mt-0.5 shrink-0" />
                    <div className="flex-1">
                      <p className="text-sm font-medium text-green-900 dark:text-green-100 mb-2">
                        {safetyAnalysis.filesSafeToRestore.length}{' '}
                        {safetyAnalysis.filesSafeToRestore.length === 1 ? 'file is' : 'files are'}{' '}
                        safe to restore:
                      </p>
                      <ul className="list-disc list-inside space-y-1 text-xs text-green-800 dark:text-green-200">
                        {safetyAnalysis.filesSafeToRestore.map((file) => (
                          <li key={file} className="font-mono">
                            {file}
                          </li>
                        ))}
                      </ul>
                    </div>
                  </div>
                </div>
              )}

              {/* Warnings */}
              {safetyAnalysis.warnings.length > 0 && (
                <Alert>
                  <AlertTriangle className="h-4 w-4" />
                  <AlertDescription>
                    <p className="font-medium mb-2">Warnings:</p>
                    <ul className="list-disc list-inside space-y-1 text-xs">
                      {safetyAnalysis.warnings.map((warning, index) => (
                        <li key={index}>{warning}</li>
                      ))}
                    </ul>
                  </AlertDescription>
                </Alert>
              )}
            </div>
          </>
        )}
      </CardContent>
    </Card>
  );
}
