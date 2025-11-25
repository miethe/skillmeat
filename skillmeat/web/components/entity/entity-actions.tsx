/**
 * Entity Actions Component
 *
 * Dropdown menu with entity lifecycle actions (edit, delete, deploy, sync, view diff).
 * Handles confirmation dialogs for destructive operations.
 */

"use client";

import * as React from "react";
import { MoreVertical, Pencil, Trash2, Rocket, RefreshCw, FileText, RotateCcw } from "lucide-react";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { RollbackDialog } from "./rollback-dialog";
import type { Entity } from "@/types/entity";

export interface EntityActionsProps {
  entity: Entity;
  onEdit?: () => void;
  onDelete?: () => void;
  onDeploy?: () => void;
  onSync?: () => void;
  onViewDiff?: () => void;
  onRollback?: () => void;
}

export function EntityActions({
  entity,
  onEdit,
  onDelete,
  onDeploy,
  onSync,
  onViewDiff,
  onRollback,
}: EntityActionsProps) {
  const [showDeleteDialog, setShowDeleteDialog] = React.useState(false);
  const [showRollbackDialog, setShowRollbackDialog] = React.useState(false);
  const [isDeleting, setIsDeleting] = React.useState(false);

  const handleDelete = async () => {
    if (!onDelete) return;

    setIsDeleting(true);
    try {
      await onDelete();
      setShowDeleteDialog(false);
    } catch (error) {
      console.error("Failed to delete entity:", error);
    } finally {
      setIsDeleting(false);
    }
  };

  const handleRollback = async () => {
    if (!onRollback) return;
    await onRollback();
  };

  const showViewDiff = entity.status === "modified" && onViewDiff;
  const showRollback =
    (entity.status === "modified" || entity.status === "conflict") &&
    onRollback;

  return (
    <>
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button variant="ghost" size="icon" className="h-8 w-8">
            <MoreVertical className="h-4 w-4" />
            <span className="sr-only">Open menu</span>
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end">
          {onEdit && (
            <DropdownMenuItem onClick={onEdit}>
              <Pencil className="mr-2 h-4 w-4" />
              Edit
            </DropdownMenuItem>
          )}

          {onDeploy && (
            <DropdownMenuItem onClick={onDeploy}>
              <Rocket className="mr-2 h-4 w-4" />
              Deploy to Project
            </DropdownMenuItem>
          )}

          {onSync && (
            <DropdownMenuItem onClick={onSync}>
              <RefreshCw className="mr-2 h-4 w-4" />
              Sync to Collection
            </DropdownMenuItem>
          )}

          {showViewDiff && (
            <DropdownMenuItem onClick={onViewDiff}>
              <FileText className="mr-2 h-4 w-4" />
              View Diff
            </DropdownMenuItem>
          )}

          {showRollback && (
            <DropdownMenuItem onClick={() => setShowRollbackDialog(true)}>
              <RotateCcw className="mr-2 h-4 w-4" />
              Rollback to Collection
            </DropdownMenuItem>
          )}

          {onDelete && (
            <>
              <DropdownMenuSeparator />
              <DropdownMenuItem
                onClick={() => setShowDeleteDialog(true)}
                className="text-destructive focus:text-destructive"
              >
                <Trash2 className="mr-2 h-4 w-4" />
                Delete
              </DropdownMenuItem>
            </>
          )}
        </DropdownMenuContent>
      </DropdownMenu>

      {/* Delete Confirmation Dialog */}
      <Dialog open={showDeleteDialog} onOpenChange={setShowDeleteDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete {entity.name}?</DialogTitle>
            <DialogDescription>
              This action cannot be undone. This will permanently delete the {entity.type}{" "}
              "{entity.name}".
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setShowDeleteDialog(false)}
              disabled={isDeleting}
            >
              Cancel
            </Button>
            <Button variant="destructive" onClick={handleDelete} disabled={isDeleting}>
              {isDeleting ? "Deleting..." : "Delete"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Rollback Confirmation Dialog */}
      <RollbackDialog
        entity={entity}
        open={showRollbackDialog}
        onOpenChange={setShowRollbackDialog}
        onConfirm={handleRollback}
      />
    </>
  );
}
