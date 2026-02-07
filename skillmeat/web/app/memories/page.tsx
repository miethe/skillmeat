'use client';

import Link from 'next/link';
import { useMemo, useState } from 'react';
import { ArrowRight, Brain, Search } from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { useGlobalMemoryItems, useProjects } from '@/hooks';
import type { MemoryStatus } from '@/sdk/models/MemoryStatus';
import type { MemoryType } from '@/sdk/models/MemoryType';

type ShareScope = 'all' | 'private' | 'project' | 'global_candidate';

export default function MemoriesPage() {
  const [projectId, setProjectId] = useState<string>('all');
  const [status, setStatus] = useState<'all' | MemoryStatus>('all');
  const [type, setType] = useState<'all' | MemoryType>('all');
  const [shareScope, setShareScope] = useState<ShareScope>('all');
  const [search, setSearch] = useState('');

  const { data: projects = [] } = useProjects();
  const selectedProject = projectId === 'all' ? undefined : projectId;

  const { data, isLoading, error } = useGlobalMemoryItems({
    projectId: selectedProject,
    status: status === 'all' ? undefined : status,
    type: type === 'all' ? undefined : type,
    shareScope: shareScope === 'all' ? undefined : shareScope,
    search: search.trim() || undefined,
    sortBy: 'created_at',
    sortOrder: 'desc',
    limit: 100,
  });

  const items = data?.items ?? [];
  const projectNameMap = useMemo(
    () => new Map(projects.map((project) => [project.id, project.name])),
    [projects]
  );

  return (
    <div className="space-y-6">
      <div className="space-y-2">
        <div className="flex items-center gap-2">
          <Brain className="h-7 w-7 text-muted-foreground" />
          <h1 className="text-3xl font-bold tracking-tight">Memories</h1>
        </div>
        <p className="text-sm text-muted-foreground">
          Browse memories across all projects, then jump directly into project memory inboxes.
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Filters</CardTitle>
          <CardDescription>Scope by project, lifecycle, type, and share scope.</CardDescription>
        </CardHeader>
        <CardContent className="grid gap-3 md:grid-cols-5">
          <Select value={projectId} onValueChange={setProjectId}>
            <SelectTrigger aria-label="Project filter">
              <SelectValue placeholder="All Projects" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Projects</SelectItem>
              {projects.map((project) => (
                <SelectItem key={project.id} value={project.id}>
                  {project.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          <Select value={status} onValueChange={(value) => setStatus(value as typeof status)}>
            <SelectTrigger aria-label="Status filter">
              <SelectValue placeholder="All Statuses" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Statuses</SelectItem>
              <SelectItem value="candidate">Candidate</SelectItem>
              <SelectItem value="active">Active</SelectItem>
              <SelectItem value="stable">Stable</SelectItem>
              <SelectItem value="deprecated">Deprecated</SelectItem>
            </SelectContent>
          </Select>

          <Select value={type} onValueChange={(value) => setType(value as typeof type)}>
            <SelectTrigger aria-label="Type filter">
              <SelectValue placeholder="All Types" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Types</SelectItem>
              <SelectItem value="decision">Decision</SelectItem>
              <SelectItem value="constraint">Constraint</SelectItem>
              <SelectItem value="gotcha">Gotcha</SelectItem>
              <SelectItem value="learning">Learning</SelectItem>
              <SelectItem value="style_rule">Style Rule</SelectItem>
            </SelectContent>
          </Select>

          <Select value={shareScope} onValueChange={(value) => setShareScope(value as ShareScope)}>
            <SelectTrigger aria-label="Share scope filter">
              <SelectValue placeholder="All Share Scopes" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Share Scopes</SelectItem>
              <SelectItem value="private">Private</SelectItem>
              <SelectItem value="project">Project</SelectItem>
              <SelectItem value="global_candidate">Global Candidate</SelectItem>
            </SelectContent>
          </Select>

          <div className="relative">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              className="pl-9"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Search memories..."
              aria-label="Search memories"
            />
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Results ({items.length})</CardTitle>
          <CardDescription>
            Select a memory to continue triage inside its project-scoped memory page.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          {isLoading && <p className="text-sm text-muted-foreground">Loading memories...</p>}

          {!isLoading && error && (
            <p className="text-sm text-destructive">Failed to load memories. Try refreshing.</p>
          )}

          {!isLoading && !error && items.length === 0 && (
            <p className="text-sm text-muted-foreground">No memories matched your current filters.</p>
          )}

          {!isLoading &&
            !error &&
            items.map((item) => {
              const resolvedProjectName = item.project_name || projectNameMap.get(item.project_id);
              return (
                <div
                  key={item.id}
                  className="flex flex-col gap-3 rounded-md border p-3 md:flex-row md:items-center md:justify-between"
                >
                  <div className="space-y-2">
                    <div className="flex flex-wrap items-center gap-2">
                      <Badge variant="outline">{item.type}</Badge>
                      <Badge variant="secondary">{item.status}</Badge>
                      <Badge variant="outline">scope: {item.share_scope}</Badge>
                      {resolvedProjectName && <Badge>{resolvedProjectName}</Badge>}
                    </div>
                    <p className="text-sm">{item.content}</p>
                  </div>
                  <Button asChild variant="outline">
                    <Link href={`/projects/${item.project_id}/memory`} aria-label={`Open memory for ${item.id}`}>
                      Open Project Memory
                      <ArrowRight className="ml-2 h-4 w-4" />
                    </Link>
                  </Button>
                </div>
              );
            })}
        </CardContent>
      </Card>
    </div>
  );
}
