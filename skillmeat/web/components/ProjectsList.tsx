"use client";

import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import { GitBranch, Clock, Package } from "lucide-react";
import { ProjectActions } from "@/app/projects/components/project-actions";
import { useOutdatedArtifacts } from "@/hooks/useOutdatedArtifacts";

interface Project {
  id: string;
  name: string;
  path: string;
  deployment_count: number;
  last_deployment?: string;
}

interface ProjectsListProps {
  projects: Project[];
  isLoading: boolean;
  onProjectClick?: (project: Project) => void;
  onActionSuccess?: () => void;
}

function formatDate(dateString?: string): string {
  if (!dateString) return "Never";
  const date = new Date(dateString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

  if (diffDays === 0) return "Today";
  if (diffDays === 1) return "Yesterday";
  if (diffDays < 7) return `${diffDays} days ago`;
  if (diffDays < 30) return `${Math.floor(diffDays / 7)} weeks ago`;
  if (diffDays < 365) return `${Math.floor(diffDays / 30)} months ago`;
  return `${Math.floor(diffDays / 365)} years ago`;
}

function ProjectSkeleton() {
  return (
    <Card>
      <CardHeader>
        <Skeleton className="h-5 w-32" />
      </CardHeader>
      <CardContent className="space-y-2">
        <Skeleton className="h-4 w-full" />
        <Skeleton className="h-4 w-24" />
      </CardContent>
    </Card>
  );
}

export function ProjectsList({
  projects,
  isLoading,
  onProjectClick,
  onActionSuccess,
}: ProjectsListProps) {
  // Fetch outdated artifacts to show counts per project
  const { data: outdatedData } = useOutdatedArtifacts();

  // Count outdated artifacts per project
  const outdatedCountsByProject = (outdatedData?.items || []).reduce(
    (acc, artifact) => {
      acc[artifact.project_id] = (acc[artifact.project_id] || 0) + 1;
      return acc;
    },
    {} as Record<string, number>
  );

  if (isLoading) {
    return (
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {[1, 2, 3, 4, 5, 6].map((i) => (
          <ProjectSkeleton key={i} />
        ))}
      </div>
    );
  }

  if (projects.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-center">
        <GitBranch className="h-12 w-12 text-muted-foreground" />
        <h3 className="mt-4 text-lg font-semibold">No projects found</h3>
        <p className="mt-2 text-sm text-muted-foreground">
          Create a project or deploy artifacts to get started.
        </p>
      </div>
    );
  }

  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
      {projects.map((project) => {
        const outdatedCount = outdatedCountsByProject[project.id] || 0;

        return (
          <Card
            key={project.id}
            className="cursor-pointer transition-colors hover:border-primary"
            onClick={() => onProjectClick?.(project)}
          >
            <CardHeader>
              <div className="flex items-start justify-between">
                <div className="flex min-w-0 flex-1 items-center gap-2">
                  <GitBranch className="h-5 w-5 flex-shrink-0 text-muted-foreground" />
                  <CardTitle className="truncate text-lg">{project.name}</CardTitle>
                </div>
                <div className="flex flex-shrink-0 items-center gap-2">
                  <Badge variant="secondary">{project.deployment_count}</Badge>
                  {outdatedCount > 0 && (
                    <Badge variant="destructive" title={`${outdatedCount} outdated artifacts`}>
                      {outdatedCount}
                    </Badge>
                  )}
                  <ProjectActions project={project} onSuccess={onActionSuccess} />
                </div>
              </div>
              <CardDescription className="truncate font-mono text-xs">
                {project.path}
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <Package className="h-4 w-4" />
                  <span>
                    {project.deployment_count}{" "}
                    {project.deployment_count === 1 ? "artifact" : "artifacts"}
                  </span>
                </div>
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <Clock className="h-4 w-4" />
                  <span>Last deployed {formatDate(project.last_deployment)}</span>
                </div>
              </div>
            </CardContent>
          </Card>
        );
      })}
    </div>
  );
}
