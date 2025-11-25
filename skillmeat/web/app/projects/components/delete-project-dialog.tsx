"use client";

import { useState, useEffect } from "react";
import { Trash2, AlertTriangle } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Checkbox } from "@/components/ui/checkbox";
import { useDeleteProject } from "@/hooks/useProjects";
import { useToast } from "@/hooks/use-toast";
import type { ProjectSummary } from "@/types/project";

export interface DeleteProjectDialogProps {
  project: ProjectSummary;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess?: () => void;
}

export function DeleteProjectDialog({
  project,
  open,
  onOpenChange,
  onSuccess,
}: DeleteProjectDialogProps) {
  const [step, setStep] = useState<1 | 2>(1);
  const [confirmName, setConfirmName] = useState("");
  const [deleteFiles, setDeleteFiles] = useState(false);

  const { toast } = useToast();
  const deleteMutation = useDeleteProject();

  // Reset state when dialog opens/closes
  useEffect(() => {
    if (open) {
      setStep(1);
      setConfirmName("");
      setDeleteFiles(false);
    }
  }, [open]);

  const handleNext = () => {
    setStep(2);
  };

  const handleBack = () => {
    setStep(1);
    setConfirmName("");
  };

  const handleDelete = async () => {
    if (confirmName !== project.name) {
      toast({
        title: "Confirmation failed",
        description: "Project name doesn't match",
        variant: "destructive",
      });
      return;
    }

    try {
      await deleteMutation.mutateAsync({
        id: project.id,
        deleteFiles,
      });

      toast({
        title: "Project deleted",
        description: `Successfully deleted project "${project.name}"`,
      });

      // Close dialog and call success callback
      onOpenChange(false);
      onSuccess?.();
    } catch (error) {
      console.error("Failed to delete project:", error);
      toast({
        title: "Failed to delete project",
        description:
          error instanceof Error
            ? error.message
            : "An unexpected error occurred",
        variant: "destructive",
      });
    }
  };

  const handleClose = () => {
    if (!deleteMutation.isPending) {
      setStep(1);
      setConfirmName("");
      setDeleteFiles(false);
      onOpenChange(false);
    }
  };

  const isConfirmValid = confirmName === project.name;

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-destructive/10">
              <Trash2 className="h-5 w-5 text-destructive" />
            </div>
            <div>
              <DialogTitle>Delete Project</DialogTitle>
              <DialogDescription>
                {step === 1
                  ? "This action cannot be undone"
                  : "Confirm project deletion"}
              </DialogDescription>
            </div>
          </div>
        </DialogHeader>

        <div className="space-y-4 py-4">
          {step === 1 ? (
            <>
              {/* Step 1: Warning */}
              <div className="rounded-lg border border-destructive/50 bg-destructive/10 p-4">
                <div className="flex items-start gap-3">
                  <AlertTriangle className="h-5 w-5 text-destructive flex-shrink-0 mt-0.5" />
                  <div className="flex-1 min-w-0 space-y-2">
                    <p className="text-sm font-semibold text-destructive">
                      Warning: This action is permanent
                    </p>
                    <p className="text-sm text-muted-foreground">
                      Deleting this project will remove it from the SkillMeat
                      tracking system. The project will no longer appear in your
                      projects list.
                    </p>
                  </div>
                </div>
              </div>

              {/* Project Info */}
              <div className="space-y-3 rounded-lg border p-4 bg-muted/50">
                <div>
                  <p className="text-sm font-medium">Project Name</p>
                  <p className="text-sm text-muted-foreground">{project.name}</p>
                </div>
                <div>
                  <p className="text-sm font-medium">Project Path</p>
                  <p className="text-sm font-mono text-muted-foreground break-all">
                    {project.path}
                  </p>
                </div>
                <div>
                  <p className="text-sm font-medium">Deployments</p>
                  <p className="text-sm text-muted-foreground">
                    {project.deployment_count}{" "}
                    {project.deployment_count === 1 ? "artifact" : "artifacts"}
                  </p>
                </div>
              </div>

              {/* Delete Files Option */}
              <div className="rounded-lg border border-destructive/30 bg-destructive/5 p-4">
                <div className="flex items-start gap-3">
                  <Checkbox
                    id="delete-files"
                    checked={deleteFiles}
                    onCheckedChange={(checked) =>
                      setDeleteFiles(checked === true)
                    }
                    className="mt-1"
                  />
                  <div className="flex-1 min-w-0">
                    <Label
                      htmlFor="delete-files"
                      className="text-sm font-semibold cursor-pointer"
                    >
                      Also delete files from disk
                    </Label>
                    <p className="text-xs text-muted-foreground mt-1">
                      WARNING: This will permanently delete all files in the
                      project directory. This action cannot be undone.
                    </p>
                  </div>
                </div>
              </div>
            </>
          ) : (
            <>
              {/* Step 2: Confirmation */}
              <div className="space-y-2">
                <Label htmlFor="confirm-name">
                  Type <code className="px-2 py-1 bg-muted rounded text-sm">{project.name}</code> to confirm
                </Label>
                <Input
                  id="confirm-name"
                  placeholder="Enter project name"
                  value={confirmName}
                  onChange={(e) => setConfirmName(e.target.value)}
                  disabled={deleteMutation.isPending}
                  autoFocus
                />
                <p className="text-xs text-muted-foreground">
                  This confirms you want to delete this project
                  {deleteFiles && " and all its files"}
                </p>
              </div>

              {deleteFiles && (
                <div className="rounded-lg border border-destructive bg-destructive/10 p-3">
                  <div className="flex items-start gap-2">
                    <AlertTriangle className="h-4 w-4 text-destructive flex-shrink-0 mt-0.5" />
                    <p className="text-sm text-destructive font-medium">
                      All files in {project.path} will be permanently deleted
                    </p>
                  </div>
                </div>
              )}
            </>
          )}
        </div>

        <DialogFooter>
          {step === 1 ? (
            <>
              <Button
                variant="outline"
                onClick={handleClose}
                disabled={deleteMutation.isPending}
              >
                Cancel
              </Button>
              <Button variant="destructive" onClick={handleNext}>
                Continue
              </Button>
            </>
          ) : (
            <>
              <Button
                variant="outline"
                onClick={handleBack}
                disabled={deleteMutation.isPending}
              >
                Back
              </Button>
              <Button
                variant="destructive"
                onClick={handleDelete}
                disabled={!isConfirmValid || deleteMutation.isPending}
              >
                {deleteMutation.isPending ? "Deleting..." : "Delete Project"}
              </Button>
            </>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
