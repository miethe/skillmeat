"use client";

import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import type { MCPServer, MCPFormData, EnvVarEntry } from "@/types/mcp";
import { MCPEnvEditor } from "./MCPEnvEditor";
import { AlertCircle } from "lucide-react";

interface MCPServerFormProps {
  open: boolean;
  onClose: () => void;
  onSubmit: (data: MCPFormData) => void;
  server?: MCPServer;
  isLoading?: boolean;
  error?: string;
}

export function MCPServerForm({
  open,
  onClose,
  onSubmit,
  server,
  isLoading,
  error,
}: MCPServerFormProps) {
  const [formData, setFormData] = useState<MCPFormData>({
    name: "",
    repo: "",
    version: "latest",
    description: "",
    env_vars: [],
  });

  const [validationErrors, setValidationErrors] = useState<
    Record<string, string>
  >({});

  // Initialize form with server data if editing
  useEffect(() => {
    if (server) {
      setFormData({
        name: server.name,
        repo: server.repo,
        version: server.version,
        description: server.description || "",
        env_vars: Object.entries(server.env_vars).map(([key, value]) => ({
          key,
          value,
        })),
      });
    } else {
      setFormData({
        name: "",
        repo: "",
        version: "latest",
        description: "",
        env_vars: [],
      });
    }
    setValidationErrors({});
  }, [server, open]);

  const validateForm = (): boolean => {
    const errors: Record<string, string> = {};

    // Name validation
    if (!formData.name) {
      errors.name = "Server name is required";
    } else if (!/^[a-zA-Z0-9_-]+$/.test(formData.name)) {
      errors.name =
        "Name must contain only alphanumeric characters, dashes, and underscores";
    }

    // Repo validation
    if (!formData.repo) {
      errors.repo = "Repository is required";
    } else if (
      !formData.repo.includes("/") &&
      !formData.repo.startsWith("http")
    ) {
      errors.repo = "Repository must be in format 'user/repo' or a full URL";
    }

    // Version validation
    if (!formData.version) {
      errors.version = "Version is required";
    }

    // Env var validation
    formData.env_vars.forEach((envVar, index) => {
      if (!envVar.key) {
        errors[`env_${index}_key`] = "Environment variable name is required";
      }
      if (!envVar.value) {
        errors[`env_${index}_value`] = "Environment variable value is required";
      }
    });

    setValidationErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();

    if (!validateForm()) {
      return;
    }

    onSubmit(formData);
  };

  const handleEnvVarsChange = (envVars: EnvVarEntry[]) => {
    setFormData((prev) => ({ ...prev, env_vars: envVars }));
  };

  const isEditMode = !!server;

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>
            {isEditMode ? "Edit MCP Server" : "Add MCP Server"}
          </DialogTitle>
          <DialogDescription>
            {isEditMode
              ? "Update the MCP server configuration"
              : "Configure a new MCP server to add to your collection"}
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Error message */}
          {error && (
            <div className="bg-destructive/10 text-destructive border border-destructive/20 rounded-md p-3 flex items-start gap-2">
              <AlertCircle className="h-4 w-4 mt-0.5 flex-shrink-0" />
              <span className="text-sm">{error}</span>
            </div>
          )}

          {/* Server Name */}
          <div className="space-y-2">
            <Label htmlFor="name">
              Server Name <span className="text-destructive">*</span>
            </Label>
            <Input
              id="name"
              value={formData.name}
              onChange={(e) =>
                setFormData((prev) => ({ ...prev, name: e.target.value }))
              }
              placeholder="filesystem"
              disabled={isEditMode || isLoading}
              aria-invalid={!!validationErrors.name}
              aria-describedby={validationErrors.name ? "name-error" : undefined}
            />
            {validationErrors.name && (
              <p id="name-error" className="text-sm text-destructive">
                {validationErrors.name}
              </p>
            )}
            <p className="text-sm text-muted-foreground">
              Unique identifier (alphanumeric, dash, underscore only)
            </p>
          </div>

          {/* Repository */}
          <div className="space-y-2">
            <Label htmlFor="repo">
              Repository <span className="text-destructive">*</span>
            </Label>
            <Input
              id="repo"
              value={formData.repo}
              onChange={(e) =>
                setFormData((prev) => ({ ...prev, repo: e.target.value }))
              }
              placeholder="anthropics/mcp-filesystem"
              disabled={isLoading}
              aria-invalid={!!validationErrors.repo}
              aria-describedby={validationErrors.repo ? "repo-error" : undefined}
            />
            {validationErrors.repo && (
              <p id="repo-error" className="text-sm text-destructive">
                {validationErrors.repo}
              </p>
            )}
            <p className="text-sm text-muted-foreground">
              GitHub repository (user/repo or full URL)
            </p>
          </div>

          {/* Version */}
          <div className="space-y-2">
            <Label htmlFor="version">
              Version <span className="text-destructive">*</span>
            </Label>
            <Input
              id="version"
              value={formData.version}
              onChange={(e) =>
                setFormData((prev) => ({ ...prev, version: e.target.value }))
              }
              placeholder="latest"
              disabled={isLoading}
              aria-invalid={!!validationErrors.version}
              aria-describedby={
                validationErrors.version ? "version-error" : undefined
              }
            />
            {validationErrors.version && (
              <p id="version-error" className="text-sm text-destructive">
                {validationErrors.version}
              </p>
            )}
            <p className="text-sm text-muted-foreground">
              Version tag, SHA, or "latest"
            </p>
          </div>

          {/* Description */}
          <div className="space-y-2">
            <Label htmlFor="description">Description</Label>
            <Textarea
              id="description"
              value={formData.description}
              onChange={(e) =>
                setFormData((prev) => ({
                  ...prev,
                  description: e.target.value,
                }))
              }
              placeholder="Brief description of this MCP server"
              rows={3}
              disabled={isLoading}
            />
          </div>

          {/* Environment Variables */}
          <div className="space-y-2">
            <Label>Environment Variables</Label>
            <MCPEnvEditor
              envVars={formData.env_vars}
              onChange={handleEnvVarsChange}
              disabled={isLoading}
            />
          </div>

          <DialogFooter className="gap-2 sm:gap-0">
            <Button
              type="button"
              variant="outline"
              onClick={onClose}
              disabled={isLoading}
            >
              Cancel
            </Button>
            <Button type="submit" disabled={isLoading}>
              {isLoading
                ? isEditMode
                  ? "Updating..."
                  : "Creating..."
                : isEditMode
                  ? "Update Server"
                  : "Add Server"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
