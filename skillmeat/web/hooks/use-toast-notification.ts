'use client';

import { useNotifications } from '@/lib/notification-store';
import {
  showSuccessToast,
  showErrorToast,
  showWarningToast,
  showImportResultToast,
  type ImportResultWithDetails,
} from '@/lib/toast-utils';

/**
 * Hook that combines toast notifications with persistent notification store
 *
 * Provides wrapper functions that show a toast AND create a notification in the store.
 * This ensures users can always review past notifications even after toasts disappear.
 *
 * Usage:
 * ```tsx
 * function MyComponent() {
 *   const { showImportResult, showError } = useToastNotification();
 *
 *   const handleImport = async () => {
 *     try {
 *       const result = await importArtifacts(sources);
 *       showImportResult({
 *         total_imported: result.succeeded.length,
 *         total_failed: result.failed.length,
 *         artifacts: result.artifacts,
 *       });
 *     } catch (error) {
 *       showError(error, 'Import failed');
 *     }
 *   };
 * }
 * ```
 */
export function useToastNotification() {
  const { addNotification } = useNotifications();

  return {
    /**
     * Show success toast (no persistent notification created)
     * Use for transient success messages that don't need to be reviewed later
     */
    showSuccess: (message: string, description?: string) => {
      showSuccessToast(message, description);
    },

    /**
     * Show warning toast (no persistent notification created)
     * Use for transient warnings that don't need to be reviewed later
     */
    showWarning: (message: string, description?: string) => {
      showWarningToast(message, description);
    },

    /**
     * Show error toast AND create persistent error notification
     * Users can review error details in the notification center
     *
     * @param error - Error object or unknown value
     * @param fallbackMessage - Message to show if error cannot be parsed
     */
    showError: (error: unknown, fallbackMessage = 'An error occurred') => {
      showErrorToast(error, fallbackMessage, addNotification);
    },

    /**
     * Show import result toast AND create persistent notification
     * Users can review detailed import results in the notification center
     *
     * @param result - Import operation results with optional artifact details
     */
    showImportResult: (result: ImportResultWithDetails) => {
      showImportResultToast(result, addNotification);
    },
  };
}
