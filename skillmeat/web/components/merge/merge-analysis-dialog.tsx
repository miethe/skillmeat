/**
 * Pre-merge safety analysis dialog
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
import { Badge } from '@/components/ui/badge';
import { AlertTriangle, CheckCircle, XCircle } from 'lucide-react';
import type { MergeSafetyResponse } from '@/types/merge';
import { cn } from '@/lib/utils';

interface MergeAnalysisDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  analysis: MergeSafetyResponse | null;
  onProceed: () => void;
  isLoading?: boolean;
}

export function MergeAnalysisDialog({
  open,
  onOpenChange,
  analysis,
  onProceed,
  isLoading = false,
}: MergeAnalysisDialogProps) {
  if (!analysis) return null;

  const getSafetyIndicator = () => {
    if (analysis.canAutoMerge && analysis.warnings.length === 0) {
      return {
        icon: CheckCircle,
        color: 'text-green-600',
        bgColor: 'bg-green-50',
        label: 'Safe to merge',
        variant: 'default' as const,
      };
    }
    if (analysis.canAutoMerge && analysis.warnings.length > 0) {
      return {
        icon: AlertTriangle,
        color: 'text-yellow-600',
        bgColor: 'bg-yellow-50',
        label: 'Merge with warnings',
        variant: 'secondary' as const,
      };
    }
    return {
      icon: XCircle,
      color: 'text-red-600',
      bgColor: 'bg-red-50',
      label: 'Conflicts detected',
      variant: 'destructive' as const,
    };
  };

  const indicator = getSafetyIndicator();
  const Icon = indicator.icon;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[600px]">
        <DialogHeader>
          <DialogTitle>Merge Safety Analysis</DialogTitle>
          <DialogDescription>
            Review the analysis results before proceeding with the merge
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          {/* Safety Indicator */}
          <div
            className={cn(
              'flex items-center gap-3 rounded-lg p-4',
              indicator.bgColor
            )}
          >
            <Icon className={cn('h-6 w-6', indicator.color)} />
            <div className="flex-1">
              <p className={cn('font-semibold', indicator.color)}>
                {indicator.label}
              </p>
              <p className="text-sm text-muted-foreground">
                {analysis.canAutoMerge
                  ? 'All changes can be automatically merged'
                  : 'Manual conflict resolution required'}
              </p>
            </div>
            <Badge variant={indicator.variant}>
              {analysis.canAutoMerge ? 'Auto-merge' : 'Manual'}
            </Badge>
          </div>

          {/* Statistics */}
          <div className="grid grid-cols-2 gap-4">
            <div className="rounded-lg border p-4">
              <p className="text-sm text-muted-foreground">Auto-mergeable</p>
              <p className="text-2xl font-bold text-green-600">
                {analysis.autoMergeableCount}
              </p>
            </div>
            <div className="rounded-lg border p-4">
              <p className="text-sm text-muted-foreground">Conflicts</p>
              <p className="text-2xl font-bold text-red-600">
                {analysis.conflictCount}
              </p>
            </div>
          </div>

          {/* Warnings */}
          {analysis.warnings.length > 0 && (
            <div className="space-y-2">
              <p className="font-semibold text-sm">Warnings</p>
              <div className="space-y-1">
                {analysis.warnings.map((warning, index) => (
                  <div
                    key={index}
                    className="flex items-start gap-2 rounded-md bg-yellow-50 p-2 text-sm"
                  >
                    <AlertTriangle className="h-4 w-4 text-yellow-600 mt-0.5 flex-shrink-0" />
                    <span className="text-yellow-900">{warning}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Conflict Summary */}
          {analysis.conflicts.length > 0 && (
            <div className="space-y-2">
              <p className="font-semibold text-sm">Conflicts Detected</p>
              <div className="max-h-[200px] overflow-y-auto space-y-1">
                {analysis.conflicts.map((conflict, index) => (
                  <div
                    key={index}
                    className="flex items-center justify-between rounded-md bg-red-50 p-2 text-sm"
                  >
                    <span className="font-mono text-xs truncate flex-1">
                      {conflict.filePath}
                    </span>
                    <Badge variant="outline" className="ml-2 text-xs">
                      {conflict.conflictType}
                    </Badge>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        <DialogFooter>
          <Button
            variant="outline"
            onClick={() => onOpenChange(false)}
            disabled={isLoading}
          >
            Cancel
          </Button>
          <Button onClick={onProceed} disabled={isLoading}>
            {isLoading ? 'Processing...' : 'Proceed with Merge'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
