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
  Calendar
} from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { ScrollArea } from '@/components/ui/scroll-area';
import { apiRequest } from '@/lib/api';
import type { EntityType, EntityStatus } from '@/types/entity';
import type { ArtifactResponse, DeploymentStatistics } from '@/sdk';

interface ProjectSelectorForDiffProps {
  entityId: string;
  entityName: string;
  entityType: EntityType;
  collection: string;
  onProjectSelected: (projectPath: string) => void;
}

interface ProjectDeploymentItem {
  projectName: string;
  projectPath: string;
  status: EntityStatus;
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
 * Get status badge variant based on entity status
 */
function getStatusVariant(status: EntityStatus): 'default' | 'secondary' | 'destructive' | 'outline' {
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
function getStatusIcon(status: EntityStatus) {
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
function getStatusLabel(status: EntityStatus): string {
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
      const status: EntityStatus = project.is_modified ? 'modified' : 'synced';

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
    onProjectSelected(projectPath);
  };

  // Loading state
  if (isLoading) {
    return (
      <div className="p-8 flex flex-col items-center justify-center gap-3">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
        <div className="text-center">
          <p className="text-sm font-medium text-foreground">Loading projects...</p>
          <p className="text-xs text-muted-foreground mt-1">
            Finding deployments of {entityName}
          </p>
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
          <p className="font-medium mb-1">Failed to load project deployments</p>
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
      <div className="border rounded-lg p-8 bg-muted/20">
        <div className="flex flex-col items-center justify-center gap-3 text-center">
          <Folder className="h-12 w-12 text-muted-foreground opacity-50" />
          <div>
            <h3 className="text-lg font-semibold mb-2">No deployments found</h3>
            <p className="text-sm text-muted-foreground max-w-md">
              This artifact has not been deployed to any projects yet. Deploy it to a project
              to view diffs and sync status.
            </p>
          </div>
        </div>
      </div>
    );
  }

  // Main content - project list
  return (
    <div className="space-y-4">
      <div>
        <h3 className="text-sm font-medium mb-1">Select Project for Comparison</h3>
        <p className="text-xs text-muted-foreground">
          Choose a project to compare the collection version of {entityName} against
        </p>
      </div>

      <ScrollArea className="max-h-[400px]">
        <div className="space-y-3">
          {deployments.map((deployment) => (
            <Card
              key={deployment.projectPath}
              className={`cursor-pointer transition-all hover:shadow-md ${
                selectedProject === deployment.projectPath
                  ? 'ring-2 ring-primary bg-primary/5'
                  : 'hover:bg-muted/50'
              }`}
              onClick={() => handleProjectClick(deployment.projectPath)}
            >
              <CardHeader className="pb-3">
                <div className="flex items-start justify-between gap-3">
                  <div className="flex items-start gap-3 flex-1 min-w-0">
                    <Folder className="h-5 w-5 text-primary flex-shrink-0 mt-0.5" />
                    <div className="flex-1 min-w-0">
                      <CardTitle className="text-base font-medium break-words">
                        {deployment.projectName}
                      </CardTitle>
                      <CardDescription className="text-xs mt-1 break-all">
                        {deployment.projectPath}
                      </CardDescription>
                    </div>
                  </div>
                  <ChevronRight
                    className={`h-5 w-5 text-muted-foreground flex-shrink-0 transition-transform ${
                      selectedProject === deployment.projectPath ? 'rotate-90' : ''
                    }`}
                  />
                </div>
              </CardHeader>

              <CardContent className="pt-0">
                <div className="flex items-center justify-between gap-3 flex-wrap">
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
      <div className="pt-2 border-t">
        <div className="flex items-center justify-between text-xs text-muted-foreground">
          <span>
            {deployments.length} {deployments.length === 1 ? 'project' : 'projects'} found
          </span>
          {artifactData?.deployment_stats && (
            <span>
              {artifactData.deployment_stats.modified_deployments} modified
            </span>
          )}
        </div>
      </div>
    </div>
  );
}
