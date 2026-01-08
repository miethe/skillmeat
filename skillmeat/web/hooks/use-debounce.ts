/**
 * Custom debounce hook for React
 *
 * Delays updating a value until a specified time has passed without changes.
 * Useful for search inputs to reduce API calls.
 *
 * @example
 * ```tsx
 * const [query, setQuery] = useState('');
 * const debouncedQuery = useDebounce(query, 300);
 *
 * // Use debouncedQuery for API calls
 * useEffect(() => {
 *   if (debouncedQuery) {
 *     searchApi(debouncedQuery);
 *   }
 * }, [debouncedQuery]);
 * ```
 */

import { useState, useEffect } from 'react';

/**
 * Debounce a value by delaying updates until the specified delay has passed.
 *
 * @param value - The value to debounce
 * @param delay - Delay in milliseconds (default: 300ms)
 * @returns The debounced value
 */
export function useDebounce<T>(value: T, delay: number = 300): T {
  const [debouncedValue, setDebouncedValue] = useState<T>(value);

  useEffect(() => {
    // Set up a timer to update the debounced value
    const timer = setTimeout(() => {
      setDebouncedValue(value);
    }, delay);

    // Clean up the timer if value changes before delay expires
    return () => {
      clearTimeout(timer);
    };
  }, [value, delay]);

  return debouncedValue;
}
