import { toast } from 'sonner';
import type { NotificationCreateInput, ArtifactImportResult } from '@/types/notification';
import type { BulkImportResult } from '@/types/discovery';

/**
 * Extended import result type with optional artifact details
 * Used to show detailed notifications for import operations
 */
export interface ImportResultWithDetails {
  total_imported: number;
  total_failed: number;
  artifacts?: ArtifactImportResult[];
}

/**
 * Options for error toast with optional notification creation
 */
export interface ErrorToastOptions {
  error: unknown;
  fallbackMessage?: string;
  code?: string;
  stack?: string;
  retryable?: boolean;
}

/**
 * Options for import result toast
 */
export interface ImportResultToastOptions {
  addNotification?: (notification: NotificationCreateInput) => void;
  onViewDetails?: () => void;
}

export function showSuccessToast(message: string, description?: string) {
  toast.success(message, {
    description,
    duration: 4000,
  });
}

/**
 * Show an error toast and optionally create a notification
 *
 * @param error - Error object or unknown value
 * @param fallbackMessage - Message to show if error cannot be parsed
 * @param addNotification - Optional callback to create a notification
 */
export function showErrorToast(
  error: unknown,
  fallbackMessage = 'An error occurred',
  addNotification?: (notification: NotificationCreateInput) => void
) {
  const message = error instanceof Error ? error.message : fallbackMessage;
  const errorCode = error && typeof error === 'object' && 'code' in error
    ? String(error.code)
    : undefined;
  const stack = error instanceof Error ? error.stack : undefined;

  toast.error(message, {
    duration: 5000,
    action: {
      label: 'Dismiss',
      onClick: () => {},
    },
  });

  // Optionally create notification if callback provided
  if (addNotification) {
    addNotification({
      type: 'error',
      title: 'Error',
      message,
      details: {
        code: errorCode,
        message,
        stack,
        retryable: false,
      },
    });
  }
}

export function showWarningToast(message: string, description?: string) {
  toast.warning(message, {
    description,
    duration: 4000,
  });
}

/**
 * Format detailed breakdown of import results
 * Creates a multi-line string showing all import metrics
 *
 * @param result - Bulk import result with detailed counters
 * @returns Formatted breakdown string
 */
export function formatImportBreakdown(result: BulkImportResult): string {
  const lines = [
    'Import Complete',
    '─────────────────',
  ];

  // Imported to collection (new artifacts)
  if (result.imported_to_collection > 0) {
    lines.push(`✓ Imported to Collection: ${result.imported_to_collection}`);
  }

  // Added to project (deployed artifacts)
  if (result.added_to_project > 0) {
    lines.push(`✓ Added to Project: ${result.added_to_project}`);
  }

  // Skipped artifacts
  if (result.total_skipped > 0) {
    lines.push(`○ Skipped: ${result.total_skipped}`);
  }

  // Failed imports
  if (result.total_failed > 0) {
    lines.push(`✗ Failed: ${result.total_failed}`);
  }

  // Handle edge case: all zeros
  if (result.total_requested === 0) {
    lines.push('No artifacts to import');
  }

  return lines.join('\n');
}

/**
 * Determine toast type based on import results
 *
 * @param result - Bulk import result
 * @returns Toast type: 'success', 'warning', or 'error'
 */
function getToastType(result: BulkImportResult): 'success' | 'warning' | 'error' {
  // All failed - error
  if (result.total_imported === 0 && result.total_failed > 0) {
    return 'error';
  }

  // Some succeeded, some failed/skipped - warning
  if (result.total_imported > 0 && (result.total_failed > 0 || result.total_skipped > 0)) {
    return 'warning';
  }

  // All succeeded - success
  return 'success';
}

/**
 * Show an import result toast with detailed breakdown
 *
 * Displays success/warning/error toast based on import results with a
 * detailed multi-line breakdown showing:
 * - Imported to Collection (new artifacts)
 * - Added to Project (deployed artifacts)
 * - Skipped (user-declined artifacts)
 * - Failed (error during import)
 *
 * If addNotification callback is provided, also creates a detailed notification.
 * If onViewDetails callback is provided, adds a clickable action button.
 *
 * @param result - Bulk import operation results
 * @param options - Optional callbacks for notification and view details
 */
export function showBulkImportResultToast(
  result: BulkImportResult,
  options?: ImportResultToastOptions
) {
  const { addNotification, onViewDetails } = options || {};
  const toastType = getToastType(result);
  const breakdown = formatImportBreakdown(result);

  // Determine title based on outcome
  let title = 'Import Complete';
  if (toastType === 'error') {
    title = 'Import Failed';
  } else if (toastType === 'warning') {
    title = 'Import Partially Complete';
  }

  // Show toast with appropriate type
  const toastOptions: Parameters<typeof toast.success>[1] = {
    description: breakdown,
    duration: 5000,
    action: onViewDetails
      ? {
          label: 'View Details',
          onClick: onViewDetails,
        }
      : undefined,
  };

  switch (toastType) {
    case 'success':
      toast.success(title, toastOptions);
      break;
    case 'warning':
      toast.warning(title, toastOptions);
      break;
    case 'error':
      toast.error(title, toastOptions);
      break;
  }

  // Optionally create notification if callback provided
  if (addNotification) {
    // Map toast type to notification type
    // 'warning' toast becomes 'info' notification since NotificationType doesn't include 'warning'
    const notificationType = toastType === 'error' ? 'error' : 'success';

    addNotification({
      type: notificationType,
      title,
      message: result.summary || `Processed ${result.total_requested} artifact(s)`,
      details: {
        metadata: {
          total_requested: result.total_requested,
          total_imported: result.total_imported,
          total_skipped: result.total_skipped,
          total_failed: result.total_failed,
          imported_to_collection: result.imported_to_collection,
          added_to_project: result.added_to_project,
          duration_ms: result.duration_ms,
        },
      },
    });
  }
}

/**
 * Show an import result toast and optionally create a notification
 *
 * Displays success/warning/error toast based on import results.
 * If addNotification callback is provided, also creates a detailed notification.
 *
 * @deprecated Use showBulkImportResultToast for BulkImportResult types
 * @param result - Import operation results
 * @param addNotification - Optional callback to create a notification
 */
export function showImportResultToast(
  result: ImportResultWithDetails,
  addNotification?: (notification: NotificationCreateInput) => void
) {
  const total = result.total_imported + result.total_failed;

  if (result.total_imported > 0 && result.total_failed === 0) {
    showSuccessToast(
      `Successfully imported ${result.total_imported} artifact(s)`
    );
  } else if (result.total_imported > 0 && result.total_failed > 0) {
    showWarningToast(
      `Imported ${result.total_imported} artifact(s)`,
      `${result.total_failed} failed`
    );
  } else {
    showErrorToast(null, 'Import failed - no artifacts imported');
  }

  // Optionally create notification if callback provided
  if (addNotification) {
    addNotification({
      type: result.total_failed > 0 ? 'error' : 'success',
      title: 'Import Complete',
      message: `Imported ${result.total_imported} of ${total} artifact(s)`,
      details: result.artifacts ? {
        total,
        succeeded: result.total_imported,
        failed: result.total_failed,
        artifacts: result.artifacts,
      } : undefined,
    });
  }
}
