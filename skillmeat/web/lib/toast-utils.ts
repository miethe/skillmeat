import { toast } from 'sonner';

export function showSuccessToast(message: string, description?: string) {
  toast.success(message, {
    description,
    duration: 4000,
  });
}

export function showErrorToast(error: unknown, fallbackMessage = 'An error occurred') {
  const message = error instanceof Error ? error.message : fallbackMessage;
  toast.error(message, {
    duration: 5000,
    action: {
      label: 'Dismiss',
      onClick: () => {},
    },
  });
}

export function showWarningToast(message: string, description?: string) {
  toast.warning(message, {
    description,
    duration: 4000,
  });
}

export function showImportResultToast(result: {
  total_imported: number;
  total_failed: number;
}) {
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
}
