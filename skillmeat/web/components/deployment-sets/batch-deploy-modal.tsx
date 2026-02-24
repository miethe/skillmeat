'use client';

import { useState } from 'react';
import { CheckCircle2, Loader2, Rocket, SkipForward, XCircle } from 'lucide-react';
import { useBatchDeploySet, useDeploymentProfiles, useProjects, useToast } from '@/hooks';
import type { BatchDeployResponse, BatchDeployResult } from '@/types/deployment-sets';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';

// ============================================================================
// Step 1 — Input form
// ============================================================================

interface InputStepProps {
  setId: string;
  setName: string;
  onDeploy: (response: BatchDeployResponse) => void;
  onClose: () => void;
}

function InputStep({ setId, setName, onDeploy, onClose }: InputStepProps) {
  const { toast } = useToast();
  const batchDeploy = useBatchDeploySet();

  const { data: projects = [], isLoading: projectsLoading } = useProjects();
  const [selectedProjectId, setSelectedProjectId] = useState<string>('');
  const [selectedProfileId, setSelectedProfileId] = useState<string>('');

  // Profiles are fetched once a project is selected
  const { data: profiles = [], isLoading: profilesLoading } = useDeploymentProfiles(
    selectedProjectId || undefined,
  );

  const canDeploy = !!selectedProjectId && !batchDeploy.isPending;

  const handleProjectChange = (projectId: string) => {
    setSelectedProjectId(projectId);
    setSelectedProfileId(''); // reset profile when project changes
  };

  const handleDeploy = async () => {
    if (!selectedProjectId) return;
    try {
      const response = await batchDeploy.mutateAsync({
        set_id: setId,
        project_id: selectedProjectId,
        profile_id: selectedProfileId || undefined,
      });
      onDeploy(response);
    } catch (err) {
      toast({
        title: 'Deployment failed',
        description: err instanceof Error ? err.message : 'An unexpected error occurred.',
        variant: 'destructive',
      });
    }
  };

  return (
    <>
      <DialogHeader>
        <DialogTitle className="flex items-center gap-2">
          <Rocket className="h-5 w-5 text-muted-foreground" aria-hidden="true" />
          Deploy Set
        </DialogTitle>
        <DialogDescription>
          Deploy all artifacts in <strong>{setName}</strong> to a project.
        </DialogDescription>
      </DialogHeader>

      <div className="space-y-4 py-4">
        {/* Project selector */}
        <div className="space-y-2">
          <Label htmlFor="project-select">Target project</Label>
          <Select
            value={selectedProjectId}
            onValueChange={handleProjectChange}
            disabled={projectsLoading || batchDeploy.isPending}
          >
            <SelectTrigger id="project-select" aria-label="Select target project">
              <SelectValue
                placeholder={projectsLoading ? 'Loading projects…' : 'Select a project'}
              />
            </SelectTrigger>
            <SelectContent>
              {projects.length === 0 && !projectsLoading ? (
                <SelectItem value="__empty__" disabled>
                  No projects found
                </SelectItem>
              ) : (
                projects.map((project) => (
                  <SelectItem key={project.id} value={project.id}>
                    {project.name}
                    <span className="ml-2 text-xs text-muted-foreground">{project.path}</span>
                  </SelectItem>
                ))
              )}
            </SelectContent>
          </Select>
        </div>

        {/* Profile selector — only shown once a project is selected */}
        {selectedProjectId && (
          <div className="space-y-2">
            <Label htmlFor="profile-select">
              Deployment profile{' '}
              <span className="text-muted-foreground font-normal">(optional)</span>
            </Label>
            <Select
              value={selectedProfileId}
              onValueChange={setSelectedProfileId}
              disabled={profilesLoading || batchDeploy.isPending}
            >
              <SelectTrigger id="profile-select" aria-label="Select deployment profile">
                <SelectValue
                  placeholder={profilesLoading ? 'Loading profiles…' : 'Default profile'}
                />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="">Default profile</SelectItem>
                {profiles.map((profile) => (
                  <SelectItem key={profile.id} value={profile.id}>
                    {profile.profile_id}
                    {profile.description && (
                      <span className="ml-2 text-xs text-muted-foreground">
                        {profile.description}
                      </span>
                    )}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        )}
      </div>

      <DialogFooter>
        <Button variant="outline" onClick={onClose} disabled={batchDeploy.isPending}>
          Cancel
        </Button>
        <Button onClick={handleDeploy} disabled={!canDeploy}>
          {batchDeploy.isPending ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" aria-hidden="true" />
              Deploying…
            </>
          ) : (
            <>
              <Rocket className="mr-2 h-4 w-4" aria-hidden="true" />
              Deploy
            </>
          )}
        </Button>
      </DialogFooter>
    </>
  );
}

// ============================================================================
// Step 2 — Results table
// ============================================================================

const STATUS_CONFIG = {
  success: {
    label: 'Success',
    icon: CheckCircle2,
    badgeClass: 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400',
  },
  skipped: {
    label: 'Skipped',
    icon: SkipForward,
    badgeClass: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400',
  },
  failed: {
    label: 'Failed',
    icon: XCircle,
    badgeClass: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400',
  },
} as const;

function StatusBadge({ status }: { status: BatchDeployResult['status'] }) {
  const config = STATUS_CONFIG[status];
  const Icon = config.icon;
  return (
    <Badge className={`gap-1 border-0 font-medium ${config.badgeClass}`} variant="outline">
      <Icon className="h-3 w-3" aria-hidden="true" />
      {config.label}
    </Badge>
  );
}

interface ResultsStepProps {
  response: BatchDeployResponse;
  onClose: () => void;
}

function ResultsStep({ response, onClose }: ResultsStepProps) {
  const { succeeded, skipped, failed, results, set_name } = response;

  return (
    <>
      <DialogHeader>
        <DialogTitle className="flex items-center gap-2">
          <Rocket className="h-5 w-5 text-muted-foreground" aria-hidden="true" />
          Deployment Results
        </DialogTitle>
        <DialogDescription>
          <strong>{set_name}</strong> deployment complete.
        </DialogDescription>
      </DialogHeader>

      <div className="py-4 space-y-4">
        {/* Summary line */}
        <p className="text-sm text-muted-foreground" aria-live="polite">
          <span className="text-green-700 dark:text-green-400 font-medium">{succeeded} succeeded</span>
          {', '}
          <span className="text-yellow-700 dark:text-yellow-400 font-medium">{skipped} skipped</span>
          {', '}
          <span className="text-red-700 dark:text-red-400 font-medium">{failed} failed</span>
        </p>

        {/* Results table */}
        <div className="rounded-md border overflow-auto max-h-80" role="region" aria-label="Deploy results">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Artifact</TableHead>
                <TableHead className="w-28">Status</TableHead>
                <TableHead>Message</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {results.map((result) => (
                <TableRow key={result.artifact_uuid}>
                  <TableCell className="font-mono text-xs">
                    <span className="font-medium text-foreground text-sm">
                      {result.artifact_name ?? 'Unnamed'}
                    </span>
                    <br />
                    <span className="text-muted-foreground">{result.artifact_uuid}</span>
                  </TableCell>
                  <TableCell>
                    <StatusBadge status={result.status} />
                  </TableCell>
                  <TableCell className="text-xs text-muted-foreground">
                    {result.error ?? '—'}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      </div>

      <DialogFooter>
        <Button onClick={onClose}>Close</Button>
      </DialogFooter>
    </>
  );
}

// ============================================================================
// Public component
// ============================================================================

export interface BatchDeployModalProps {
  /** The deployment set ID to deploy */
  setId: string;
  /** Human-readable name shown in the dialog title */
  setName: string;
  /** Controlled open state */
  open: boolean;
  /** Called when the dialog should close */
  onOpenChange: (open: boolean) => void;
}

/**
 * BatchDeployModal — two-step dialog for batch-deploying a deployment set.
 *
 * Step 1 (Input): project + profile selection
 * Step 2 (Results): per-artifact result table with summary line
 *
 * Triggered via `open`/`onOpenChange` props. Resets to step 1 whenever
 * the dialog is re-opened so state does not bleed between sessions.
 */
export function BatchDeployModal({ setId, setName, open, onOpenChange }: BatchDeployModalProps) {
  const [result, setResult] = useState<BatchDeployResponse | null>(null);

  const handleClose = () => {
    onOpenChange(false);
    // Reset state after animation completes
    setTimeout(() => setResult(null), 200);
  };

  const handleOpenChange = (next: boolean) => {
    if (!next) {
      handleClose();
    } else {
      onOpenChange(true);
    }
  };

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent
        className="sm:max-w-lg"
        aria-label={result ? 'Deployment results' : 'Deploy deployment set'}
      >
        {result ? (
          <ResultsStep response={result} onClose={handleClose} />
        ) : (
          <InputStep
            setId={setId}
            setName={setName}
            onDeploy={setResult}
            onClose={handleClose}
          />
        )}
      </DialogContent>
    </Dialog>
  );
}
