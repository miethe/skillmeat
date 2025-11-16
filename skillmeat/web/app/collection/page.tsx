import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Package } from 'lucide-react';

export default function CollectionPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Collection</h1>
        <p className="text-muted-foreground">Browse and manage your artifact collection</p>
      </div>

      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <Package className="h-5 w-5" />
            <CardTitle>Artifacts</CardTitle>
          </div>
          <CardDescription>View all artifacts in your collection</CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            This page will display your collection of Skills, Commands, Agents, MCP servers, and
            Hooks.
          </p>
          <p className="mt-2 text-sm text-muted-foreground">
            Connect to the FastAPI backend to see your collection.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
