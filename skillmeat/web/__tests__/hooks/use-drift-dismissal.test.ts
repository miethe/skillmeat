/**
 * @jest-environment jsdom
 */
import { renderHook, act } from '@testing-library/react';
import { useDriftDismissal } from '@/hooks/use-drift-dismissal';
import type { ComparisonScope, DriftStatus } from '@/components/sync-status/drift-alert-banner';

// In-memory store for localStorage mock
let store: Record<string, string> = {};

// Track calls for assertions
let getItemCalls: string[] = [];
let setItemCalls: Array<{ key: string; value: string }> = [];
let removeItemCalls: string[] = [];

// Override localStorage with a working mock
const originalLocalStorage = Object.getOwnPropertyDescriptor(window, 'localStorage');

beforeAll(() => {
  Object.defineProperty(window, 'localStorage', {
    configurable: true,
    value: {
      getItem(key: string): string | null {
        getItemCalls.push(key);
        return store[key] ?? null;
      },
      setItem(key: string, value: string) {
        setItemCalls.push({ key, value });
        store[key] = value;
      },
      removeItem(key: string) {
        removeItemCalls.push(key);
        delete store[key];
      },
      clear() {
        store = {};
      },
      get length() {
        return Object.keys(store).length;
      },
      key(index: number) {
        return Object.keys(store)[index] ?? null;
      },
    },
  });
});

afterAll(() => {
  if (originalLocalStorage) {
    Object.defineProperty(window, 'localStorage', originalLocalStorage);
  }
});

describe('useDriftDismissal', () => {
  const defaultProps = {
    artifactId: 'test-artifact-123',
    scope: 'collection-vs-project' as ComparisonScope,
    driftStatus: 'modified' as DriftStatus,
  };

  beforeEach(() => {
    store = {};
    getItemCalls = [];
    setItemCalls = [];
    removeItemCalls = [];
  });

  it('returns isDismissed=false when no dismissal exists', () => {
    const { result } = renderHook(() => useDriftDismissal(defaultProps));

    expect(result.current.isDismissed).toBe(false);
    expect(typeof result.current.dismiss).toBe('function');
  });

  it('dismisses and persists to localStorage', () => {
    const { result } = renderHook(() => useDriftDismissal(defaultProps));

    act(() => {
      result.current.dismiss();
    });

    expect(result.current.isDismissed).toBe(true);

    // Verify localStorage was written
    const key = `skillmeat:drift-dismissed:${defaultProps.artifactId}:${defaultProps.scope}`;
    const written = setItemCalls.find((c) => c.key === key);
    expect(written).toBeDefined();
    expect(written!.value).toContain('"driftStatus":"modified"');
  });

  it('persists dismissal across re-renders (simulates page refresh)', () => {
    const key = `skillmeat:drift-dismissed:${defaultProps.artifactId}:${defaultProps.scope}`;

    // First render: dismiss
    const { result: result1, unmount } = renderHook(() => useDriftDismissal(defaultProps));

    act(() => {
      result1.current.dismiss();
    });
    expect(result1.current.isDismissed).toBe(true);
    unmount();

    // Second render: should still be dismissed (reads from localStorage)
    const { result: result2 } = renderHook(() => useDriftDismissal(defaultProps));
    expect(result2.current.isDismissed).toBe(true);

    // Verify it read from localStorage
    expect(getItemCalls).toContain(key);
  });

  it('expires after 24 hours', () => {
    const key = `skillmeat:drift-dismissed:${defaultProps.artifactId}:${defaultProps.scope}`;

    // Write a record that is 25 hours old
    const record = {
      driftStatus: 'modified',
      dismissedAt: Date.now() - 25 * 60 * 60 * 1000, // 25 hours ago
    };
    store[key] = JSON.stringify(record);

    const { result } = renderHook(() => useDriftDismissal(defaultProps));

    // Should NOT be dismissed because it expired
    expect(result.current.isDismissed).toBe(false);
    // Should have removed the expired entry
    expect(removeItemCalls).toContain(key);
  });

  it('does not expire before 24 hours', () => {
    const key = `skillmeat:drift-dismissed:${defaultProps.artifactId}:${defaultProps.scope}`;

    // Write a record that is 23 hours old
    const record = {
      driftStatus: 'modified',
      dismissedAt: Date.now() - 23 * 60 * 60 * 1000, // 23 hours ago
    };
    store[key] = JSON.stringify(record);

    const { result } = renderHook(() => useDriftDismissal(defaultProps));

    // Should still be dismissed
    expect(result.current.isDismissed).toBe(true);
  });

  it('clears dismissal when drift status changes', () => {
    const key = `skillmeat:drift-dismissed:${defaultProps.artifactId}:${defaultProps.scope}`;

    // First: dismiss with 'modified' status
    const { result, rerender } = renderHook((props) => useDriftDismissal(props), {
      initialProps: defaultProps,
    });

    act(() => {
      result.current.dismiss();
    });
    expect(result.current.isDismissed).toBe(true);

    // Change drift status to 'conflict'
    act(() => {
      rerender({ ...defaultProps, driftStatus: 'conflict' as DriftStatus });
    });

    // Should auto-clear because drift status changed
    expect(result.current.isDismissed).toBe(false);
    expect(removeItemCalls).toContain(key);
  });

  it('does not clear dismissal when drift status remains the same', () => {
    const { result, rerender } = renderHook((props) => useDriftDismissal(props), {
      initialProps: defaultProps,
    });

    act(() => {
      result.current.dismiss();
    });
    expect(result.current.isDismissed).toBe(true);

    // Rerender with same drift status
    act(() => {
      rerender({ ...defaultProps });
    });

    expect(result.current.isDismissed).toBe(true);
  });

  it('uses different keys for different scopes', () => {
    const scope1Props = { ...defaultProps, scope: 'collection-vs-project' as ComparisonScope };
    const scope2Props = { ...defaultProps, scope: 'source-vs-collection' as ComparisonScope };

    // Dismiss for scope 1
    const { result: result1 } = renderHook(() => useDriftDismissal(scope1Props));
    act(() => {
      result1.current.dismiss();
    });
    expect(result1.current.isDismissed).toBe(true);

    // Scope 2 should not be dismissed
    const { result: result2 } = renderHook(() => useDriftDismissal(scope2Props));
    expect(result2.current.isDismissed).toBe(false);
  });

  it('uses different keys for different artifacts', () => {
    const artifact1Props = { ...defaultProps, artifactId: 'artifact-1' };
    const artifact2Props = { ...defaultProps, artifactId: 'artifact-2' };

    // Dismiss for artifact 1
    const { result: result1 } = renderHook(() => useDriftDismissal(artifact1Props));
    act(() => {
      result1.current.dismiss();
    });
    expect(result1.current.isDismissed).toBe(true);

    // Artifact 2 should not be dismissed
    const { result: result2 } = renderHook(() => useDriftDismissal(artifact2Props));
    expect(result2.current.isDismissed).toBe(false);
  });

  it('handles invalid JSON in localStorage gracefully', () => {
    const key = `skillmeat:drift-dismissed:${defaultProps.artifactId}:${defaultProps.scope}`;
    store[key] = 'not-valid-json';

    const { result } = renderHook(() => useDriftDismissal(defaultProps));

    // Should fallback to not dismissed
    expect(result.current.isDismissed).toBe(false);
  });

  it('handles malformed record in localStorage gracefully', () => {
    const key = `skillmeat:drift-dismissed:${defaultProps.artifactId}:${defaultProps.scope}`;
    // Missing dismissedAt field
    store[key] = JSON.stringify({ driftStatus: 'modified' });

    const { result } = renderHook(() => useDriftDismissal(defaultProps));

    // Should fallback to not dismissed
    expect(result.current.isDismissed).toBe(false);
  });

  it('is SSR-safe when localStorage throws', () => {
    // Temporarily make localStorage throw (simulating unavailable storage)
    const savedGetItem = window.localStorage.getItem;
    const savedSetItem = window.localStorage.setItem;
    const savedRemoveItem = window.localStorage.removeItem;

    Object.defineProperty(window.localStorage, 'getItem', {
      configurable: true,
      value: () => {
        throw new Error('localStorage not available');
      },
    });
    Object.defineProperty(window.localStorage, 'setItem', {
      configurable: true,
      value: () => {
        throw new Error('localStorage not available');
      },
    });
    Object.defineProperty(window.localStorage, 'removeItem', {
      configurable: true,
      value: () => {
        throw new Error('localStorage not available');
      },
    });

    // Should not throw
    const { result } = renderHook(() => useDriftDismissal(defaultProps));
    expect(result.current.isDismissed).toBe(false);

    // Dismiss should not throw either
    act(() => {
      result.current.dismiss();
    });

    // Restore
    Object.defineProperty(window.localStorage, 'getItem', {
      configurable: true,
      value: savedGetItem,
    });
    Object.defineProperty(window.localStorage, 'setItem', {
      configurable: true,
      value: savedSetItem,
    });
    Object.defineProperty(window.localStorage, 'removeItem', {
      configurable: true,
      value: savedRemoveItem,
    });
  });

  it('handles "none" drift status correctly', () => {
    const noneProps = { ...defaultProps, driftStatus: 'none' as DriftStatus };

    const { result } = renderHook(() => useDriftDismissal(noneProps));

    // Can still dismiss even if status is 'none'
    act(() => {
      result.current.dismiss();
    });
    expect(result.current.isDismissed).toBe(true);
  });

  it('clears dismissal when status changes from dismissed value back to different status', () => {
    // Dismiss with 'modified'
    const { result, rerender } = renderHook((props) => useDriftDismissal(props), {
      initialProps: defaultProps,
    });

    act(() => {
      result.current.dismiss();
    });
    expect(result.current.isDismissed).toBe(true);

    // Change to 'outdated' - should clear
    act(() => {
      rerender({ ...defaultProps, driftStatus: 'outdated' as DriftStatus });
    });
    expect(result.current.isDismissed).toBe(false);

    // Dismiss again with 'outdated'
    act(() => {
      result.current.dismiss();
    });
    expect(result.current.isDismissed).toBe(true);

    // Change back to 'modified' - should clear again
    act(() => {
      rerender({ ...defaultProps, driftStatus: 'modified' as DriftStatus });
    });
    expect(result.current.isDismissed).toBe(false);
  });
});
