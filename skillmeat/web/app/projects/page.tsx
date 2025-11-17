import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { GitBranch } from 'lucide-react';

export default function ProjectsPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Projects</h1>
        <p className="text-muted-foreground">Manage your deployed projects and configurations</p>
      </div>

      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <GitBranch className="h-5 w-5" />
            <CardTitle>Deployed Projects</CardTitle>
          </div>
          <CardDescription>View and manage artifacts deployed to projects</CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            This page will display all projects with deployed artifacts and their deployment
            status.
          </p>
          <p className="mt-2 text-sm text-muted-foreground">
            Connect to the FastAPI backend to see your projects.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
