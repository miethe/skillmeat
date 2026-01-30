/**
 * Unit tests for toast utilities
 *
 * Tests the detailed import breakdown formatting and toast display logic.
 */

import { formatImportBreakdown, showBulkImportResultToast } from '@/lib/toast-utils';
import type { BulkImportResult } from '@/types/discovery';
import { toast } from 'sonner';

// Mock sonner
jest.mock('sonner', () => ({
  toast: {
    success: jest.fn(),
    warning: jest.fn(),
    error: jest.fn(),
  },
}));

describe('formatImportBreakdown', () => {
  it('formats successful import with all metrics', () => {
    const result: BulkImportResult = {
      total_requested: 10,
      total_imported: 8,
      total_skipped: 1,
      total_failed: 1,
      imported_to_collection: 3,
      added_to_project: 5,
      results: [],
      duration_ms: 1000,
    };

    const breakdown = formatImportBreakdown(result);

    expect(breakdown).toContain('Import Complete');
    expect(breakdown).toContain('✓ Imported to Collection: 3');
    expect(breakdown).toContain('✓ Added to Project: 5');
    expect(breakdown).toContain('○ Skipped: 1');
    expect(breakdown).toContain('✗ Failed: 1');
  });

  it('formats successful import with only collection imports', () => {
    const result: BulkImportResult = {
      total_requested: 3,
      total_imported: 3,
      total_skipped: 0,
      total_failed: 0,
      imported_to_collection: 3,
      added_to_project: 0,
      results: [],
      duration_ms: 500,
    };

    const breakdown = formatImportBreakdown(result);

    expect(breakdown).toContain('✓ Imported to Collection: 3');
    expect(breakdown).not.toContain('Added to Project');
    expect(breakdown).not.toContain('Skipped');
    expect(breakdown).not.toContain('Failed');
  });

  it('formats successful import with only project additions', () => {
    const result: BulkImportResult = {
      total_requested: 5,
      total_imported: 5,
      total_skipped: 0,
      total_failed: 0,
      imported_to_collection: 0,
      added_to_project: 5,
      results: [],
      duration_ms: 800,
    };

    const breakdown = formatImportBreakdown(result);

    expect(breakdown).toContain('✓ Added to Project: 5');
    expect(breakdown).not.toContain('Imported to Collection');
    expect(breakdown).not.toContain('Skipped');
    expect(breakdown).not.toContain('Failed');
  });

  it('handles edge case of all zeros', () => {
    const result: BulkImportResult = {
      total_requested: 0,
      total_imported: 0,
      total_skipped: 0,
      total_failed: 0,
      imported_to_collection: 0,
      added_to_project: 0,
      results: [],
      duration_ms: 0,
    };

    const breakdown = formatImportBreakdown(result);

    expect(breakdown).toContain('No artifacts to import');
  });

  it('formats import with only failures', () => {
    const result: BulkImportResult = {
      total_requested: 5,
      total_imported: 0,
      total_skipped: 0,
      total_failed: 5,
      imported_to_collection: 0,
      added_to_project: 0,
      results: [],
      duration_ms: 1200,
    };

    const breakdown = formatImportBreakdown(result);

    expect(breakdown).toContain('✗ Failed: 5');
    expect(breakdown).not.toContain('Imported to Collection');
    expect(breakdown).not.toContain('Added to Project');
    expect(breakdown).not.toContain('Skipped');
  });

  it('formats import with only skipped artifacts', () => {
    const result: BulkImportResult = {
      total_requested: 3,
      total_imported: 0,
      total_skipped: 3,
      total_failed: 0,
      imported_to_collection: 0,
      added_to_project: 0,
      results: [],
      duration_ms: 300,
    };

    const breakdown = formatImportBreakdown(result);

    expect(breakdown).toContain('○ Skipped: 3');
    expect(breakdown).not.toContain('Imported to Collection');
    expect(breakdown).not.toContain('Added to Project');
    expect(breakdown).not.toContain('Failed');
  });
});

describe('showBulkImportResultToast', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('shows success toast when all imports succeed', () => {
    const result: BulkImportResult = {
      total_requested: 5,
      total_imported: 5,
      total_skipped: 0,
      total_failed: 0,
      imported_to_collection: 5,
      added_to_project: 0,
      results: [],
      duration_ms: 1000,
    };

    showBulkImportResultToast(result);

    expect(toast.success).toHaveBeenCalledWith(
      'Import Complete',
      expect.objectContaining({
        duration: 5000,
      })
    );
  });

  it('shows warning toast when some imports fail or are skipped', () => {
    const result: BulkImportResult = {
      total_requested: 10,
      total_imported: 7,
      total_skipped: 2,
      total_failed: 1,
      imported_to_collection: 7,
      added_to_project: 0,
      results: [],
      duration_ms: 1500,
    };

    showBulkImportResultToast(result);

    expect(toast.warning).toHaveBeenCalledWith(
      'Import Partially Complete',
      expect.objectContaining({
        duration: 5000,
      })
    );
  });

  it('shows error toast when all imports fail', () => {
    const result: BulkImportResult = {
      total_requested: 3,
      total_imported: 0,
      total_skipped: 0,
      total_failed: 3,
      imported_to_collection: 0,
      added_to_project: 0,
      results: [],
      duration_ms: 800,
    };

    showBulkImportResultToast(result);

    expect(toast.error).toHaveBeenCalledWith(
      'Import Failed',
      expect.objectContaining({
        duration: 5000,
      })
    );
  });

  it('includes view details action when callback provided', () => {
    const result: BulkImportResult = {
      total_requested: 5,
      total_imported: 5,
      total_skipped: 0,
      total_failed: 0,
      imported_to_collection: 5,
      added_to_project: 0,
      results: [],
      duration_ms: 1000,
    };

    const onViewDetails = jest.fn();

    showBulkImportResultToast(result, { onViewDetails });

    expect(toast.success).toHaveBeenCalledWith(
      'Import Complete',
      expect.objectContaining({
        action: expect.objectContaining({
          label: 'View Details',
          onClick: onViewDetails,
        }),
      })
    );
  });

  it('creates notification when callback provided', () => {
    const result: BulkImportResult = {
      total_requested: 5,
      total_imported: 5,
      total_skipped: 0,
      total_failed: 0,
      imported_to_collection: 3,
      added_to_project: 2,
      results: [],
      duration_ms: 1000,
      summary: 'All imports successful',
    };

    const addNotification = jest.fn();

    showBulkImportResultToast(result, { addNotification });

    expect(addNotification).toHaveBeenCalledWith(
      expect.objectContaining({
        type: 'success',
        title: 'Import Complete',
        message: 'All imports successful',
        details: expect.objectContaining({
          metadata: expect.objectContaining({
            total_requested: 5,
            total_imported: 5,
            total_skipped: 0,
            total_failed: 0,
            imported_to_collection: 3,
            added_to_project: 2,
            duration_ms: 1000,
          }),
        }),
      })
    );
  });

  it('uses fallback message when summary is not provided', () => {
    const result: BulkImportResult = {
      total_requested: 3,
      total_imported: 3,
      total_skipped: 0,
      total_failed: 0,
      imported_to_collection: 3,
      added_to_project: 0,
      results: [],
      duration_ms: 500,
    };

    const addNotification = jest.fn();

    showBulkImportResultToast(result, { addNotification });

    expect(addNotification).toHaveBeenCalledWith(
      expect.objectContaining({
        message: 'Processed 3 artifact(s)',
      })
    );
  });

  it('handles mixed success and skipped as warning', () => {
    const result: BulkImportResult = {
      total_requested: 10,
      total_imported: 5,
      total_skipped: 5,
      total_failed: 0,
      imported_to_collection: 5,
      added_to_project: 0,
      results: [],
      duration_ms: 1200,
    };

    showBulkImportResultToast(result);

    expect(toast.warning).toHaveBeenCalledWith('Import Partially Complete', expect.any(Object));
  });
});
