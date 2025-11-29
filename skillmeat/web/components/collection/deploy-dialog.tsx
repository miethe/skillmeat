'use client';

import { useState } from 'react';
import { Upload, Folder, AlertTriangle } from 'lucide-react';
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
import { ProgressIndicator, ProgressStep } from './progress-indicator';
import { useDeploy } from '@/hooks/useDeploy';
import type { Artifact } from '@/types/artifact';

export interface DeployDialogProps {
  artifact: Artifact | null;
  isOpen: boolean;
  onClose: () => void;
  onSuccess?: () => void;
}

export function DeployDialog({ artifact, isOpen, onClose, onSuccess }: DeployDialogProps) {
  const [projectPath, setProjectPath] = useState('');
  const [overwrite, setOverwrite] = useState(false);
  const [isDeploying, setIsDeploying] = useState(false);
  const [streamUrl, setStreamUrl] = useState<string | null>(null);
  const [initialSteps] = useState<ProgressStep[]>([
    { step: 'Validating artifact', status: 'pending' },
    { step: 'Checking project path', status: 'pending' },
    { step: 'Copying files', status: 'pending' },
    { step: 'Updating deployment registry', status: 'pending' },
  ]);

  const deployMutation = useDeploy({
    onSuccess: () => {
      // Deployment successful - show completion
      handleComplete(true);
    },
    onError: () => {
      setIsDeploying(false);
    },
  });

  const handleDeploy = async () => {
    if (!artifact) return;

    setIsDeploying(true);

    try {
      await deployMutation.mutateAsync({
        artifactId: artifact.id,
        artifactName: artifact.name,
        artifactType: artifact.type,
        projectPath: projectPath || undefined,
        overwrite,
      });
    } catch (error) {
      console.error('Deploy failed:', error);
    }
  };

  const handleComplete = (success: boolean) => {
    setIsDeploying(false);

    if (success) {
      setTimeout(() => {
        onSuccess?.();
        onClose();
        // Reset state
        setProjectPath('');
        setOverwrite(false);
        setStreamUrl(null);
      }, 1500);
    }
  };

  const handleClose = () => {
    if (!isDeploying) {
      onClose();
      // Reset state
      setProjectPath('');
      setOverwrite(false);
      setStreamUrl(null);
      setIsDeploying(false);
    }
  };

  if (!artifact) return null;

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && handleClose()}>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <div className="flex items-center gap-3">
            <div className="rounded-lg bg-primary/10 p-2">
              <Upload className="h-5 w-5 text-primary" />
            </div>
            <div>
              <DialogTitle>Deploy Artifact</DialogTitle>
              <DialogDescription>Deploy {artifact.name} to a project</DialogDescription>
            </div>
          </div>
        </DialogHeader>

        <div className="space-y-4 py-4">
          {!isDeploying ? (
            <>
              {/* Artifact Info */}
              <div className="space-y-2 rounded-lg border p-3">
                <div className="flex items-center justify-between text-sm">
                  <span className="text-muted-foreground">Artifact</span>
                  <span className="font-medium">{artifact.name}</span>
                </div>
                <div className="flex items-center justify-between text-sm">
                  <span className="text-muted-foreground">Type</span>
                  <span className="font-medium capitalize">{artifact.type}</span>
                </div>
                <div className="flex items-center justify-between text-sm">
                  <span className="text-muted-foreground">Version</span>
                  <code className="rounded bg-muted px-2 py-1 text-xs">
                    {artifact.version || 'N/A'}
                  </code>
                </div>
              </div>

              {/* Project Path Input */}
              <div className="space-y-2">
                <label
                  htmlFor="projectPath"
                  className="flex items-center gap-2 text-sm font-medium"
                >
                  <Folder className="h-4 w-4" />
                  Project Path
                </label>
                <Input
                  id="projectPath"
                  placeholder="/path/to/project (leave empty for current directory)"
                  value={projectPath}
                  onChange={(e) => setProjectPath(e.target.value)}
                  disabled={isDeploying}
                />
                <p className="text-xs text-muted-foreground">
                  The artifact will be deployed to the .claude directory in this project
                </p>
              </div>

              {/* Overwrite Warning */}
              {artifact.usageStats.totalDeployments > 0 && (
                <div className="rounded-lg border border-yellow-500/50 bg-yellow-500/10 p-3">
                  <div className="flex items-start gap-2">
                    <AlertTriangle className="mt-0.5 h-4 w-4 flex-shrink-0 text-yellow-600" />
                    <div className="min-w-0 flex-1">
                      <p className="text-sm font-medium text-yellow-900 dark:text-yellow-100">
                        Existing Deployments
                      </p>
                      <p className="mt-1 text-xs text-yellow-800 dark:text-yellow-200">
                        This artifact is already deployed to {artifact.usageStats.totalDeployments}{' '}
                        project(s). If the target project already has this artifact, it will be
                        overwritten.
                      </p>
                    </div>
                  </div>
                </div>
              )}
            </>
          ) : (
            <>
              {/* Progress Indicator */}
              <ProgressIndicator
                streamUrl={streamUrl}
                enabled={isDeploying}
                initialSteps={initialSteps}
                onComplete={handleComplete}
                onError={(error) => {
                  console.error('Deploy error:', error);
                  setIsDeploying(false);
                }}
              />
            </>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={handleClose} disabled={isDeploying}>
            Cancel
          </Button>
          <Button onClick={handleDeploy} disabled={isDeploying || deployMutation.isPending}>
            {isDeploying ? 'Deploying...' : 'Deploy'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
