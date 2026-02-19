/**
 * useCompositeImportFlow
 *
 * React hook that orchestrates the full composite import lifecycle, including:
 *   1. Triggering an atomic composite + children import via `useImportComposite`
 *   2. Detecting hash-mismatch conflicts from a 409 response
 *   3. Surfacing `ConflictResolutionDialog` when conflicts are detected
 *   4. Applying user-chosen resolutions via `useResolveCompositeConflicts`
 *
 * Usage pattern (render the dialog wherever the import button lives):
 *
 * ```tsx
 * function MyImportButton({ compositeId, collectionId, members }) {
 *   const {
 *     importComposite,
 *     isPending,
 *     conflictDialogProps,
 *   } = useCompositeImportFlow({
 *     collectionId,
 *     onImportSuccess: (composite) => router.push(`/artifacts/${composite.id}`),
 *   });
 *
 *   return (
 *     <>
 *       <Button onClick={() => importComposite({ composite_id: compositeId, ... })} disabled={isPending}>
 *         Import
 *       </Button>
 *       <CompositeConflictResolutionDialog {...conflictDialogProps} />
 *     </>
 *   );
 * }
 * ```
 *
 * The `CompositeConflictResolutionDialog` is the thin adapter exported from this
 * module — it bridges `ConflictResolutionDialog`'s `VersionConflict[]` shape with
 * the `ImportVersionConflict[]` shape returned by the backend.
 */

'use client';

import { useState, useCallback } from 'react';
import {
  ConflictResolutionDialog,
  type VersionConflict,
  type ConflictResolution,
} from '@/components/deployment/conflict-resolution-dialog';
import {
  useImportComposite,
  useResolveCompositeConflicts,
  type CompositeImportRequest,
  type CompositeImportResponse,
  type ImportVersionConflict,
} from '@/hooks/useImportComposite';

// ---------------------------------------------------------------------------
// Adapter: ImportVersionConflict → VersionConflict (dialog shape)
// ---------------------------------------------------------------------------

/**
 * Converts backend ImportVersionConflict[] to the VersionConflict[] shape
 * expected by ConflictResolutionDialog.
 */
function toDialogConflicts(conflicts: ImportVersionConflict[]): VersionConflict[] {
  return conflicts.map((c) => ({
    artifactName: c.artifactName,
    artifactType: c.artifactType,
    pinnedHash: c.pinnedHash,
    currentHash: c.currentHash,
    detectedAt: c.detectedAt,
  }));
}

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

export interface UseCompositeImportFlowOptions {
  /** Owning collection ID (e.g. "default"). Used for cache invalidation. */
  collectionId: string;
  /**
   * Platform string passed to ConflictResolutionDialog.
   * Defaults to "claude-code". Non-claude-code platforms receive an informational notice.
   */
  platform?: string;
  /** Called on successful atomic import (no conflicts, or after all conflicts resolved). */
  onImportSuccess?: (composite: CompositeImportResponse) => void;
  /** Called when the user cancels the conflict dialog without resolving. */
  onImportCancelled?: () => void;
}

// ---------------------------------------------------------------------------
// Return type
// ---------------------------------------------------------------------------

export interface CompositeConflictDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  conflicts: VersionConflict[];
  pluginName: string;
  platform: string;
  /** Connected to useResolveCompositeConflicts */
  onResolve: (resolutions: Map<string, ConflictResolution>) => void;
  onCancel: () => void;
  /** Whether resolution mutations are in-flight (use to disable the Proceed button) */
  isResolving: boolean;
}

export interface UseCompositeImportFlowReturn {
  /**
   * Trigger the import. Pass the full CompositeImportRequest.
   * If a 409 version-conflict is returned, the conflict dialog will open automatically.
   */
  importComposite: (request: CompositeImportRequest) => void;
  /** True while the initial import mutation or resolution mutations are in-flight. */
  isPending: boolean;
  /** Props to spread onto <CompositeConflictResolutionDialog /> */
  conflictDialogProps: CompositeConflictDialogProps;
}

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

/**
 * Orchestrates composite import with automatic conflict resolution dialog.
 *
 * @param options - Configuration for the import flow
 * @returns `{ importComposite, isPending, conflictDialogProps }`
 *
 * @example
 * ```tsx
 * const { importComposite, isPending, conflictDialogProps } = useCompositeImportFlow({
 *   collectionId: 'default',
 *   onImportSuccess: (c) => toast.success(`Imported ${c.display_name}`),
 * });
 *
 * <Button onClick={() => importComposite(request)} disabled={isPending}>Import</Button>
 * <CompositeConflictResolutionDialog {...conflictDialogProps} />
 * ```
 */
export function useCompositeImportFlow({
  collectionId,
  platform = 'claude-code',
  onImportSuccess,
  onImportCancelled,
}: UseCompositeImportFlowOptions): UseCompositeImportFlowReturn {
  // Track whether the conflict dialog is open
  const [conflictDialogOpen, setConflictDialogOpen] = useState(false);

  // Pending import conflicts (populated on 409 version-conflict)
  const [pendingConflicts, setPendingConflicts] = useState<ImportVersionConflict[]>([]);

  // Store the in-flight request so we can re-surface the plugin name in the dialog
  const [pendingRequest, setPendingRequest] = useState<CompositeImportRequest | null>(null);

  // ── Import mutation ────────────────────────────────────────────────────────

  const importMutation = useImportComposite({
    collectionId,
    onSuccess: (composite) => {
      onImportSuccess?.(composite);
    },
    onConflict: (conflicts) => {
      // A 409 version-conflict was detected — open the resolution dialog
      setPendingConflicts(conflicts);
      setConflictDialogOpen(true);
    },
  });

  // ── Resolution mutation ────────────────────────────────────────────────────

  const resolveMutation = useResolveCompositeConflicts({
    onSuccess: () => {
      setConflictDialogOpen(false);
      setPendingConflicts([]);
      setPendingRequest(null);

      // Re-import after all conflicts are resolved so the composite is fully created
      if (pendingRequest) {
        importMutation.mutate(pendingRequest);
      }
    },
  });

  // ── Handlers ──────────────────────────────────────────────────────────────

  const importComposite = useCallback(
    (request: CompositeImportRequest) => {
      setPendingRequest(request);
      importMutation.mutate(request);
    },
    [importMutation]
  );

  const handleResolve = useCallback(
    (resolutions: Map<string, ConflictResolution>) => {
      if (!pendingRequest) return;
      resolveMutation.mutate({
        compositeId: pendingRequest.composite_id,
        collectionId,
        resolutions,
        conflicts: pendingConflicts,
      });
    },
    [pendingRequest, collectionId, pendingConflicts, resolveMutation]
  );

  const handleCancel = useCallback(() => {
    setConflictDialogOpen(false);
    setPendingConflicts([]);
    setPendingRequest(null);
    onImportCancelled?.();
  }, [onImportCancelled]);

  const handleOpenChange = useCallback(
    (open: boolean) => {
      if (!open) handleCancel();
    },
    [handleCancel]
  );

  // ── Derive plugin display name from the pending request ───────────────────

  // Extract the name portion from "composite:my-plugin" → "my-plugin"
  const pluginName =
    pendingRequest?.display_name ??
    pendingRequest?.composite_id?.replace(/^composite:/, '') ??
    'Unknown Plugin';

  // ── Compose return value ───────────────────────────────────────────────────

  return {
    importComposite,
    isPending: importMutation.isPending || resolveMutation.isPending,
    conflictDialogProps: {
      open: conflictDialogOpen,
      onOpenChange: handleOpenChange,
      conflicts: toDialogConflicts(pendingConflicts),
      pluginName,
      platform,
      onResolve: handleResolve,
      onCancel: handleCancel,
      isResolving: resolveMutation.isPending,
    },
  };
}

// ---------------------------------------------------------------------------
// Thin dialog adapter component
// ---------------------------------------------------------------------------

/**
 * Drop-in dialog wrapper that connects `ConflictResolutionDialog` to the
 * `useCompositeImportFlow` hook output.
 *
 * Accepts the `conflictDialogProps` returned by `useCompositeImportFlow` and
 * renders `ConflictResolutionDialog` with all props wired correctly.
 *
 * The `isResolving` flag disables the "Proceed" button while resolution mutations
 * are in-flight to prevent double-submission.
 *
 * @example
 * ```tsx
 * const { importComposite, conflictDialogProps } = useCompositeImportFlow({ collectionId });
 *
 * return (
 *   <>
 *     <Button onClick={() => importComposite(req)}>Import Plugin</Button>
 *     <CompositeConflictResolutionDialog {...conflictDialogProps} />
 *   </>
 * );
 * ```
 */
export function CompositeConflictResolutionDialog(props: CompositeConflictDialogProps) {
  const {
    open,
    onOpenChange,
    conflicts,
    pluginName,
    platform,
    onResolve,
    onCancel,
    isResolving,
  } = props;

  // While resolutions are in-flight, we pass an empty conflicts array to
  // re-use the dialog's loading state via the disabled "Proceed" button.
  // The dialog's own allResolved gating disables the button until selections
  // are made, so we also need to block re-submission once isPending.
  //
  // Strategy: wrap onResolve to no-op when already resolving.
  const guardedOnResolve = useCallback(
    (resolutions: Map<string, ConflictResolution>) => {
      if (isResolving) return;
      onResolve(resolutions);
    },
    [isResolving, onResolve]
  );

  return (
    <ConflictResolutionDialog
      open={open}
      onOpenChange={onOpenChange}
      conflicts={conflicts}
      pluginName={pluginName}
      platform={platform}
      onResolve={guardedOnResolve}
      onCancel={onCancel}
    />
  );
}
