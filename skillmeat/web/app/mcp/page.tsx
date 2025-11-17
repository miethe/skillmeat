import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Database } from 'lucide-react';

export default function McpPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">MCP Servers</h1>
        <p className="text-muted-foreground">
          Manage Model Context Protocol server configurations
        </p>
      </div>

      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <Database className="h-5 w-5" />
            <CardTitle>MCP Server Management</CardTitle>
          </div>
          <CardDescription>
            Configure and monitor MCP servers for Claude integration
          </CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            This page will allow you to configure MCP servers, manage environment variables, and
            monitor server health.
          </p>
          <p className="mt-2 text-sm text-muted-foreground">
            Connect to the FastAPI backend to manage MCP servers.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
