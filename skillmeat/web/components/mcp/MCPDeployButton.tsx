"use client";

import { useState } from "react";
import {
  Play,
  StopCircle,
  AlertTriangle,
  Loader2,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Progress } from "@/components/ui/progress";
import { useToast } from "@/hooks/use-toast";
import type { MCPServer, DeploymentResponse } from "@/types/mcp";

interface MCPDeployButtonProps {
  server: MCPServer;
  deployed: boolean;
  onDeploy: (dryRun?: boolean) => Promise<DeploymentResponse>;
  onUndeploy: () => Promise<DeploymentResponse>;
  disabled?: boolean;
}

export function MCPDeployButton({
  server,
  deployed,
  onDeploy,
  onUndeploy,
  disabled,
}: MCPDeployButtonProps) {
  const [showDialog, setShowDialog] = useState(false);
  const [isDeploying, setIsDeploying] = useState(false);
  const [deploymentStage, setDeploymentStage] = useState<string>("");
  const [deploymentProgress, setDeploymentProgress] = useState(0);
  const { toast } = useToast();

  const handleDeployClick = () => {
    if (deployed) {
      // Undeploy directly without confirmation
      handleUndeploy();
    } else {
      // Show security warning for deployment
      setShowDialog(true);
    }
  };

  const handleDeploy = async (dryRun: boolean = false) => {
    try {
      setIsDeploying(true);
      setDeploymentProgress(0);
      setDeploymentStage(dryRun ? "Validating configuration..." : "Resolving version...");

      // Simulate progress updates (in real implementation, use SSE or polling)
      const progressInterval = setInterval(() => {
        setDeploymentProgress((prev) => Math.min(prev + 10, 90));
      }, 300);

      const result = await onDeploy(dryRun);

      clearInterval(progressInterval);
      setDeploymentProgress(100);

      if (result.success) {
        setDeploymentStage("Deployment complete!");

        toast({
          title: dryRun ? "Validation Successful" : "Deployment Successful",
          description: result.message,
        });

        if (!dryRun) {
          setShowDialog(false);
        }
      } else {
        throw new Error(result.error_message || "Deployment failed");
      }
    } catch (error) {
      toast({
        title: "Deployment Failed",
        description: error instanceof Error ? error.message : "Unknown error",
        variant: "destructive",
      });
    } finally {
      setIsDeploying(false);
      setDeploymentStage("");
      setDeploymentProgress(0);
    }
  };

  const handleUndeploy = async () => {
    try {
      setIsDeploying(true);
      setDeploymentStage("Removing from settings...");

      const result = await onUndeploy();

      if (result.success) {
        toast({
          title: "Undeployment Successful",
          description: result.message,
        });
      } else {
        throw new Error(result.error_message || "Undeployment failed");
      }
    } catch (error) {
      toast({
        title: "Undeployment Failed",
        description: error instanceof Error ? error.message : "Unknown error",
        variant: "destructive",
      });
    } finally {
      setIsDeploying(false);
      setDeploymentStage("");
    }
  };

  const handleConfirmDeploy = () => {
    handleDeploy(false);
  };

  const handleDryRun = () => {
    handleDeploy(true);
  };

  return (
    <>
      <Button
        onClick={handleDeployClick}
        disabled={disabled || isDeploying}
        variant={deployed ? "outline" : "default"}
      >
        {isDeploying ? (
          <>
            <Loader2 className="h-4 w-4 mr-2 animate-spin" />
            {deploymentStage || "Processing..."}
          </>
        ) : deployed ? (
          <>
            <StopCircle className="h-4 w-4 mr-2" />
            Undeploy
          </>
        ) : (
          <>
            <Play className="h-4 w-4 mr-2" />
            Deploy
          </>
        )}
      </Button>

      {/* Deployment confirmation dialog */}
      <Dialog open={showDialog} onOpenChange={setShowDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <AlertTriangle className="h-5 w-5 text-yellow-600" />
              Deploy MCP Server
            </DialogTitle>
            <DialogDescription>
              You are about to deploy <strong>{server.name}</strong> to Claude
              Desktop.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4">
            {/* Security warning */}
            <div className="bg-yellow-50 dark:bg-yellow-950/20 border border-yellow-200 dark:border-yellow-800 rounded-lg p-4">
              <h4 className="font-semibold text-sm mb-2 flex items-center gap-2">
                <AlertTriangle className="h-4 w-4" />
                Security Notice
              </h4>
              <ul className="text-sm space-y-1 text-muted-foreground list-disc list-inside">
                <li>MCP servers have access to system resources</li>
                <li>Review environment variables before deploying</li>
                <li>A backup of settings.json will be created</li>
                <li>You may need to restart Claude Desktop</li>
              </ul>
            </div>

            {/* Deployment info */}
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-muted-foreground">Repository:</span>
                <span className="font-mono text-xs">{server.repo}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Version:</span>
                <span className="font-mono text-xs">{server.version}</span>
              </div>
              {Object.keys(server.env_vars).length > 0 && (
                <div className="flex justify-between">
                  <span className="text-muted-foreground">
                    Environment Variables:
                  </span>
                  <span className="text-xs">
                    {Object.keys(server.env_vars).length} configured
                  </span>
                </div>
              )}
            </div>

            {/* Progress indicator */}
            {isDeploying && (
              <div className="space-y-2">
                <Progress value={deploymentProgress} />
                <p className="text-sm text-center text-muted-foreground">
                  {deploymentStage}
                </p>
              </div>
            )}
          </div>

          <DialogFooter className="gap-2 sm:gap-0">
            <Button
              variant="outline"
              onClick={() => setShowDialog(false)}
              disabled={isDeploying}
            >
              Cancel
            </Button>
            <Button
              variant="outline"
              onClick={handleDryRun}
              disabled={isDeploying}
            >
              Dry Run
            </Button>
            <Button onClick={handleConfirmDeploy} disabled={isDeploying}>
              {isDeploying ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Deploying...
                </>
              ) : (
                <>
                  <Play className="h-4 w-4 mr-2" />
                  Deploy
                </>
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
