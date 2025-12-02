/**
 * UpdateAvailableModal Component
 *
 * Modal showing details about available artifact updates
 */

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
import { Package, ArrowRight, GitBranch, AlertTriangle } from 'lucide-react';
import { cn } from '@/lib/utils';

export interface UpdateAvailableModalProps {
  isOpen: boolean;
  onClose: () => void;
  artifact: {
    id: string;
    name: string;
    type: string;
    projectName: string;
    deployedVersion?: string;
    upstreamVersion?: string;
    versionDifference?: string;
  };
  onUpdate?: () => void;
}

/**
 * Get severity indicator based on version difference
 */
function getVersionSeverity(versionDifference?: string): {
  variant: 'destructive' | 'secondary' | 'outline';
  icon: typeof AlertTriangle;
  label: string;
} {
  if (!versionDifference) {
    return {
      variant: 'secondary',
      icon: AlertTriangle,
      label: 'Update Available',
    };
  }

  const lowerDiff = versionDifference.toLowerCase();

  if (lowerDiff.includes('major')) {
    return {
      variant: 'destructive',
      icon: AlertTriangle,
      label: 'Major Update',
    };
  }

  return {
    variant: 'secondary',
    icon: AlertTriangle,
    label: 'Minor Update',
  };
}

/**
 * Modal displaying update information and actions
 */
export function UpdateAvailableModal({
  isOpen,
  onClose,
  artifact,
  onUpdate,
}: UpdateAvailableModalProps) {
  const severity = getVersionSeverity(artifact.versionDifference);
  const SeverityIcon = severity.icon;

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Package className="h-5 w-5" />
            Update Available
          </DialogTitle>
          <DialogDescription>
            A newer version of this artifact is available upstream
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          {/* Artifact Info */}
          <div className="rounded-lg border p-4">
            <div className="mb-2 flex items-start justify-between">
              <div>
                <h3 className="font-semibold">{artifact.name}</h3>
                <div className="mt-1 flex items-center gap-2 text-sm text-muted-foreground">
                  <GitBranch className="h-3 w-3" />
                  <span>{artifact.projectName}</span>
                </div>
              </div>
              <Badge variant="outline">{artifact.type}</Badge>
            </div>

            {/* Severity Badge */}
            <Badge variant={severity.variant} className="mt-2 gap-1">
              <SeverityIcon className="h-3 w-3" />
              {severity.label}
            </Badge>
          </div>

          {/* Version Comparison */}
          <div className="space-y-3">
            <div className="flex items-center justify-between rounded-lg border p-3">
              <div className="flex-1">
                <p className="text-xs text-muted-foreground">Current Version</p>
                <p className="font-mono text-sm font-medium">
                  {artifact.deployedVersion || 'unknown'}
                </p>
              </div>
              <ArrowRight className="mx-2 h-4 w-4 text-muted-foreground" />
              <div className="flex-1">
                <p className="text-xs text-muted-foreground">Available Version</p>
                <p className="font-mono text-sm font-medium text-primary">
                  {artifact.upstreamVersion || 'unknown'}
                </p>
              </div>
            </div>

            {/* Version Difference Details */}
            {artifact.versionDifference && (
              <div className="rounded-lg bg-muted p-3">
                <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                  Change Type
                </p>
                <p className="mt-1 text-sm">{artifact.versionDifference}</p>
              </div>
            )}
          </div>

          {/* Warning for major updates */}
          {artifact.versionDifference?.toLowerCase().includes('major') && (
            <div className="rounded-lg border border-destructive/50 bg-destructive/10 p-3">
              <div className="flex items-start gap-2">
                <AlertTriangle className="mt-0.5 h-4 w-4 text-destructive" />
                <div className="flex-1">
                  <p className="text-sm font-medium text-destructive">Major Version Update</p>
                  <p className="mt-1 text-xs text-destructive/80">
                    This update may include breaking changes. Review the changelog before updating.
                  </p>
                </div>
              </div>
            </div>
          )}
        </div>

        <DialogFooter className="gap-2 sm:gap-0">
          <Button variant="outline" onClick={onClose}>
            Close
          </Button>
          {onUpdate && (
            <Button onClick={onUpdate} className="gap-2">
              <Package className="h-4 w-4" />
              Update Artifact
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
