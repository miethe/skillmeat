---
title: "Notification System Developer Guide"
description: "Technical documentation for integrating with SkillMeat's notification system"
audience: "developers"
tags: ["notifications", "api", "frontend", "react", "hooks"]
created: "2025-12-04"
updated: "2025-12-04"
category: "API Documentation"
status: "published"
related_documents: []
---

# Notification System Developer Guide

The SkillMeat notification system provides a persistent, read-state-aware notification center with localStorage persistence, smart memory management, and seamless toast integration.

## Table of Contents

- [Architecture Overview](#architecture-overview)
- [API Reference](#api-reference)
- [Integration Guide](#integration-guide)
- [Testing](#testing)
- [Best Practices](#best-practices)
- [File Locations](#file-locations)

## Architecture Overview

The notification system consists of layered components designed for reliability and performance:

```
┌─────────────────────────────────────────────────────────────┐
│ Components (NotificationBell, NotificationCenter)           │
│ - UI rendering                                               │
│ - User interactions                                           │
│ - Accessibility features (ARIA, keyboard nav)                │
└────────────────────┬────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────────┐
│ useNotifications Hook                                        │
│ - State management interface                                 │
│ - Action creators                                            │
│ - Direct API to store                                        │
└────────────────────┬────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────────┐
│ NotificationProvider (React Context)                        │
│ - Central state management                                   │
│ - Event handlers                                             │
│ - localStorage sync                                          │
└────────────────────┬────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────────┐
│ localStorage (skillmeat-notifications)                       │
│ - Persistent storage                                         │
│ - Cross-tab sync                                             │
│ - Max 50 notifications (smart eviction)                      │
└─────────────────────────────────────────────────────────────┘
```

### Data Flow

1. **Component triggers action**: `addNotification()`, `markAsRead()`, etc.
2. **Context updates**: State changes propagate through React
3. **localStorage persisted**: New state automatically saved
4. **Components re-render**: UI updates reflect new state
5. **Accessibility announced**: Screen readers notified of changes

### Key Features

- **Persistence**: Notifications survive page refreshes
- **Memory Management**: Smart FIFO eviction prioritizes unread notifications
- **Screen Reader Support**: ARIA live regions announce new notifications
- **Keyboard Navigation**: Full keyboard support with arrow keys and Home/End
- **Type Safety**: Full TypeScript support with discriminated unions
- **SSR Safe**: Handles server-side rendering without errors

## API Reference

### Types

#### `NotificationType`

The type of notification event.

```typescript
type NotificationType = 'import' | 'sync' | 'error' | 'info' | 'success';
```

#### `NotificationStatus`

The read/unread status of a notification.

```typescript
type NotificationStatus = 'read' | 'unread';
```

#### `NotificationData`

Complete notification structure (auto-generated fields included).

```typescript
interface NotificationData {
  id: string;                    // Auto-generated unique ID
  type: NotificationType;        // Type of notification
  title: string;                 // Short title (30-50 chars recommended)
  message: string;               // Descriptive message (under 100 chars)
  timestamp: Date;               // When notification was created
  status: NotificationStatus;    // Read or unread
  details?: NotificationDetails; // Optional type-specific details
}
```

#### `NotificationCreateInput`

Input type for creating notifications (without auto-generated fields).

```typescript
interface NotificationCreateInput {
  type: NotificationType;
  title: string;
  message: string;
  status?: NotificationStatus;              // Defaults to 'unread'
  details?: NotificationDetails | null;     // Optional
}
```

#### `ImportResultDetails`

Details for import/sync operations.

```typescript
interface ImportResultDetails {
  total: number;                 // Total artifacts in batch
  succeeded: number;             // Successful imports
  failed: number;                // Failed imports
  artifacts: Array<{
    name: string;
    type: ArtifactType;
    success: boolean;
    error?: string;              // Error message if failed
  }>;
}
```

#### `ErrorDetails`

Details for error notifications.

```typescript
interface ErrorDetails {
  code?: string;                 // Error code (e.g., 'NETWORK_ERROR')
  message: string;               // Error message
  stack?: string;                // Stack trace
  retryable?: boolean;           // Whether operation can be retried
}
```

#### `GenericDetails`

Details for info/success/warning notifications.

```typescript
interface GenericDetails {
  metadata?: Record<string, string | number | boolean>;
}
```

### `useNotifications` Hook

Access the notification store from any component.

```typescript
import { useNotifications } from '@/lib/notification-store';

function MyComponent() {
  const {
    // State
    notifications,      // NotificationData[] (newest first)
    unreadCount,        // number

    // Actions
    addNotification,    // (input: NotificationCreateInput) => void
    markAsRead,         // (id: string) => void
    markAllAsRead,      // () => void
    dismissNotification,// (id: string) => void
    clearAll,           // () => void
  } = useNotifications();
}
```

**Throws**: Error if used outside `NotificationProvider`

### `NotificationProvider`

Root provider component (already configured in `components/providers.tsx`).

```typescript
import { NotificationProvider } from '@/lib/notification-store';

export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <NotificationProvider>
      {children}
    </NotificationProvider>
  );
}
```

### `useToastNotification` Hook

Combines toast notifications with persistent notifications.

```typescript
import { useToastNotification } from '@/hooks/use-toast-notification';

function MyComponent() {
  const {
    showSuccess,       // (message: string, description?: string) => void
    showWarning,       // (message: string, description?: string) => void
    showError,         // (error: unknown, fallbackMessage?: string) => void
    showImportResult,  // (result: ImportResultWithDetails) => void
  } = useToastNotification();
}
```

## Integration Guide

### Basic Setup

The notification provider is already configured. Simply use the hook in any component:

```typescript
'use client';

import { useNotifications } from '@/lib/notification-store';

export function MyComponent() {
  const { addNotification, notifications } = useNotifications();

  const handleAction = () => {
    addNotification({
      type: 'success',
      title: 'Action Complete',
      message: 'Your action was successful.',
    });
  };

  return (
    <div>
      <button onClick={handleAction}>Perform Action</button>
      <p>Total notifications: {notifications.length}</p>
    </div>
  );
}
```

### Adding Notifications from API Calls

Integrate with React Query mutations:

```typescript
'use client';

import { useMutation } from '@tanstack/react-query';
import { useNotifications } from '@/lib/notification-store';

function useImportArtifacts() {
  const { addNotification } = useNotifications();

  return useMutation({
    mutationFn: importArtifactsAPI,
    onSuccess: (result) => {
      addNotification({
        type: 'import',
        title: 'Import Complete',
        message: `${result.succeeded} of ${result.total} artifacts imported`,
        details: {
          total: result.total,
          succeeded: result.succeeded,
          failed: result.failed,
          artifacts: result.artifacts,
        },
      });
    },
    onError: (error) => {
      addNotification({
        type: 'error',
        title: 'Import Failed',
        message: error instanceof Error ? error.message : 'Unknown error',
        details: {
          code: error instanceof Error ? undefined : 'UNKNOWN',
          message: error instanceof Error ? error.message : String(error),
          retryable: true,
        },
      });
    },
  });
}

export function ArtifactImporter() {
  const importMutation = useImportArtifacts();

  return (
    <button
      onClick={() => importMutation.mutate([])}
      disabled={importMutation.isPending}
    >
      Import Artifacts
    </button>
  );
}
```

### Using Toast Utils

For transient messages (toasts) that also create persistent notifications:

```typescript
'use client';

import { useToastNotification } from '@/hooks/use-toast-notification';
import { useMutation } from '@tanstack/react-query';

export function DataComponent() {
  const { showError, showImportResult, showSuccess } = useToastNotification();

  const syncMutation = useMutation({
    mutationFn: syncData,
    onSuccess: (result) => {
      // Show toast AND create persistent notification
      showImportResult({
        total_imported: result.succeeded,
        total_failed: result.failed,
        artifacts: result.artifacts,
      });
    },
    onError: (error) => {
      // Show toast AND create persistent error notification
      showError(error, 'Sync failed');
    },
  });

  return (
    <button onClick={() => syncMutation.mutate()}>
      Sync Data
    </button>
  );
}
```

### Reading Notifications in Real-Time

Monitor notification changes:

```typescript
'use client';

import { useNotifications } from '@/lib/notification-store';
import { useEffect } from 'react';

export function NotificationLogger() {
  const { notifications, unreadCount } = useNotifications();

  useEffect(() => {
    console.log(`Notifications changed: ${unreadCount} unread`);
  }, [unreadCount]);

  return (
    <div>
      <h2>Total: {notifications.length}</h2>
      <h3>Unread: {unreadCount}</h3>
      <ul>
        {notifications.map((n) => (
          <li key={n.id}>
            [{n.status}] {n.title} - {n.message}
          </li>
        ))}
      </ul>
    </div>
  );
}
```

### Handling Different Notification Types

```typescript
'use client';

import { useNotifications } from '@/lib/notification-store';

export function NotificationDispatcher() {
  const { addNotification } = useNotifications();

  const handleImport = (result: ImportResult) => {
    addNotification({
      type: 'import',
      title: 'Artifacts Imported',
      message: `${result.count} artifacts added to collection`,
      details: {
        total: result.count,
        succeeded: result.count,
        failed: 0,
        artifacts: result.artifacts,
      },
    });
  };

  const handleSync = (status: 'complete' | 'failed') => {
    addNotification({
      type: 'sync',
      title: status === 'complete' ? 'Sync Complete' : 'Sync Failed',
      message: status === 'complete'
        ? 'Collection synchronized with upstream'
        : 'Failed to sync with upstream repository',
    });
  };

  const handleError = (error: Error) => {
    addNotification({
      type: 'error',
      title: 'Operation Failed',
      message: error.message,
      details: {
        code: 'OPERATION_ERROR',
        message: error.message,
        stack: error.stack,
        retryable: true,
      },
    });
  };

  const handleInfo = (message: string) => {
    addNotification({
      type: 'info',
      title: 'Information',
      message,
    });
  };

  const handleSuccess = (message: string) => {
    addNotification({
      type: 'success',
      title: 'Success',
      message,
    });
  };

  return null;
}
```

## Testing

### Testing Components with Notifications

Setup helper for tests:

```typescript
// __tests__/utils/notification-test-utils.ts
import { render, RenderOptions } from '@testing-library/react';
import { NotificationProvider } from '@/lib/notification-store';
import React from 'react';

function AllTheProviders({ children }: { children: React.ReactNode }) {
  return (
    <NotificationProvider>
      {children}
    </NotificationProvider>
  );
}

type CustomRenderOptions = Omit<RenderOptions, 'wrapper'>;

export function renderWithNotifications(
  ui: React.ReactElement,
  options?: CustomRenderOptions
) {
  return render(ui, { wrapper: AllTheProviders, ...options });
}

export * from '@testing-library/react';
```

Example test:

```typescript
// __tests__/components/my-component.test.tsx
import { renderWithNotifications, screen } from '@/__tests__/utils/notification-test-utils';
import { MyComponent } from '@/components/my-component';

describe('MyComponent with Notifications', () => {
  it('creates notification on action', async () => {
    const { getByRole } = renderWithNotifications(<MyComponent />);
    const button = getByRole('button', { name: /perform action/i });

    fireEvent.click(button);

    await waitFor(() => {
      // Note: Check notification center or the hook value
      expect(screen.getByText('Success')).toBeInTheDocument();
    });
  });
});
```

### Mocking useNotifications

Mock the hook for isolated component tests:

```typescript
// __tests__/components/component-with-notifications.test.tsx
import { useNotifications } from '@/lib/notification-store';

jest.mock('@/lib/notification-store', () => ({
  useNotifications: jest.fn(),
}));

describe('ComponentWithNotifications', () => {
  beforeEach(() => {
    (useNotifications as jest.Mock).mockReturnValue({
      notifications: [],
      unreadCount: 0,
      addNotification: jest.fn(),
      markAsRead: jest.fn(),
      markAllAsRead: jest.fn(),
      dismissNotification: jest.fn(),
      clearAll: jest.fn(),
    });
  });

  it('calls addNotification on button click', () => {
    const addNotificationMock = jest.fn();
    (useNotifications as jest.Mock).mockReturnValue({
      notifications: [],
      unreadCount: 0,
      addNotification: addNotificationMock,
      markAsRead: jest.fn(),
      markAllAsRead: jest.fn(),
      dismissNotification: jest.fn(),
      clearAll: jest.fn(),
    });

    render(<MyComponent />);
    fireEvent.click(screen.getByRole('button'));

    expect(addNotificationMock).toHaveBeenCalledWith(
      expect.objectContaining({
        type: 'success',
        title: 'Success',
      })
    );
  });
});
```

### Testing useNotifications Hook Directly

```typescript
// __tests__/lib/notification-store.test.tsx
import { renderHook, act } from '@testing-library/react';
import { NotificationProvider, useNotifications } from '@/lib/notification-store';

const wrapper = ({ children }: { children: React.ReactNode }) => (
  <NotificationProvider>{children}</NotificationProvider>
);

describe('useNotifications', () => {
  it('adds notification with generated id', () => {
    const { result } = renderHook(() => useNotifications(), { wrapper });

    act(() => {
      result.current.addNotification({
        type: 'info',
        title: 'Test',
        message: 'Test message',
      });
    });

    expect(result.current.notifications).toHaveLength(1);
    expect(result.current.notifications[0].id).toMatch(/^\d+-[a-z0-9]+$/);
  });

  it('marks notification as read', () => {
    const { result } = renderHook(() => useNotifications(), { wrapper });

    act(() => {
      result.current.addNotification({
        type: 'info',
        title: 'Test',
        message: 'Test message',
      });
    });

    const id = result.current.notifications[0].id;

    act(() => {
      result.current.markAsRead(id);
    });

    expect(result.current.notifications[0].status).toBe('read');
    expect(result.current.unreadCount).toBe(0);
  });

  it('prioritizes keeping unread notifications on eviction', () => {
    const { result } = renderHook(() => useNotifications(), { wrapper });

    act(() => {
      // Add 50 unread notifications
      for (let i = 0; i < 50; i++) {
        result.current.addNotification({
          type: 'info',
          title: `Unread ${i}`,
          message: 'Message',
        });
      }

      // Mark some as read
      result.current.markAsRead(result.current.notifications[40].id);
      result.current.markAsRead(result.current.notifications[39].id);

      // Add one more to trigger eviction
      result.current.addNotification({
        type: 'info',
        title: 'Trigger eviction',
        message: 'Message',
      });
    });

    // Should still have 50
    expect(result.current.notifications).toHaveLength(50);

    // The two read notifications should be evicted, not unread ones
    expect(
      result.current.notifications.every((n) => n.status === 'unread')
    ).toBe(true);
  });
});
```

## Best Practices

### 1. Use Appropriate Notification Types

Match the semantic meaning to notification type:

```typescript
// Good: Type matches semantic meaning
addNotification({
  type: 'import',
  title: 'Import Complete',
  message: '5 artifacts imported',
});

addNotification({
  type: 'error',
  title: 'Operation Failed',
  message: 'Failed to sync collection',
});

// Avoid: Using wrong type
addNotification({
  type: 'info',  // Bad: Should be 'error' for failures
  title: 'Operation Failed',
  message: 'Failed to sync collection',
});
```

### 2. Keep Messages Concise

Keep messages under 100 characters:

```typescript
// Good: Concise, actionable
addNotification({
  type: 'success',
  title: 'Deployed',
  message: '3 artifacts deployed to project',
});

// Avoid: Too verbose
addNotification({
  type: 'success',
  title: 'Deployment Complete',
  message: 'Your artifacts have been successfully deployed to the project. The deployment took 5 seconds.',
});
```

### 3. Include Actionable Details

Provide context in details when relevant:

```typescript
// Good: Includes artifact details for review
addNotification({
  type: 'import',
  title: 'Import Complete',
  message: '3 of 5 artifacts imported',
  details: {
    total: 5,
    succeeded: 3,
    failed: 2,
    artifacts: [
      { name: 'skill-1', type: 'skill', success: true },
      { name: 'skill-2', type: 'skill', success: true },
      { name: 'skill-3', type: 'skill', success: true },
      { name: 'agent-1', type: 'agent', success: false, error: 'Already exists' },
      { name: 'command-1', type: 'command', success: false, error: 'Invalid schema' },
    ],
  },
});

// Avoid: No details for failed operations
addNotification({
  type: 'error',
  title: 'Import Failed',
  message: 'Failed to import artifacts',
  // Details missing - user can't see which ones failed
});
```

### 4. Check Before Adding Duplicates

Avoid duplicate notifications:

```typescript
const { notifications, addNotification } = useNotifications();

const handleSync = () => {
  // Check if sync is already in progress
  const syncInProgress = notifications.some(
    (n) => n.type === 'sync' && n.status === 'unread'
  );

  if (!syncInProgress) {
    addNotification({
      type: 'sync',
      title: 'Syncing...',
      message: 'Collection sync in progress',
    });
  }
};
```

### 5. Use toast-utils for Related Messages

Combine toasts with notifications:

```typescript
'use client';

import { useToastNotification } from '@/hooks/use-toast-notification';

export function DataSync() {
  const { showError, showImportResult } = useToastNotification();

  const handleSync = async () => {
    try {
      const result = await syncCollection();

      // Shows transient toast AND persistent notification
      showImportResult({
        total_imported: result.succeeded,
        total_failed: result.failed,
        artifacts: result.artifacts,
      });
    } catch (error) {
      // Shows transient toast AND persistent error notification
      showError(error, 'Sync failed');
    }
  };

  return <button onClick={handleSync}>Sync</button>;
}
```

### 6. Test with Screen Readers

Verify announcements work for accessibility:

```typescript
// Component automatically announces with aria-live="polite"
// Test with screen readers or aria-live testing utilities
it('announces new notifications to screen readers', async () => {
  const { getByRole } = renderWithNotifications(<MyComponent />);

  act(() => {
    // Trigger notification
  });

  // NotificationAnnouncer announces: "New import notification: Import Complete"
  expect(getByRole('status')).toHaveTextContent('Import Complete');
});
```

## File Locations

### Source Files

| File | Purpose |
|------|---------|
| `skillmeat/web/types/notification.ts` | Type definitions |
| `skillmeat/web/lib/notification-store.tsx` | NotificationProvider + useNotifications hook |
| `skillmeat/web/lib/toast-utils.ts` | Toast integration utilities |
| `skillmeat/web/hooks/use-toast-notification.ts` | useToastNotification hook |
| `skillmeat/web/components/notifications/NotificationCenter.tsx` | UI components (Bell, Dropdown, Item) |

### Test Files

| File | Purpose |
|------|---------|
| `skillmeat/web/__tests__/lib/notification-store.test.tsx` | Store and hook tests |
| `skillmeat/web/__tests__/integration/notification-integration.test.tsx` | Integration tests |

### Storage

- **Key**: `skillmeat-notifications`
- **Location**: Browser localStorage
- **Max Size**: 50 notifications (smart FIFO eviction)
- **Persistence**: Cross-tab, survives page refresh

## Constants

```typescript
// Maximum number of notifications stored
const MAX_NOTIFICATIONS = 50;

// localStorage key
const STORAGE_KEY = 'skillmeat-notifications';

// Notification ID format
// timestamp-randomhash (e.g., "1701700000000-a1b2c3d4")
```

## Common Patterns

### Pattern: Async Operation with Progress

```typescript
const handleLongOperation = async () => {
  const { addNotification, dismissNotification } = useNotifications();

  // Create "in progress" notification
  const notificationId = generateId(); // You'll need to extract this from the returned value

  const notif = await new Promise<NotificationData>((resolve) => {
    addNotification({
      type: 'info',
      title: 'Processing...',
      message: 'Operation in progress',
    });
    // Note: You'll need to track the created notification somehow
  });

  try {
    const result = await longRunningOperation();

    // Replace with success
    dismissNotification(notif.id);
    addNotification({
      type: 'success',
      title: 'Complete',
      message: 'Operation completed successfully',
    });
  } catch (error) {
    dismissNotification(notif.id);
    addNotification({
      type: 'error',
      title: 'Failed',
      message: 'Operation failed',
    });
  }
};
```

### Pattern: Batch Operations with Summary

```typescript
const handleBatchImport = async (artifacts: Artifact[]) => {
  const { addNotification } = useNotifications();
  const results: ArtifactImportResult[] = [];
  let succeeded = 0;
  let failed = 0;

  for (const artifact of artifacts) {
    try {
      await importArtifact(artifact);
      results.push({
        name: artifact.name,
        type: artifact.type,
        success: true,
      });
      succeeded++;
    } catch (error) {
      results.push({
        name: artifact.name,
        type: artifact.type,
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error',
      });
      failed++;
    }
  }

  addNotification({
    type: failed > 0 ? 'error' : 'success',
    title: 'Import Complete',
    message: `${succeeded} of ${artifacts.length} artifacts imported`,
    details: {
      total: artifacts.length,
      succeeded,
      failed,
      artifacts: results,
    },
  });
};
```

## Troubleshooting

### Notifications Not Persisting

**Problem**: Notifications disappear after page refresh

**Solutions**:
1. Check localStorage quota (use DevTools → Application → Storage)
2. Verify QuotaExceededError not logged in console
3. Clear localStorage and try again: `localStorage.clear()`
4. Check browser allows localStorage for your domain

### useNotifications Hook Error

**Problem**: "useNotifications must be used within a NotificationProvider"

**Solutions**:
1. Ensure component is wrapped in `<NotificationProvider>`
2. Check it's not a server component (add `'use client'`)
3. Verify providers are properly configured in `components/providers.tsx`

### Notifications Not Announcing to Screen Readers

**Problem**: Screen readers don't announce new notifications

**Solutions**:
1. Verify `NotificationAnnouncer` component is rendered
2. Use screen reader test mode in DevTools
3. Check aria-live="polite" is present
4. Verify announcement text has content

### Memory Management Issues

**Problem**: Notifications exceeding 50 limit

**Solution**: Smart eviction automatically handles this:
- Read notifications evicted first (FIFO)
- Unread notifications preserved
- If all unread, oldest evicted
- Monitor `unreadCount` to see retention
