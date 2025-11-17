"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Database, AlertCircle } from "lucide-react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { useToast } from "@/hooks/use-toast";
import {
  useMcpServers,
  useCreateMcpServer,
} from "@/hooks/useMcpServers";
import { MCPServerList } from "@/components/mcp/MCPServerList";
import { MCPServerForm } from "@/components/mcp/MCPServerForm";
import type { MCPServer, MCPFormData } from "@/types/mcp";

export default function McpPage() {
  const router = useRouter();
  const { toast } = useToast();

  // State
  const [showAddDialog, setShowAddDialog] = useState(false);

  // Data fetching
  const { data, isLoading, error, refetch } = useMcpServers();

  // Mutations
  const createMutation = useCreateMcpServer();

  const handleAddServer = () => {
    setShowAddDialog(true);
  };

  const handleServerClick = (server: MCPServer) => {
    // Navigate to server detail page
    router.push(`/mcp/${server.name}`);
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

      await createMutation.mutateAsync({
        name: formData.name,
        repo: formData.repo,
        version: formData.version || "latest",
        description: formData.description || undefined,
        env_vars,
      });

      toast({
        title: "Server Added",
        description: `MCP server '${formData.name}' has been added successfully.`,
      });

      setShowAddDialog(false);
    } catch (error) {
      toast({
        title: "Failed to Add Server",
        description: error instanceof Error ? error.message : "Unknown error",
        variant: "destructive",
      });
    }
  };

  const handleRefresh = () => {
    refetch();
  };

  const servers = data?.servers || [];

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div>
        <h1 className="text-3xl font-bold tracking-tight">MCP Servers</h1>
        <p className="text-muted-foreground">
          Manage Model Context Protocol server configurations
        </p>
      </div>

      {/* Error state */}
      {error && (
        <Card className="border-destructive">
          <CardHeader>
            <div className="flex items-center gap-2">
              <AlertCircle className="h-5 w-5 text-destructive" />
              <CardTitle className="text-destructive">
                Failed to Load Servers
              </CardTitle>
            </div>
            <CardDescription>
              {error instanceof Error ? error.message : "Unknown error occurred"}
            </CardDescription>
          </CardHeader>
          <CardContent>
            <button
              onClick={handleRefresh}
              className="text-sm text-primary hover:underline"
            >
              Try again
            </button>
          </CardContent>
        </Card>
      )}

      {/* Server list */}
      {!error && (
        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <Database className="h-5 w-5" />
              <CardTitle>MCP Server Management</CardTitle>
            </div>
            <CardDescription>
              Configure and deploy MCP servers for Claude Desktop integration
            </CardDescription>
          </CardHeader>
          <CardContent>
            <MCPServerList
              servers={servers}
              isLoading={isLoading}
              onServerClick={handleServerClick}
              onAddServer={handleAddServer}
              onRefresh={handleRefresh}
            />
          </CardContent>
        </Card>
      )}

      {/* Add/Edit server dialog */}
      <MCPServerForm
        open={showAddDialog}
        onClose={() => setShowAddDialog(false)}
        onSubmit={handleFormSubmit}
        isLoading={createMutation.isPending}
        error={
          createMutation.isError
            ? createMutation.error instanceof Error
              ? createMutation.error.message
              : "Unknown error"
            : undefined
        }
      />
    </div>
  );
}
