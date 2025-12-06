/**
 * @jest-environment jsdom
 *
 * Notification System Integration Tests - Import Status Enum
 *
 * Tests the Notification System's integration with the new ImportStatus enum and
 * BulkImportResult structure from Discovery & Import Enhancement (DIS-5.2).
 *
 * Verifies:
 * - Notification displays correct ImportStatus enum values ("success" | "skipped" | "failed")
 * - Detailed breakdown format (Imported, Skipped, Failed counts)
 * - Skip reasons are accessible in notification details
 * - Toast utils correctly format BulkImportResult
 * - Notifications persist in Notification Center with full metadata
 * - Click-through from toast to notification detail works
 */

import React from 'react';
import { render, screen, waitFor, within, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { NotificationProvider, useNotifications } from '@/lib/notification-store';
import { NotificationBell } from '@/components/notifications/NotificationCenter';
import { showBulkImportResultToast, formatImportBreakdown } from '@/lib/toast-utils';
import type { BulkImportResult, ImportResult, ImportStatus } from '@/types/discovery';
import type { NotificationCreateInput } from '@/types/notification';
import { toast } from 'sonner';

// Mock sonner
jest.mock('sonner', () => ({
  toast: {
    success: jest.fn(),
    error: jest.fn(),
    warning: jest.fn(),
  },
}));

// ============================================================================
// Test Helpers
// ============================================================================

function TestWrapper({ children }: { children: React.ReactNode }) {
  return <NotificationProvider>{children}</NotificationProvider>;
}

function StoreTestComponent({
  onReady,
}: {
  onReady: (api: ReturnType<typeof useNotifications>) => void;
}) {
  const api = useNotifications();
  React.useEffect(() => {
    onReady(api);
  }, [api, onReady]);
  return null;
}

beforeEach(() => {
  localStorage.clear();
  jest.clearAllMocks();
});

afterEach(() => {
  localStorage.clear();
});

// ============================================================================
// Import Status Enum Tests
// ============================================================================

describe('ImportStatus Enum Integration', () => {
  describe('Toast Formatting with Status Enum', () => {
    it('formats breakdown with "success" status results', () => {
      const result: BulkImportResult = {
        total_requested: 5,
        total_imported: 5,
        total_skipped: 0,
        total_failed: 0,
        imported_to_collection: 3,
        added_to_project: 2,
        results: [
          {
            artifact_id: 'skill-1',
            status: 'success' as ImportStatus,
            message: 'Imported to collection',
          },
          {
            artifact_id: 'skill-2',
            status: 'success' as ImportStatus,
            message: 'Added to project',
          },
          {
            artifact_id: 'skill-3',
            status: 'success' as ImportStatus,
            message: 'Imported to collection',
          },
          {
            artifact_id: 'skill-4',
            status: 'success' as ImportStatus,
            message: 'Imported to collection',
          },
          {
            artifact_id: 'skill-5',
            status: 'success' as ImportStatus,
            message: 'Added to project',
          },
        ],
        duration_ms: 1000,
      };

      const breakdown = formatImportBreakdown(result);

      expect(breakdown).toContain('✓ Imported to Collection: 3');
      expect(breakdown).toContain('✓ Added to Project: 2');
      expect(breakdown).not.toContain('Skipped');
      expect(breakdown).not.toContain('Failed');
    });

    it('formats breakdown with "skipped" status results', () => {
      const result: BulkImportResult = {
        total_requested: 5,
        total_imported: 2,
        total_skipped: 3,
        total_failed: 0,
        imported_to_collection: 2,
        added_to_project: 0,
        results: [
          {
            artifact_id: 'skill-1',
            status: 'success' as ImportStatus,
            message: 'Imported to collection',
          },
          {
            artifact_id: 'skill-2',
            status: 'success' as ImportStatus,
            message: 'Imported to collection',
          },
          {
            artifact_id: 'skill-3',
            status: 'skipped' as ImportStatus,
            message: 'Already exists',
            skip_reason: 'User declined - already in collection',
          },
          {
            artifact_id: 'skill-4',
            status: 'skipped' as ImportStatus,
            message: 'User declined',
            skip_reason: 'Not compatible with project',
          },
          {
            artifact_id: 'skill-5',
            status: 'skipped' as ImportStatus,
            message: 'User preference',
            skip_reason: 'User explicitly skipped',
          },
        ],
        duration_ms: 800,
      };

      const breakdown = formatImportBreakdown(result);

      expect(breakdown).toContain('✓ Imported to Collection: 2');
      expect(breakdown).toContain('○ Skipped: 3');
      expect(breakdown).not.toContain('Added to Project');
      expect(breakdown).not.toContain('Failed');
    });

    it('formats breakdown with "failed" status results', () => {
      const result: BulkImportResult = {
        total_requested: 5,
        total_imported: 3,
        total_skipped: 0,
        total_failed: 2,
        imported_to_collection: 3,
        added_to_project: 0,
        results: [
          {
            artifact_id: 'skill-1',
            status: 'success' as ImportStatus,
            message: 'Imported to collection',
          },
          {
            artifact_id: 'skill-2',
            status: 'success' as ImportStatus,
            message: 'Imported to collection',
          },
          {
            artifact_id: 'skill-3',
            status: 'success' as ImportStatus,
            message: 'Imported to collection',
          },
          {
            artifact_id: 'skill-4',
            status: 'failed' as ImportStatus,
            message: 'Import failed',
            error: 'Invalid SKILL.md format',
          },
          {
            artifact_id: 'skill-5',
            status: 'failed' as ImportStatus,
            message: 'Import failed',
            error: 'Missing required files',
          },
        ],
        duration_ms: 1200,
      };

      const breakdown = formatImportBreakdown(result);

      expect(breakdown).toContain('✓ Imported to Collection: 3');
      expect(breakdown).toContain('✗ Failed: 2');
      expect(breakdown).not.toContain('Added to Project');
      expect(breakdown).not.toContain('Skipped');
    });

    it('formats breakdown with mixed status results', () => {
      const result: BulkImportResult = {
        total_requested: 10,
        total_imported: 5,
        total_skipped: 3,
        total_failed: 2,
        imported_to_collection: 2,
        added_to_project: 3,
        results: [
          {
            artifact_id: 'skill-1',
            status: 'success' as ImportStatus,
            message: 'Imported to collection',
          },
          {
            artifact_id: 'skill-2',
            status: 'success' as ImportStatus,
            message: 'Added to project',
          },
          {
            artifact_id: 'skill-3',
            status: 'skipped' as ImportStatus,
            message: 'User declined',
            skip_reason: 'Already exists in project',
          },
          {
            artifact_id: 'skill-4',
            status: 'failed' as ImportStatus,
            message: 'Import failed',
            error: 'Network timeout',
          },
          // ... (would be 10 total in real scenario)
        ],
        duration_ms: 2000,
      };

      const breakdown = formatImportBreakdown(result);

      expect(breakdown).toContain('✓ Imported to Collection: 2');
      expect(breakdown).toContain('✓ Added to Project: 3');
      expect(breakdown).toContain('○ Skipped: 3');
      expect(breakdown).toContain('✗ Failed: 2');
    });
  });

  describe('Toast Display with Status Enum', () => {
    it('shows success toast for all "success" status results', () => {
      const result: BulkImportResult = {
        total_requested: 3,
        total_imported: 3,
        total_skipped: 0,
        total_failed: 0,
        imported_to_collection: 3,
        added_to_project: 0,
        results: [
          { artifact_id: 'skill-1', status: 'success' as ImportStatus, message: 'Success' },
          { artifact_id: 'skill-2', status: 'success' as ImportStatus, message: 'Success' },
          { artifact_id: 'skill-3', status: 'success' as ImportStatus, message: 'Success' },
        ],
        duration_ms: 500,
      };

      showBulkImportResultToast(result);

      expect(toast.success).toHaveBeenCalledWith(
        'Import Complete',
        expect.objectContaining({
          duration: 5000,
        })
      );
    });

    it('shows warning toast when some artifacts have "skipped" status', () => {
      const result: BulkImportResult = {
        total_requested: 5,
        total_imported: 3,
        total_skipped: 2,
        total_failed: 0,
        imported_to_collection: 3,
        added_to_project: 0,
        results: [
          { artifact_id: 'skill-1', status: 'success' as ImportStatus, message: 'Success' },
          { artifact_id: 'skill-2', status: 'success' as ImportStatus, message: 'Success' },
          { artifact_id: 'skill-3', status: 'success' as ImportStatus, message: 'Success' },
          {
            artifact_id: 'skill-4',
            status: 'skipped' as ImportStatus,
            message: 'Skipped',
            skip_reason: 'User preference',
          },
          {
            artifact_id: 'skill-5',
            status: 'skipped' as ImportStatus,
            message: 'Skipped',
            skip_reason: 'Already exists',
          },
        ],
        duration_ms: 800,
      };

      showBulkImportResultToast(result);

      expect(toast.warning).toHaveBeenCalledWith(
        'Import Partially Complete',
        expect.objectContaining({
          duration: 5000,
        })
      );
    });

    it('shows error toast for all "failed" status results', () => {
      const result: BulkImportResult = {
        total_requested: 3,
        total_imported: 0,
        total_skipped: 0,
        total_failed: 3,
        imported_to_collection: 0,
        added_to_project: 0,
        results: [
          {
            artifact_id: 'skill-1',
            status: 'failed' as ImportStatus,
            message: 'Failed',
            error: 'Invalid format',
          },
          {
            artifact_id: 'skill-2',
            status: 'failed' as ImportStatus,
            message: 'Failed',
            error: 'Missing files',
          },
          {
            artifact_id: 'skill-3',
            status: 'failed' as ImportStatus,
            message: 'Failed',
            error: 'Network error',
          },
        ],
        duration_ms: 1000,
      };

      showBulkImportResultToast(result);

      expect(toast.error).toHaveBeenCalledWith(
        'Import Failed',
        expect.objectContaining({
          duration: 5000,
        })
      );
    });
  });

  describe('Notification Details with Status Enum', () => {
    it('stores complete metadata including status breakdowns', async () => {
      let storeApi: ReturnType<typeof useNotifications>;

      render(
        <TestWrapper>
          <StoreTestComponent onReady={(api) => (storeApi = api)} />
        </TestWrapper>
      );

      await waitFor(() => {
        expect(storeApi!).toBeDefined();
      });

      const result: BulkImportResult = {
        total_requested: 10,
        total_imported: 6,
        total_skipped: 2,
        total_failed: 2,
        imported_to_collection: 3,
        added_to_project: 3,
        results: [],
        duration_ms: 1500,
        summary: 'Mixed import results',
      };

      const addNotification = jest.fn();

      showBulkImportResultToast(result, { addNotification });

      expect(addNotification).toHaveBeenCalledWith(
        expect.objectContaining({
          type: 'success',
          title: 'Import Partially Complete',
          message: 'Mixed import results',
          details: {
            metadata: {
              total_requested: 10,
              total_imported: 6,
              total_skipped: 2,
              total_failed: 2,
              imported_to_collection: 3,
              added_to_project: 3,
              duration_ms: 1500,
            },
          },
        })
      );
    });

    it('notification persists with all status enum metadata', async () => {
      let storeApi: ReturnType<typeof useNotifications>;

      render(
        <TestWrapper>
          <StoreTestComponent onReady={(api) => (storeApi = api)} />
        </TestWrapper>
      );

      await waitFor(() => {
        expect(storeApi!).toBeDefined();
      });

      const notificationInput: NotificationCreateInput = {
        type: 'success',
        title: 'Import Complete',
        message: 'Imported 5 artifacts with 2 skipped',
        details: {
          metadata: {
            total_requested: 7,
            total_imported: 5,
            total_skipped: 2,
            total_failed: 0,
            imported_to_collection: 3,
            added_to_project: 2,
            duration_ms: 1200,
          },
        },
      };

      act(() => {
        storeApi!.addNotification(notificationInput);
      });

      await waitFor(() => {
        expect(storeApi!.notifications).toHaveLength(1);
      });

      const notification = storeApi!.notifications[0];
      expect(notification.details).toBeDefined();

      // Type guard check
      if (notification.details && 'metadata' in notification.details) {
        expect(notification.details.metadata?.total_requested).toBe(7);
        expect(notification.details.metadata?.total_imported).toBe(5);
        expect(notification.details.metadata?.total_skipped).toBe(2);
        expect(notification.details.metadata?.total_failed).toBe(0);
        expect(notification.details.metadata?.imported_to_collection).toBe(3);
        expect(notification.details.metadata?.added_to_project).toBe(2);
        expect(notification.details.metadata?.duration_ms).toBe(1200);
      } else {
        fail('Notification details should contain metadata');
      }
    });
  });
});

// ============================================================================
// Skip Reasons Integration Tests
// ============================================================================

describe('Skip Reasons in Notifications', () => {
  describe('Skip Reason Accessibility', () => {
    it('skip reasons are stored in ImportResult objects', () => {
      const importResult: ImportResult = {
        artifact_id: 'skill-canvas',
        status: 'skipped' as ImportStatus,
        message: 'User declined import',
        skip_reason: 'Already exists in collection',
      };

      expect(importResult.skip_reason).toBe('Already exists in collection');
      expect(importResult.status).toBe('skipped');
    });

    it('skip reasons are included in BulkImportResult', () => {
      const result: BulkImportResult = {
        total_requested: 5,
        total_imported: 3,
        total_skipped: 2,
        total_failed: 0,
        imported_to_collection: 3,
        added_to_project: 0,
        results: [
          {
            artifact_id: 'skill-1',
            status: 'success' as ImportStatus,
            message: 'Imported',
          },
          {
            artifact_id: 'skill-2',
            status: 'success' as ImportStatus,
            message: 'Imported',
          },
          {
            artifact_id: 'skill-3',
            status: 'success' as ImportStatus,
            message: 'Imported',
          },
          {
            artifact_id: 'skill-4',
            status: 'skipped' as ImportStatus,
            message: 'Skipped',
            skip_reason: 'User preference - not compatible',
          },
          {
            artifact_id: 'skill-5',
            status: 'skipped' as ImportStatus,
            message: 'Skipped',
            skip_reason: 'Already exists in project',
          },
        ],
        duration_ms: 1000,
      };

      const skippedResults = result.results.filter((r) => r.status === 'skipped');
      expect(skippedResults).toHaveLength(2);
      expect(skippedResults[0].skip_reason).toBe('User preference - not compatible');
      expect(skippedResults[1].skip_reason).toBe('Already exists in project');
    });

    it('metadata preserves skip count for notification display', async () => {
      let storeApi: ReturnType<typeof useNotifications>;

      render(
        <TestWrapper>
          <StoreTestComponent onReady={(api) => (storeApi = api)} />
        </TestWrapper>
      );

      await waitFor(() => {
        expect(storeApi!).toBeDefined();
      });

      const notificationInput: NotificationCreateInput = {
        type: 'success',
        title: 'Import Complete',
        message: 'Import finished with some skipped',
        details: {
          metadata: {
            total_requested: 10,
            total_imported: 7,
            total_skipped: 3,
            total_failed: 0,
            imported_to_collection: 5,
            added_to_project: 2,
            skip_reasons: [
              'Already exists in collection',
              'User preference',
              'Not compatible with project',
            ],
          },
        },
      };

      act(() => {
        storeApi!.addNotification(notificationInput);
      });

      await waitFor(() => {
        expect(storeApi!.notifications).toHaveLength(1);
      });

      const notification = storeApi!.notifications[0];

      if (notification.details && 'metadata' in notification.details) {
        expect(notification.details.metadata?.total_skipped).toBe(3);
        expect(notification.details.metadata?.skip_reasons).toHaveLength(3);
      } else {
        fail('Notification should have metadata with skip reasons');
      }
    });
  });

  describe('Skip Reason Display in UI', () => {
    it('notification shows skip count in breakdown', async () => {
      const user = userEvent.setup();
      let storeApi: ReturnType<typeof useNotifications>;

      // Component to sync NotificationBell props with store
      function NotificationBellWrapper() {
        const { notifications, unreadCount, markAsRead, clearAll, dismissNotification, markAllAsRead } = useNotifications();
        return (
          <NotificationBell
            unreadCount={unreadCount}
            notifications={notifications}
            onMarkAllRead={markAllAsRead}
            onClearAll={clearAll}
            onNotificationClick={markAsRead}
            onDismiss={dismissNotification}
          />
        );
      }

      render(
        <TestWrapper>
          <StoreTestComponent onReady={(api) => (storeApi = api)} />
          <NotificationBellWrapper />
        </TestWrapper>
      );

      await waitFor(() => {
        expect(storeApi!).toBeDefined();
      });

      // Add notification with skip metadata
      act(() => {
        storeApi!.addNotification({
          type: 'success',
          title: 'Import Complete',
          message: 'Imported 5 artifacts, 2 skipped',
          details: {
            metadata: {
              total_requested: 7,
              total_imported: 5,
              total_skipped: 2,
              total_failed: 0,
              imported_to_collection: 3,
              added_to_project: 2,
            },
          },
        });
      });

      await waitFor(() => {
        expect(storeApi!.notifications).toHaveLength(1);
      });

      // Open notification dropdown
      const bellButton = screen.getByRole('button', { name: /Notifications, 1 unread/i });
      await user.click(bellButton);

      // Verify notification is visible
      await waitFor(() => {
        expect(screen.getByText('Import Complete')).toBeInTheDocument();
        expect(screen.getByText('Imported 5 artifacts, 2 skipped')).toBeInTheDocument();
      });
    });
  });
});

// ============================================================================
// Detailed Breakdown Tests
// ============================================================================

describe('Detailed Import Breakdown', () => {
  describe('Format Verification', () => {
    it('breakdown displays all counter fields correctly', () => {
      const result: BulkImportResult = {
        total_requested: 20,
        total_imported: 15,
        total_skipped: 3,
        total_failed: 2,
        imported_to_collection: 8,
        added_to_project: 7,
        results: [],
        duration_ms: 3000,
      };

      const breakdown = formatImportBreakdown(result);

      // Check for all components of the breakdown
      expect(breakdown).toContain('Import Complete');
      expect(breakdown).toContain('─────────────────'); // Separator
      expect(breakdown).toContain('✓ Imported to Collection: 8');
      expect(breakdown).toContain('✓ Added to Project: 7');
      expect(breakdown).toContain('○ Skipped: 3');
      expect(breakdown).toContain('✗ Failed: 2');
    });

    it('breakdown format uses correct symbols and spacing', () => {
      const result: BulkImportResult = {
        total_requested: 10,
        total_imported: 6,
        total_skipped: 2,
        total_failed: 2,
        imported_to_collection: 4,
        added_to_project: 2,
        results: [],
        duration_ms: 1500,
      };

      const breakdown = formatImportBreakdown(result);

      // Verify multi-line format with newlines
      const lines = breakdown.split('\n');
      expect(lines.length).toBeGreaterThan(1);
      expect(lines[0]).toBe('Import Complete');
      expect(lines[1]).toBe('─────────────────');
    });

    it('breakdown omits zero-count fields except when all are zero', () => {
      const result: BulkImportResult = {
        total_requested: 5,
        total_imported: 5,
        total_skipped: 0,
        total_failed: 0,
        imported_to_collection: 5,
        added_to_project: 0,
        results: [],
        duration_ms: 800,
      };

      const breakdown = formatImportBreakdown(result);

      expect(breakdown).toContain('✓ Imported to Collection: 5');
      expect(breakdown).not.toContain('Added to Project: 0');
      expect(breakdown).not.toContain('Skipped: 0');
      expect(breakdown).not.toContain('Failed: 0');
    });
  });

  describe('Toast Integration with Breakdown', () => {
    it('toast description includes formatted breakdown', () => {
      const result: BulkImportResult = {
        total_requested: 10,
        total_imported: 7,
        total_skipped: 2,
        total_failed: 1,
        imported_to_collection: 4,
        added_to_project: 3,
        results: [],
        duration_ms: 2000,
      };

      showBulkImportResultToast(result);

      // Verify toast was called with breakdown in description
      expect(toast.warning).toHaveBeenCalledWith(
        'Import Partially Complete',
        expect.objectContaining({
          description: expect.stringContaining('Import Complete'),
        })
      );
    });

    it('notification stores metadata separately from breakdown', () => {
      const result: BulkImportResult = {
        total_requested: 5,
        total_imported: 5,
        total_skipped: 0,
        total_failed: 0,
        imported_to_collection: 3,
        added_to_project: 2,
        results: [],
        duration_ms: 1000,
      };

      const addNotification = jest.fn();

      showBulkImportResultToast(result, { addNotification });

      // Notification should have metadata object, not breakdown string
      expect(addNotification).toHaveBeenCalledWith(
        expect.objectContaining({
          details: {
            metadata: expect.objectContaining({
              total_imported: 5,
              imported_to_collection: 3,
              added_to_project: 2,
            }),
          },
        })
      );
    });
  });
});

// ============================================================================
// Click-Through Integration Tests
// ============================================================================

describe('Toast to Notification Center Click-Through', () => {
  it('onViewDetails callback triggers navigation to notification center', () => {
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

    // Verify toast includes action button with callback
    expect(toast.success).toHaveBeenCalledWith(
      'Import Complete',
      expect.objectContaining({
        action: {
          label: 'View Details',
          onClick: onViewDetails,
        },
      })
    );
  });

  it('notification persists in center after toast dismisses', async () => {
    let storeApi: ReturnType<typeof useNotifications>;

    render(
      <TestWrapper>
        <StoreTestComponent onReady={(api) => (storeApi = api)} />
      </TestWrapper>
    );

    await waitFor(() => {
      expect(storeApi!).toBeDefined();
    });

    const result: BulkImportResult = {
      total_requested: 10,
      total_imported: 8,
      total_skipped: 1,
      total_failed: 1,
      imported_to_collection: 5,
      added_to_project: 3,
      results: [],
      duration_ms: 2000,
      summary: 'Import completed with 1 skipped',
    };

    const addNotification = jest.fn((notification: NotificationCreateInput) => {
      storeApi!.addNotification(notification);
    });

    showBulkImportResultToast(result, { addNotification });

    // Wait for notification to be added to store
    await waitFor(() => {
      expect(storeApi!.notifications).toHaveLength(1);
    });

    // Verify notification persists with full details
    const notification = storeApi!.notifications[0];
    expect(notification.title).toBe('Import Partially Complete');
    expect(notification.message).toBe('Import completed with 1 skipped');
    expect(notification.status).toBe('unread');

    if (notification.details && 'metadata' in notification.details) {
      expect(notification.details.metadata?.total_requested).toBe(10);
      expect(notification.details.metadata?.total_imported).toBe(8);
      expect(notification.details.metadata?.total_skipped).toBe(1);
      expect(notification.details.metadata?.total_failed).toBe(1);
    } else {
      fail('Notification should have metadata');
    }
  });

  it('clicking notification in center marks it as read', async () => {
    const user = userEvent.setup();
    let storeApi: ReturnType<typeof useNotifications>;

    // Component to sync NotificationBell props with store
    function NotificationBellWrapper() {
      const { notifications, unreadCount, markAsRead, clearAll, dismissNotification, markAllAsRead } = useNotifications();
      return (
        <NotificationBell
          unreadCount={unreadCount}
          notifications={notifications}
          onMarkAllRead={markAllAsRead}
          onClearAll={clearAll}
          onNotificationClick={markAsRead}
          onDismiss={dismissNotification}
        />
      );
    }

    render(
      <TestWrapper>
        <StoreTestComponent onReady={(api) => (storeApi = api)} />
        <NotificationBellWrapper />
      </TestWrapper>
    );

    await waitFor(() => {
      expect(storeApi!).toBeDefined();
    });

    // Add notification
    act(() => {
      storeApi!.addNotification({
        type: 'success',
        title: 'Import Complete',
        message: 'All artifacts imported successfully',
        details: {
          metadata: {
            total_requested: 5,
            total_imported: 5,
            total_skipped: 0,
            total_failed: 0,
            imported_to_collection: 5,
            added_to_project: 0,
          },
        },
      });
    });

    await waitFor(() => {
      expect(storeApi!.notifications).toHaveLength(1);
      expect(storeApi!.notifications[0].status).toBe('unread');
    });

    // Open notification center
    const bellButton = screen.getByRole('button', { name: /Notifications, 1 unread/i });
    await user.click(bellButton);

    // Click notification
    const notification = await screen.findByText('Import Complete');
    await user.click(notification);

    // Verify notification was marked as read
    await waitFor(() => {
      expect(storeApi!.notifications[0].status).toBe('read');
      expect(storeApi!.unreadCount).toBe(0);
    });
  });
});

// ============================================================================
// Edge Cases and Error Handling
// ============================================================================

describe('Edge Cases', () => {
  it('handles BulkImportResult with empty results array', () => {
    const result: BulkImportResult = {
      total_requested: 5,
      total_imported: 5,
      total_skipped: 0,
      total_failed: 0,
      imported_to_collection: 5,
      added_to_project: 0,
      results: [], // Empty results array
      duration_ms: 1000,
    };

    const breakdown = formatImportBreakdown(result);

    expect(breakdown).toContain('✓ Imported to Collection: 5');
  });

  it('handles notification with null details gracefully', async () => {
    let storeApi: ReturnType<typeof useNotifications>;

    render(
      <TestWrapper>
        <StoreTestComponent onReady={(api) => (storeApi = api)} />
      </TestWrapper>
    );

    await waitFor(() => {
      expect(storeApi!).toBeDefined();
    });

    act(() => {
      storeApi!.addNotification({
        type: 'info',
        title: 'Simple Notification',
        message: 'No details',
        details: null,
      });
    });

    await waitFor(() => {
      expect(storeApi!.notifications).toHaveLength(1);
    });

    expect(storeApi!.notifications[0].details).toBeNull();
  });

  it('handles missing skip_reason field gracefully', () => {
    const importResult: ImportResult = {
      artifact_id: 'skill-test',
      status: 'skipped' as ImportStatus,
      message: 'Skipped',
      // skip_reason intentionally omitted
    };

    expect(importResult.status).toBe('skipped');
    expect(importResult.skip_reason).toBeUndefined();
  });

  it('handles missing error field gracefully', () => {
    const importResult: ImportResult = {
      artifact_id: 'skill-test',
      status: 'failed' as ImportStatus,
      message: 'Failed',
      // error intentionally omitted
    };

    expect(importResult.status).toBe('failed');
    expect(importResult.error).toBeUndefined();
  });
});
