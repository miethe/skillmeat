/**
 * Merge progress indicator component
 */
'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { CheckCircle, XCircle, Clock, FileText } from 'lucide-react';
import { cn } from '@/lib/utils';

interface FileStatus {
  filePath: string;
  status: 'pending' | 'processing' | 'success' | 'failed';
  error?: string;
}

interface MergeProgressIndicatorProps {
  filesTotal: number;
  filesProcessed: number;
  currentFile?: string;
  fileStatuses: FileStatus[];
}

export function MergeProgressIndicator({
  filesTotal,
  filesProcessed,
  currentFile,
  fileStatuses,
}: MergeProgressIndicatorProps) {
  const progressPercentage = filesTotal > 0 ? (filesProcessed / filesTotal) * 100 : 0;

  const successCount = fileStatuses.filter((f) => f.status === 'success').length;
  const failedCount = fileStatuses.filter((f) => f.status === 'failed').length;
  const pendingCount = fileStatuses.filter((f) => f.status === 'pending').length;

  const getStatusIcon = (status: FileStatus['status']) => {
    switch (status) {
      case 'success':
        return CheckCircle;
      case 'failed':
        return XCircle;
      case 'processing':
        return FileText;
      case 'pending':
      default:
        return Clock;
    }
  };

  const getStatusColor = (status: FileStatus['status']) => {
    switch (status) {
      case 'success':
        return 'text-green-600';
      case 'failed':
        return 'text-red-600';
      case 'processing':
        return 'text-blue-600';
      case 'pending':
      default:
        return 'text-gray-400';
    }
  };

  const getStatusLabel = (status: FileStatus['status']) => {
    switch (status) {
      case 'success':
        return 'Success';
      case 'failed':
        return 'Failed';
      case 'processing':
        return 'Processing';
      case 'pending':
      default:
        return 'Pending';
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg">Merge Progress</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Progress Bar */}
        <div className="space-y-2">
          <div className="flex items-center justify-between text-sm">
            <span className="text-muted-foreground">
              {filesProcessed} of {filesTotal} files processed
            </span>
            <span className="font-semibold">{Math.round(progressPercentage)}%</span>
          </div>
          <Progress value={progressPercentage} className="h-2" />
        </div>

        {/* Current File */}
        {currentFile && (
          <div className="rounded-lg border border-blue-200 bg-blue-50 p-3">
            <p className="mb-1 text-sm font-semibold text-blue-900">Currently Processing:</p>
            <p className="truncate font-mono text-sm text-blue-700">{currentFile}</p>
          </div>
        )}

        {/* Status Summary */}
        <div className="grid grid-cols-3 gap-2">
          <div className="rounded-lg border p-2 text-center">
            <p className="text-lg font-bold text-green-600">{successCount}</p>
            <p className="text-xs text-muted-foreground">Success</p>
          </div>
          <div className="rounded-lg border p-2 text-center">
            <p className="text-lg font-bold text-red-600">{failedCount}</p>
            <p className="text-xs text-muted-foreground">Failed</p>
          </div>
          <div className="rounded-lg border p-2 text-center">
            <p className="text-lg font-bold text-gray-600">{pendingCount}</p>
            <p className="text-xs text-muted-foreground">Pending</p>
          </div>
        </div>

        {/* File Status List */}
        {fileStatuses.length > 0 && (
          <div className="space-y-2">
            <p className="text-sm font-semibold">File Details</p>
            <ScrollArea className="h-[200px]">
              <div className="space-y-1 pr-4">
                {fileStatuses.map((fileStatus, index) => {
                  const Icon = getStatusIcon(fileStatus.status);
                  const color = getStatusColor(fileStatus.status);

                  return (
                    <div
                      key={index}
                      className={cn(
                        'flex items-center gap-2 rounded-md border p-2',
                        fileStatus.status === 'success' && 'bg-green-50',
                        fileStatus.status === 'failed' && 'bg-red-50',
                        fileStatus.status === 'processing' && 'bg-blue-50'
                      )}
                    >
                      <Icon className={cn('h-4 w-4 flex-shrink-0', color)} />
                      <span className="flex-1 truncate font-mono text-xs">
                        {fileStatus.filePath}
                      </span>
                      <Badge
                        variant={
                          fileStatus.status === 'success'
                            ? 'default'
                            : fileStatus.status === 'failed'
                              ? 'destructive'
                              : 'secondary'
                        }
                        className="text-xs"
                      >
                        {getStatusLabel(fileStatus.status)}
                      </Badge>
                    </div>
                  );
                })}
              </div>
            </ScrollArea>
          </div>
        )}

        {/* Failed Files Details */}
        {failedCount > 0 && (
          <div className="space-y-2">
            <p className="text-sm font-semibold text-red-600">Failed Files ({failedCount})</p>
            <ScrollArea className="h-[100px]">
              <div className="space-y-1 pr-4">
                {fileStatuses
                  .filter((f) => f.status === 'failed')
                  .map((fileStatus, index) => (
                    <div
                      key={index}
                      className="space-y-1 rounded-md border border-red-200 bg-red-50 p-2"
                    >
                      <p className="font-mono text-xs text-red-900">{fileStatus.filePath}</p>
                      {fileStatus.error && (
                        <p className="text-xs text-red-700">{fileStatus.error}</p>
                      )}
                    </div>
                  ))}
              </div>
            </ScrollArea>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
