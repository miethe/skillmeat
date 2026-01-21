/**
 * Multi-Step Artifact Deletion Dialog
 *
 * Provides a confirmation dialog for deleting artifacts with options to:
 * - Remove from collection
 * - Undeploy from projects
 * - Delete deployment metadata
 *
 * Uses step-based flow with toggle options and project/deployment selection.
 *
 * Mobile-responsive: Optimized for 320px-768px viewports with:
 * - 44px minimum touch targets (WCAG)
 * - Scrollable content areas
 * - Stacked buttons on mobile
 * - Truncated/wrapped text
 */

'use client';

import * as React from 'react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Checkbox } from '@/components/ui/checkbox';
import { Label } from '@/components/ui/label';
import { AlertTriangle, Loader2, Trash2 } from 'lucide-react';
import { useArtifactDeletion, useDeploymentList } from '@/hooks';
import { toast } from 'sonner';
import type { Artifact } from '@/types/artifact';

export interface ArtifactDeletionDialogProps {
  /** Artifact to delete */
  artifact: Artifact;
  /** Whether dialog is open */
  open: boolean;
  /** Callback when open state changes */
  onOpenChange: (open: boolean) => void;
  /** Context where delete was initiated from */
  context?: 'collection' | 'project';
  /** Project path if initiated from project context */
  projectPath?: string;
  /** Collection ID if initiated from collection context */
  collectionId?: string;
  /** Success callback */
  onSuccess?: () => void;
  /** Error callback */
  onError?: (error: Error) => void;
}

/**
 * ArtifactDeletionDialog - Multi-step artifact deletion with toggle options
 *
 * Primary confirmation step provides toggles for:
 * - Delete from collection (context-aware)
 * - Delete from projects (shows count)
 * - Delete deployments (shows count, destructive styling)
 *
 * @example
 * ```tsx
 * <ArtifactDeletionDialog
 *   artifact={artifact}
 *   open={showDialog}
 *   onOpenChange={setShowDialog}
 *   context="collection"
 *   onSuccess={() => router.refresh()}
 * />
 * ```
 */
export function ArtifactDeletionDialog({
  artifact,
  open,
  onOpenChange,
  context = 'collection',
  projectPath,
  collectionId,
  onSuccess,
  onError,
}: ArtifactDeletionDialogProps) {
  // State for deletion options
  const [deleteFromCollection, setDeleteFromCollection] = React.useState(context === 'collection');
  const [deleteFromProjects, setDeleteFromProjects] = React.useState(false);
  const [deleteDeployments, setDeleteDeployments] = React.useState(false);
  const [selectedProjectPaths, setSelectedProjectPaths] = React.useState<Set<string>>(new Set());
  const [selectedDeploymentPaths, setSelectedDeploymentPaths] = React.useState<Set<string>>(
    new Set()
  );

  // Fetch deployments for this artifact
  // Note: useDeployments returns filtered list but we need project_path from deployment list
  // For now, we'll use the deployment list hook directly
  // Performance: Only fetch when dialog is open, use longer staleTime for modal context
  const { data: deploymentList, isLoading: deploymentsLoading } = useDeploymentList(undefined, {
    enabled: open,
    staleTime: 5 * 60 * 1000, // 5 minutes - deployments won't change while modal is open
  });

  // Filter deployments for this artifact
  // Performance: Memoized to avoid re-filtering on every render
  const deployments = React.useMemo(() => {
    if (!deploymentList) return [];
    return deploymentList.deployments.filter((d) => d.artifact_name === artifact.name);
  }, [deploymentList, artifact.name]);

  // Extract unique project paths from deployments
  // Performance: Memoized to avoid re-computing on every render
  const projectPaths = React.useMemo(() => {
    // Since ArtifactDeploymentInfo doesn't have project_path,
    // we use the parent deploymentList.project_path
    // In the actual implementation, each project would have its own deployment list
    // For now, we'll derive project paths from artifact_path patterns
    const paths = new Set<string>();
    deployments.forEach((d) => {
      // artifact_path is relative to .claude/, so we extract project from context
      // If we have deploymentList.project_path, all deployments are in that project
      if (deploymentList?.project_path) {
        paths.add(deploymentList.project_path);
      }
    });
    return Array.from(paths);
  }, [deployments, deploymentList]);

  // Deletion mutation
  const deletion = useArtifactDeletion();

  // Reset state when dialog opens/closes
  React.useEffect(() => {
    if (!open) {
      setDeleteFromCollection(context === 'collection');
      setDeleteFromProjects(false);
      setDeleteDeployments(false);
      setSelectedProjectPaths(new Set());
      setSelectedDeploymentPaths(new Set());
    }
  }, [open, context]);

  // Auto-select all project paths when "Delete from Projects" is toggled
  React.useEffect(() => {
    if (deleteFromProjects) {
      const allPaths = new Set(projectPaths);
      setSelectedProjectPaths(allPaths);
    } else {
      setSelectedProjectPaths(new Set());
    }
  }, [deleteFromProjects, projectPaths]);

  // Auto-select all deployment paths when "Delete Deployments" is toggled
  React.useEffect(() => {
    if (deleteDeployments) {
      const allPaths = new Set(deployments.map((d) => d.artifact_path));
      setSelectedDeploymentPaths(allPaths);
    } else {
      setSelectedDeploymentPaths(new Set());
    }
  }, [deleteDeployments, deployments]);

  // Toggle individual project selection
  // Performance: useCallback to prevent re-creating function on every render
  const toggleProject = React.useCallback((projectPath: string) => {
    setSelectedProjectPaths((prev) => {
      const next = new Set(prev);
      if (next.has(projectPath)) {
        next.delete(projectPath);
      } else {
        next.add(projectPath);
      }
      return next;
    });
  }, []);

  // Toggle all projects
  // Performance: useCallback with dependencies to avoid re-creating unless needed
  const toggleAllProjects = React.useCallback(() => {
    if (selectedProjectPaths.size === projectPaths.length) {
      // Deselect all
      setSelectedProjectPaths(new Set());
    } else {
      // Select all
      setSelectedProjectPaths(new Set(projectPaths));
    }
  }, [selectedProjectPaths.size, projectPaths]);

  // Toggle individual deployment selection
  // Performance: useCallback to prevent re-creating function on every render
  const toggleDeployment = React.useCallback((deploymentPath: string) => {
    setSelectedDeploymentPaths((prev) => {
      const next = new Set(prev);
      if (next.has(deploymentPath)) {
        next.delete(deploymentPath);
      } else {
        next.add(deploymentPath);
      }
      return next;
    });
  }, []);

  // Toggle all deployments
  // Performance: useCallback with dependencies to avoid re-creating unless needed
  const toggleAllDeployments = React.useCallback(() => {
    if (selectedDeploymentPaths.size === deployments.length) {
      // Deselect all
      setSelectedDeploymentPaths(new Set());
    } else {
      // Select all
      setSelectedDeploymentPaths(new Set(deployments.map((d) => d.artifact_path)));
    }
  }, [selectedDeploymentPaths.size, deployments]);

  // Handle deletion
  const handleDelete = async () => {
    try {
      const result = await deletion.mutateAsync({
        artifact,
        deleteFromCollection,
        deleteFromProjects,
        deleteDeployments,
        selectedProjectPaths: Array.from(selectedProjectPaths),
        selectedDeploymentPaths: Array.from(selectedDeploymentPaths),
      });

      // Show success toast with details
      const messages: string[] = [];
      if (result.collectionDeleted) {
        messages.push('Removed from collection');
      }
      if (result.projectsUndeployed > 0) {
        messages.push(`Undeployed from ${result.projectsUndeployed} project(s)`);
      }
      if (result.deploymentsDeleted > 0) {
        messages.push(`Deleted ${result.deploymentsDeleted} deployment(s)`);
      }

      // Show warnings if there were errors
      if (result.errors.length > 0) {
        toast.warning(`${artifact.name} partially deleted`, {
          description: `${messages.join(', ')}. ${result.errors.length} operation(s) failed.`,
        });
      } else {
        toast.success(`${artifact.name} deleted`, {
          description: messages.join(', '),
        });
      }

      onOpenChange(false);
      onSuccess?.();
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      toast.error(`Failed to delete ${artifact.name}`, {
        description: errorMessage,
      });
      onError?.(error instanceof Error ? error : new Error(errorMessage));
    }
  };

  // Context-aware description
  const getContextDescription = () => {
    if (context === 'collection') {
      return 'This will remove the artifact from your collection.';
    }
    if (context === 'project') {
      return 'This will remove the artifact from this project.';
    }
    return 'This action will delete the artifact.';
  };

  const projectCount = projectPaths.length;
  const deploymentCount = deployments.length;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="flex max-h-[90vh] w-[90vw] max-w-md flex-col sm:w-full">
        <DialogHeader className="flex-shrink-0">
          <DialogTitle className="flex items-center gap-2 text-base sm:text-lg">
            <AlertTriangle className="h-5 w-5 flex-shrink-0 text-destructive" aria-hidden="true" />
            <span className="truncate">Delete {artifact.name}?</span>
          </DialogTitle>
          <DialogDescription asChild>
            <div className="space-y-3">
              <p
                className="text-sm font-medium text-destructive text-muted-foreground"
                role="alert"
              >
                This action cannot be undone.
              </p>
              <p className="text-sm text-muted-foreground">{getContextDescription()}</p>
            </div>
          </DialogDescription>
        </DialogHeader>

        {/* Deletion Options - Scrollable on mobile */}
        <div className="min-h-0 flex-1 space-y-4 overflow-y-auto py-4">
          {/* Delete from Collection Toggle */}
          {context === 'collection' && (
            <div className="flex min-h-[44px] items-start space-x-3">
              <Checkbox
                id="delete-collection"
                checked={deleteFromCollection}
                onCheckedChange={(checked) => setDeleteFromCollection(checked === true)}
                disabled={deletion.isPending}
                className="mt-0.5 min-h-[20px] min-w-[20px]"
              />
              <div className="grid min-w-0 flex-1 gap-1.5 leading-none">
                <Label
                  htmlFor="delete-collection"
                  className="cursor-pointer text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70 sm:text-base"
                >
                  Delete from Collection
                </Label>
                <p className="text-sm text-muted-foreground">
                  Remove this artifact from your collection
                </p>
              </div>
            </div>
          )}

          {/* Delete from Projects Toggle */}
          <div className="flex min-h-[44px] items-start space-x-3">
            <Checkbox
              id="delete-projects"
              checked={deleteFromProjects}
              onCheckedChange={(checked) => setDeleteFromProjects(checked === true)}
              disabled={deletion.isPending || deploymentsLoading || projectCount === 0}
              className="mt-0.5 min-h-[20px] min-w-[20px]"
            />
            <div className="grid min-w-0 flex-1 gap-1.5 leading-none">
              <Label
                htmlFor="delete-projects"
                className="cursor-pointer text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70 sm:text-base"
              >
                Also delete from Projects
                {!deploymentsLoading && projectCount > 0 && (
                  <span
                    className="ml-1 text-muted-foreground"
                    aria-label={`${projectCount} project${projectCount !== 1 ? 's' : ''} found`}
                  >
                    ({projectCount} project{projectCount !== 1 ? 's' : ''})
                  </span>
                )}
              </Label>
              <p className="text-sm text-muted-foreground">
                {deploymentsLoading
                  ? 'Loading deployments...'
                  : projectCount === 0
                    ? 'No deployments found'
                    : 'Undeploy from all projects where this artifact is deployed'}
              </p>
            </div>
          </div>

          {/* Delete Deployments Toggle - RED styling with AlertTriangle */}
          <div className="flex min-h-[44px] items-start space-x-3">
            <Checkbox
              id="delete-deployments"
              checked={deleteDeployments}
              onCheckedChange={(checked) => setDeleteDeployments(checked === true)}
              disabled={deletion.isPending || deploymentsLoading || deploymentCount === 0}
              className="mt-0.5 min-h-[20px] min-w-[20px] border-destructive data-[state=checked]:bg-destructive"
            />
            <div className="grid min-w-0 flex-1 gap-1.5 leading-none">
              <Label
                htmlFor="delete-deployments"
                className="flex cursor-pointer flex-wrap items-center gap-1.5 text-sm font-medium leading-none text-destructive peer-disabled:cursor-not-allowed peer-disabled:opacity-70 sm:text-base"
              >
                <span className="flex items-center gap-1.5">
                  <AlertTriangle className="h-4 w-4 flex-shrink-0" aria-hidden="true" />
                  Delete Deployments
                </span>
                {!deploymentsLoading && deploymentCount > 0 && (
                  <span
                    className="text-muted-foreground"
                    aria-label={`${deploymentCount} deployment${deploymentCount !== 1 ? 's' : ''} found`}
                  >
                    ({deploymentCount} deployment{deploymentCount !== 1 ? 's' : ''})
                  </span>
                )}
              </Label>
              <p className="text-sm text-muted-foreground">
                {deploymentsLoading
                  ? 'Loading deployments...'
                  : deploymentCount === 0
                    ? 'No deployments found'
                    : 'Permanently delete deployment metadata (cannot be undone)'}
              </p>
            </div>
          </div>

          {/* Project Selection Section - Expandable */}
          {deleteFromProjects && projectPaths.length > 0 && (
            <div
              className="space-y-3 rounded-md border bg-muted/30 p-3 sm:p-4"
              role="region"
              aria-label="Project selection"
            >
              {/* Section Header with Counter */}
              <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                <Label className="text-sm font-medium">
                  Select which projects:{' '}
                  <span className="text-muted-foreground" aria-live="polite">
                    ({selectedProjectPaths.size} of {projectPaths.length} selected)
                  </span>
                </Label>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={toggleAllProjects}
                  disabled={deletion.isPending}
                  type="button"
                  className="min-h-[44px] w-full sm:w-auto"
                  aria-label={
                    selectedProjectPaths.size === projectPaths.length
                      ? 'Deselect all projects'
                      : 'Select all projects'
                  }
                >
                  {selectedProjectPaths.size === projectPaths.length
                    ? 'Deselect All'
                    : 'Select All'}
                </Button>
              </div>

              {/* Project List - Scrollable */}
              <div
                className={`space-y-2 ${
                  projectPaths.length > 5 ? 'max-h-48 overflow-y-auto pr-2' : ''
                }`}
                role="list"
                aria-label="Projects to undeploy from"
              >
                {deploymentsLoading ? (
                  <div
                    className="flex items-center justify-center py-4"
                    role="status"
                    aria-live="polite"
                  >
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" aria-hidden="true" />
                    <span className="text-sm text-muted-foreground">Loading projects...</span>
                  </div>
                ) : (
                  projectPaths.map((projectPath) => (
                    <div
                      key={projectPath}
                      className="flex min-h-[44px] items-center space-x-2"
                      role="listitem"
                    >
                      <Checkbox
                        id={`project-${projectPath}`}
                        checked={selectedProjectPaths.has(projectPath)}
                        onCheckedChange={() => toggleProject(projectPath)}
                        disabled={deletion.isPending}
                        className="min-h-[20px] min-w-[20px]"
                        aria-label={`Undeploy from ${projectPath}`}
                      />
                      <Label
                        htmlFor={`project-${projectPath}`}
                        className="min-w-0 flex-1 cursor-pointer break-all text-sm font-normal sm:truncate"
                        title={projectPath}
                      >
                        {projectPath}
                      </Label>
                    </div>
                  ))
                )}
              </div>
            </div>
          )}

          {/* Deployment Deletion Section - RED WARNING */}
          {deleteDeployments && deployments.length > 0 && (
            <div
              className="space-y-4 rounded-md border border-red-200 bg-red-50 p-3 dark:border-red-800 dark:bg-red-950 sm:p-4"
              role="region"
              aria-label="Deployment deletion warning"
            >
              {/* RED Warning Banner */}
              <div
                className="flex items-start gap-2 rounded-md border border-red-300 bg-red-100 p-3 dark:border-red-700 dark:bg-red-900"
                role="alert"
                aria-live="assertive"
              >
                <AlertTriangle
                  className="mt-0.5 h-5 w-5 flex-shrink-0 text-red-600 dark:text-red-400"
                  aria-hidden="true"
                />
                <div className="min-w-0 space-y-1">
                  <p className="text-sm font-semibold text-red-700 dark:text-red-300">
                    WARNING: This will permanently delete files from your filesystem.
                  </p>
                  <p className="text-sm text-red-600 dark:text-red-400">This cannot be undone!</p>
                </div>
              </div>

              {/* Section Header with Counter */}
              <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                <Label className="text-sm font-semibold text-red-700 dark:text-red-300">
                  Deployments to delete:{' '}
                  <span className="text-red-600 dark:text-red-400" aria-live="polite">
                    ({selectedDeploymentPaths.size} of {deployments.length} selected)
                  </span>
                </Label>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={toggleAllDeployments}
                  disabled={deletion.isPending}
                  type="button"
                  className="min-h-[44px] w-full text-red-700 hover:bg-red-100 hover:text-red-800 dark:text-red-300 dark:hover:bg-red-900 dark:hover:text-red-200 sm:w-auto"
                  aria-label={
                    selectedDeploymentPaths.size === deployments.length
                      ? 'Deselect all deployments'
                      : 'Select all deployments'
                  }
                >
                  {selectedDeploymentPaths.size === deployments.length
                    ? 'Deselect All'
                    : 'Select All'}
                </Button>
              </div>

              {/* Deployment List - Scrollable */}
              <div
                className={`space-y-2 ${
                  deployments.length > 5 ? 'max-h-48 overflow-y-auto pr-2' : ''
                }`}
                role="list"
                aria-label="Deployment files to delete"
              >
                {deploymentsLoading ? (
                  <div
                    className="flex items-center justify-center py-4"
                    role="status"
                    aria-live="polite"
                  >
                    <Loader2
                      className="mr-2 h-4 w-4 animate-spin text-red-600 dark:text-red-400"
                      aria-hidden="true"
                    />
                    <span className="text-sm text-red-700 dark:text-red-300">
                      Loading deployments...
                    </span>
                  </div>
                ) : (
                  deployments.map((deployment) => (
                    <div
                      key={deployment.artifact_path}
                      className="flex min-h-[44px] items-start space-x-2 rounded bg-white p-2 dark:bg-red-900/20"
                      role="listitem"
                    >
                      <Checkbox
                        id={`deployment-${deployment.artifact_path}`}
                        checked={selectedDeploymentPaths.has(deployment.artifact_path)}
                        onCheckedChange={() => toggleDeployment(deployment.artifact_path)}
                        disabled={deletion.isPending}
                        className="mt-0.5 min-h-[20px] min-w-[20px] border-red-300 data-[state=checked]:border-red-600 data-[state=checked]:bg-red-600 dark:border-red-700"
                        aria-label={`Delete deployment at ${deployment.artifact_path}`}
                      />
                      <div className="min-w-0 flex-1">
                        <Label
                          htmlFor={`deployment-${deployment.artifact_path}`}
                          className="block cursor-pointer break-all font-mono text-xs text-red-900 dark:text-red-100 sm:text-sm"
                          title={deployment.artifact_path}
                        >
                          {deployment.artifact_path}
                        </Label>
                        {deployment.deployed_at && (
                          <p className="mt-0.5 text-xs text-red-600 dark:text-red-400">
                            Deployed: {new Date(deployment.deployed_at).toLocaleDateString()}
                          </p>
                        )}
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          )}
        </div>

        {/* Footer with Actions */}
        <DialogFooter className="flex-shrink-0 flex-col gap-2 sm:flex-row sm:gap-0">
          <Button
            variant="outline"
            onClick={() => onOpenChange(false)}
            disabled={deletion.isPending}
            className="order-2 min-h-[44px] w-full sm:order-1 sm:w-auto"
          >
            Cancel
          </Button>
          <Button
            variant="destructive"
            onClick={handleDelete}
            disabled={deletion.isPending || deploymentsLoading}
            className="order-1 min-h-[44px] w-full sm:order-2 sm:w-auto"
          >
            {deletion.isPending ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 flex-shrink-0 animate-spin" />
                <span>Deleting...</span>
              </>
            ) : (
              <>
                <Trash2 className="mr-2 h-4 w-4 flex-shrink-0" />
                <span>Delete Artifact</span>
              </>
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
