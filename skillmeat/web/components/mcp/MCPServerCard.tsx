'use client';

import { Server, ExternalLink, Package, Calendar } from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import type { MCPServer, MCPServerStatus } from '@/types/mcp';

interface MCPServerCardProps {
  server: MCPServer;
  onClick: () => void;
}

const statusConfig: Record<
  MCPServerStatus,
  { label: string; variant: 'default' | 'secondary' | 'destructive' | 'outline' }
> = {
  installed: { label: 'Installed', variant: 'default' },
  not_installed: { label: 'Not Installed', variant: 'secondary' },
  updating: { label: 'Updating', variant: 'outline' },
  error: { label: 'Error', variant: 'destructive' },
};

function formatDate(dateString?: string): string {
  if (!dateString) return 'Never';

  try {
    const date = new Date(dateString);
    return new Intl.RelativeTimeFormat('en', { numeric: 'auto' }).format(
      Math.round((date.getTime() - Date.now()) / (1000 * 60 * 60 * 24)),
      'day'
    );
  } catch {
    return 'Invalid date';
  }
}

export function MCPServerCard({ server, onClick }: MCPServerCardProps) {
  const statusInfo = statusConfig[server.status];
  const envVarCount = Object.keys(server.env_vars).length;

  return (
    <Card className="cursor-pointer transition-colors hover:border-primary/50" onClick={onClick}>
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between gap-2">
          <div className="flex items-center gap-2">
            <Server className="h-5 w-5 text-primary" />
            <CardTitle className="text-lg">{server.name}</CardTitle>
          </div>
          <Badge variant={statusInfo.variant}>{statusInfo.label}</Badge>
        </div>
        {server.description && (
          <CardDescription className="line-clamp-2">{server.description}</CardDescription>
        )}
      </CardHeader>

      <CardContent className="space-y-3">
        {/* Repository */}
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <Package className="h-4 w-4 flex-shrink-0" />
          <span className="truncate">{server.repo}</span>
          <ExternalLink className="h-3 w-3 flex-shrink-0" />
        </div>

        {/* Version info */}
        <div className="flex items-center justify-between text-sm">
          <span className="text-muted-foreground">Version:</span>
          <span className="font-mono text-xs">{server.resolved_version || server.version}</span>
        </div>

        {/* Environment variables count */}
        {envVarCount > 0 && (
          <div className="flex items-center justify-between text-sm">
            <span className="text-muted-foreground">Environment:</span>
            <span className="text-xs">
              {envVarCount} variable{envVarCount !== 1 ? 's' : ''}
            </span>
          </div>
        )}

        {/* Last updated */}
        {server.last_updated && (
          <div className="flex items-center gap-2 border-t pt-2 text-sm text-muted-foreground">
            <Calendar className="h-3 w-3" />
            <span className="text-xs">Updated {formatDate(server.last_updated)}</span>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
