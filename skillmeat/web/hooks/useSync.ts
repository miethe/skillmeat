/**
 * Sync hook for artifact synchronization operations
 */

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

export interface SyncRequest {
  artifactId: string;
  artifactName: string;
  artifactType: string;
  collectionName?: string;
  force?: boolean;
  mergeStrategy?: "ours" | "theirs" | "manual";
}

export interface SyncResponse {
  success: boolean;
  message: string;
  syncId?: string;
  streamUrl?: string;
  hasConflicts?: boolean;
  conflicts?: ConflictInfo[];
  updatedVersion?: string;
  changesSummary?: {
    filesAdded: number;
    filesModified: number;
    filesDeleted: number;
  };
}

export interface ConflictInfo {
  filePath: string;
  conflictType: "modified" | "deleted" | "added";
  currentVersion: string;
  upstreamVersion: string;
  description: string;
}

export interface SyncError {
  message: string;
  code?: string;
  details?: any;
  conflicts?: ConflictInfo[];
}

export interface UseSyncOptions {
  onSuccess?: (data: SyncResponse, variables: SyncRequest) => void;
  onError?: (error: SyncError, variables: SyncRequest) => void;
  onConflict?: (conflicts: ConflictInfo[], variables: SyncRequest) => void;
  onSettled?: () => void;
}

export function useSync(options: UseSyncOptions = {}) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (request: SyncRequest): Promise<SyncResponse> => {
      await new Promise((resolve) => setTimeout(resolve, 1500));

      const hasConflicts = !request.force && Math.random() < 0.2;

      if (hasConflicts) {
        const conflicts: ConflictInfo[] = [
          {
            filePath: "SKILL.md",
            conflictType: "modified",
            currentVersion: "v1.0.0",
            upstreamVersion: "v1.1.0",
            description: "Local modifications conflict with upstream changes",
          },
        ];

        return {
          success: false,
          message: "Conflicts detected during sync",
          hasConflicts: true,
          conflicts,
        };
      }

      const syncId = "sync-" + Date.now().toString();
      const streamUrl = "/api/v1/sync/" + request.artifactId + "/stream";
      const message = "Successfully synced " + request.artifactName;

      return {
        success: true,
        message,
        syncId,
        streamUrl,
        hasConflicts: false,
        updatedVersion: "v1.1.0",
        changesSummary: {
          filesAdded: 0,
          filesModified: 2,
          filesDeleted: 0,
        },
      };
    },

    onSuccess: (data, variables) => {
      if (data.hasConflicts && data.conflicts) {
        options.onConflict?.(data.conflicts, variables);

        toast.warning("Conflicts detected", {
          description: "Please resolve conflicts before syncing",
        });
      } else {
        queryClient.invalidateQueries({ queryKey: ["artifacts"] });
        queryClient.invalidateQueries({ queryKey: ["artifact", variables.artifactId] });

        const summary = data.changesSummary;
        let description;
        if (summary) {
          description = summary.filesModified + " modified, " + summary.filesAdded + " added, " + summary.filesDeleted + " deleted";
        }

        toast.success(data.message || "Sync successful", {
          description,
        });

        options.onSuccess?.(data, variables);
      }
    },

    onError: (error: any, variables) => {
      const syncError: SyncError = {
        message: error.message || "Sync failed",
        code: error.code,
        details: error.details,
        conflicts: error.conflicts,
      };

      toast.error(syncError.message);

      options.onError?.(syncError, variables);
    },

    onSettled: () => {
      options.onSettled?.();
    },
  });
}

export function useCheckUpstream() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (_artifactId: string): Promise<{
      hasUpdate: boolean;
      currentVersion: string;
      upstreamVersion?: string;
      updateAvailable: boolean;
    }> => {
      await new Promise((resolve) => setTimeout(resolve, 500));

      const hasUpdate = Math.random() < 0.3;

      return {
        hasUpdate,
        currentVersion: "v1.0.0",
        upstreamVersion: hasUpdate ? "v1.1.0" : undefined,
        updateAvailable: hasUpdate,
      };
    },

    onSuccess: (data) => {
      if (data.updateAvailable) {
        const description = "New version " + data.upstreamVersion + " is available";
        toast.info("Update available", {
          description,
        });
      } else {
        toast.success("Up to date", {
          description: "No updates available",
        });
      }

      queryClient.invalidateQueries({ queryKey: ["artifacts"] });
    },

    onError: (error: any) => {
      toast.error("Failed to check for updates", {
        description: error.message,
      });
    },
  });
}
