'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { GitBranch, Plus } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { useProjectCache } from '@/hooks/useProjectCache';
import { ProjectsToolbar } from '@/components/ProjectsToolbar';
import { ProjectsList } from '@/components/ProjectsList';
import { CreateProjectDialog } from './components/create-project-dialog';
import type { ProjectSummary } from '@/types/project';

export default function ProjectsPage() {
  const router = useRouter();
  const { projects, isLoading, error, cacheInfo, refetch } = useProjectCache();
  const [selectedProject, setSelectedProject] = useState<ProjectSummary | null>(null);
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [isCreateOpen, setIsCreateOpen] = useState(false);

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

  const handleRefreshComplete = () => {
    refetch();
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
        <Button onClick={() => setIsCreateOpen(true)}>
          <Plus className="mr-2 h-4 w-4" />
          New Project
        </Button>
      </div>

      {/* Cache Toolbar */}
      <ProjectsToolbar
        lastFetched={cacheInfo?.lastFetched ?? null}
        isStale={cacheInfo?.isStale ?? false}
        cacheHit={cacheInfo?.cacheHit ?? false}
        onRefreshComplete={handleRefreshComplete}
      />

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

      {/* Projects List */}
      {!error && (
        <>
          {!isLoading && projects.length > 0 && (
            <div className="flex items-center justify-between">
              <h2 className="font-semibold">
                {projects.length} {projects.length === 1 ? 'Project' : 'Projects'}
              </h2>
            </div>
          )}

          <ProjectsList
            projects={projects}
            isLoading={isLoading}
            onProjectClick={handleProjectClick}
            onActionSuccess={handleActionSuccess}
          />
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
