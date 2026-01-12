'use client';

import { use, useState } from 'react';
import { useRouter } from 'next/navigation';
import {
  ArrowLeft,
  Server,
  Package,
  Settings,
  Trash2,
  Edit,
  AlertCircle,
  CheckCircle2,
  FileCode,
} from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import {
  useToast,
  useMcpServer,
  useMcpDeploymentStatus,
  useUpdateMcpServer,
  useDeleteMcpServer,
  useDeployMcpServer,
  useUndeployMcpServer,
} from '@/hooks';
import { MCPServerForm } from '@/components/mcp/MCPServerForm';
import { MCPDeployButton } from '@/components/mcp/MCPDeployButton';
import type { MCPFormData, MCPServerStatus } from '@/types/mcp';

interface MCPServerDetailPageProps {
  params: Promise<{ name: string }>;
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

export default function MCPServerDetailPage(props: MCPServerDetailPageProps) {
  const params = use(props.params);
  const serverName = decodeURIComponent(params.name);
  const router = useRouter();
  const { toast } = useToast();

  // State
  const [showEditDialog, setShowEditDialog] = useState(false);
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);

  // Data fetching
  const { data: server, isLoading, error } = useMcpServer(serverName);
  const { data: deploymentStatus } = useMcpDeploymentStatus(serverName);

  // Mutations
  const updateMutation = useUpdateMcpServer(serverName);
  const deleteMutation = useDeleteMcpServer();
  const deployMutation = useDeployMcpServer(serverName);
  const undeployMutation = useUndeployMcpServer(serverName);

  const handleBack = () => {
    router.push('/mcp');
  };

  const handleEdit = () => {
    setShowEditDialog(true);
  };

  const handleDelete = () => {
    setShowDeleteDialog(true);
  };

  const handleConfirmDelete = async () => {
    try {
      await deleteMutation.mutateAsync(serverName);

      toast({
        title: 'Server Deleted',
        description: `MCP server '${serverName}' has been deleted.`,
      });

      router.push('/mcp');
    } catch (error) {
      toast({
        title: 'Failed to Delete Server',
        description: error instanceof Error ? error.message : 'Unknown error',
        variant: 'destructive',
      });
    }
  };

  const handleFormSubmit = async (formData: MCPFormData) => {
    try {
      // Convert env_vars array to object
      const env_vars = formData.env_vars.reduce(
        (acc, { key, value }) => {
          if (key && value) {
            acc[key] = value;
          }
          return acc;
        },
        {} as Record<string, string>
      );

      await updateMutation.mutateAsync({
        repo: formData.repo,
        version: formData.version || undefined,
        description: formData.description || undefined,
        env_vars,
      });

      toast({
        title: 'Server Updated',
        description: `MCP server '${serverName}' has been updated successfully.`,
      });

      setShowEditDialog(false);
    } catch (error) {
      toast({
        title: 'Failed to Update Server',
        description: error instanceof Error ? error.message : 'Unknown error',
        variant: 'destructive',
      });
    }
  };

  const handleDeploy = async (dryRun: boolean = false) => {
    return await deployMutation.mutateAsync({ dry_run: dryRun, backup: true });
  };

  const handleUndeploy = async () => {
    return await undeployMutation.mutateAsync();
  };

  if (error) {
    return (
      <div className="space-y-6">
        <div>
          <Button variant="ghost" onClick={handleBack}>
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back to Servers
          </Button>
        </div>

        <Card className="border-destructive">
          <CardHeader>
            <div className="flex items-center gap-2">
              <AlertCircle className="h-5 w-5 text-destructive" />
              <CardTitle className="text-destructive">Server Not Found</CardTitle>
            </div>
            <CardDescription>
              {error instanceof Error ? error.message : 'Unknown error occurred'}
            </CardDescription>
          </CardHeader>
        </Card>
      </div>
    );
  }

  if (isLoading || !server) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-10 w-48" />
        <Card>
          <CardHeader>
            <Skeleton className="h-6 w-64" />
            <Skeleton className="h-4 w-full" />
          </CardHeader>
          <CardContent className="space-y-4">
            <Skeleton className="h-20 w-full" />
            <Skeleton className="h-20 w-full" />
          </CardContent>
        </Card>
      </div>
    );
  }

  const statusInfo = statusConfig[server.status];
  const deployed = deploymentStatus?.deployed || false;

  return (
    <div className="space-y-6">
      {/* Back button and header */}
      <div className="flex items-center justify-between">
        <Button variant="ghost" onClick={handleBack}>
          <ArrowLeft className="mr-2 h-4 w-4" />
          Back to Servers
        </Button>

        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={handleEdit}>
            <Edit className="mr-2 h-4 w-4" />
            Edit
          </Button>
          <Button variant="outline" size="sm" onClick={handleDelete} disabled={deployed}>
            <Trash2 className="mr-2 h-4 w-4" />
            Delete
          </Button>
        </div>
      </div>

      {/* Server details */}
      <Card>
        <CardHeader>
          <div className="flex items-start justify-between">
            <div className="space-y-2">
              <div className="flex items-center gap-2">
                <Server className="h-6 w-6 text-primary" />
                <CardTitle className="text-2xl">{server.name}</CardTitle>
                <Badge variant={statusInfo.variant}>{statusInfo.label}</Badge>
              </div>
              {server.description && <CardDescription>{server.description}</CardDescription>}
            </div>
          </div>
        </CardHeader>

        <CardContent className="space-y-6">
          {/* Repository information */}
          <div className="space-y-3">
            <h3 className="flex items-center gap-2 text-sm font-semibold">
              <Package className="h-4 w-4" />
              Repository
            </h3>
            <div className="space-y-2 pl-6 text-sm">
              <div className="flex justify-between">
                <span className="text-muted-foreground">Source:</span>
                <span className="font-mono text-xs">{server.repo}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Version Spec:</span>
                <span className="font-mono text-xs">{server.version}</span>
              </div>
              {server.resolved_version && (
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Resolved Version:</span>
                  <span className="font-mono text-xs">{server.resolved_version}</span>
                </div>
              )}
              {server.resolved_sha && (
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Resolved SHA:</span>
                  <span className="font-mono text-xs">{server.resolved_sha.substring(0, 8)}</span>
                </div>
              )}
            </div>
          </div>

          {/* Environment variables */}
          <div className="space-y-3">
            <h3 className="flex items-center gap-2 text-sm font-semibold">
              <Settings className="h-4 w-4" />
              Environment Variables
            </h3>
            {Object.keys(server.env_vars).length === 0 ? (
              <p className="pl-6 text-sm text-muted-foreground">
                No environment variables configured
              </p>
            ) : (
              <div className="space-y-2 pl-6">
                {Object.entries(server.env_vars).map(([key, value]) => (
                  <div
                    key={key}
                    className="flex items-center justify-between rounded bg-muted/50 p-2 text-sm"
                  >
                    <span className="font-mono text-xs">{key}</span>
                    <span className="font-mono text-xs text-muted-foreground">
                      {value.substring(0, 20)}
                      {value.length > 20 ? '...' : ''}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Deployment section */}
          <div className="space-y-3 border-t pt-4">
            <h3 className="flex items-center gap-2 text-sm font-semibold">
              <FileCode className="h-4 w-4" />
              Deployment
            </h3>
            <div className="space-y-3 pl-6">
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">Status:</span>
                <div className="flex items-center gap-2">
                  {deployed ? (
                    <>
                      <CheckCircle2 className="h-4 w-4 text-green-600" />
                      <span className="text-sm">Deployed</span>
                    </>
                  ) : (
                    <>
                      <AlertCircle className="h-4 w-4 text-gray-500" />
                      <span className="text-sm text-muted-foreground">Not Deployed</span>
                    </>
                  )}
                </div>
              </div>

              {deploymentStatus?.settings_path && (
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">Settings Path:</span>
                  <span className="max-w-md truncate font-mono text-xs">
                    {deploymentStatus.settings_path}
                  </span>
                </div>
              )}

              {deploymentStatus?.command && (
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">Command:</span>
                  <span className="font-mono text-xs">
                    {deploymentStatus.command} {deploymentStatus.args?.join(' ')}
                  </span>
                </div>
              )}

              <div className="pt-2">
                <MCPDeployButton
                  server={server}
                  deployed={deployed}
                  onDeploy={handleDeploy}
                  onUndeploy={handleUndeploy}
                />
              </div>

              {deployed && (
                <p className="text-sm text-muted-foreground">
                  Note: You may need to restart Claude Desktop for changes to take effect.
                </p>
              )}
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Edit dialog */}
      <MCPServerForm
        open={showEditDialog}
        onClose={() => setShowEditDialog(false)}
        onSubmit={handleFormSubmit}
        server={server}
        isLoading={updateMutation.isPending}
        error={
          updateMutation.isError
            ? updateMutation.error instanceof Error
              ? updateMutation.error.message
              : 'Unknown error'
            : undefined
        }
      />

      {/* Delete confirmation dialog */}
      <Dialog open={showDeleteDialog} onOpenChange={setShowDeleteDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <AlertCircle className="h-5 w-5 text-destructive" />
              Delete MCP Server
            </DialogTitle>
            <DialogDescription>
              Are you sure you want to delete <strong>{server.name}</strong>? This action cannot be
              undone.
            </DialogDescription>
          </DialogHeader>

          {deployed && (
            <div className="rounded-lg border border-yellow-200 bg-yellow-50 p-4 dark:border-yellow-800 dark:bg-yellow-950/20">
              <p className="text-sm text-yellow-800 dark:text-yellow-200">
                Warning: This server is currently deployed. Undeploy it first before deleting.
              </p>
            </div>
          )}

          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setShowDeleteDialog(false)}
              disabled={deleteMutation.isPending}
            >
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={handleConfirmDelete}
              disabled={deleteMutation.isPending || deployed}
            >
              {deleteMutation.isPending ? 'Deleting...' : 'Delete Server'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
