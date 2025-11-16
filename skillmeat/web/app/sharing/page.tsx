import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Users } from 'lucide-react';

export default function SharingPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Team Sharing</h1>
        <p className="text-muted-foreground">Share and collaborate on artifact bundles</p>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <Users className="h-5 w-5" />
              <CardTitle>Export Bundles</CardTitle>
            </div>
            <CardDescription>Create shareable bundles from your collection</CardDescription>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground">
              Export selected artifacts as .skillmeat-pack bundles for sharing with team members.
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <Users className="h-5 w-5" />
              <CardTitle>Import Bundles</CardTitle>
            </div>
            <CardDescription>Import shared bundles into your collection</CardDescription>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground">
              Import bundles shared by team members with merge, fork, or skip options.
            </p>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
