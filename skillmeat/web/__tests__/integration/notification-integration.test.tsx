/**
 * @jest-environment jsdom
 *
 * Notification System Integration Tests
 *
 * Tests the complete notification flow from toast utils to notification display:
 * - useToastNotification hook integration
 * - NotificationProvider state management
 * - Header + NotificationBell UI integration
 * - End-to-end notification flows
 * - localStorage persistence
 */
import React from 'react';
import { render, screen, waitFor, within, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { NotificationProvider, useNotifications } from '@/lib/notification-store';
import { NotificationBell } from '@/components/notifications/NotificationCenter';
import { Header } from '@/components/header';
import { useToastNotification } from '@/hooks/use-toast-notification';
import type { ArtifactImportResult } from '@/types/notification';
import { toast } from 'sonner';

// Mock sonner toast to isolate notification behavior
jest.mock('sonner', () => ({
  toast: {
    success: jest.fn(),
    error: jest.fn(),
    warning: jest.fn(),
  },
}));

// Mock Link from next/link
jest.mock('next/link', () => {
  return ({ children, href }: { children: React.ReactNode; href: string }) => (
    <a href={href}>{children}</a>
  );
});

// ============================================================================
// Test Helpers
// ============================================================================

/**
 * Test wrapper with NotificationProvider
 */
function TestWrapper({ children }: { children: React.ReactNode }) {
  return <NotificationProvider>{children}</NotificationProvider>;
}

/**
 * Helper component to expose useToastNotification hook API
 */
function TestComponent({
  onReady,
}: {
  onReady: (api: ReturnType<typeof useToastNotification>) => void;
}) {
  const api = useToastNotification();
  React.useEffect(() => {
    onReady(api);
  }, [api, onReady]);
  return null;
}

/**
 * Helper component to expose useNotifications hook API
 */
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

/**
 * Clear localStorage before each test
 */
beforeEach(() => {
  localStorage.clear();
  jest.clearAllMocks();
});

/**
 * Clean up after each test
 */
afterEach(() => {
  localStorage.clear();
});

// ============================================================================
// Toast + Notification Integration Tests
// ============================================================================

describe('Toast + Notification Integration', () => {
  describe('useToastNotification hook', () => {
    it('showImportResult creates notification with correct type', async () => {
      let hookApi: ReturnType<typeof useToastNotification>;
      let storeApi: ReturnType<typeof useNotifications>;

      const { rerender } = render(
        <TestWrapper>
          <TestComponent onReady={(api) => (hookApi = api)} />
          <StoreTestComponent onReady={(api) => (storeApi = api)} />
        </TestWrapper>
      );

      await waitFor(() => {
        expect(hookApi!).toBeDefined();
        expect(storeApi!).toBeDefined();
      });

      // Call showImportResult
      const result = {
        total_imported: 2,
        total_failed: 0,
        artifacts: [
          { name: 'skill-1', type: 'skill' as const, success: true },
          { name: 'skill-2', type: 'skill' as const, success: true },
        ],
      };

      act(() => {
        hookApi!.showImportResult(result);
      });

      // Force re-render to get updated state
      rerender(
        <TestWrapper>
          <TestComponent onReady={(api) => (hookApi = api)} />
          <StoreTestComponent onReady={(api) => (storeApi = api)} />
        </TestWrapper>
      );

      await waitFor(() => {
        expect(storeApi!.notifications).toHaveLength(1);
      });

      // Verify notification was created with correct type
      const notification = storeApi!.notifications[0];
      expect(notification.type).toBe('success');
      expect(notification.title).toBe('Import Complete');
      expect(notification.status).toBe('unread');
      expect(storeApi!.unreadCount).toBe(1);

      // Verify toast was called
      expect(toast.success).toHaveBeenCalledWith(
        'Successfully imported 2 artifact(s)',
        expect.objectContaining({ duration: 4000 })
      );
    });

    it('showImportResult includes artifact details in notification', async () => {
      let hookApi: ReturnType<typeof useToastNotification>;
      let storeApi: ReturnType<typeof useNotifications>;

      render(
        <TestWrapper>
          <TestComponent onReady={(api) => (hookApi = api)} />
          <StoreTestComponent onReady={(api) => (storeApi = api)} />
        </TestWrapper>
      );

      await waitFor(() => {
        expect(hookApi!).toBeDefined();
        expect(storeApi!).toBeDefined();
      });

      // Create import with multiple artifacts
      const artifacts: ArtifactImportResult[] = [
        { name: 'canvas-design', type: 'skill', success: true },
        { name: 'mcp-server', type: 'mcp', success: true },
        { name: 'failed-artifact', type: 'command', success: false, error: 'Parse error' },
      ];

      act(() => {
        hookApi!.showImportResult({
          total_imported: 2,
          total_failed: 1,
          artifacts,
        });
      });

      await waitFor(() => {
        expect(storeApi!.notifications).toHaveLength(1);
      });

      const notification = storeApi!.notifications[0];
      expect(notification.details).toBeDefined();

      // Type guard check
      if (
        notification.details &&
        'artifacts' in notification.details &&
        Array.isArray(notification.details.artifacts)
      ) {
        expect(notification.details.total).toBe(3);
        expect(notification.details.succeeded).toBe(2);
        expect(notification.details.failed).toBe(1);
        expect(notification.details.artifacts).toHaveLength(3);
        expect(notification.details.artifacts[0].name).toBe('canvas-design');
        expect(notification.details.artifacts[2].error).toBe('Parse error');
      } else {
        fail('Notification details should contain artifacts array');
      }
    });

    it('showError creates error notification with details', async () => {
      let hookApi: ReturnType<typeof useToastNotification>;
      let storeApi: ReturnType<typeof useNotifications>;

      render(
        <TestWrapper>
          <TestComponent onReady={(api) => (hookApi = api)} />
          <StoreTestComponent onReady={(api) => (storeApi = api)} />
        </TestWrapper>
      );

      await waitFor(() => {
        expect(hookApi!).toBeDefined();
        expect(storeApi!).toBeDefined();
      });

      // Call showError with Error object
      const error = new Error('Network request failed');
      act(() => {
        hookApi!.showError(error);
      });

      await waitFor(() => {
        expect(storeApi!.notifications).toHaveLength(1);
      });

      const notification = storeApi!.notifications[0];
      expect(notification.type).toBe('error');
      expect(notification.title).toBe('Error');
      expect(notification.message).toBe('Network request failed');

      // Verify error details
      if (notification.details && 'message' in notification.details) {
        expect(notification.details.message).toBe('Network request failed');
        expect(notification.details.stack).toBeDefined();
        expect(notification.details.retryable).toBe(false);
      } else {
        fail('Notification details should contain error message');
      }

      // Verify toast was called
      expect(toast.error).toHaveBeenCalledWith(
        'Network request failed',
        expect.objectContaining({ duration: 5000 })
      );
    });

    it('showError handles non-Error objects', async () => {
      let hookApi: ReturnType<typeof useToastNotification>;
      let storeApi: ReturnType<typeof useNotifications>;

      render(
        <TestWrapper>
          <TestComponent onReady={(api) => (hookApi = api)} />
          <StoreTestComponent onReady={(api) => (storeApi = api)} />
        </TestWrapper>
      );

      await waitFor(() => {
        expect(hookApi!).toBeDefined();
        expect(storeApi!).toBeDefined();
      });

      // Call showError with string
      act(() => {
        hookApi!.showError('Something went wrong', 'Custom fallback message');
      });

      await waitFor(() => {
        expect(storeApi!.notifications).toHaveLength(1);
      });

      const notification = storeApi!.notifications[0];
      expect(notification.message).toBe('Custom fallback message');

      // Verify toast used fallback
      expect(toast.error).toHaveBeenCalledWith(
        'Custom fallback message',
        expect.objectContaining({ duration: 5000 })
      );
    });

    it('showSuccess and showWarning work without creating notifications', async () => {
      let hookApi: ReturnType<typeof useToastNotification>;
      let storeApi: ReturnType<typeof useNotifications>;

      render(
        <TestWrapper>
          <TestComponent onReady={(api) => (hookApi = api)} />
          <StoreTestComponent onReady={(api) => (storeApi = api)} />
        </TestWrapper>
      );

      await waitFor(() => {
        expect(hookApi!).toBeDefined();
        expect(storeApi!).toBeDefined();
      });

      // Call transient toast methods
      act(() => {
        hookApi!.showSuccess('Operation completed');
        hookApi!.showWarning('Please note');
      });

      // Wait a bit to ensure no notifications were created
      await new Promise((resolve) => setTimeout(resolve, 100));

      // Verify no notifications in store
      expect(storeApi!.notifications).toHaveLength(0);
      expect(storeApi!.unreadCount).toBe(0);

      // Verify toasts were called
      expect(toast.success).toHaveBeenCalledWith(
        'Operation completed',
        expect.objectContaining({ duration: 4000 })
      );
      expect(toast.warning).toHaveBeenCalledWith(
        'Please note',
        expect.objectContaining({ duration: 4000 })
      );
    });
  });
});

// ============================================================================
// Provider Integration Tests
// ============================================================================

describe('Provider Integration', () => {
  it('NotificationProvider makes store available throughout app', async () => {
    let storeApi: ReturnType<typeof useNotifications>;

    // Deeply nested component
    function DeepNestedComponent() {
      const api = useNotifications();
      React.useEffect(() => {
        storeApi = api;
      }, [api]);
      return <div>Nested Component</div>;
    }

    render(
      <TestWrapper>
        <div>
          <div>
            <div>
              <DeepNestedComponent />
            </div>
          </div>
        </div>
      </TestWrapper>
    );

    await waitFor(() => {
      expect(storeApi!).toBeDefined();
    });

    // Verify store is accessible
    expect(storeApi!.notifications).toBeDefined();
    expect(storeApi!.addNotification).toBeDefined();
  });

  it('notifications persist across component remounts', async () => {
    let storeApi: ReturnType<typeof useNotifications>;

    const Component = () => {
      const api = useNotifications();
      storeApi = api;
      return <div>Component</div>;
    };

    const { unmount } = render(
      <TestWrapper>
        <Component />
      </TestWrapper>
    );

    await waitFor(() => {
      expect(storeApi!).toBeDefined();
    });

    // Add notification
    act(() => {
      storeApi!.addNotification({
        type: 'info',
        title: 'Test',
        message: 'Persisted notification',
      });
    });

    await waitFor(() => {
      expect(storeApi!.notifications).toHaveLength(1);
    });

    const notificationId = storeApi!.notifications[0].id;

    // Unmount component
    unmount();

    // Wait for localStorage write
    await new Promise((resolve) => setTimeout(resolve, 100));

    // Verify persisted to localStorage
    const stored = localStorage.getItem('skillmeat-notifications');
    expect(stored).toBeTruthy();
    const parsed = JSON.parse(stored!);
    expect(parsed).toHaveLength(1);
    expect(parsed[0].id).toBe(notificationId);

    // Create new render (simulates page reload)
    const { container } = render(
      <TestWrapper>
        <Component />
      </TestWrapper>
    );

    // Verify notification still exists after reload
    await waitFor(() => {
      expect(storeApi!.notifications).toHaveLength(1);
    });

    expect(storeApi!.notifications[0].message).toBe('Persisted notification');
  });

  it('throws error when useNotifications used outside provider', () => {
    // Suppress console.error for this test
    const consoleSpy = jest.spyOn(console, 'error').mockImplementation(() => {});

    expect(() => {
      render(<StoreTestComponent onReady={() => {}} />);
    }).toThrow('useNotifications must be used within a NotificationProvider');

    consoleSpy.mockRestore();
  });
});

// ============================================================================
// Header Integration Tests
// ============================================================================

describe('Header Integration', () => {
  it('NotificationBell receives notifications from store', async () => {
    let storeApi: ReturnType<typeof useNotifications>;

    const { container } = render(
      <TestWrapper>
        <StoreTestComponent onReady={(api) => (storeApi = api)} />
        <Header />
      </TestWrapper>
    );

    await waitFor(() => {
      expect(storeApi!).toBeDefined();
    });

    // Initially no badge
    expect(screen.queryByText('1')).not.toBeInTheDocument();

    // Add notification
    act(() => {
      storeApi!.addNotification({
        type: 'import',
        title: 'Import Complete',
        message: 'Successfully imported 2 artifacts',
      });
    });

    // Verify badge appears with count
    await waitFor(() => {
      const badge = screen.getByText('1');
      expect(badge).toBeInTheDocument();
    });
  });

  it('Header shows correct unread count', async () => {
    let storeApi: ReturnType<typeof useNotifications>;

    render(
      <TestWrapper>
        <StoreTestComponent onReady={(api) => (storeApi = api)} />
        <Header />
      </TestWrapper>
    );

    await waitFor(() => {
      expect(storeApi!).toBeDefined();
    });

    // Add multiple notifications
    act(() => {
      storeApi!.addNotification({
        type: 'import',
        title: 'Import 1',
        message: 'First import',
      });
      storeApi!.addNotification({
        type: 'import',
        title: 'Import 2',
        message: 'Second import',
      });
      storeApi!.addNotification({
        type: 'sync',
        title: 'Sync',
        message: 'Synced',
      });
    });

    // Verify badge shows 3
    await waitFor(() => {
      expect(screen.getByText('3')).toBeInTheDocument();
    });
  });

  it('clicking notification marks it as read', async () => {
    const user = userEvent.setup();
    let storeApi: ReturnType<typeof useNotifications>;

    render(
      <TestWrapper>
        <StoreTestComponent onReady={(api) => (storeApi = api)} />
        <Header />
      </TestWrapper>
    );

    await waitFor(() => {
      expect(storeApi!).toBeDefined();
    });

    // Add unread notification
    act(() => {
      storeApi!.addNotification({
        type: 'info',
        title: 'Test Notification',
        message: 'Click me',
      });
    });

    await waitFor(() => {
      expect(storeApi!.unreadCount).toBe(1);
    });

    // Open notification dropdown
    const bellButton = screen.getByRole('button', { name: /Notifications, 1 unread/i });
    await user.click(bellButton);

    // Find and click the notification
    const notification = await screen.findByText('Test Notification');
    await user.click(notification);

    // Verify status changed to read (unread count should be 0)
    // Note: The dropdown closes on click, so we need to check the store
    await waitFor(() => {
      expect(storeApi!.unreadCount).toBe(0);
      expect(storeApi!.notifications[0].status).toBe('read');
    });
  });

  it('badge handles large numbers correctly (50 max due to eviction)', async () => {
    let storeApi: ReturnType<typeof useNotifications>;

    render(
      <TestWrapper>
        <StoreTestComponent onReady={(api) => (storeApi = api)} />
        <Header />
      </TestWrapper>
    );

    await waitFor(() => {
      expect(storeApi!).toBeDefined();
    });

    // Add 100 notifications (but store only keeps 50 due to MAX_NOTIFICATIONS)
    act(() => {
      for (let i = 0; i < 100; i++) {
        storeApi!.addNotification({
          type: 'info',
          title: `Notification ${i}`,
          message: `Message ${i}`,
        });
      }
    });

    // Verify badge shows 50 (max after eviction)
    await waitFor(() => {
      expect(screen.getByText('50')).toBeInTheDocument();
      expect(storeApi!.notifications).toHaveLength(50);
    });
  });
});

// ============================================================================
// End-to-End Flow Tests
// ============================================================================

describe('End-to-End Notification Flow', () => {
  it('import result toast creates viewable notification', async () => {
    const user = userEvent.setup();
    let hookApi: ReturnType<typeof useToastNotification>;

    render(
      <TestWrapper>
        <TestComponent onReady={(api) => (hookApi = api)} />
        <Header />
      </TestWrapper>
    );

    await waitFor(() => {
      expect(hookApi!).toBeDefined();
    });

    // Step 1: Call showImportResult
    act(() => {
      hookApi!.showImportResult({
        total_imported: 3,
        total_failed: 1,
        artifacts: [
          { name: 'skill-a', type: 'skill', success: true },
          { name: 'skill-b', type: 'skill', success: true },
          { name: 'skill-c', type: 'agent', success: true },
          { name: 'skill-d', type: 'command', success: false, error: 'Invalid format' },
        ],
      });
    });

    // Step 2: Verify toast appears
    expect(toast.warning).toHaveBeenCalled();

    // Step 3: Verify bell badge increments
    await waitFor(() => {
      expect(screen.getByText('1')).toBeInTheDocument();
    });

    // Step 4: Click bell to open dropdown
    const bellButton = screen.getByRole('button', { name: /Notifications, 1 unread/i });
    await user.click(bellButton);

    // Step 5: Verify notification visible in list
    await waitFor(() => {
      expect(screen.getByText('Import Complete')).toBeInTheDocument();
      expect(screen.getByText('Imported 3 of 4 artifact(s)')).toBeInTheDocument();
    });

    // Step 6: Expand notification
    const showDetailsButton = screen.getByRole('button', { name: /Show details/i });
    await user.click(showDetailsButton);

    // Step 7: Verify artifact details visible
    await waitFor(() => {
      expect(screen.getByText('skill-a')).toBeInTheDocument();
      expect(screen.getByText('skill-b')).toBeInTheDocument();
      expect(screen.getByText('skill-c')).toBeInTheDocument();
      expect(screen.getByText('skill-d')).toBeInTheDocument();
      expect(screen.getByText('Invalid format')).toBeInTheDocument();
      expect(screen.getByText('3 succeeded')).toBeInTheDocument();
      expect(screen.getByText('1 failed')).toBeInTheDocument();
    });
  });

  it('error notification flow works end-to-end', async () => {
    const user = userEvent.setup();
    let hookApi: ReturnType<typeof useToastNotification>;

    render(
      <TestWrapper>
        <TestComponent onReady={(api) => (hookApi = api)} />
        <Header />
      </TestWrapper>
    );

    await waitFor(() => {
      expect(hookApi!).toBeDefined();
    });

    // Step 1: Call showError
    const error = new Error('API connection timeout');
    act(() => {
      hookApi!.showError(error);
    });

    // Step 2: Verify bell shows notification
    await waitFor(() => {
      expect(screen.getByText('1')).toBeInTheDocument();
    });

    // Step 3: Open dropdown
    const bellButton = screen.getByRole('button', { name: /Notifications, 1 unread/i });
    await user.click(bellButton);

    // Step 4: Find error notification
    await waitFor(() => {
      expect(screen.getByText('Error')).toBeInTheDocument();
      expect(screen.getByText('API connection timeout')).toBeInTheDocument();
    });

    // Step 5: Expand error details
    const showDetailsButton = screen.getByRole('button', { name: /Show details/i });
    await user.click(showDetailsButton);

    // Step 6: Verify error details visible (there may be multiple matches, just check one exists)
    await waitFor(() => {
      expect(screen.getAllByText('API connection timeout').length).toBeGreaterThan(0);
    });
  });

  it('dismiss notification removes from list', async () => {
    const user = userEvent.setup();
    let storeApi: ReturnType<typeof useNotifications>;

    render(
      <TestWrapper>
        <StoreTestComponent onReady={(api) => (storeApi = api)} />
        <Header />
      </TestWrapper>
    );

    await waitFor(() => {
      expect(storeApi!).toBeDefined();
    });

    // Add notification
    act(() => {
      storeApi!.addNotification({
        type: 'info',
        title: 'Dismissible',
        message: 'This can be dismissed',
      });
    });

    await waitFor(() => {
      expect(storeApi!.notifications).toHaveLength(1);
    });

    // Open dropdown
    const bellButton = screen.getByRole('button', { name: /Notifications, 1 unread/i });
    await user.click(bellButton);

    // Find notification card
    const notification = await screen.findByText('Dismissible');
    const notificationCard = notification.closest('.px-4');

    // Find dismiss button (it has aria-label)
    const dismissButton = within(notificationCard!).getByRole('button', {
      name: /Dismiss notification/i,
    });
    await user.click(dismissButton);

    // Verify removed from list
    await waitFor(() => {
      expect(storeApi!.notifications).toHaveLength(0);
    });

    // Verify persisted to localStorage
    await new Promise((resolve) => setTimeout(resolve, 100));
    const stored = localStorage.getItem('skillmeat-notifications');
    const parsed = JSON.parse(stored!);
    expect(parsed).toHaveLength(0);
  });

  it('clear all removes all notifications', async () => {
    const user = userEvent.setup();
    let storeApi: ReturnType<typeof useNotifications>;

    render(
      <TestWrapper>
        <StoreTestComponent onReady={(api) => (storeApi = api)} />
        <Header />
      </TestWrapper>
    );

    await waitFor(() => {
      expect(storeApi!).toBeDefined();
    });

    // Add multiple notifications
    act(() => {
      storeApi!.addNotification({
        type: 'info',
        title: 'Notification 1',
        message: 'Message 1',
      });
      storeApi!.addNotification({
        type: 'info',
        title: 'Notification 2',
        message: 'Message 2',
      });
      storeApi!.addNotification({
        type: 'info',
        title: 'Notification 3',
        message: 'Message 3',
      });
    });

    await waitFor(() => {
      expect(storeApi!.notifications).toHaveLength(3);
    });

    // Open dropdown
    const bellButton = screen.getByRole('button', { name: /Notifications, 3 unread/i });
    await user.click(bellButton);

    // Click Clear All
    const clearAllButton = await screen.findByRole('button', { name: /Clear all/i });
    await user.click(clearAllButton);

    // Verify all removed
    await waitFor(() => {
      expect(storeApi!.notifications).toHaveLength(0);
    });

    // Verify empty state shown
    expect(screen.getByText('No notifications')).toBeInTheDocument();
    expect(
      screen.getByText("You'll see updates about imports, syncs, and errors here")
    ).toBeInTheDocument();
  });

  it('mark all as read updates all notification statuses', async () => {
    const user = userEvent.setup();
    let storeApi: ReturnType<typeof useNotifications>;

    render(
      <TestWrapper>
        <StoreTestComponent onReady={(api) => (storeApi = api)} />
        <Header />
      </TestWrapper>
    );

    await waitFor(() => {
      expect(storeApi!).toBeDefined();
    });

    // Add unread notifications
    act(() => {
      storeApi!.addNotification({
        type: 'info',
        title: 'Unread 1',
        message: 'Message 1',
      });
      storeApi!.addNotification({
        type: 'info',
        title: 'Unread 2',
        message: 'Message 2',
      });
    });

    await waitFor(() => {
      expect(storeApi!.unreadCount).toBe(2);
    });

    // Open dropdown
    const bellButton = screen.getByRole('button', { name: /Notifications, 2 unread/i });
    await user.click(bellButton);

    // Click Mark all read
    const markAllButton = await screen.findByRole('button', { name: /Mark all read/i });
    await user.click(markAllButton);

    // Verify all marked as read
    await waitFor(() => {
      expect(storeApi!.unreadCount).toBe(0);
      expect(storeApi!.notifications.every((n) => n.status === 'read')).toBe(true);
    });

    // Verify badge disappears
    await waitFor(() => {
      expect(screen.queryByText('2')).not.toBeInTheDocument();
    });
  });
});
