'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  Folder,
  CheckCircle2,
  AlertCircle,
  Clock,
  Loader2,
  ChevronRight,
  ChevronDown,
  ChevronUp,
  Calendar,
} from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { ScrollArea } from '@/components/ui/scroll-area';
import { apiRequest } from '@/lib/api';
import type { ArtifactType, SyncStatus } from '@/types/artifact';
import type { ArtifactResponse, DeploymentStatistics } from '@/sdk';

interface ProjectSelectorForDiffProps {
  entityId: string;
  entityName: string;
  entityType: ArtifactType;
  collection: string;
  onProjectSelected: (projectPath: string) => void;
}

interface ProjectDeploymentItem {
  projectName: string;
  projectPath: string;
  status: SyncStatus;
  deployedAt: string;
  isModified: boolean;
}

/**
 * Format relative time for display
 */
function formatRelativeTime(date: Date): string {
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffSecs = Math.floor(diffMs / 1000);
  const diffMins = Math.floor(diffSecs / 60);
  const diffHours = Math.floor(diffMins / 60);
  const diffDays = Math.floor(diffHours / 24);

  if (diffSecs < 60) {
    return 'just now';
  } else if (diffMins < 60) {
    return `${diffMins} ${diffMins === 1 ? 'minute' : 'minutes'} ago`;
  } else if (diffHours < 24) {
    return `${diffHours} ${diffHours === 1 ? 'hour' : 'hours'} ago`;
  } else if (diffDays < 30) {
    return `${diffDays} ${diffDays === 1 ? 'day' : 'days'} ago`;
  } else {
    return date.toLocaleDateString();
  }
}

/**
 * Get status badge variant based on sync status
 */
function getStatusVariant(
  status: SyncStatus
): 'default' | 'secondary' | 'destructive' | 'outline' {
  switch (status) {
    case 'synced':
      return 'default';
    case 'modified':
      return 'secondary';
    case 'outdated':
      return 'outline';
    case 'conflict':
      return 'destructive';
    default:
      return 'outline';
  }
}

/**
 * Get status icon component
 */
function getStatusIcon(status: SyncStatus) {
  switch (status) {
    case 'synced':
      return <CheckCircle2 className="h-4 w-4 text-green-500" />;
    case 'modified':
      return <AlertCircle className="h-4 w-4 text-yellow-500" />;
    case 'outdated':
      return <Clock className="h-4 w-4 text-blue-500" />;
    case 'conflict':
      return <AlertCircle className="h-4 w-4 text-red-500" />;
    default:
      return null;
  }
}

/**
 * Get status label text
 */
function getStatusLabel(status: SyncStatus): string {
  switch (status) {
    case 'synced':
      return 'Synced';
    case 'modified':
      return 'Modified';
    case 'outdated':
      return 'Outdated';
    case 'conflict':
      return 'Conflict';
    default:
      return 'Unknown';
  }
}

/**
 * ProjectSelectorForDiff - Select a project for diff comparison
 *
 * When viewing a collection-mode entity (no projectPath), this component
 * allows users to select which project to compare the collection version against.
 *
 * Features:
 * - Shows projects where this artifact is deployed
 * - Displays deployment status for each project (synced/modified/outdated/conflict)
 * - Shows last deployment date
 * - Includes empty state when no deployments exist
 * - Loading and error states
 *
 * @example
 * ```tsx
 * <ProjectSelectorForDiff
 *   entityId="skill:canvas-design"
 *   entityName="canvas-design"
 *   entityType="skill"
 *   collection="default"
 *   onProjectSelected={(projectPath) => console.log('Selected:', projectPath)}
 * />
 * ```
 */
export function ProjectSelectorForDiff({
  entityId,
  entityName,
  entityType,
  collection,
  onProjectSelected,
}: ProjectSelectorForDiffProps) {
  const [selectedProject, setSelectedProject] = useState<string | null>(null);
  const [isCollapsed, setIsCollapsed] = useState(false);

  // Fetch artifact details with deployment statistics
  const {
    data: artifactData,
    isLoading,
    error,
  } = useQuery<ArtifactResponse>({
    queryKey: ['artifact-deployments', entityId, collection],
    queryFn: async () => {
      return await apiRequest<ArtifactResponse>(
        `/artifacts/${entityId}?collection=${encodeURIComponent(collection)}&include_deployments=true`
      );
    },
    staleTime: 5 * 60 * 1000, // Cache for 5 minutes
    gcTime: 30 * 60 * 1000, // Keep in cache for 30 minutes
  });

  // Transform deployment statistics into project deployment items
  const deployments: ProjectDeploymentItem[] =
    artifactData?.deployment_stats?.projects?.map((project) => {
      // Derive status from is_modified flag
      // In a real implementation, you might want to fetch full sync status
      const status: SyncStatus = project.is_modified ? 'modified' : 'synced';

      return {
        projectName: project.project_name,
        projectPath: project.project_path,
        status,
        deployedAt: project.deployed_at,
        isModified: project.is_modified,
      };
    }) ?? [];

  const handleProjectClick = (projectPath: string) => {
    setSelectedProject(projectPath);
    setIsCollapsed(true);
    onProjectSelected(projectPath);
  };

  // Loading state
  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center gap-3 p-8">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
        <div className="text-center">
          <p className="text-sm font-medium text-foreground">Loading projects...</p>
          <p className="mt-1 text-xs text-muted-foreground">Finding deployments of {entityName}</p>
        </div>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <Alert variant="destructive">
        <AlertCircle className="h-4 w-4" />
        <AlertDescription>
          <p className="mb-1 font-medium">Failed to load project deployments</p>
          <p className="text-xs">
            {error instanceof Error ? error.message : 'An unknown error occurred'}
          </p>
        </AlertDescription>
      </Alert>
    );
  }

  // Empty state - no deployments
  if (deployments.length === 0) {
    return (
      <div className="rounded-lg border bg-muted/20 p-8">
        <div className="flex flex-col items-center justify-center gap-3 text-center">
          <Folder className="h-12 w-12 text-muted-foreground opacity-50" />
          <div>
            <h3 className="mb-2 text-lg font-semibold">No deployments found</h3>
            <p className="max-w-md text-sm text-muted-foreground">
              This artifact has not been deployed to any projects yet. Deploy it to a project to
              view diffs and sync status.
            </p>
          </div>
        </div>
      </div>
    );
  }

  // Collapsed view - compact summary bar
  if (isCollapsed && selectedProject) {
    const selected = deployments.find((d) => d.projectPath === selectedProject);
    if (selected) {
      return (
        <div className="flex items-center justify-between rounded-lg border bg-muted/30 px-4 py-2.5">
          <div className="flex items-center gap-3">
            <Folder className="h-4 w-4 text-primary" />
            <div className="flex items-center gap-2">
              <span className="text-sm font-medium">{selected.projectName}</span>
              <Badge variant={getStatusVariant(selected.status)} className="text-xs">
                {getStatusLabel(selected.status)}
              </Badge>
            </div>
          </div>
          <Button
            variant="ghost"
            size="sm"
            onClick={(e) => {
              e.stopPropagation();
              setIsCollapsed(false);
            }}
            className="h-7 gap-1 text-xs text-muted-foreground"
          >
            Change
            <ChevronDown className="h-3 w-3" />
          </Button>
        </div>
      );
    }
  }

  // Main content - project list
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="mb-1 text-sm font-medium">Select Project for Comparison</h3>
          <p className="text-xs text-muted-foreground">
            Choose a project to compare the collection version of {entityName} against
          </p>
        </div>
        {selectedProject && (
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setIsCollapsed(true)}
            className="h-7 gap-1 text-xs text-muted-foreground"
          >
            Collapse
            <ChevronUp className="h-3 w-3" />
          </Button>
        )}
      </div>

      <ScrollArea className="max-h-[400px]">
        <div className="space-y-3">
          {deployments.map((deployment) => (
            <Card
              key={deployment.projectPath}
              className={`cursor-pointer transition-all hover:shadow-md ${
                selectedProject === deployment.projectPath
                  ? 'bg-primary/5 ring-2 ring-primary'
                  : 'hover:bg-muted/50'
              }`}
              onClick={() => handleProjectClick(deployment.projectPath)}
            >
              <CardHeader className="pb-3">
                <div className="flex items-start justify-between gap-3">
                  <div className="flex min-w-0 flex-1 items-start gap-3">
                    <Folder className="mt-0.5 h-5 w-5 flex-shrink-0 text-primary" />
                    <div className="min-w-0 flex-1">
                      <CardTitle className="break-words text-base font-medium">
                        {deployment.projectName}
                      </CardTitle>
                      <CardDescription className="mt-1 break-all text-xs">
                        {deployment.projectPath}
                      </CardDescription>
                    </div>
                  </div>
                  <ChevronRight
                    className={`h-5 w-5 flex-shrink-0 text-muted-foreground transition-transform ${
                      selectedProject === deployment.projectPath ? 'rotate-90' : ''
                    }`}
                  />
                </div>
              </CardHeader>

              <CardContent className="pt-0">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  {/* Status badge */}
                  <div className="flex items-center gap-2">
                    {getStatusIcon(deployment.status)}
                    <Badge variant={getStatusVariant(deployment.status)} className="text-xs">
                      {getStatusLabel(deployment.status)}
                    </Badge>
                  </div>

                  {/* Deployment date */}
                  <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
                    <Calendar className="h-3 w-3" />
                    <span title={new Date(deployment.deployedAt).toLocaleString()}>
                      {formatRelativeTime(new Date(deployment.deployedAt))}
                    </span>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      </ScrollArea>

      {/* Summary info */}
      <div className="border-t pt-2">
        <div className="flex items-center justify-between text-xs text-muted-foreground">
          <span>
            {deployments.length} {deployments.length === 1 ? 'project' : 'projects'} found
          </span>
          {artifactData?.deployment_stats && (
            <span>{artifactData.deployment_stats.modified_deployments} modified</span>
          )}
        </div>
      </div>
    </div>
  );
}
