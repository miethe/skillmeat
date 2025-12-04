import { toast } from 'sonner';
import type { NotificationCreateInput, ArtifactImportResult } from '@/types/notification';

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
 * Show an import result toast and optionally create a notification
 *
 * Displays success/warning/error toast based on import results.
 * If addNotification callback is provided, also creates a detailed notification.
 *
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
