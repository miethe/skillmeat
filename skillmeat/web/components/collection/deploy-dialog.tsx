'use client';

import { useState, useEffect, useMemo } from 'react';
import { Upload, Folder, AlertTriangle, Plus, Check, FolderOpen } from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Switch } from '@/components/ui/switch';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectSeparator,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { ProgressIndicator, ProgressStep } from './progress-indicator';
import { useDeployArtifact, useProjects } from '@/hooks';
import { CreateProjectDialog } from '@/app/projects/components/create-project-dialog';
import type { Artifact } from '@/types/artifact';
import { cn } from '@/lib/utils';

const CUSTOM_PATH_VALUE = '__custom__';

/**
 * Get the default deployment directory based on artifact type
 */
function getDefaultDeployPath(artifactType: string): string {
  switch (artifactType) {
    case 'skill':
      return '.claude/skills/';
    case 'command':
      return '.claude/commands/';
    case 'hook':
      return '.claude/hooks/';
    case 'agent':
      return '.claude/agents/';
    case 'mcp':
    case 'mcp-server':
      return '.claude/mcp/';
    default:
      return '.claude/skills/';
  }
}

/**
 * Validate and sanitize a custom sub-path for deployment
 * @param input - The user input for sub-directory
 * @returns Object with sanitized value and any error message
 */
function validateAndSanitizeSubPath(input: string): { value: string; error: string | null } {
  const trimmed = input.trim();

  // Check for directory traversal attempts
  if (trimmed.includes('../') || trimmed.includes('..\\')) {
    return { value: trimmed, error: 'Directory traversal not allowed' };
  }

  // Check for absolute paths
  if (trimmed.startsWith('/') || /^[a-zA-Z]:/.test(trimmed)) {
    return { value: trimmed, error: 'Absolute paths not allowed' };
  }

  // If non-empty, ensure it ends with /
  if (trimmed && !trimmed.endsWith('/')) {
    return { value: trimmed + '/', error: null };
  }

  return { value: trimmed, error: null };
}

export interface DeployDialogProps {
  artifact: Artifact | null;
  existingDeploymentPaths?: string[];
  isOpen: boolean;
  onClose: () => void;
  onSuccess?: () => void;
}

export function DeployDialog({
  artifact,
  existingDeploymentPaths,
  isOpen,
  onClose,
  onSuccess,
}: DeployDialogProps) {
  const [selectedProjectId, setSelectedProjectId] = useState<string | null>(null);
  const [customPath, setCustomPath] = useState('');
  const [showCreateProject, setShowCreateProject] = useState(false);
  const [overwriteEnabled, setOverwriteEnabled] = useState(false);
  const [showOverwriteWarning, setShowOverwriteWarning] = useState(false);
  const [showConfirmDialog, setShowConfirmDialog] = useState(false);
  const [isDeploying, setIsDeploying] = useState(false);
  // Custom deployment path state
  const [customPathEnabled, setCustomPathEnabled] = useState(false);
  const [customSubPath, setCustomSubPath] = useState('');
  const [customPathError, setCustomPathError] = useState<string | null>(null);
  const [streamUrl, setStreamUrl] = useState<string | null>(null);
  const [initialSteps] = useState<ProgressStep[]>([
    { step: 'Validating artifact', status: 'pending' },
    { step: 'Checking project path', status: 'pending' },
    { step: 'Copying files', status: 'pending' },
    { step: 'Updating deployment registry', status: 'pending' },
  ]);

  const { data: projects, isLoading: projectsLoading } = useProjects();

  // Determine if using custom path mode
  const useCustomPath = selectedProjectId === CUSTOM_PATH_VALUE;

  // Get selected project object
  const selectedProject =
    selectedProjectId && !useCustomPath ? projects?.find((p) => p.id === selectedProjectId) : null;

  // Get the effective path for deployment
  const effectivePath = useCustomPath ? customPath : selectedProject?.path || '';

  // Default deploy path based on artifact type
  const defaultDeployPath = useMemo(() => {
    return artifact ? getDefaultDeployPath(artifact.type) : '.claude/skills/';
  }, [artifact]);

  // Compute the full custom destination path if enabled
  const computedDestPath = useMemo(() => {
    if (!customPathEnabled || customPathError) return undefined;
    // If no sub-path, just use the default
    if (!customSubPath.trim()) return undefined;
    // Combine default path with sub-path
    // e.g., '.claude/skills/' + 'dev/' = '.claude/skills/dev/'
    const sanitized = validateAndSanitizeSubPath(customSubPath);
    if (sanitized.error) return undefined;
    return defaultDeployPath + sanitized.value;
  }, [customPathEnabled, customSubPath, customPathError, defaultDeployPath]);

  // Handle custom sub-path input change with validation
  const handleCustomSubPathChange = (value: string) => {
    const result = validateAndSanitizeSubPath(value);
    setCustomSubPath(value);
    setCustomPathError(result.error);
  };

  // Check if artifact is already deployed to a project
  const checkIsAlreadyDeployed = (projectPath: string): boolean => {
    if (!Array.isArray(existingDeploymentPaths)) return false;
    // Check if any deployment path starts with this project path
    return existingDeploymentPaths.some(
      (deployPath) =>
        deployPath.startsWith(projectPath + '/.claude/') || deployPath.startsWith(projectPath + '/')
    );
  };

  // Track if current selection is already deployed
  const currentSelectionDeployed = useMemo(() => {
    if (useCustomPath || !selectedProject) return false;
    return checkIsAlreadyDeployed(selectedProject.path);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedProject, existingDeploymentPaths, useCustomPath]);

  // Check if current selection is valid for deployment
  const canDeploy = useMemo(() => {
    if (!selectedProjectId) return false;

    // If custom deployment path is enabled with error, prevent deployment
    if (customPathEnabled && customPathError) return false;

    if (useCustomPath) {
      // Custom path is valid if not empty
      return customPath.trim().length > 0;
    }

    // For project selection, allow if not deployed OR overwrite is enabled
    if (selectedProject) {
      const deployed = checkIsAlreadyDeployed(selectedProject.path);
      return !deployed || overwriteEnabled;
    }

    return false;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [
    selectedProjectId,
    useCustomPath,
    customPath,
    selectedProject,
    existingDeploymentPaths,
    overwriteEnabled,
    customPathEnabled,
    customPathError,
  ]);

  // Reset selection when dialog opens for a new artifact
  useEffect(() => {
    if (isOpen) {
      setSelectedProjectId(null);
      setCustomPath('');
      setOverwriteEnabled(false);
      setShowOverwriteWarning(false);
      setShowConfirmDialog(false);
      // Reset custom deployment path state
      setCustomPathEnabled(false);
      setCustomSubPath('');
      setCustomPathError(null);
    }
  }, [isOpen, artifact?.id]);

  // Reset overwrite warning when overwrite is enabled
  useEffect(() => {
    if (overwriteEnabled) {
      setShowOverwriteWarning(false);
    }
  }, [overwriteEnabled]);

  // Reset overwrite state when project selection changes
  useEffect(() => {
    setOverwriteEnabled(false);
    setShowOverwriteWarning(false);
  }, [selectedProjectId]);

  const deployMutation = useDeployArtifact();

  const handleDeployClick = () => {
    if (!artifact) return;

    // If already deployed and overwrite not enabled, show warning
    if (currentSelectionDeployed && !overwriteEnabled) {
      setShowOverwriteWarning(true);
      return;
    }

    // If overwrite enabled, show confirmation dialog
    if (currentSelectionDeployed && overwriteEnabled) {
      setShowConfirmDialog(true);
      return;
    }

    // Normal deployment (not already deployed)
    executeDeploy();
  };

  const executeDeploy = async () => {
    if (!artifact) return;

    setShowConfirmDialog(false);
    setIsDeploying(true);

    try {
      await deployMutation.mutateAsync({
        artifact_id: `${artifact.type}:${artifact.name}`,
        artifact_name: artifact.name,
        artifact_type: artifact.type,
        project_path: effectivePath || undefined,
        overwrite: overwriteEnabled,
        // Include custom destination path if enabled and valid
        dest_path: computedDestPath,
      });
      // Deployment successful
      handleComplete(true);
    } catch (error) {
      console.error('Deploy failed:', error);
      setIsDeploying(false);
    }
  };

  const handleProjectCreated = (newProject?: { id: string; path: string; name: string }) => {
    // Select the newly created project if provided
    if (newProject) {
      setSelectedProjectId(newProject.id);
    }
    setShowCreateProject(false);
  };

  const handleComplete = (success: boolean) => {
    setIsDeploying(false);

    if (success) {
      setTimeout(() => {
        onSuccess?.();
        onClose();
        // Reset state
        setSelectedProjectId(null);
        setCustomPath('');
        setOverwriteEnabled(false);
        setShowOverwriteWarning(false);
        setShowConfirmDialog(false);
        setStreamUrl(null);
      }, 1500);
    }
  };

  const handleClose = () => {
    if (!isDeploying) {
      onClose();
      // Reset state
      setSelectedProjectId(null);
      setCustomPath('');
      setOverwriteEnabled(false);
      setShowOverwriteWarning(false);
      setShowConfirmDialog(false);
      setStreamUrl(null);
      setIsDeploying(false);
      // Reset custom deployment path state
      setCustomPathEnabled(false);
      setCustomSubPath('');
      setCustomPathError(null);
    }
  };

  if (!artifact) return null;

  return (
    <>
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

                {/* Project Selector */}
                <div className="space-y-2">
                  <label className="flex items-center gap-2 text-sm font-medium">
                    <Folder className="h-4 w-4" />
                    Target Project
                  </label>
                  <div className="flex gap-2">
                    <Select
                      value={selectedProjectId || ''}
                      onValueChange={(value) => setSelectedProjectId(value || null)}
                      disabled={isDeploying || projectsLoading}
                    >
                      <SelectTrigger className="flex-1" aria-label="Select target project">
                        <SelectValue
                          placeholder={
                            projectsLoading ? 'Loading projects...' : 'Select a project...'
                          }
                        />
                      </SelectTrigger>
                      <SelectContent className="z-[60]">
                        {projects && projects.length > 0 ? (
                          <>
                            {projects.map((project) => {
                              const deployed = checkIsAlreadyDeployed(project.path);
                              return (
                                <SelectItem key={project.id} value={project.id}>
                                  <div className="flex items-center gap-2">
                                    {deployed && (
                                      <Check className="h-4 w-4 flex-shrink-0 text-green-500" />
                                    )}
                                    <div className="flex flex-col">
                                      <div className="flex items-center gap-2">
                                        <span className={deployed ? 'text-muted-foreground' : ''}>
                                          {project.name}
                                        </span>
                                        {deployed && (
                                          <span className="text-xs text-yellow-600 dark:text-yellow-500">
                                            (Already Deployed)
                                          </span>
                                        )}
                                      </div>
                                      <span className="max-w-[280px] truncate text-xs text-muted-foreground">
                                        {project.path}
                                      </span>
                                    </div>
                                  </div>
                                </SelectItem>
                              );
                            })}
                            <SelectSeparator />
                          </>
                        ) : !projectsLoading ? (
                          <div className="px-2 py-1.5 text-sm text-muted-foreground">
                            No projects found
                          </div>
                        ) : null}
                        <SelectItem value={CUSTOM_PATH_VALUE}>
                          <span className="text-muted-foreground">Custom path...</span>
                        </SelectItem>
                      </SelectContent>
                    </Select>
                    <Button
                      type="button"
                      variant="outline"
                      size="icon"
                      onClick={() => setShowCreateProject(true)}
                      disabled={isDeploying}
                      aria-label="Add new project"
                    >
                      <Plus className="h-4 w-4" />
                    </Button>
                  </div>
                  {selectedProject && (
                    <div>
                      <p className="text-xs text-muted-foreground">
                        Deploy to: {selectedProject.path}
                      </p>
                      {currentSelectionDeployed && !overwriteEnabled && (
                        <p className="text-xs text-yellow-600">
                          Artifact is already deployed to this project. Enable overwrite to replace.
                        </p>
                      )}
                    </div>
                  )}
                </div>

                {/* Custom Path Input (shown when "Custom path..." is selected) */}
                {useCustomPath && (
                  <div className="space-y-2">
                    <label htmlFor="customPath" className="text-sm font-medium">
                      Custom Path
                    </label>
                    <Input
                      id="customPath"
                      placeholder="/path/to/project"
                      value={customPath}
                      onChange={(e) => setCustomPath(e.target.value)}
                      disabled={isDeploying}
                    />
                    <p className="text-xs text-muted-foreground">
                      The artifact will be deployed to the .claude directory in this path
                    </p>
                  </div>
                )}

                {/* Overwrite Toggle - Only shown when selecting an already-deployed project */}
                {currentSelectionDeployed && (
                  <div
                    className={cn(
                      'flex items-center gap-3 rounded-lg border p-3 transition-all',
                      showOverwriteWarning
                        ? 'border-red-500 bg-red-50 ring-2 ring-red-500/20 dark:bg-red-950/20'
                        : 'border-border'
                    )}
                  >
                    <Switch
                      id="overwrite-toggle"
                      checked={overwriteEnabled}
                      onCheckedChange={setOverwriteEnabled}
                      disabled={isDeploying}
                    />
                    <div className="flex-1 space-y-1">
                      <Label
                        htmlFor="overwrite-toggle"
                        className={cn(
                          'cursor-pointer text-sm font-medium',
                          showOverwriteWarning && 'text-red-700 dark:text-red-400'
                        )}
                      >
                        Overwrite Deployment
                      </Label>
                      {showOverwriteWarning ? (
                        <p className="text-xs text-red-600 dark:text-red-400">
                          Enable overwrite to replace existing deployment
                        </p>
                      ) : (
                        <p className="text-xs text-muted-foreground">
                          Replace the existing deployment with this version
                        </p>
                      )}
                    </div>
                  </div>
                )}

                {/* Custom Deployment Path Toggle */}
                <div className="space-y-3">
                  <div className="flex items-center gap-3">
                    <Switch
                      id="custom-path-toggle"
                      checked={customPathEnabled}
                      onCheckedChange={(checked) => {
                        setCustomPathEnabled(checked);
                        if (!checked) {
                          setCustomSubPath('');
                          setCustomPathError(null);
                        }
                      }}
                      disabled={isDeploying}
                    />
                    <Label
                      htmlFor="custom-path-toggle"
                      className="cursor-pointer text-sm font-medium"
                    >
                      Custom Deployment Path
                    </Label>
                  </div>

                  {/* Custom path input - shown when toggle is ON */}
                  {customPathEnabled && (
                    <div className="space-y-2 pl-1">
                      <div className="flex items-center gap-2">
                        <div className="flex shrink-0 items-center gap-1.5 text-sm text-muted-foreground">
                          <FolderOpen className="h-4 w-4" />
                          <span className="font-mono">{defaultDeployPath}</span>
                        </div>
                        <Input
                          id="customSubPath"
                          placeholder="subdirectory/"
                          value={customSubPath}
                          onChange={(e) => handleCustomSubPathChange(e.target.value)}
                          disabled={isDeploying}
                          className={cn(
                            'flex-1 font-mono text-sm',
                            customPathError && 'border-red-500 focus-visible:ring-red-500'
                          )}
                          aria-invalid={!!customPathError}
                          aria-describedby={customPathError ? 'custom-path-error' : undefined}
                        />
                      </div>
                      {customPathError ? (
                        <p
                          id="custom-path-error"
                          className="flex items-center gap-1.5 text-xs text-red-600 dark:text-red-400"
                        >
                          <AlertTriangle className="h-3 w-3" />
                          Invalid path: {customPathError}
                        </p>
                      ) : (
                        <p className="text-xs text-muted-foreground">
                          {customSubPath.trim()
                            ? `Deploys to: ${defaultDeployPath}${validateAndSanitizeSubPath(customSubPath).value}`
                            : 'Enter a sub-directory to append to the default path (optional)'}
                        </p>
                      )}
                    </div>
                  )}
                </div>

                {/* Existing Deployments Info */}
                {artifact.usageStats.totalDeployments > 0 && (
                  <div className="rounded-lg border border-yellow-500/50 bg-yellow-500/10 p-3">
                    <div className="flex items-start gap-2">
                      <AlertTriangle className="mt-0.5 h-4 w-4 flex-shrink-0 text-yellow-600" />
                      <div className="min-w-0 flex-1">
                        <p className="text-sm font-medium text-yellow-900 dark:text-yellow-100">
                          Existing Deployments
                        </p>
                        <p className="mt-1 text-xs text-yellow-800 dark:text-yellow-200">
                          This artifact is already deployed to{' '}
                          {artifact.usageStats.totalDeployments} project(s). If the target project
                          already has this artifact, it will be overwritten.
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
            <Button
              onClick={handleDeployClick}
              disabled={
                isDeploying || deployMutation.isPending || (!canDeploy && !currentSelectionDeployed)
              }
            >
              {isDeploying
                ? 'Deploying...'
                : currentSelectionDeployed && overwriteEnabled
                  ? 'Overwrite'
                  : 'Deploy'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Create Project Dialog */}
      <CreateProjectDialog
        open={showCreateProject}
        onOpenChange={setShowCreateProject}
        onSuccess={handleProjectCreated}
      />

      {/* Overwrite Confirmation Dialog */}
      <AlertDialog open={showConfirmDialog} onOpenChange={setShowConfirmDialog}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Overwrite Existing Deployment?</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to overwrite the existing deployment of{' '}
              <span className="font-semibold">{artifact?.name}</span> in{' '}
              <span className="font-semibold">{selectedProject?.name}</span>?
              <br />
              <br />
              This will replace the currently deployed version with the version from your
              collection.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={executeDeploy}>Overwrite Deployment</AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
}
