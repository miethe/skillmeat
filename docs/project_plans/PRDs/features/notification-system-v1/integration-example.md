---
status: inferred_complete
---
# Notification System Integration Guide

**Feature**: Notification Center for SkillMeat
**Version**: 1.0
**Created**: 2025-12-03

---

## Quick Start

### 1. Install Dependencies

```bash
cd skillmeat/web
pnpm install
```

This will install `date-fns@^4.1.0` which was added to package.json.

### 2. Update Header Component

**File**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/web/components/header.tsx`

```tsx
import Link from 'next/link';
import { Package2 } from 'lucide-react';
import { NotificationBell, useNotifications } from '@/components/notifications/NotificationCenter';

export function Header() {
  const {
    notifications,
    unreadCount,
    markAsRead,
    markAllAsRead,
    clearAll,
    dismissNotification,
  } = useNotifications();

  return (
    <header className="sticky top-0 z-50 w-full border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="container flex h-14 items-center">
        <div className="mr-4 flex">
          <Link href="/" className="mr-6 flex items-center space-x-2">
            <Package2 className="h-6 w-6" />
            <span className="font-bold">SkillMeat</span>
          </Link>
        </div>
        <div className="flex flex-1 items-center justify-between space-x-2 md:justify-end">
          <nav className="flex items-center space-x-6 text-sm font-medium">
            <Link
              href="https://github.com/miethe/skillmeat"
              target="_blank"
              rel="noreferrer"
              className="text-foreground/60 transition-colors hover:text-foreground/80"
            >
              GitHub
            </Link>
            <Link
              href="https://github.com/miethe/skillmeat#readme"
              target="_blank"
              rel="noreferrer"
              className="text-foreground/60 transition-colors hover:text-foreground/80"
            >
              Documentation
            </Link>
          </nav>
          {/* Notification Bell */}
          <NotificationBell
            unreadCount={unreadCount}
            notifications={notifications}
            onMarkAllRead={markAllAsRead}
            onClearAll={clearAll}
            onNotificationClick={markAsRead}
            onDismiss={dismissNotification}
          />
        </div>
      </div>
    </header>
  );
}
```

### 3. Test with Mock Data

To verify the UI works correctly, add test notifications:

```tsx
'use client';

import { useEffect } from 'react';
import { useNotifications } from '@/components/notifications/NotificationCenter';

export function TestNotifications() {
  const { addNotification } = useNotifications();

  useEffect(() => {
    // Add a test import notification
    addNotification({
      type: 'import',
      title: 'Import Complete',
      message: '6 artifacts imported successfully',
      timestamp: new Date(),
      status: 'unread',
      details: {
        total: 8,
        succeeded: 6,
        failed: 2,
        artifacts: [
          { name: 'canvas-design', type: 'skill', success: true },
          { name: 'doc-writer', type: 'skill', success: true },
          { name: 'deploy', type: 'command', success: true },
          { name: 'code-reviewer', type: 'agent', success: true },
          { name: 'postgres-mcp', type: 'mcp', success: true },
          { name: 'pre-commit', type: 'hook', success: true },
          {
            name: 'broken-skill',
            type: 'skill',
            success: false,
            error: 'Invalid manifest format: missing required field "version"',
          },
          {
            name: 'missing-deps',
            type: 'command',
            success: false,
            error: 'Dependency not found: python-package==1.2.3',
          },
        ],
      },
    });

    // Add a sync notification
    setTimeout(() => {
      addNotification({
        type: 'sync',
        title: 'Sync Complete',
        message: 'All artifacts are up to date',
        timestamp: new Date(),
        status: 'unread',
      });
    }, 2000);

    // Add an error notification
    setTimeout(() => {
      addNotification({
        type: 'error',
        title: 'Connection Failed',
        message: 'Unable to connect to GitHub API',
        timestamp: new Date(),
        status: 'unread',
      });
    }, 4000);
  }, [addNotification]);

  return null;
}
```

Add to your layout or page:

```tsx
// In app/layout.tsx or app/page.tsx
import { TestNotifications } from '@/components/test-notifications';

export default function Layout({ children }) {
  return (
    <>
      <TestNotifications />
      {children}
    </>
  );
}
```

---

## Backend Integration

### Option 1: WebSocket (Real-time)

**Backend** (FastAPI):

```python
# skillmeat/api/websockets.py
from fastapi import WebSocket, WebSocketDisconnect
from typing import Dict, Set
import json

class NotificationManager:
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.add(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, notification: Dict):
        """Broadcast notification to all connected clients"""
        for connection in self.active_connections:
            try:
                await connection.send_json(notification)
            except Exception:
                # Handle disconnected clients
                self.active_connections.remove(connection)

    async def send_personal(self, websocket: WebSocket, notification: Dict):
        """Send notification to specific client"""
        await websocket.send_json(notification)

notification_manager = NotificationManager()

# Add to router
@router.websocket("/ws/notifications")
async def websocket_notifications(websocket: WebSocket):
    await notification_manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()  # Keep connection alive
    except WebSocketDisconnect:
        notification_manager.disconnect(websocket)

# Trigger from import operation
async def import_artifacts_batch(sources: List[str]):
    results = []
    for source in sources:
        try:
            result = await import_artifact(source)
            results.append(result)
        except Exception as e:
            results.append({'success': False, 'error': str(e)})

    # Send notification
    await notification_manager.broadcast({
        'type': 'import',
        'title': 'Import Complete',
        'message': f'{len([r for r in results if r["success"]])} artifacts imported',
        'timestamp': datetime.now().isoformat(),
        'status': 'unread',
        'details': {
            'total': len(results),
            'succeeded': len([r for r in results if r['success']]),
            'failed': len([r for r in results if not r['success']]),
            'artifacts': results,
        },
    })
```

**Frontend** (React Hook):

```tsx
// hooks/use-notification-websocket.ts
import { useEffect, useRef } from 'react';
import { useNotifications } from '@/components/notifications/NotificationCenter';

export function useNotificationWebSocket() {
  const { addNotification } = useNotifications();
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    const ws = new WebSocket('ws://localhost:8080/ws/notifications');

    ws.onopen = () => {
      console.log('Notification WebSocket connected');
    };

    ws.onmessage = (event) => {
      const notification = JSON.parse(event.data);
      addNotification({
        ...notification,
        timestamp: new Date(notification.timestamp),
      });
    };

    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
    };

    ws.onclose = () => {
      console.log('Notification WebSocket disconnected');
    };

    wsRef.current = ws;

    return () => {
      ws.close();
    };
  }, [addNotification]);

  return wsRef.current;
}
```

**Usage**:

```tsx
// components/providers.tsx
'use client';

import { useNotificationWebSocket } from '@/hooks/use-notification-websocket';

export function NotificationProvider({ children }: { children: React.ReactNode }) {
  useNotificationWebSocket();
  return <>{children}</>;
}

// Wrap in app/layout.tsx
<Providers>
  <NotificationProvider>
    {children}
  </NotificationProvider>
</Providers>
```

### Option 2: Server-Sent Events (Simpler)

**Backend**:

```python
# skillmeat/api/routers/notifications.py
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
import asyncio
import json

router = APIRouter()

@router.get("/stream")
async def stream_notifications():
    async def event_generator():
        while True:
            # Poll for new notifications or wait for events
            notification = await get_next_notification()
            if notification:
                yield f"data: {json.dumps(notification)}\n\n"
            await asyncio.sleep(1)  # Adjust polling interval

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )
```

**Frontend**:

```tsx
// hooks/use-notification-sse.ts
import { useEffect } from 'react';
import { useNotifications } from '@/components/notifications/NotificationCenter';

export function useNotificationSSE() {
  const { addNotification } = useNotifications();

  useEffect(() => {
    const eventSource = new EventSource('http://localhost:8080/api/v1/notifications/stream');

    eventSource.onmessage = (event) => {
      const notification = JSON.parse(event.data);
      addNotification({
        ...notification,
        timestamp: new Date(notification.timestamp),
      });
    };

    eventSource.onerror = (error) => {
      console.error('SSE error:', error);
      eventSource.close();
    };

    return () => {
      eventSource.close();
    };
  }, [addNotification]);
}
```

### Option 3: Polling (Simplest)

**Backend**:

```python
# skillmeat/api/routers/notifications.py
from typing import List
from pydantic import BaseModel

class NotificationResponse(BaseModel):
    id: str
    type: str
    title: str
    message: str
    timestamp: datetime
    status: str
    details: Optional[Dict] = None

@router.get("/notifications", response_model=List[NotificationResponse])
async def get_notifications(
    since: Optional[datetime] = None,
    limit: int = 50,
):
    """Get recent notifications"""
    # Fetch from database or in-memory store
    notifications = await db.get_notifications(since=since, limit=limit)
    return notifications
```

**Frontend**:

```tsx
// hooks/use-notification-polling.ts
import { useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useNotifications } from '@/components/notifications/NotificationCenter';

export function useNotificationPolling(interval: number = 10000) {
  const { notifications, addNotification } = useNotifications();
  const lastTimestamp = notifications[0]?.timestamp;

  const { data } = useQuery({
    queryKey: ['notifications', lastTimestamp],
    queryFn: async () => {
      const params = new URLSearchParams();
      if (lastTimestamp) {
        params.append('since', lastTimestamp.toISOString());
      }
      const res = await fetch(`/api/v1/notifications?${params}`);
      return res.json();
    },
    refetchInterval: interval,
  });

  useEffect(() => {
    if (data) {
      data.forEach((notification: any) => {
        addNotification({
          ...notification,
          timestamp: new Date(notification.timestamp),
        });
      });
    }
  }, [data, addNotification]);
}
```

---

## Persistence (Optional)

Store notifications in localStorage to persist across sessions:

```tsx
// hooks/use-notifications.ts (enhanced)
export function useNotifications() {
  const [notifications, setNotifications] = useState<NotificationData[]>(() => {
    // Load from localStorage on mount
    if (typeof window !== 'undefined') {
      const stored = localStorage.getItem('skillmeat_notifications');
      if (stored) {
        try {
          const parsed = JSON.parse(stored);
          return parsed.map((n: any) => ({
            ...n,
            timestamp: new Date(n.timestamp),
          }));
        } catch {
          return [];
        }
      }
    }
    return [];
  });

  // Save to localStorage on change
  useEffect(() => {
    if (typeof window !== 'undefined') {
      localStorage.setItem('skillmeat_notifications', JSON.stringify(notifications));
    }
  }, [notifications]);

  // ... rest of hook implementation
}
```

---

## Testing

### Unit Tests

```tsx
// __tests__/components/notifications/NotificationCenter.test.tsx
import { render, screen, fireEvent } from '@testing-library/react';
import { NotificationBell, useNotifications } from '@/components/notifications/NotificationCenter';

describe('NotificationBell', () => {
  it('shows badge with unread count', () => {
    const { rerender } = render(
      <NotificationBell
        unreadCount={3}
        notifications={[]}
        onMarkAllRead={() => {}}
        onClearAll={() => {}}
        onNotificationClick={() => {}}
        onDismiss={() => {}}
      />
    );

    expect(screen.getByText('3')).toBeInTheDocument();
  });

  it('hides badge when no unread notifications', () => {
    render(
      <NotificationBell
        unreadCount={0}
        notifications={[]}
        onMarkAllRead={() => {}}
        onClearAll={() => {}}
        onNotificationClick={() => {}}
        onDismiss={() => {}}
      />
    );

    expect(screen.queryByText('0')).not.toBeInTheDocument();
  });

  it('opens dropdown on click', async () => {
    render(
      <NotificationBell
        unreadCount={1}
        notifications={[
          {
            id: '1',
            type: 'import',
            title: 'Test Notification',
            message: 'Test message',
            timestamp: new Date(),
            status: 'unread',
          },
        ]}
        onMarkAllRead={() => {}}
        onClearAll={() => {}}
        onNotificationClick={() => {}}
        onDismiss={() => {}}
      />
    );

    fireEvent.click(screen.getByRole('button'));
    expect(await screen.findByText('Test Notification')).toBeInTheDocument();
  });
});
```

### E2E Tests

```tsx
// tests/notifications.spec.ts
import { test, expect } from '@playwright/test';

test.describe('Notification System', () => {
  test('displays notification bell in header', async ({ page }) => {
    await page.goto('/');
    const bell = page.getByRole('button', { name: /notifications/i });
    await expect(bell).toBeVisible();
  });

  test('shows unread badge when notifications exist', async ({ page }) => {
    await page.goto('/');
    // Trigger notification via API or action
    await page.evaluate(() => {
      window.dispatchEvent(
        new CustomEvent('notification', {
          detail: {
            type: 'import',
            title: 'Test',
            message: 'Test message',
          },
        })
      );
    });

    const badge = page.locator('[role="button"] .badge');
    await expect(badge).toBeVisible();
    await expect(badge).toContainText('1');
  });

  test('opens dropdown and displays notifications', async ({ page }) => {
    await page.goto('/');
    const bell = page.getByRole('button', { name: /notifications/i });
    await bell.click();

    const dropdown = page.getByRole('dialog'); // or appropriate role
    await expect(dropdown).toBeVisible();
    await expect(dropdown).toContainText('Notifications');
  });

  test('marks notification as read on click', async ({ page }) => {
    // ... test implementation
  });

  test('clears all notifications', async ({ page }) => {
    // ... test implementation
  });
});
```

---

## Accessibility Checklist

- [x] Bell button has descriptive `aria-label`
- [x] Badge count announced to screen readers
- [x] Dropdown keyboard navigable (Tab, Arrow keys, Escape)
- [x] Focus management (trap, return to trigger)
- [x] Notification items have proper roles
- [x] Dismiss buttons have `aria-label`
- [x] Relative timestamps are accessible
- [x] Color not sole indicator (icons + text)
- [x] Sufficient color contrast (WCAG AA)

---

## Performance Considerations

1. **Virtualized List**: For 100+ notifications, use `react-window`:
   ```tsx
   import { FixedSizeList } from 'react-window';

   <FixedSizeList
     height={500}
     itemCount={notifications.length}
     itemSize={80}
   >
     {({ index, style }) => (
       <NotificationItem
         notification={notifications[index]}
         style={style}
       />
     )}
   </FixedSizeList>
   ```

2. **Debounce Rapid Notifications**:
   ```tsx
   const addNotification = useMemo(
     () => debounce((notification) => {
       setNotifications(prev => [notification, ...prev]);
     }, 100),
     []
   );
   ```

3. **Lazy Load Details**:
   - Fetch import details only when user expands
   - Cache expanded state

---

## Next Steps

1. **Install dependency**: `pnpm install` in `skillmeat/web`
2. **Update header**: Add NotificationBell to header component
3. **Choose integration**: WebSocket, SSE, or polling
4. **Test UI**: Use mock data to verify appearance
5. **Connect backend**: Implement notification endpoints
6. **Add persistence**: localStorage for cross-session notifications
7. **Monitor performance**: Ensure smooth with 50+ notifications

---

## Files Created

1. **Component**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/web/components/notifications/NotificationCenter.tsx`
2. **Design Doc**: `/Users/miethe/dev/homelab/development/skillmeat/docs/project_plans/PRDs/features/notification-system-v1/ui-design.md`
3. **Integration Guide**: `/Users/miethe/dev/homelab/development/skillmeat/docs/project_plans/PRDs/features/notification-system-v1/integration-example.md`
4. **Updated**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/web/package.json` (added date-fns)

---

**Ready for integration!** The notification system is fully designed and implemented, awaiting backend connection.
