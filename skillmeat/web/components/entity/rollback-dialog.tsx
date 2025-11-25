/**
 * Rollback Confirmation Dialog
 *
 * Multi-step confirmation dialog for rolling back an entity to its collection version.
 * Shows what will be rolled back and warns about losing local changes.
 */

"use client";

import * as React from "react";
import { AlertTriangle, RotateCcw } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import type { Entity } from "@/types/entity";

export interface RollbackDialogProps {
  entity: Entity;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onConfirm: () => Promise<void>;
}

export function RollbackDialog({
  entity,
  open,
  onOpenChange,
  onConfirm,
}: RollbackDialogProps) {
  const [isRollingBack, setIsRollingBack] = React.useState(false);

  const handleConfirm = async () => {
    setIsRollingBack(true);
    try {
      await onConfirm();
      onOpenChange(false);
    } catch (error) {
      console.error("Failed to rollback entity:", error);
    } finally {
      setIsRollingBack(false);
    }
  };

  const currentVersion = entity.version || "Unknown";
  const targetVersion = entity.version || "Collection version";

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <RotateCcw className="h-5 w-5" />
            Rollback to Collection Version?
          </DialogTitle>
          <DialogDescription>
            This will replace your local version with the version from the collection.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          {/* Version Comparison */}
          <div className="space-y-3">
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <p className="text-muted-foreground mb-1">Current (Local)</p>
                <p className="font-mono text-xs bg-muted px-2 py-1.5 rounded border">
                  {currentVersion}
                </p>
              </div>
              <div>
                <p className="text-muted-foreground mb-1">Target (Collection)</p>
                <p className="font-mono text-xs bg-muted px-2 py-1.5 rounded border">
                  {targetVersion}
                </p>
              </div>
            </div>

            <div className="text-sm text-muted-foreground">
              <p className="font-medium mb-1">Entity Details:</p>
              <ul className="space-y-1 pl-4">
                <li>Name: <span className="font-mono">{entity.name}</span></li>
                <li>Type: <span className="capitalize">{entity.type}</span></li>
                {entity.projectPath && (
                  <li className="break-all">
                    Project: <span className="font-mono text-xs">{entity.projectPath}</span>
                  </li>
                )}
              </ul>
            </div>
          </div>

          {/* Warning */}
          <Alert variant="destructive">
            <AlertTriangle className="h-4 w-4" />
            <AlertTitle>Warning: This action cannot be undone</AlertTitle>
            <AlertDescription>
              All local modifications will be lost. The collection version will overwrite
              your current local version. Make sure you have backed up any important changes
              before proceeding.
            </AlertDescription>
          </Alert>
        </div>

        <DialogFooter>
          <Button
            variant="outline"
            onClick={() => onOpenChange(false)}
            disabled={isRollingBack}
          >
            Cancel
          </Button>
          <Button
            variant="destructive"
            onClick={handleConfirm}
            disabled={isRollingBack}
          >
            {isRollingBack ? (
              <>
                <RotateCcw className="mr-2 h-4 w-4 animate-spin" />
                Rolling Back...
              </>
            ) : (
              <>
                <RotateCcw className="mr-2 h-4 w-4" />
                Rollback
              </>
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
