/**
 * @jest-environment jsdom
 */
import { renderHook, act } from '@testing-library/react';
import { useDebounce } from '@/hooks/use-debounce';

describe('useDebounce', () => {
  beforeEach(() => {
    jest.useFakeTimers();
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  it('returns initial value immediately', () => {
    const { result } = renderHook(() => useDebounce('initial', 300));

    expect(result.current).toBe('initial');
  });

  it('debounces value updates', () => {
    const { result, rerender } = renderHook(
      ({ value, delay }) => useDebounce(value, delay),
      { initialProps: { value: 'initial', delay: 300 } }
    );

    expect(result.current).toBe('initial');

    // Update the value
    rerender({ value: 'updated', delay: 300 });

    // Should still have old value immediately
    expect(result.current).toBe('initial');

    // Fast-forward time
    act(() => {
      jest.advanceTimersByTime(300);
    });

    // Now should have new value
    expect(result.current).toBe('updated');
  });

  it('resets timer on rapid updates', () => {
    const { result, rerender } = renderHook(
      ({ value }) => useDebounce(value, 300),
      { initialProps: { value: 'initial' } }
    );

    // Update multiple times rapidly
    rerender({ value: 'update1' });
    act(() => {
      jest.advanceTimersByTime(100);
    });

    rerender({ value: 'update2' });
    act(() => {
      jest.advanceTimersByTime(100);
    });

    rerender({ value: 'update3' });

    // Should still have initial value (timer keeps resetting)
    expect(result.current).toBe('initial');

    // Wait for final debounce
    act(() => {
      jest.advanceTimersByTime(300);
    });

    // Should have the final value
    expect(result.current).toBe('update3');
  });

  it('uses default delay of 300ms', () => {
    const { result, rerender } = renderHook(
      ({ value }) => useDebounce(value),
      { initialProps: { value: 'initial' } }
    );

    rerender({ value: 'updated' });

    // At 200ms, should still be old value
    act(() => {
      jest.advanceTimersByTime(200);
    });
    expect(result.current).toBe('initial');

    // At 300ms total, should be new value
    act(() => {
      jest.advanceTimersByTime(100);
    });
    expect(result.current).toBe('updated');
  });

  it('handles different delay values', () => {
    const { result, rerender } = renderHook(
      ({ value, delay }) => useDebounce(value, delay),
      { initialProps: { value: 'initial', delay: 500 } }
    );

    rerender({ value: 'updated', delay: 500 });

    // At 300ms, should still be old value
    act(() => {
      jest.advanceTimersByTime(300);
    });
    expect(result.current).toBe('initial');

    // At 500ms total, should be new value
    act(() => {
      jest.advanceTimersByTime(200);
    });
    expect(result.current).toBe('updated');
  });

  it('works with different types', () => {
    // Number
    const { result: numberResult, rerender: rerenderNumber } = renderHook(
      ({ value }) => useDebounce(value, 100),
      { initialProps: { value: 0 } }
    );

    rerenderNumber({ value: 42 });
    act(() => {
      jest.advanceTimersByTime(100);
    });
    expect(numberResult.current).toBe(42);

    // Object
    const { result: objectResult, rerender: rerenderObject } = renderHook(
      ({ value }) => useDebounce(value, 100),
      { initialProps: { value: { name: 'initial' } } }
    );

    rerenderObject({ value: { name: 'updated' } });
    act(() => {
      jest.advanceTimersByTime(100);
    });
    expect(objectResult.current).toEqual({ name: 'updated' });

    // Boolean
    const { result: boolResult, rerender: rerenderBool } = renderHook(
      ({ value }) => useDebounce(value, 100),
      { initialProps: { value: false } }
    );

    rerenderBool({ value: true });
    act(() => {
      jest.advanceTimersByTime(100);
    });
    expect(boolResult.current).toBe(true);
  });

  it('cleans up timer on unmount', () => {
    const clearTimeoutSpy = jest.spyOn(global, 'clearTimeout');

    const { unmount, rerender } = renderHook(
      ({ value }) => useDebounce(value, 300),
      { initialProps: { value: 'initial' } }
    );

    rerender({ value: 'updated' });

    // Unmount before timer completes
    unmount();

    // clearTimeout should have been called
    expect(clearTimeoutSpy).toHaveBeenCalled();

    clearTimeoutSpy.mockRestore();
  });

  it('handles null and undefined values', () => {
    const { result: nullResult, rerender: rerenderNull } = renderHook(
      ({ value }) => useDebounce<string | null>(value, 100),
      { initialProps: { value: 'initial' as string | null } }
    );

    rerenderNull({ value: null });
    act(() => {
      jest.advanceTimersByTime(100);
    });
    expect(nullResult.current).toBeNull();

    const { result: undefinedResult, rerender: rerenderUndefined } = renderHook(
      ({ value }) => useDebounce<string | undefined>(value, 100),
      { initialProps: { value: 'initial' as string | undefined } }
    );

    rerenderUndefined({ value: undefined });
    act(() => {
      jest.advanceTimersByTime(100);
    });
    expect(undefinedResult.current).toBeUndefined();
  });

  it('handles empty string', () => {
    const { result, rerender } = renderHook(
      ({ value }) => useDebounce(value, 100),
      { initialProps: { value: 'initial' } }
    );

    rerender({ value: '' });
    act(() => {
      jest.advanceTimersByTime(100);
    });
    expect(result.current).toBe('');
  });
});
