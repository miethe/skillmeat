'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { GitBranch, FolderOpen, Clock, Package, Plus, RefreshCw } from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { useProjects } from '@/hooks/useProjects';
import { CreateProjectDialog } from './components/create-project-dialog';
import { ProjectActions } from './components/project-actions';
import type { ProjectSummary } from '@/types/project';

export default function ProjectsPage() {
  const router = useRouter();
  const { data: projects, isLoading, error, refetch, forceRefresh } = useProjects();
  const [selectedProject, setSelectedProject] = useState<ProjectSummary | null>(null);
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [isRefreshing, setIsRefreshing] = useState(false);

  const handleProjectClick = (project: ProjectSummary) => {
    setSelectedProject(project);
    setIsDialogOpen(true);
  };

  const handleExpandProject = () => {
    if (selectedProject) {
      router.push(`/projects/${selectedProject.id}`);
      setIsDialogOpen(false);
    }
  };

  const handleCreateSuccess = () => {
    refetch();
  };

  const handleActionSuccess = () => {
    refetch();
  };

  const handleRefresh = async () => {
    setIsRefreshing(true);
    try {
      await forceRefresh();
    } finally {
      setIsRefreshing(false);
    }
  };

  const formatDate = (dateString?: string) => {
    if (!dateString) return 'Never';
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

    if (diffDays === 0) return 'Today';
    if (diffDays === 1) return 'Yesterday';
    if (diffDays < 7) return `${diffDays} days ago`;
    if (diffDays < 30) return `${Math.floor(diffDays / 7)} weeks ago`;
    if (diffDays < 365) return `${Math.floor(diffDays / 30)} months ago`;
    return `${Math.floor(diffDays / 365)} years ago`;
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Projects</h1>
          <p className="text-muted-foreground">Manage your deployed projects and configurations</p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="icon"
            onClick={handleRefresh}
            disabled={isRefreshing || isLoading}
            title="Refresh projects (rescan filesystem)"
          >
            <RefreshCw className={`h-4 w-4 ${isRefreshing ? 'animate-spin' : ''}`} />
          </Button>
          <Button onClick={() => setIsCreateOpen(true)}>
            <Plus className="mr-2 h-4 w-4" />
            New Project
          </Button>
        </div>
      </div>

      {/* Loading State */}
      {isLoading && (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {[...Array(6)].map((_, i) => (
            <Card key={i} className="animate-pulse">
              <CardHeader>
                <div className="h-6 w-3/4 rounded bg-muted" />
                <div className="mt-2 h-4 w-1/2 rounded bg-muted" />
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  <div className="h-4 w-full rounded bg-muted" />
                  <div className="h-4 w-2/3 rounded bg-muted" />
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Error State */}
      {error && (
        <Card className="border-destructive">
          <CardContent className="pt-6">
            <div className="flex items-center gap-2 text-destructive">
              <p className="text-sm">
                Failed to load projects. Please check if the API is running and try again.
              </p>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Empty State */}
      {!isLoading && !error && projects?.length === 0 && (
        <Card>
          <CardContent className="pt-6">
            <div className="py-8 text-center">
              <FolderOpen className="mx-auto mb-4 h-12 w-12 text-muted-foreground" />
              <h3 className="mb-2 text-lg font-semibold">No projects found</h3>
              <p className="mb-4 text-sm text-muted-foreground">
                Create a new project to start deploying artifacts
              </p>
              <Button onClick={() => setIsCreateOpen(true)}>
                <Plus className="mr-2 h-4 w-4" />
                Create Your First Project
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Projects Grid */}
      {!isLoading && !error && projects && projects.length > 0 && (
        <>
          <div className="flex items-center justify-between">
            <h2 className="font-semibold">
              {projects.length} {projects.length === 1 ? 'Project' : 'Projects'}
            </h2>
          </div>

          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {projects.map((project) => (
              <Card
                key={project.id}
                className="cursor-pointer transition-colors hover:border-primary"
                onClick={() => handleProjectClick(project)}
              >
                <CardHeader>
                  <div className="flex items-start justify-between">
                    <div className="flex min-w-0 flex-1 items-center gap-2">
                      <GitBranch className="h-5 w-5 flex-shrink-0 text-muted-foreground" />
                      <CardTitle className="truncate text-lg">{project.name}</CardTitle>
                    </div>
                    <div className="flex flex-shrink-0 items-center gap-2">
                      <Badge variant="secondary">{project.deployment_count}</Badge>
                      <ProjectActions project={project} onSuccess={handleActionSuccess} />
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
                        {project.deployment_count}{' '}
                        {project.deployment_count === 1 ? 'artifact' : 'artifacts'}
                      </span>
                    </div>
                    <div className="flex items-center gap-2 text-sm text-muted-foreground">
                      <Clock className="h-4 w-4" />
                      <span>Last deployed {formatDate(project.last_deployment)}</span>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </>
      )}

      {/* Project Detail Dialog */}
      <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <GitBranch className="h-5 w-5" />
              {selectedProject?.name}
            </DialogTitle>
          </DialogHeader>
          {selectedProject && (
            <div className="space-y-4">
              <div className="text-sm">
                <div className="mb-4 font-mono text-xs text-muted-foreground">
                  {selectedProject.path}
                </div>
                <div className="mb-4 grid grid-cols-2 gap-4">
                  <div>
                    <p className="text-muted-foreground">Deployments</p>
                    <p className="text-2xl font-bold">{selectedProject.deployment_count}</p>
                  </div>
                  <div>
                    <p className="text-muted-foreground">Last Deployed</p>
                    <p className="text-lg font-semibold">
                      {formatDate(selectedProject.last_deployment)}
                    </p>
                  </div>
                </div>
              </div>
              <div className="flex gap-2">
                <Button onClick={handleExpandProject} className="flex-1">
                  View Full Details
                </Button>
                <Button variant="outline" onClick={() => setIsDialogOpen(false)} className="flex-1">
                  Close
                </Button>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* Create Project Dialog */}
      <CreateProjectDialog
        open={isCreateOpen}
        onOpenChange={setIsCreateOpen}
        onSuccess={handleCreateSuccess}
      />
    </div>
  );
}
